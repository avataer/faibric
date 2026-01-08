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


def fix_code_loop(
    code: str,
    max_attempts: int = 3
) -> Tuple[bool, str, str]:
    """
    Validate code with esbuild and retry with AI fixes if needed.
    
    Args:
        code: The code to validate/fix
        max_attempts: Maximum number of AI fix attempts
        
    Returns:
        Tuple of (success, final_code, final_error)
    """
    from apps.code_library.jsx_validator import validate_jsx
    
    current_code = code
    last_error = None
    
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
        
        # Ask AI to fix
        logger.info(f"[CODE_FIXER] Attempt {attempt + 1}/{max_attempts}: {error[:80]}")
        success, fixed_code = fix_code_with_ai(current_code, error, attempt + 1)
        
        if success and fixed_code != current_code:
            current_code = fixed_code
        else:
            logger.warning(f"[CODE_FIXER] AI didn't change the code, trying again with more context")
            # Add more context on retry
            success, fixed_code = fix_code_with_ai(
                current_code, 
                f"{error}\n\nPREVIOUS FIX ATTEMPT FAILED. Please look more carefully at the error.",
                attempt + 1
            )
            if success:
                current_code = fixed_code
    
    return False, current_code, last_error
