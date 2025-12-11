"""
V3 Generator - Universal App Builder
"""
import json
import logging
from typing import Dict, Any, Optional

from ..ai_client import AIClient
from .prompts import get_prompt_for_request, get_modify_prompt, get_analyze_prompt

logger = logging.getLogger(__name__)


class UniversalGenerator:
    """
    V3 Generator that creates apps using the Universal Gateway
    """
    
    def __init__(self):
        self.client = AIClient()
    
    def analyze_request(self, user_prompt: str) -> Dict[str, Any]:
        """Analyze user request to understand what they want"""
        try:
            prompt = get_analyze_prompt(user_prompt)
            messages = [
                {"role": "system", "content": "You are an expert at understanding user requirements. Respond with JSON only."},
                {"role": "user", "content": prompt}
            ]
            response = self.client.chat_completion(messages)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                'app_type': 'website',
                'complexity': 'medium',
                'needs_backend': False,
                'external_apis': [],
                'suggested_services': ['coingecko', 'yahoo_finance']
            }
    
    def generate(self, user_prompt: str, project_id: int = None) -> Dict[str, Any]:
        """
        Generate a complete app from user prompt
        
        Returns:
            {
                'app_type': str,
                'title': str,
                'components': {'App': '...code...'},
                'api_services': [...]
            }
        """
        logger.info(f"[{project_id}] Generating app for: {user_prompt[:100]}...")
        
        # Get prompt with relevant hints
        prompt = get_prompt_for_request(user_prompt)
        
        # Generate
        messages = [
            {"role": "system", "content": "You are an expert React developer. Return ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ]
        response = self.client.chat_completion(messages)
        
        # Parse response
        try:
            # Clean response
            response = response.strip()
            if response.startswith('```'):
                response = response.split('\n', 1)[1]
                response = response.rsplit('```', 1)[0]
            
            result = json.loads(response)
            
            # Validate required fields
            if 'components' not in result or 'App' not in result.get('components', {}):
                raise ValueError("Missing App component")
            
            # Ensure imports are present
            app_code = result['components']['App']
            if 'import React' not in app_code:
                imports = self._detect_needed_imports(app_code)
                app_code = imports + '\n\n' + app_code
                result['components']['App'] = app_code
            
            # Ensure export
            if 'export default' not in app_code:
                app_code += '\n\nexport default App;'
                result['components']['App'] = app_code
            
            logger.info(f"[{project_id}] Generated {result.get('app_type', 'unknown')} app")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"[{project_id}] JSON parse error: {e}")
            logger.error(f"Response was: {response[:500]}")
            
            # Try to extract code anyway
            if 'function App' in response or 'const App' in response:
                return self._extract_code_from_response(response)
            
            raise ValueError(f"Invalid JSON response: {e}")
    
    def modify(self, current_code: str, user_request: str, project_id: int = None) -> str:
        """
        Modify existing app based on user request
        
        Returns: Modified code string
        """
        logger.info(f"[{project_id}] Modifying app: {user_request[:100]}...")
        
        prompt = get_modify_prompt(current_code, user_request)
        
        messages = [
            {"role": "system", "content": "You are an expert React developer. Return ONLY code."},
            {"role": "user", "content": prompt}
        ]
        response = self.client.chat_completion(messages)
        
        # Clean response
        code = response.strip()
        if code.startswith('```'):
            code = code.split('\n', 1)[1]
            code = code.rsplit('```', 1)[0]
        
        # Ensure imports
        if 'import React' not in code:
            imports = self._detect_needed_imports(code)
            code = imports + '\n\n' + code
        
        # Ensure export
        if 'export default' not in code:
            code += '\n\nexport default App;'
        
        return code
    
    def _detect_needed_imports(self, code: str) -> str:
        """Detect and generate needed React imports"""
        hooks = []
        if 'useState' in code:
            hooks.append('useState')
        if 'useEffect' in code:
            hooks.append('useEffect')
        if 'useRef' in code:
            hooks.append('useRef')
        if 'useCallback' in code:
            hooks.append('useCallback')
        if 'useMemo' in code:
            hooks.append('useMemo')
        
        if hooks:
            return f"import React, {{ {', '.join(hooks)} }} from 'react';"
        return "import React from 'react';"
    
    def _extract_code_from_response(self, response: str) -> Dict[str, Any]:
        """Extract code from non-JSON response"""
        # Find the code block
        if '```' in response:
            parts = response.split('```')
            for part in parts:
                if 'function App' in part or 'const App' in part:
                    code = part.strip()
                    if code.startswith('jsx') or code.startswith('javascript') or code.startswith('tsx'):
                        code = code.split('\n', 1)[1]
                    break
            else:
                code = response
        else:
            code = response
        
        # Ensure imports
        if 'import React' not in code:
            imports = self._detect_needed_imports(code)
            code = imports + '\n\n' + code
        
        if 'export default' not in code:
            code += '\n\nexport default App;'
        
        return {
            'app_type': 'website',
            'title': 'Generated App',
            'components': {'App': code},
            'api_services': []
        }

