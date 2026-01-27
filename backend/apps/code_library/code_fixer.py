"""
AI Code Fixer

When esbuild finds a syntax error, this module asks Claude to fix it.
Claude is excellent at fixing specific errors when given precise feedback.

Usage:
    from apps.code_library.code_fixer import fix_code_with_ai
    
    fixed_code = fix_code_with_ai(
        broken_code="const App = () => { return <div>...",
        error_message="Unexpected end of input at line 15"
    )
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def fix_code_with_ai(
    broken_code: str,
    error_message: str,
    attempt: int = 1
) -> Tuple[bool, str]:
    """
    Ask AI to fix code that has a syntax error.
    
    Args:
        broken_code: The code that failed esbuild validation
        error_message: The specific error from esbuild
        attempt: Which retry attempt this is (for logging)
        
    Returns:
        Tuple of (success, fixed_code)
    """
    try:
        from apps.ai_engine.ai_client import AIClient
        
        client = AIClient()
        
        # Create a focused prompt for fixing the specific error
        prompt = f"""You are a React/JSX syntax expert. The following code has a syntax error that must be fixed.

ERROR FROM VALIDATOR:
{error_message}

BROKEN CODE:
```tsx
{broken_code}
```

INSTRUCTIONS:
1. Find the exact syntax error mentioned above
2. Fix ONLY that error - do not change anything else
3. Return the COMPLETE fixed code
4. Do NOT explain - just return the code

CRITICAL RULES:
- Every arrow function must end with }};
- Every JSX tag must be properly closed
- Braces and parentheses must be balanced
- Do not add new features or components
- Do not remove any existing code except to fix the error

Return ONLY the fixed code, no markdown, no explanation:"""

        logger.info(f"[CODE_FIXER] Attempt {attempt}: Asking AI to fix: {error_message[:100]}")
        
        # Use the AIClient's chat_completion method
        messages = [
            {"role": "system", "content": "You are a React/JSX syntax expert. Fix the code error and return only the fixed code."},
            {"role": "user", "content": prompt}
        ]
        
        fixed_code = client.chat_completion(
            messages=messages,
            temperature=0.3  # Lower temperature for precise fixes
        )
        
        # AIClient.chat_completion already strips markdown code blocks
        fixed_code = fixed_code.strip()
        
        logger.info(f"[CODE_FIXER] AI returned {len(fixed_code)} bytes of fixed code")
        
        return True, fixed_code
        
    except Exception as e:
        logger.error(f"[CODE_FIXER] AI fix failed: {e}")
        return False, broken_code


def _search_for_fix_solution(error: str) -> Optional[str]:
    """
    Search web for solutions when stuck on an error.

    Returns context string with solutions or None if search fails.
    """
    try:
        from apps.ai_engine.v6.research import research_topic_sync
        import re

        # Build a search query from the error
        error_lower = error.lower()

        if 'unexpected token' in error_lower:
            query = "React JSX unexpected token syntax error fix"
        elif 'undefined' in error_lower:
            query = "React undefined variable error fix"
        elif 'brace' in error_lower or 'bracket' in error_lower:
            query = "React JSX unbalanced braces syntax error fix"
        elif 'closing tag' in error_lower:
            query = "React JSX closing tag mismatch fix"
        elif 'export' in error_lower:
            query = "React export default component fix"
        else:
            # Extract key terms
            clean_error = re.sub(r'[^\w\s]', ' ', error[:100])
            query = f"React JSX {clean_error} syntax error fix"

        logger.info(f"[CODE_FIXER] Searching for: {query}")

        results = research_topic_sync(
            query,
            language='javascript',
            include_web=True,
            include_github=False,  # Skip GitHub for faster results
            include_packages=False
        )

        if results and results.get('summary'):
            return results['summary'][:1500]  # Limit context length

    except Exception as e:
        logger.warning(f"[CODE_FIXER] Search failed: {e}")

    return None


def fix_code_with_search_context(
    broken_code: str,
    error_message: str,
    search_context: str,
    attempt: int
) -> Tuple[bool, str]:
    """
    Fix code with additional context from web search.
    """
    try:
        from apps.ai_engine.ai_client import AIClient

        client = AIClient()

        prompt = f"""You are a React/JSX syntax expert. The following code has a syntax error that must be fixed.

ERROR FROM VALIDATOR:
{error_message}

HELPFUL CONTEXT FROM DOCUMENTATION:
{search_context}

BROKEN CODE:
```tsx
{broken_code}
```

INSTRUCTIONS:
1. Use the documentation context above to understand how to fix this type of error
2. Find the exact syntax error mentioned
3. Fix ONLY that error - do not change anything else
4. Return the COMPLETE fixed code

Return ONLY the fixed code, no markdown, no explanation:"""

        logger.info(f"[CODE_FIXER] Attempt {attempt} with search context")

        messages = [
            {"role": "system", "content": "You are a React/JSX syntax expert. Use the provided documentation to fix the code error."},
            {"role": "user", "content": prompt}
        ]

        fixed_code = client.chat_completion(
            messages=messages,
            temperature=0.3
        )

        fixed_code = fixed_code.strip()
        logger.info(f"[CODE_FIXER] AI returned {len(fixed_code)} bytes with search context")

        return True, fixed_code

    except Exception as e:
        logger.error(f"[CODE_FIXER] AI fix with search failed: {e}")
        return False, broken_code


def fix_code_loop(
    code: str,
    max_attempts: int = 3,
    use_web_search: bool = True
) -> Tuple[bool, str, str]:
    """
    Validate code with esbuild and retry with AI fixes if needed.

    Enhanced with web search when stuck on errors.

    Args:
        code: The code to validate/fix
        max_attempts: Maximum number of AI fix attempts
        use_web_search: Whether to search for solutions when stuck

    Returns:
        Tuple of (success, final_code, final_error)
    """
    from apps.code_library.jsx_validator import validate_jsx

    current_code = code
    last_error = None
    search_context = None

    for attempt in range(max_attempts + 1):  # +1 because first is validation only
        # Validate with esbuild
        is_valid, error = validate_jsx(current_code)

        if is_valid:
            if attempt > 0:
                logger.info(f"[CODE_FIXER] Fixed after {attempt} AI attempt(s)")
            else:
                logger.info("[CODE_FIXER] Code valid on first try")
            return True, current_code, None

        last_error = error

        # If we've used all attempts, give up
        if attempt >= max_attempts:
            logger.error(f"[CODE_FIXER] Failed after {max_attempts} attempts. Last error: {error}")
            break

        # On 3rd attempt, search for solutions if enabled
        if attempt >= 2 and use_web_search and not search_context:
            logger.info(f"[CODE_FIXER] Stuck on error, searching for solutions...")
            search_context = _search_for_fix_solution(error)
            if search_context:
                logger.info(f"[CODE_FIXER] Found search context: {len(search_context)} chars")

        # Ask AI to fix (with or without search context)
        logger.info(f"[CODE_FIXER] Attempt {attempt + 1}/{max_attempts}: {error[:80]}")

        if search_context:
            success, fixed_code = fix_code_with_search_context(
                current_code, error, search_context, attempt + 1
            )
        else:
            success, fixed_code = fix_code_with_ai(current_code, error, attempt + 1)

        if success and fixed_code != current_code:
            current_code = fixed_code
        else:
            logger.warning(f"[CODE_FIXER] AI didn't change the code, trying again with more context")
            # Add more context on retry
            enhanced_error = f"{error}\n\nPREVIOUS FIX ATTEMPT FAILED. Please look more carefully at the error."

            if search_context:
                success, fixed_code = fix_code_with_search_context(
                    current_code, enhanced_error, search_context, attempt + 1
                )
            else:
                success, fixed_code = fix_code_with_ai(
                    current_code, enhanced_error, attempt + 1
                )

            if success:
                current_code = fixed_code

    return False, current_code, last_error


def fix_code_loop_enhanced(
    code: str,
    error: str,
    max_attempts: int = 5,
    on_progress: callable = None
) -> Tuple[bool, str, dict]:
    """
    Enhanced fix loop with detailed progress tracking.

    Returns:
        Tuple of (success, final_code, stats_dict)
    """
    from apps.code_library.jsx_validator import validate_jsx

    stats = {
        'attempts': 0,
        'errors_encountered': [],
        'search_used': False,
        'search_results': None
    }

    current_code = code
    search_context = None

    for attempt in range(max_attempts):
        stats['attempts'] = attempt + 1

        if on_progress:
            on_progress(f"Fix attempt {attempt + 1}/{max_attempts}")

        # Validate
        is_valid, new_error = validate_jsx(current_code)

        if is_valid:
            logger.info(f"[CODE_FIXER_ENHANCED] Fixed after {attempt + 1} attempts")
            return True, current_code, stats

        stats['errors_encountered'].append(new_error or error)

        # Search on 3rd attempt
        if attempt >= 2 and not search_context:
            if on_progress:
                on_progress("Searching documentation for solutions...")
            search_context = _search_for_fix_solution(new_error or error)
            if search_context:
                stats['search_used'] = True
                stats['search_results'] = search_context[:500]  # Truncate for stats

        # Fix
        if search_context:
            success, fixed_code = fix_code_with_search_context(
                current_code, new_error or error, search_context, attempt + 1
            )
        else:
            success, fixed_code = fix_code_with_ai(
                current_code, new_error or error, attempt + 1
            )

        if success and fixed_code:
            current_code = fixed_code

    return False, current_code, stats
