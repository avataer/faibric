"""
Library-First Pipeline - Enforces checking library before generating new code.

This is the "Hidden Factory" - customers never see these operations.
They only see friendly messages in the chat.
"""
import logging
import json
import re
from typing import Optional, Dict, List, Tuple
from django.conf import settings

from . import constants
from .metrics import ReuseMetrics, DuplicateDetector

logger = logging.getLogger(__name__)

# Cache for column check
_has_is_approved = None

def _check_has_is_approved_column():
    """Check if is_approved column exists."""
    global _has_is_approved
    if _has_is_approved is None:
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'code_library_libraryitem' AND column_name = 'is_approved'
                """)
                _has_is_approved = cursor.fetchone() is not None
        except Exception:
            _has_is_approved = False
    return _has_is_approved


class CustomerMessenger:
    """
    Sends customer-friendly messages while hiding internal operations.
    """
    
    # Default message mappings (used if database messages not found)
    DEFAULT_MESSAGES = {
        'start': "Starting to build your website...",
        'analyzing': "Understanding your requirements...",
        'designing': "Designing your perfect layout...",
        'building_hero': "Creating your homepage...",
        'building_sections': "Adding your content sections...",
        'styling': "Applying beautiful styling...",
        'polishing': "Polishing the design...",
        'finalizing': "Finalizing your website...",
        'deploying': "Publishing your website...",
        'complete': "Your website is ready!",
    }
    
    def __init__(self, session):
        self.session = session
        self._load_custom_messages()
    
    def _load_custom_messages(self):
        """Load custom messages from database."""
        try:
            from apps.code_library.models import CustomerMessage
            db_messages = CustomerMessage.objects.filter(is_active=True)
            self.messages = {m.operation_key: m for m in db_messages}
        except Exception:
            self.messages = {}
    
    def send(self, operation_key: str, **kwargs):
        """
        Send a customer-friendly message.
        Internal operation_key is mapped to friendly message.
        """
        from apps.onboarding.models import SessionEvent
        
        # Get message from DB or defaults
        if operation_key in self.messages:
            message = self.messages[operation_key].get_message()
        else:
            message = self.DEFAULT_MESSAGES.get(operation_key, "Working on your project...")
        
        # Format with any kwargs
        try:
            message = message.format(**kwargs)
        except (KeyError, ValueError):
            pass
        
        # Send to customer
        SessionEvent.objects.create(
            session=self.session,
            event_type='build_progress',
            event_data={'message': message}
        )
        
        logger.info(f"[Customer Message] {operation_key} → {message}")


class LibrarySearcher:
    """
    Searches the code library for matching components.
    Uses keyword matching and semantic search.
    """
    
    def __init__(self):
        # Utility model for classification/extraction (not code generation)
        self.utility_model = constants.UTILITY_MODEL
    
    def extract_requirements(self, user_prompt: str) -> Dict:
        """
        Use cheap AI to extract structured requirements from user prompt.
        Returns: {site_type, sections_needed, features, style_preferences}
        """
        import anthropic
        
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        extraction_prompt = f"""Analyze this website request and extract structured requirements.

Request: "{user_prompt}"

Return JSON only:
{{
    "site_type": "salon|restaurant|portfolio|ecommerce|blog|dashboard|other",
    "industry": "beauty|food|tech|finance|health|education|other",
    "sections_needed": ["hero", "services", "pricing", "about", "contact", "testimonials", "gallery", "team"],
    "features": ["booking", "menu", "gallery", "contact_form", "pricing_table", "testimonials"],
    "style_hints": ["modern", "minimal", "bold", "elegant", "playful", "professional"]
}}

Only include sections and features actually mentioned or implied. Return ONLY valid JSON."""

        try:
            response = client.messages.create(
                model=self.utility_model,  # Haiku for classification only
                max_tokens=500,
                messages=[{"role": "user", "content": extraction_prompt}]
            )
            result_text = response.content[0].text.strip()
            # Clean markdown if present
            if result_text.startswith('```'):
                result_text = re.sub(r'^```\w*\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)
            return json.loads(result_text)
        except Exception as e:
            logger.warning(f"Failed to extract requirements: {e}")
            return {
                "site_type": "other",
                "industry": "other", 
                "sections_needed": ["hero", "about", "contact"],
                "features": [],
                "style_hints": ["modern"]
            }
    
    def search_library(self, requirements: Dict) -> List[Dict]:
        """
        Search library for matching components.
        Returns list of {item, match_score, match_reason}
        """
        from apps.code_library.models import LibraryItem
        
        matches = []
        
        # Build search keywords
        keywords = []
        keywords.append(requirements.get('site_type', ''))
        keywords.append(requirements.get('industry', ''))
        keywords.extend(requirements.get('sections_needed', []))
        keywords.extend(requirements.get('features', []))
        keywords = [k.lower() for k in keywords if k]
        
        # Search active, approved items - handle missing column
        filters = {'is_active': True}
        if _check_has_is_approved_column():
            filters['is_approved'] = True
        items = LibraryItem.objects.filter(**filters).order_by('-quality_score', '-usage_count')
        
        for item in items:
            # Handle keywords as list (JSONField) or legacy string
            if isinstance(item.keywords, list):
                item_keywords = ' '.join([k.lower() for k in item.keywords])
            else:
                item_keywords = (item.keywords or '').lower()
            item_tags = [t.lower() for t in (item.tags or [])]
            item_name = item.name.lower()
            item_desc = item.description.lower()
            
            # Calculate match score
            score = 0
            matched_keywords = []
            
            for kw in keywords:
                if kw in item_keywords or kw in item_name or kw in item_desc:
                    score += constants.KEYWORD_IN_TEXT_WEIGHT
                    matched_keywords.append(kw)
                if kw in item_tags:
                    score += constants.KEYWORD_IN_TAG_WEIGHT
                    matched_keywords.append(kw)
            
            # Boost by quality
            score *= (constants.QUALITY_SCORE_BOOST_FACTOR + item.quality_score)
            
            if score > 0:
                matches.append({
                    'item': item,
                    'score': score,
                    'matched_keywords': list(set(matched_keywords))
                })
        
        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:10]  # Top 10 matches


class LibraryFirstPipeline:
    """
    The main pipeline that ENFORCES library-first approach.
    
    Flow:
    1. Extract requirements from user prompt
    2. MANDATORY: Search library for matches
    3. If good matches found → adapt existing code (Opus 4.5)
    4. If no matches → generate new code (Opus 4.5) → auto-save to library
    5. Verify the AI actually used library (if it should have)
    
    ALL code generation uses Opus 4.5 - no exceptions.
    Items are auto-approved for immediate reuse.
    Admin reviews happen AFTER, not as a gate.
    """
    
    # ALL code generation uses Opus 4.5
    GENERATION_MODEL = constants.GENERATION_MODEL
    UTILITY_MODEL = constants.UTILITY_MODEL
    
    def __init__(self, session):
        self.session = session
        self.messenger = CustomerMessenger(session)
        self.searcher = LibrarySearcher()
        self._library_was_used = False
        self._generated_new_code = False
    
    def build(self, user_prompt: str, project) -> str:
        """
        Main entry point. Returns the final App.jsx code.
        """
        import anthropic
        from apps.code_library.models import AdminDesignRules
        
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Step 1: Customer sees friendly message
        self.messenger.send('analyzing')
        
        # Step 2: Extract requirements (hidden from customer)
        logger.info("[Pipeline] Extracting requirements...")
        requirements = self.searcher.extract_requirements(user_prompt)
        logger.info(f"[Pipeline] Requirements: {requirements}")
        
        # Step 3: MANDATORY library search (hidden from customer)
        self.messenger.send('designing')
        logger.info("[Pipeline] Searching library...")
        matches = self.searcher.search_library(requirements)
        logger.info(f"[Pipeline] Found {len(matches)} library matches")
        
        # Step 4: Get design rules
        design_rules = AdminDesignRules.get_active_rules()
        rules_text = design_rules.get_full_rules() if design_rules else ""
        
        # Step 5: Decide path - reuse or generate
        top_score = matches[0]['score'] if matches else 0
        candidate_count = len(matches)
        
        print(f"[LIBRARY] Search results: {len(matches)} matches, top_score={top_score:.1f}")
        
        if matches and top_score >= constants.REUSE_THRESHOLD_HIGH:
            # Good match found - ADAPT existing code
            decision = 'reused'
            print(f"[LIBRARY] 🔄 REUSE: score={top_score:.1f} >= {constants.REUSE_THRESHOLD_HIGH} - using '{matches[0]['item'].name}'")
            self._library_was_used = True
            
            self.messenger.send('building_hero')
            code = self._adapt_from_library(
                client, user_prompt, matches, requirements, rules_text
            )
            library_item_id = str(matches[0]['item'].id)
            
        elif matches and top_score >= constants.GRAY_ZONE_MIN:
            # Gray zone - generate new but log for review
            decision = 'gray_zone'
            print(f"[LIBRARY] [WARN] GRAY_ZONE: score={top_score:.1f} in [{constants.GRAY_ZONE_MIN}, {constants.REUSE_THRESHOLD_HIGH})")
            self._generated_new_code = True
            
            self.messenger.send('building_hero')
            code = self._generate_new(
                client, user_prompt, requirements, rules_text
            )
            self.messenger.send('polishing')
            self._save_to_library(code, user_prompt, requirements, project)
            library_item_id = None
            
        else:
            # No good match - GENERATE new code
            decision = 'generated'
            print(f"[LIBRARY] [NEW] GENERATE: score={top_score:.1f} < {constants.GRAY_ZONE_MIN} (no good match)")
            self._generated_new_code = True
            
            self.messenger.send('building_hero')
            code = self._generate_new(
                client, user_prompt, requirements, rules_text
            )
            
            # Save new code to library for future use
            self.messenger.send('polishing')
            self._save_to_library(code, user_prompt, requirements, project)
            library_item_id = None
        
        # Log the decision for metrics
        ReuseMetrics.log_decision(
            session_token=self.session.session_token,
            decision=decision,
            match_score=top_score,
            library_item_id=library_item_id,
            candidate_count=candidate_count,
            threshold_used=constants.REUSE_THRESHOLD_HIGH,
        )
        
        self.messenger.send('finalizing')
        
        # Step 6: Verify (hidden from customer)
        self._verify_output(code, requirements)
        
        return code
    
    def _adapt_from_library(
        self, client, user_prompt: str, matches: List[Dict], 
        requirements: Dict, rules_text: str
    ) -> str:
        """Adapt library components to user's needs using cheap AI."""
        
        # Get top matching components
        library_code_sections = []
        for match in matches[:3]:
            item = match['item']
            library_code_sections.append(f"""
=== COMPONENT: {item.name} (Quality: {item.quality_score:.0%}, Used {item.usage_count} times) ===
{item.code}
""")
            # Increment usage
            item.increment_usage()
            
            # Track usage
            from apps.code_library.models import LibraryItemUsage
            try:
                LibraryItemUsage.objects.create(
                    item=item,
                    project_id=self.session.converted_to_project_id,
                    usage_type='adapted'
                )
            except Exception:
                pass
        
        library_context = "\n".join(library_code_sections)
        
        prompt = f"""You are adapting existing high-quality components for a new project.

USER REQUEST:
{user_prompt}

EXISTING COMPONENTS TO USE AS BASE (these are proven, high-quality):
{library_context}

{rules_text}

INSTRUCTIONS:
1. Use the existing components as your foundation
2. Adapt colors, text, and content to match the user's request
3. Keep the proven structure and patterns from the library components
4. Combine multiple components if needed
5. Return a COMPLETE, WORKING App.jsx (plain JavaScript, NO TypeScript)

Return ONLY the code, no markdown, no explanation. Start with import, end with export default."""

        response = client.messages.create(
            model=self.GENERATION_MODEL,  # Opus 4.5 for ALL code generation
            max_tokens=12000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        code = response.content[0].text.strip()
        return self._clean_code(code)
    
    def _generate_new(
        self, client, user_prompt: str, 
        requirements: Dict, rules_text: str
    ) -> str:
        """Generate completely new code using expensive AI."""
        
        sections = requirements.get('sections_needed', ['hero', 'about', 'contact'])
        features = requirements.get('features', [])
        
        prompt = f"""You are an expert React developer creating a complete website.

USER REQUEST:
{user_prompt}

DETECTED REQUIREMENTS:
- Site type: {requirements.get('site_type', 'website')}
- Industry: {requirements.get('industry', 'general')}
- Sections needed: {', '.join(sections)}
- Features: {', '.join(features) if features else 'standard website features'}

{rules_text}

CRITICAL RULES:
1. Return ONLY valid React code - no markdown, no backticks
2. Use ONLY inline styles: style={{{{ backgroundColor: '#000' }}}}
3. NO external API calls - all data must be in the component
4. Import ONLY from 'react'
5. Generate REAL content - no Lorem ipsum or placeholders
6. Make it visually stunning with proper spacing and colors
7. Use Apple San Francisco font on ALL text

Return the complete App.jsx code (plain JavaScript, NO TypeScript). Start with import, end with export default App;"""

        response = client.messages.create(
            model=self.GENERATION_MODEL,  # Opus 4.5 for ALL code generation
            max_tokens=12000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        code = response.content[0].text.strip()
        return self._clean_code(code)
    
    def _save_to_library(
        self, code: str, user_prompt: str, 
        requirements: Dict, project
    ):
        """Save newly generated code to library for future reuse."""
        from apps.code_library.models import LibraryItem
        
        print(f"[LIBRARY] Saving code to library: {len(code)} chars, prompt: {user_prompt[:50]}...")
        
        # Only save if code is substantial
        if len(code) < constants.MIN_CODE_LENGTH_FOR_LIBRARY:
            print(f"[LIBRARY] Code too short ({len(code)} < {constants.MIN_CODE_LENGTH_FOR_LIBRARY}), not saving")
            return
        
        # Check for near-duplicates before saving
        duplicate_check = DuplicateDetector.check_for_duplicate(code)
        if duplicate_check:
            print(f"[LIBRARY] DUPLICATE BLOCKED: {duplicate_check['similarity']:.0%} similar to {duplicate_check['matching_item_name']}")
            return

        # RULE 3: No TypeScript - strip any TypeScript annotations before saving
        from apps.code_library.typescript_stripper import strip_typescript_annotations
        code = strip_typescript_annotations(code)

        try:
            import re
            
            # Generate rich keywords from requirements AND user prompt
            keywords = []
            keywords.append(requirements.get('site_type', ''))
            keywords.append(requirements.get('industry', ''))
            keywords.extend(requirements.get('sections_needed', []))
            keywords.extend(requirements.get('features', []))
            
            # Also extract keywords from user prompt for better matching
            prompt_words = [w.lower() for w in user_prompt.split() if len(w) > 3]
            keywords.extend(prompt_words[:5])
            
            keywords = [k for k in keywords if k and k != 'other'][:constants.MAX_KEYWORDS]
            
            # Generate slug from user prompt
            slug = re.sub(r'[^a-z0-9]+', '-', user_prompt.lower())[:100].strip('-')
            
            # Generate better documentation
            doc = f"""
## Auto-Generated Component

**Original Request:** {user_prompt}

**Features:**
{chr(10).join(['- ' + k for k in keywords if k])}

**Gateway Usage:**
Uses Faibric Gateway at https://api.faibric.com/api/gateway/

**How to Reuse:**
This component can be adapted for similar requests. The AI will modify
the specific data endpoints and styling while keeping the core structure.
"""
            
            # Create library item with comprehensive metadata
            # Handle missing columns gracefully
            create_kwargs = {
                'name': f"Generated: {user_prompt[:50]}...",
                'slug': slug,
                'description': f"Auto-generated for: {user_prompt[:200]}",
                'usage_example': f'''
// Import and use this component
import App from './App';

// Customize by passing props:
// <App ticker="BTC" theme="dark" />

// Original prompt: {user_prompt[:100]}
''',
                'documentation': doc,
                'item_type': 'template',
                'language': 'jsx',
                'code': code,
                'keywords': keywords,
                'tags': keywords[:constants.MAX_TAGS],
                'embedding_model': '',
                'dependencies': [],
                'source': 'generated',
                'source_url': '',
                'quality_score': constants.DEFAULT_AI_QUALITY_SCORE,
                'is_active': True,
                'is_public': True,
                'is_deprecated': False,
                'deprecation_note': '',
                'needs_review': True,  # Flag for admin to review later
                'source_project': project,
                'created_by': 'ai'
            }
            
            if _check_has_is_approved_column():
                create_kwargs['is_approved'] = True
            
            item = LibraryItem.objects.create(**create_kwargs)
            
            print(f"[LIBRARY] [OK] SAVED: {item.id} - {item.name} (keywords: {keywords})")
            
            # Queue admin feedback question
            self._queue_admin_feedback(item, user_prompt, requirements)
            
        except Exception as e:
            print(f"[LIBRARY] [ERROR] FAILED to save: {e}")
    
    def _verify_output(self, code: str, requirements: Dict):
        """Verify the generated code meets requirements."""
        issues = []
        
        # Check for forbidden patterns
        forbidden = [
            ('lorem ipsum', 'Contains placeholder text'),
            ('placeholder', 'Contains placeholder'),
            ('example.com', 'Contains example domain'),
            ('localhost', 'Contains localhost'),
            ('TODO', 'Contains TODO'),
            ('FIXME', 'Contains FIXME'),
        ]
        
        code_lower = code.lower()
        for pattern, issue in forbidden:
            if pattern in code_lower:
                issues.append(issue)
        
        # Check for required patterns
        required = [
            ('import', 'Missing import statement'),
            ('export default', 'Missing export default'),
            ('function App', 'Missing App function'),
            ('return', 'Missing return statement'),
        ]
        
        for pattern, issue in required:
            if pattern not in code:
                issues.append(issue)
        
        if issues:
            logger.warning(f"[Pipeline] Verification issues: {issues}")
        else:
            logger.info("[Pipeline] Verification passed")
        
        return len(issues) == 0
    
    def _clean_code(self, code: str) -> str:
        """Clean up AI-generated code."""
        # Remove markdown code blocks
        if code.startswith('```'):
            code = re.sub(r'^```\w*\n?', '', code)
            code = re.sub(r'\n?```$', '', code)
        
        # Remove any leading/trailing whitespace
        code = code.strip()
        
        # Ensure it starts with import
        if not code.startswith('import'):
            # Try to find import statement
            import_match = re.search(r'(import\s+.*?;)', code)
            if import_match:
                code = code[import_match.start():]
        
        return code
    
    def _queue_admin_feedback(self, item, user_prompt: str, requirements: Dict):
        """
        Generate questions for admin to review this item later.
        Uses LLM to create natural language questions.
        """
        import anthropic
        from apps.code_library.models import AdminFeedbackQuestion
        
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            prompt = f"""You are helping an admin review AI-generated code.

The code was generated for this request: "{user_prompt[:200]}"
Site type: {requirements.get('site_type', 'unknown')}
Industry: {requirements.get('industry', 'unknown')}

Generate 2-3 SHORT questions for the admin to answer later.
Questions should help improve future generations.

Format as JSON array:
[
  {{"question": "...", "type": "quality|like_dislike|improvement|categorization"}}
]

Examples:
- "Does this salon website have the right sections for a typical beauty business?"
- "Rate the visual design quality from 1-5"
- "What would you change about the hero section?"

Return ONLY the JSON array, no explanation."""

            response = client.messages.create(
                model=self.UTILITY_MODEL,  # Haiku for generating questions
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text.strip()
            if result_text.startswith('```'):
                result_text = re.sub(r'^```\w*\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)
            
            questions = json.loads(result_text)
            
            for q in questions[:3]:  # Max 3 questions
                AdminFeedbackQuestion.objects.create(
                    library_item=item,
                    question=q.get('question', ''),
                    question_type=q.get('type', 'quality'),
                    context=f"Generated for: {user_prompt[:100]}",
                )
            
            logger.info(f"[Pipeline] Queued {len(questions)} feedback questions for admin")
            
        except Exception as e:
            logger.warning(f"[Pipeline] Failed to queue feedback questions: {e}")
    
    def get_stats(self) -> Dict:
        """Return stats about this build for logging."""
        return {
            'library_used': self._library_was_used,
            'new_code_generated': self._generated_new_code,
        }

