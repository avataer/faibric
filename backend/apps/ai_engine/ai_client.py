"""
Anthropic Claude client for code generation
"""
import os
import json
import re
import anthropic
from django.conf import settings
from datetime import datetime
from pathlib import Path

# Import from centralized config - SINGLE SOURCE OF TRUTH
from .models_config import CODE_MODEL, CHAT_MODEL, get_model_id

# Customer Test AI Logging
AI_LOG_FILE = Path.home() / "Code/Faibric/customer-tests/coffee-shop-menu/ai_calls.jsonl"

def log_ai_call(call_type: str, messages: list, response: str, metadata: dict = None):
    """Log AI call to file for Customer Test verification"""
    try:
        AI_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "call_type": call_type,
            "messages": messages,
            "response_preview": response[:500] if response else None,
            "response_length": len(response) if response else 0,
            "metadata": metadata or {}
        }
        with open(AI_LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[AI_LOG] Error logging: {e}")


class AIClient:
    """Wrapper for Anthropic Claude API"""

    def __init__(self, model_key=None):
        """
        Initialize the AI client.

        Args:
            model_key: Optional model key (e.g., 'claude-opus', 'claude-sonnet', 'claude-haiku').
                      If not provided, defaults to CODE_MODEL.
        """
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        if model_key:
            self.model = get_model_id(model_key)
        else:
            self.model = CODE_MODEL  # From models_config.py - Claude Opus 4.5

    def set_model(self, model_key):
        """
        Dynamically change the model used for API calls.

        Args:
            model_key: Model key (e.g., 'claude-opus', 'claude-sonnet', 'claude-haiku')
        """
        self.model = get_model_id(model_key)
    
    def chat_completion(self, messages, temperature=0.7, response_format=None, project_id=None, step_description="Processing"):
        """
        Send a chat completion request to Anthropic Claude
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            response_format: Optional response format (e.g., {"type": "json_object"})
            project_id: Project ID to broadcast progress to
            step_description: Description of what this API call is for
        
        Returns:
            Response text from the API
        """
        # Broadcast what we're asking AI - ADD to message history
        if project_id and step_description:
            from django.core.cache import cache
            from django.utils import timezone
            import json
            
            print(f"[fire] BROADCASTING: {step_description} for project {project_id}")
            
            # Get existing messages
            messages_key = f'project_messages_{project_id}'
            existing = cache.get(messages_key, [])
            
            print(f"[fire] Existing messages: {len(existing)}")
            
            # Add new message
            existing.append({
                'id': f'{project_id}_{len(existing)}',
                'type': 'thinking',
                'content': f'[bot] {step_description}...',
                'timestamp': timezone.now().isoformat()
            })
            
            cache.set(messages_key, existing, timeout=3600)
            print(f"[fire] Saved {len(existing)} messages to cache")

        # Convert messages to Anthropic format
        # Extract system message if present
        system_content = None
        anthropic_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_content = msg['content']
            else:
                anthropic_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
        
        # Build request kwargs
        # Use 16K tokens to avoid truncation on complex apps
        kwargs = {
            "model": self.model,
            "max_tokens": 16384,
            "messages": anthropic_messages,
        }
        
        if system_content:
            kwargs["system"] = system_content
        
        if temperature != 1.0:
            kwargs["temperature"] = min(temperature, 1.0)  # Anthropic max temp is 1.0
        
        response = self.client.messages.create(**kwargs)
        result = response.content[0].text

        # Log token usage
        token_info = {}
        if hasattr(response, 'usage') and response.usage:
            token_info = {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
            print(f"🔢 Tokens - Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}")

        # Log AI call for Customer Test verification
        log_ai_call(
            call_type="chat_completion",
            messages=messages,
            response=result,
            metadata={"step": step_description, "project_id": project_id, "tokens": token_info, "model": self.model}
        )
        
        # Strip code block markers if present
        result = self._strip_code_markers(result)
        
        # Broadcast response - ADD to message history
        if project_id and step_description:
            from django.core.cache import cache
            from django.utils import timezone
            
            messages_key = f'project_messages_{project_id}'
            existing = cache.get(messages_key, [])
            
            preview = result[:150].replace('\n', ' ') + "..." if len(result) > 150 else result
            existing.append({
                'id': f'{project_id}_{len(existing)}',
                'type': 'success',
                'content': f'[OK] {step_description}: {preview}',
                'timestamp': timezone.now().isoformat()
            })
            
            cache.set(messages_key, existing, timeout=3600)
        
        return result
    
    def _strip_code_markers(self, code):
        """Remove markdown code block markers from AI response"""
        import re
        
        # Remove ```tsx ... ``` or ```python ... ``` etc
        code = re.sub(r'^```\w*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n```$', '', code, flags=re.MULTILINE)
        code = code.strip()
        
        return code
    
    def analyze_app_description(self, user_prompt, project_id=None):
        """
        Analyze user's app description and extract structured requirements
        
        Args:
            user_prompt: Natural language description of the app
            project_id: Project ID to broadcast progress to
        
        Returns:
            Dict with structured analysis
        """
        from .prompts import ANALYZE_APP_PROMPT
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert software architect who analyzes application requirements. Always respond with valid JSON."
            },
            {
                "role": "user",
                "content": ANALYZE_APP_PROMPT.format(user_prompt=user_prompt)
            }
        ]
        
        response = self.chat_completion(
            messages=messages,
            temperature=0.5,
            response_format={"type": "json_object"},
            project_id=project_id,
            step_description="Analyzing app requirements"
        )
        
        return json.loads(response)
    
    def generate_django_model(self, model_name, fields, relationships, project_id=None):
        """Generate Django model code"""
        from .prompts import GENERATE_DJANGO_MODEL_PROMPT
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert Django developer."
            },
            {
                "role": "user",
                "content": GENERATE_DJANGO_MODEL_PROMPT.format(
                    model_name=model_name,
                    fields=json.dumps(fields, indent=2),
                    relationships=json.dumps(relationships, indent=2)
                )
            }
        ]
        
        return self.chat_completion(
            messages=messages,
            temperature=0.3,
            project_id=project_id,
            step_description=f"Generating Django model: {model_name}"
        )
    
    def generate_serializer(self, model_name, fields, project_id=None):
        """Generate DRF serializer code"""
        from .prompts import GENERATE_DRF_SERIALIZER_PROMPT
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert Django REST Framework developer."
            },
            {
                "role": "user",
                "content": GENERATE_DRF_SERIALIZER_PROMPT.format(
                    model_name=model_name,
                    fields=json.dumps(fields, indent=2)
                )
            }
        ]
        
        return self.chat_completion(
            messages=messages,
            temperature=0.3,
            project_id=project_id,
            step_description=f"Generating API serializer: {model_name}"
        )
    
    def generate_viewset(self, model_name, endpoints, permissions="IsAuthenticated", project_id=None):
        """Generate DRF viewset code"""
        from .prompts import GENERATE_DRF_VIEW_PROMPT
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert Django REST Framework developer."
            },
            {
                "role": "user",
                "content": GENERATE_DRF_VIEW_PROMPT.format(
                    model_name=model_name,
                    endpoints=json.dumps(endpoints, indent=2),
                    permissions=permissions
                )
            }
        ]
        
        return self.chat_completion(
            messages=messages,
            temperature=0.3,
            project_id=project_id,
            step_description=f"Generating API viewset: {model_name}"
        )
    
    def generate_react_component(self, component_name, component_type, description, data_fields, project_id=None):
        """Generate React component code"""
        from .prompts import GENERATE_REACT_COMPONENT_PROMPT
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert React and TypeScript developer."
            },
            {
                "role": "user",
                "content": GENERATE_REACT_COMPONENT_PROMPT.format(
                    component_name=component_name,
                    component_type=component_type,
                    description=description,
                    data_fields=json.dumps(data_fields, indent=2)
                )
            }
        ]
        
        return self.chat_completion(
            messages=messages,
            temperature=0.4,
            project_id=project_id,
            step_description=f"Generating React component: {component_name}"
        )
    
    def refine_code(self, original_code, user_feedback):
        """Refine code based on user feedback"""
        from .prompts import REFINE_CODE_PROMPT
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert software developer focused on code improvement."
            },
            {
                "role": "user",
                "content": REFINE_CODE_PROMPT.format(
                    original_code=original_code,
                    user_feedback=user_feedback
                )
            }
        ]
        
        return self.chat_completion(messages=messages, temperature=0.4)
