"""
V2 AI Generator - Single-shot generation with Anthropic Claude
"""
import json
import re
from typing import Generator, Dict, Any, Optional
import anthropic
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .prompts import CLASSIFY_PROMPT, MODIFY_PROMPT, get_prompt_for_type


class AIGeneratorV2:
    """
    Single-shot app generator using Anthropic Claude Opus 4.5
    """
    
    def __init__(self, model: str = None):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model or "claude-sonnet-4-20250514"  # Claude Opus 4.5
    
    def classify_prompt(self, user_prompt: str) -> str:
        """Quickly classify what type of app the user wants"""
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Use Haiku for fast classification
                max_tokens=20,
                messages=[
                    {"role": "user", "content": CLASSIFY_PROMPT.format(prompt=user_prompt)}
                ],
                temperature=0
            )
            result = response.content[0].text.strip().lower()
            
            # Validate result
            valid_types = ['website', 'tool', 'dashboard', 'form', 'game', 'webapp']
            if result in valid_types:
                return result
            return 'website'  # Default
        except Exception as e:
            print(f"Classification error: {e}")
            return 'website'
    
    def generate_app(
        self, 
        user_prompt: str, 
        project_id: int = None,
        session = None
    ) -> Dict[str, Any]:
        """
        Generate a complete app in a single AI call with streaming.
        Returns dict with components and metadata.
        """
        
        # Broadcast: Starting
        self._broadcast(project_id, "thinking", "🧠 Analyzing your request...")
        self._add_session_event(session, "🧠 Analyzing your request...")
        
        # Classify the prompt
        app_type = self.classify_prompt(user_prompt)
        self._broadcast(project_id, "action", f"📋 Building a {app_type}...")
        self._add_session_event(session, f"📋 Identified app type: {app_type}")
        
        # Get the specialized prompt
        prompt_template = get_prompt_for_type(app_type)
        full_prompt = prompt_template.format(user_prompt=user_prompt)
        
        # IMPORTANT: Force San Francisco fonts in all generated apps
        font_instruction = """
CRITICAL STYLING REQUIREMENT:
- Use ONLY Apple San Francisco font family in ALL CSS
- Always set: font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', system-ui, sans-serif;
- Apply this font to body, html, and all text elements
- NEVER use other fonts unless explicitly requested by the user
"""
        full_prompt = font_instruction + "\n\n" + full_prompt
        
        # Stream AI response for real-time thinking
        self._broadcast(project_id, "thinking", "🎨 Generating components...")
        self._add_session_event(session, "🎨 Claude Opus 4.5 is writing your code...")
        
        try:
            # Use streaming to get real-time updates
            full_response = ""
            thinking_shown = False
            
            with self.client.messages.stream(
                model=self.model,
                max_tokens=8000,
                system="You are an expert React developer. Output ONLY valid JSON. ALWAYS use San Francisco font (-apple-system, BlinkMacSystemFont, 'SF Pro Display').",
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7
            ) as stream:
                chunk_count = 0
                for text in stream.text_stream:
                    full_response += text
                    chunk_count += 1
                    
                    # Show progress every 20 chunks
                    if chunk_count % 20 == 0:
                        progress_msg = f"💭 Writing code... ({len(full_response)} chars)"
                        self._add_session_event(session, progress_msg)
                    
                    # Show first substantial content
                    if not thinking_shown and len(full_response) > 100:
                        thinking_shown = True
                        preview = full_response[:80].replace('\n', ' ')
                        self._add_session_event(session, f"✍️ Started: {preview}...")
            
            result_text = full_response
            self._add_session_event(session, f"✅ Generated {len(result_text)} characters of code")
            
            result_text = response.content[0].text
            
            # Log token usage
            if hasattr(response, 'usage') and response.usage:
                print(f"🔢 Tokens - Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}")
            
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
            
            self._broadcast(project_id, "success", f"✅ Generated {len(result['components'])} component(s)")
            
            return result
            
        except Exception as e:
            self._broadcast(project_id, "error", f"❌ Generation failed: {str(e)[:100]}")
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
        
        self._broadcast(project_id, "thinking", f"🔧 Applying changes: {user_request[:50]}...")
        
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
            
            self._broadcast(project_id, "success", "✅ Changes applied")
            
            return result
            
        except Exception as e:
            self._broadcast(project_id, "error", f"❌ Modification failed: {str(e)[:100]}")
            raise
    
    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """Parse JSON from AI response, handling common issues"""
        
        # Remove markdown code blocks if present
        text = re.sub(r'^```(?:json)?\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```$', '', text, flags=re.MULTILINE)
        text = text.strip()
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
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
    
    def _broadcast(self, project_id: int, msg_type: str, content: str):
        """Broadcast progress message to Redis cache"""
        if not project_id:
            return
        
        messages_key = f'project_messages_{project_id}'
        existing = cache.get(messages_key, [])
        
        existing.append({
            'id': f'{project_id}_{len(existing)}',
            'type': msg_type,
            'content': content,
            'timestamp': timezone.now().isoformat()
        })
        
        cache.set(messages_key, existing, timeout=3600)
        print(f"📢 [{project_id}] {content}")
    
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
