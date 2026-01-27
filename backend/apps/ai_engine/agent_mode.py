"""
Agent Mode - Autonomous development with debugging, self-correction, and web search.

Enhanced for v2 with:
- Self-correcting builds (validates JSX and auto-fixes errors)
- Error detection loop (parses errors and feeds back to AI)
- Web search for solutions (searches docs when stuck)
"""
import logging
import re
import asyncio
from typing import Dict, List, Optional, Tuple
from anthropic import Anthropic

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = '''You are an autonomous development agent specialized in React/JSX. You can:
1. Generate and modify code
2. Debug errors by analyzing stack traces and syntax errors
3. Search documentation when needed
4. Make multiple iterations to fix issues autonomously

When given a task:
- Analyze the requirements thoroughly
- Generate COMPLETE, VALID JSX code
- If you encounter an error, analyze it carefully and fix it
- Continue iterating until the code validates successfully

CRITICAL RULES for generating JSX:
- Always include `function App` or `const App` component
- Always include `export default App;` at the end
- Ensure all braces {} and parentheses () are balanced
- Close all JSX tags properly
- Use defensive array patterns: {(items || []).map(...)}
- Never use undefined variables or icons

When fixing errors:
1. Read the error message carefully
2. Identify the exact line and issue
3. Provide the COMPLETE fixed code, not just the changed lines
4. Verify your fix addresses the specific error

Always explain your reasoning at each step.
'''

ERROR_FIX_PROMPT = '''The previous code had a validation error:

ERROR: {error}

Please analyze this error and provide a COMPLETE fixed version of the code.
Focus on:
1. The specific error mentioned above
2. Ensuring all JSX syntax is valid
3. Balancing all braces and parentheses
4. Properly closing all tags

Provide the complete fixed code:'''

SEARCH_CONTEXT_PROMPT = '''I searched for solutions and found this relevant information:

{search_results}

Based on this information, please fix the error in the code.
The error was: {error}

Provide the complete fixed code:'''


class AgentModeService:
    """
    Enhanced autonomous agent with self-correcting builds.

    Features:
    - JSX validation with esbuild
    - Automatic error detection and fix loop
    - Web search for solutions when stuck
    - Max 5 fix attempts before escalating
    """

    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.client = Anthropic()
        self.conversation_history: List[Dict] = []
        self.iteration_count = 0
        self.max_iterations = 10
        self.fix_attempts = 0
        self.max_fix_attempts = 5
        self.errors_encountered: List[str] = []
        self.search_used = False

    def run_agent_task(self, task_description: str, current_code: str = None) -> Dict:
        """Run an autonomous agent task with self-correction."""
        self.conversation_history.append({
            'role': 'user',
            'content': f"Task: {task_description}\n\nCurrent code:\n{current_code or 'No code yet'}"
        })

        while self.iteration_count < self.max_iterations:
            response = self._call_ai()

            # Extract code from response
            code = self._extract_code(response)

            if code:
                # Validate the generated code
                is_valid, error = self._validate_code(code)

                if is_valid:
                    logger.info(f"[AGENT] Code validated successfully after {self.iteration_count} iterations")
                    return {
                        'status': 'complete',
                        'code': code,
                        'result': response,
                        'iterations': self.iteration_count,
                        'fix_attempts': self.fix_attempts,
                        'errors_fixed': self.errors_encountered
                    }
                else:
                    # Self-correction: feed error back to AI
                    logger.warning(f"[AGENT] Validation failed: {error}")
                    self._handle_validation_error(error, code)

            if self._is_task_complete(response):
                return {
                    'status': 'complete',
                    'result': response,
                    'iterations': self.iteration_count
                }

            self.iteration_count += 1

        return {
            'status': 'max_iterations',
            'result': response,
            'iterations': self.iteration_count,
            'errors': self.errors_encountered
        }

    def _call_ai(self) -> str:
        """Call Claude API with conversation history."""
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=AGENT_SYSTEM_PROMPT,
            messages=self.conversation_history
        )
        content = response.content[0].text
        self.conversation_history.append({'role': 'assistant', 'content': content})
        return content

    def _extract_code(self, response: str) -> Optional[str]:
        """Extract JSX code from AI response."""
        # Try to find code blocks
        code_patterns = [
            r'```jsx\n(.*?)```',
            r'```javascript\n(.*?)```',
            r'```tsx\n(.*?)```',
            r'```\n(.*?)```',
        ]

        for pattern in code_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                code = match.group(1).strip()
                if 'function App' in code or 'const App' in code:
                    return code

        # Check if response itself looks like code
        if 'function App' in response or 'const App' in response:
            # Extract from start of component to export
            start_patterns = [r'(const\s+\w+\s*=.*)', r'(function\s+\w+.*)']
            for pattern in start_patterns:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    potential_code = match.group(1)
                    if 'export default' in potential_code:
                        return potential_code

        return None

    def _validate_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate JSX code using the jsx_validator."""
        try:
            from apps.code_library.jsx_validator import validate_jsx
            return validate_jsx(code)
        except ImportError:
            logger.warning("[AGENT] jsx_validator not available, using fallback")
            return self._fallback_validate(code)

    def _fallback_validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """Basic validation when esbuild not available."""
        errors = []

        # Check brace balance
        if code.count('{') != code.count('}'):
            errors.append(f"Unbalanced braces: {code.count('{')} open, {code.count('}')} close")

        # Check parenthesis balance
        if code.count('(') != code.count(')'):
            errors.append(f"Unbalanced parentheses: {code.count('(')} open, {code.count(')')} close")

        # Check for App component
        if 'function App' not in code and 'const App' not in code:
            errors.append("Missing App component")

        # Check for export
        if 'export default' not in code:
            errors.append("Missing export default")

        if errors:
            return False, "; ".join(errors)
        return True, None

    def _handle_validation_error(self, error: str, code: str):
        """Handle validation error by requesting a fix from AI."""
        self.fix_attempts += 1
        self.errors_encountered.append(error)

        logger.info(f"[AGENT] Fix attempt {self.fix_attempts}/{self.max_fix_attempts} for: {error}")

        # If we've tried multiple times, search for solutions
        if self.fix_attempts >= 3 and not self.search_used:
            self._search_for_solution(error)
            self.search_used = True

        # Build fix prompt with error context
        fix_prompt = ERROR_FIX_PROMPT.format(error=error)

        # Add the problematic code snippet if error mentions line number
        line_match = re.search(r'line\s*(\d+)', error, re.IGNORECASE)
        if line_match:
            line_num = int(line_match.group(1))
            lines = code.split('\n')
            start = max(0, line_num - 3)
            end = min(len(lines), line_num + 3)
            context_lines = lines[start:end]
            fix_prompt += f"\n\nContext around line {line_num}:\n```\n" + '\n'.join(
                f"{i+start+1}: {line}" for i, line in enumerate(context_lines)
            ) + "\n```"

        self.conversation_history.append({
            'role': 'user',
            'content': fix_prompt
        })

    def _search_for_solution(self, error: str):
        """Search web/docs for solution when stuck on an error."""
        logger.info(f"[AGENT] Searching for solution to: {error}")

        try:
            from apps.ai_engine.v6.research import research_topic_sync

            # Build search query from error
            search_query = self._build_search_query(error)

            # Run synchronous research
            results = research_topic_sync(
                search_query,
                language='javascript',
                include_web=True,
                include_github=True,
                include_packages=False
            )

            if results and results.get('summary'):
                # Add search results to conversation
                search_context = SEARCH_CONTEXT_PROMPT.format(
                    search_results=results['summary'][:2000],  # Limit length
                    error=error
                )
                self.conversation_history.append({
                    'role': 'user',
                    'content': search_context
                })
                logger.info(f"[AGENT] Added search context: {len(results.get('summary', ''))} chars")

        except Exception as e:
            logger.warning(f"[AGENT] Search failed: {e}")

    def _build_search_query(self, error: str) -> str:
        """Build a search query from an error message."""
        # Extract key terms from error
        error_lower = error.lower()

        if 'unexpected token' in error_lower:
            return "React JSX unexpected token syntax error fix"
        elif 'undefined' in error_lower:
            return "React undefined variable error fix"
        elif 'brace' in error_lower or 'bracket' in error_lower:
            return "React JSX unbalanced braces syntax error"
        elif 'export' in error_lower:
            return "React export default App component"
        elif 'map' in error_lower:
            return "React map undefined array defensive pattern"
        else:
            # Generic query with first part of error
            clean_error = re.sub(r'[^\w\s]', ' ', error[:100])
            return f"React JSX {clean_error} fix"

    def _is_task_complete(self, response: str) -> bool:
        """Check if AI indicates task is complete."""
        markers = ['TASK_COMPLETE', 'task is complete', 'code is complete', 'successfully generated']
        return any(marker.lower() in response.lower() for marker in markers)


def self_correcting_build(
    prompt: str,
    max_attempts: int = 3,
    on_progress: callable = None
) -> Dict:
    """
    High-level function for self-correcting code generation.

    This is the main entry point for the enhanced agent mode.
    Uses the component pipeline but adds automatic error correction.

    Args:
        prompt: User's build request
        max_attempts: Maximum number of generation attempts
        on_progress: Optional callback for progress updates

    Returns:
        Dict with 'success', 'code', 'error', and 'attempts'
    """
    from apps.code_library.component_pipeline import ComponentPipeline
    from apps.code_library.jsx_validator import validate_jsx

    attempt = 0
    last_error = None
    errors_fixed = []

    while attempt < max_attempts:
        attempt += 1

        if on_progress:
            on_progress(f"Build attempt {attempt}/{max_attempts}")

        # If we have a previous error, add it to the prompt
        enhanced_prompt = prompt
        if last_error:
            enhanced_prompt = f"""{prompt}

IMPORTANT: The previous attempt had this error: {last_error}
Please fix this error in the new code."""
            errors_fixed.append(last_error)

        try:
            # Use component pipeline
            pipeline = ComponentPipeline(
                project_id=None,
                progress_callback=on_progress
            )
            code = pipeline.build(enhanced_prompt)

            # Validate
            is_valid, error = validate_jsx(code)

            if is_valid:
                logger.info(f"[SELF_CORRECT] Build succeeded on attempt {attempt}")
                return {
                    'success': True,
                    'code': code,
                    'attempts': attempt,
                    'errors_fixed': errors_fixed
                }
            else:
                logger.warning(f"[SELF_CORRECT] Validation failed: {error}")
                last_error = error

        except Exception as e:
            logger.error(f"[SELF_CORRECT] Build error: {e}")
            last_error = str(e)

    # All attempts failed
    logger.error(f"[SELF_CORRECT] All {max_attempts} attempts failed")
    return {
        'success': False,
        'code': None,
        'error': last_error,
        'attempts': max_attempts,
        'errors_encountered': errors_fixed
    }
