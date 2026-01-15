"""
V2 AI Generator - Single-shot generation with Anthropic Claude
Uses code library for reusable components to save API costs.
"""
import json
import re
import logging
from typing import Generator, Dict, Any, Optional, List
import anthropic
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .prompts import CLASSIFY_PROMPT, MODIFY_PROMPT, get_prompt_for_type

# Import from centralized config - SINGLE SOURCE OF TRUTH
from ..models_config import CODE_MODEL, CHAT_MODEL

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


class CodeLibraryMixin:
    """
    Mixin for searching and saving to the code library.
    Prevents regenerating the same components over and over.
    """
    
    def search_existing_components(self, query: str, limit: int = 5) -> List[dict]:
        """Search for existing similar components in the library."""
        try:
            from apps.code_library.search import LibrarySearchService
            service = LibrarySearchService()
            results = service.keyword_search(
                query=query,
                item_type='component',
                language='javascript',
                limit=limit
            )
            return results
        except Exception as e:
            logger.warning(f"Code library search failed: {e}")
            return []
    
    def get_component_code(self, component_id: str) -> Optional[str]:
        """Get the actual code for a library component."""
        try:
            from apps.code_library.models import LibraryItem
            item = LibraryItem.objects.get(id=component_id)
            item.increment_usage()
            return item.code
        except Exception as e:
            logger.warning(f"Failed to get component {component_id}: {e}")
            return None
    
    def save_to_library(
        self, 
        code: str, 
        name: str, 
        description: str,
        keywords: List[str],
        project_id: int = None
    ) -> Optional[str]:
        """Save generated code to library for future reuse."""
        try:
            from apps.code_library.models import LibraryItem
            
            # Check if similar already exists by name
            existing = LibraryItem.objects.filter(name=name, is_active=True).first()
            if existing:
                # Update usage count instead of creating duplicate
                existing.increment_usage()
                return str(existing.id)
            
            # Get source project if provided
            source_project = None
            if project_id:
                try:
                    from apps.projects.models import Project
                    source_project = Project.objects.get(id=project_id)
                except Exception:
                    pass
            
            # Ensure keywords is a list
            kw_list = keywords if isinstance(keywords, list) else []
            
            # Create with ONLY fields that exist in Django model
            # Handle missing is_approved column
            create_kwargs = {
                'name': name[:200],
                'item_type': 'component',
                'language': 'jsx',
                'code': code,
                'description': description[:500] if description else 'Auto-generated component',
                'keywords': kw_list,  # JSONField - pass as list
                'tags': kw_list[:5],  # JSONField - pass as list
                'source_project': source_project,
                'created_by': 'ai',
                'is_public': True,
                'needs_review': True,
                'quality_score': 0.7,
            }
            if _check_has_is_approved_column():
                create_kwargs['is_approved'] = True
            
            item = LibraryItem.objects.create(**create_kwargs)
            logger.info(f"Saved component to library: {name}")
            return str(item.id)
        except Exception as e:
            logger.warning(f"Failed to save to library: {e}")
            return None
    
    def build_library_context(self, user_prompt: str) -> str:
        """
        Search library and build context string with relevant existing code.
        This helps AI customize existing components instead of regenerating.
        """
        # Extract keywords from prompt
        keywords = [w.lower() for w in user_prompt.split() if len(w) > 3][:10]
        query = ' '.join(keywords)
        
        results = self.search_existing_components(query, limit=3)
        
        if not results:
            return ""
        
        context_parts = ["\n\nEXISTING COMPONENTS IN LIBRARY (use as reference, customize as needed):"]
        
        for result in results:
            code = self.get_component_code(result['id'])
            if code and len(code) < 3000:  # Only include reasonably sized components
                context_parts.append(f"\n--- {result['name']} ({result['item_type']}) ---")
                context_parts.append(f"Description: {result.get('description', 'N/A')}")
                keywords = result.get('keywords', '')
                if isinstance(keywords, list):
                    keywords = ', '.join(keywords)
                context_parts.append(f"Keywords: {keywords}")
                context_parts.append(f"```\n{code[:2000]}\n```")
        
        if len(context_parts) > 1:
            context_parts.append("\nYou can use these as inspiration or customize them. Don't regenerate from scratch if a similar component exists.")
            return "\n".join(context_parts)
        
        return ""


class AIGeneratorV2(CodeLibraryMixin):
    """
    Single-shot app generator using Anthropic Claude.
    Uses smart model selection:
    - Opus 4.5 for NEW code generation
    - Haiku for classification, summaries, and reusing existing code
    """
    
    # Model tiers - from centralized config (models_config.py)
    EXPENSIVE_MODEL = CODE_MODEL  # Claude Opus 4.5 - for code generation
    CHEAP_MODEL = CHAT_MODEL       # Claude Haiku 4.5 - for chat/classification
    
    def __init__(self, model: str = None):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model or self.EXPENSIVE_MODEL
        self.session_token = None  # Set by caller for cost tracking
    
    def _track_usage(self, model: str, input_tokens: int, output_tokens: int, 
                     task_type: str, success: bool = True):
        """Track API usage for cost analysis."""
        try:
            from apps.analytics.cost_tracker import APIUsageTracker
            APIUsageTracker.log_usage(
                session_token=self.session_token,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                task_type=task_type,
                success=success,
            )
        except Exception as e:
            logger.warning(f"Failed to track usage: {e}")
    
    def classify_prompt(self, user_prompt: str) -> str:
        """Quickly classify what type of app the user wants - uses CHEAP model"""
        try:
            response = self.client.messages.create(
                model=self.CHEAP_MODEL,  # Use cheap model for classification
                max_tokens=20,
                messages=[
                    {"role": "user", "content": CLASSIFY_PROMPT.format(prompt=user_prompt)}
                ],
                temperature=0
            )
            result = response.content[0].text.strip().lower()
            
            # Track usage
            self._track_usage(
                model=self.CHEAP_MODEL,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                task_type='classify',
            )
            
            # Validate result
            valid_types = ['website', 'tool', 'dashboard', 'form', 'game', 'webapp']
            if result in valid_types:
                return result
            return 'website'  # Default
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return 'website'
    
    def generate_app(
        self, 
        user_prompt: str, 
        project_id: int = None,
        session = None
    ) -> Dict[str, Any]:
        """
        Generate a complete app using COMPONENT-BASED building blocks.
        
        NEW ARCHITECTURE:
        1. Decompose request into building blocks (navigation, hero, cards, etc.)
        2. Search library for EACH block
        3. Reuse found blocks, generate missing ones
        4. Save new blocks to library for future reuse
        5. Compose final app from blocks
        """
        
        # Broadcast: Starting
        self._broadcast(project_id, "thinking", "Analyzing your request...")
        self._add_session_event(session, "Analyzing request...")
        
        # NEW: Use component-based generation
        try:
            return self._generate_with_components(user_prompt, project_id, session)
        except Exception as e:
            logger.warning(f"Component pipeline failed, falling back to legacy: {e}")
            print(f"[GENERATOR] Component pipeline failed: {e}, using legacy")
            return self._generate_legacy(user_prompt, project_id, session)
    
    def _generate_with_components(
        self, 
        user_prompt: str, 
        project_id: int = None,
        session = None
    ) -> Dict[str, Any]:
        """
        Component-based generation pipeline.
        
        Each project is decomposed into reusable building blocks.
        This is the RIGHT way - components, not whole projects.
        """
        from apps.code_library.component_pipeline import ComponentGenerationPipeline
        
        self._broadcast(project_id, "action", "Decomposing into building blocks...")
        self._add_session_event(session, "Breaking down into components...")
        
        pipeline = ComponentGenerationPipeline(session=session)
        
        # Build using component blocks
        code = pipeline.build(user_prompt, project=None)
        
        # Get stats
        stats = pipeline.get_stats()
        
        self._broadcast(project_id, "success", 
            f"Built from {stats['components_required']} blocks "
            f"({stats['components_reused']} reused, {stats['components_generated']} new)")
        
        # Classify for app type
        app_type = self.classify_prompt(user_prompt)
        
        return {
            'app_type': app_type,
            'components': {
                'App.jsx': code
            },
            'build_stats': stats
        }
    
    def _generate_legacy(
        self, 
        user_prompt: str, 
        project_id: int = None,
        session = None
    ) -> Dict[str, Any]:
        """
        LEGACY: Monolithic generation (fallback).
        """
        
        # Classify the prompt
        app_type = self.classify_prompt(user_prompt)
        self._broadcast(project_id, "action", f"Building a {app_type}...")
        self._add_session_event(session, f"App type: {app_type}")
        
        # Get the specialized prompt
        prompt_template = get_prompt_for_type(app_type)
        full_prompt = prompt_template.format(user_prompt=user_prompt)
        
        # IMPORTANT: Strict requirements for generated apps
        # Check if user wants stock/trading data
        wants_stock_data = any(w in user_prompt.lower() for w in ['stock', 'trading', 'nbis', 'crwv', 'ticker', 'price data', 'historical', 'yahoo', 'factual data', 'real data'])
        
        stock_requirement = ""
        if wants_stock_data:
            stock_requirement = """
5. STOCK/FINANCIAL DATA - MUST USE REAL API:
   - You MUST fetch real data using useEffect and fetch
   - Use this EXACT pattern:
   ```
   useEffect(() => {
     const fetchStock = async () => {
       setLoading(true);
       const res = await fetch('https://api.faibric.com/api/gateway/', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ service: 'yahoo_finance', endpoint: '/chart/NBIS?range=1y&interval=1d' })
       });
       const result = await res.json();
       if (result.success) setStockData(result.data);
       setLoading(false);
     };
     fetchStock();
   }, []);
   ```
   - REPLACE 'NBIS' with the actual ticker(s) the user mentioned
   - NEVER hardcode stock prices - they will be WRONG
   - Show "Loading market data..." while fetching
   - THIS IS MANDATORY FOR ANY STOCK/TRADING REQUEST
"""
        
        strict_requirements = """
CRITICAL REQUIREMENTS - FOLLOW EXACTLY:

1. FONTS: Use ONLY Apple San Francisco font family in ALL CSS
   - Always set: font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', system-ui, sans-serif;
   - Apply this font to body, html, and all text elements

2. NO PLACEHOLDERS - This is extremely important:
   - NEVER use placeholder text like "Lorem ipsum", "[Your text here]", "Coming soon", etc.
   - NEVER use placeholder images like "placeholder.jpg", "example.jpg", empty src attributes
   - Instead, generate REAL, realistic content that matches the user's request
   - Write actual compelling copy, descriptions, and text content
   - If the user asks for a restaurant site, write real menu items with prices
   - If it's a portfolio, write realistic project descriptions
   - Make the content feel like a real, finished website

3. IMAGES - USE PICSUM (source.unsplash.com is broken):
   - Use Picsum: https://picsum.photos/seed/KEYWORD/800/600
   - Replace KEYWORD with descriptive text: seed/asian-woman-1, seed/dog-portrait-2
   - Each image needs a UNIQUE seed to get different images
   - Increment numbers for variety: seed/art1, seed/art2, seed/art3
   - Example for NFT artist: https://picsum.photos/seed/nft-art-1/800/600
   - NEVER use source.unsplash.com - it returns 503 errors
   - NEVER leave image src empty

4. COMPLETE CODE: Always finish all JSX tags and exports
""" + stock_requirement
        full_prompt = strict_requirements + "\n\n" + full_prompt
        
        # Search code library for reusable components (internal - no client message)
        library_context = self.build_library_context(user_prompt)
        has_library_match = bool(library_context)
        
        if has_library_match:
            full_prompt = full_prompt + library_context
            logger.info(f"Found reusable components for project {project_id}")
        
        # SMART MODEL SELECTION:
        # - If library has similar code -> use cheap model to customize
        # - If generating from scratch -> use expensive model
        if has_library_match:
            generation_model = self.CHEAP_MODEL
            self._add_session_event(session, "Customizing existing components...")
            logger.info(f"Using cheap model (library match found)")
        else:
            generation_model = self.EXPENSIVE_MODEL
            self._add_session_event(session, "Generating new components...")
            logger.info(f"Using expensive model (no library match)")
        
        # Stream AI response for real-time thinking
        self._broadcast(project_id, "thinking", "Generating components...")
        
        try:
            # Use streaming to get real-time updates
            full_response = ""
            thinking_shown = False
            
            # Build dynamic system prompt
            system_prompt = """You are an expert React developer. 
CRITICAL RULES:
1. Output ONLY valid JSON
2. ALWAYS use San Francisco font (-apple-system, BlinkMacSystemFont, 'SF Pro Display')
3. NEVER use placeholder content - no "Lorem ipsum", "placeholder", "[Your text]", "Coming soon"
4. Generate REAL, compelling content that matches the user's request
5. IMAGES: Use Picsum: https://picsum.photos/seed/KEYWORD/800/600
   - Use unique seeds: seed/portrait1, seed/art2, seed/photo3
   - NEVER use source.unsplash.com (broken, returns 503)
   - NEVER leave image src empty
6. Always complete all JSX tags - never leave code incomplete"""

            # ADD STOCK DATA REQUIREMENT TO SYSTEM PROMPT
            if wants_stock_data:
                system_prompt += """

7. STOCK DATA - THIS IS MANDATORY:
   - You MUST fetch REAL data using the Gateway API
   - Use this EXACT code pattern in useEffect:
     fetch('https://api.faibric.com/api/gateway/', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ service: 'yahoo_finance', endpoint: '/chart/TICKER' })
     })
   - Replace TICKER with the actual stock symbol (NBIS, CRWV, etc.)
   - NEVER hardcode stock prices - they will be WRONG
   - Show "Loading market data..." while fetching
   - The user asked for REAL data - you MUST use the API"""
            
            with self.client.messages.stream(
                model=generation_model,
                max_tokens=16000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7
            ) as stream:
                chunk_count = 0
                last_update_len = 0
                
                for text in stream.text_stream:
                    full_response += text
                    chunk_count += 1
                    
                    # Show progress every 60 chunks
                    if chunk_count % 60 == 0:
                        # Extract a readable code snippet from recent content
                        snippet = self._extract_readable_snippet(full_response, last_update_len)
                        if snippet:
                            self._add_session_event(session, snippet)
                        last_update_len = len(full_response)
            
            result_text = full_response
            self._add_session_event(session, f"Generated {len(result_text)} characters")
            
            # Track API usage (estimate tokens from character count)
            # Roughly 4 chars per token for code
            estimated_input_tokens = len(full_prompt) // 4
            estimated_output_tokens = len(result_text) // 4
            self._track_usage(
                model=generation_model,
                input_tokens=estimated_input_tokens,
                output_tokens=estimated_output_tokens,
                task_type='generate_new' if not has_library_match else 'reuse',
                success=True,
            )
            
            # Clean and parse JSON
            result = self._parse_json_response(result_text)
            
            if not result:
                raise ValueError("Failed to parse AI response as JSON")
            
            # Ensure we have the components structure
            if 'components' not in result:
                result = {'components': {'App': result_text}, 'title': 'Generated App'}
            
            # Clean component code
            result['components'] = self._clean_components(result['components'])
            result['app_type'] = app_type
            
            self._broadcast(project_id, "success", f"Generated {len(result['components'])} component(s)")
            
            # Save to library for future reuse (async, don't block)
            try:
                app_code = result['components'].get('App', '')
                if app_code and len(app_code) > 500:  # Only save substantial code
                    # Extract keywords from prompt
                    keywords = [w.lower() for w in user_prompt.split() if len(w) > 3][:10]
                    self.save_to_library(
                        code=app_code,
                        name=f"{app_type.title()} - {user_prompt[:50]}",
                        description=user_prompt[:200],
                        keywords=keywords,
                        project_id=project_id
                    )
            except Exception as e:
                logger.warning(f"Failed to save to library: {e}")
            
            return result
            
        except Exception as e:
            self._broadcast(project_id, "error", f"[ERROR] Generation failed: {str(e)[:100]}")
            raise
    
    def modify_app(
        self,
        current_code: str,
        user_request: str,
        project_id: int = None
    ) -> str:
        """
        Modify existing app code based on user request.
        Returns the modified code.
        """
        
        self._broadcast(project_id, "thinking", f"Applying changes: {user_request[:50]}...")
        
        prompt = MODIFY_PROMPT.format(
            current_code=current_code,
            user_request=user_request
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system="You are an expert React developer. Return ONLY the modified code.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            result = response.content[0].text
            result = self._strip_code_markers(result)
            
            self._broadcast(project_id, "success", "Changes applied")
            
            return result
            
        except Exception as e:
            self._broadcast(project_id, "error", f"[ERROR] Modification failed: {str(e)[:100]}")
            raise
    
    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """Parse JSON from AI response, handling common issues"""
        
        # Remove markdown code blocks if present
        text = re.sub(r'^```(?:json)?\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```$', '', text, flags=re.MULTILINE)
        text = re.sub(r'```\w*\n?', '', text)  # Remove any remaining code blocks
        text = text.strip()
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object starting with {"
        # Use greedy match to find the largest valid JSON
        start_idx = text.find('{"')
        if start_idx != -1:
            # Find matching closing brace
            depth = 0
            for i, char in enumerate(text[start_idx:]):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = text[start_idx:start_idx + i + 1]
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            pass
                        break
        
        # Fallback: look for component code directly
        # If we find React code, wrap it in a components dict
        if 'import React' in text or 'function App' in text or 'export default' in text or 'const App' in text:
            # Try to extract the entire code block
            code = text
            # Clean up any explanation text before/after the code
            if 'import' in code:
                start = code.find('import')
                code = code[start:]
            # Find end - either export default or end of substantial code
            if 'export default' in code:
                end_match = re.search(r'export default \w+;?\s*$', code, re.MULTILINE)
                if end_match:
                    code = code[:end_match.end()]
            
            return {
                'title': 'Generated App',
                'components': {'App': code.strip()}
            }
        
        # Last resort: if we have any JSX-looking content, wrap it
        if '<' in text and '/>' in text:
            # Wrap in a basic component
            wrapped = f"""import React from 'react';

function App() {{
  return (
    {text}
  );
}}

export default App;"""
            return {
                'title': 'Generated App', 
                'components': {'App': wrapped}
            }
        
        return None
    
    def _clean_components(self, components: Dict[str, str]) -> Dict[str, str]:
        """Clean component code - remove markers, fix common issues"""
        cleaned = {}
        
        for name, code in components.items():
            if isinstance(code, str):
                # Remove markdown code block markers
                code = self._strip_code_markers(code)
                
                # Fix common JSX issues
                code = self._fix_jsx_issues(code)
                
                cleaned[name] = code
        
        return cleaned
    
    def _strip_code_markers(self, code: str) -> str:
        """Remove markdown code block markers"""
        code = re.sub(r'^```\w*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n?```$', '', code, flags=re.MULTILINE)
        return code.strip()
    
    def _fix_jsx_issues(self, code: str) -> str:
        """Fix common JSX syntax issues"""
        
        # Fix template literals in href/src (common AI mistake)
        # Change: href=`mailto:${email}` to href={'mailto:' + email}
        code = re.sub(
            r'(\w+)=`([^`]*)\$\{([^}]+)\}([^`]*)`',
            r"\1={{'\2' + \3 + '\4'}}",
            code
        )
        
        return code
    
    def _extract_readable_snippet(self, full_text: str, start_from: int) -> str:
        """Show simple progress instead of code fragments"""
        total = len(full_text)
        
        # Just show clean progress messages
        if total < 1500:
            return "Creating app structure..."
        elif total < 3000:
            return "Building components..."
        elif total < 5000:
            return "Adding functionality..."
        elif total < 7000:
            return "Styling interface..."
        elif total < 9000:
            return "Adding interactions..."
        else:
            return "Finishing up..."
    
    def _broadcast(self, project_id: int, msg_type: str, content: str):
        """Broadcast progress message to Redis cache - non-critical, don't crash on failure"""
        if not project_id:
            return
        
        try:
            messages_key = f'project_messages_{project_id}'
            existing = cache.get(messages_key, []) or []
            
            existing.append({
                'id': f'{project_id}_{len(existing)}',
                'type': msg_type,
                'content': content,
                'timestamp': timezone.now().isoformat()
            })
            
            cache.set(messages_key, existing, timeout=3600)
        except Exception as e:
            # Redis failure is non-critical - just log and continue
            print(f"Redis broadcast failed: {e}")
        
        print(f"[{project_id}] {content}")
    
    def _add_session_event(self, session, message: str):
        """Add a build progress event to the session for frontend polling"""
        if not session:
            return
        
        try:
            from apps.onboarding.models import SessionEvent
            SessionEvent.objects.create(
                session=session,
                event_type='build_progress',
                event_data={'message': message, 'progress': 0},
            )
        except Exception as e:
            print(f"Failed to add session event: {e}")
