"""
JSX Validator using esbuild

This module validates JSX/TSX code using esbuild, which is:
- Fast (<10ms per file)
- Accurate (real parser, not regex)
- Definitive (if it parses, it's valid)

Usage:
    from apps.code_library.jsx_validator import validate_jsx, is_valid_jsx
    
    valid, error = validate_jsx(code)
    if not valid:
        # Retry AI generation with error message
        pass
"""

import subprocess
import tempfile
import os
import json
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Check if esbuild is available
_esbuild_available = None


def _get_esbuild_path() -> Optional[str]:
    """Get the path to esbuild binary."""
    import shutil
    
    # This file is at: backend/apps/code_library/jsx_validator.py
    # node_modules is at: backend/node_modules
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    # Check for local node_modules first
    local_esbuild = os.path.join(backend_dir, 'node_modules', '.bin', 'esbuild')
    if os.path.exists(local_esbuild):
        return local_esbuild
    
    # Also try relative to current working directory
    cwd_esbuild = os.path.join(os.getcwd(), 'node_modules', '.bin', 'esbuild')
    if os.path.exists(cwd_esbuild):
        return cwd_esbuild
    
    # Check system path
    esbuild_path = shutil.which('esbuild')
    if esbuild_path:
        return esbuild_path
    
    return None


def _check_esbuild() -> bool:
    """Check if esbuild is installed and available."""
    global _esbuild_available
    
    if _esbuild_available is not None:
        return _esbuild_available
    
    esbuild_path = _get_esbuild_path()
    if esbuild_path:
        try:
            result = subprocess.run(
                [esbuild_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            _esbuild_available = result.returncode == 0
            if _esbuild_available:
                logger.info(f"[JSX_VALIDATOR] esbuild available at {esbuild_path}: {result.stdout.strip()}")
            else:
                logger.warning("[JSX_VALIDATOR] esbuild not available")
        except Exception as e:
            logger.warning(f"[JSX_VALIDATOR] esbuild check failed: {e}")
            _esbuild_available = False
    else:
        logger.warning("[JSX_VALIDATOR] esbuild binary not found")
        _esbuild_available = False
    
    return _esbuild_available


def validate_jsx(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate JSX/TSX code.
    
    Strategy:
    1. Try esbuild if available (most accurate)
    2. Fall back to Python-based validation (always works)
    
    Args:
        code: The JSX/TSX code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if code is valid
        - (False, "error description") if code is invalid
    """
    if not code or not code.strip():
        return False, "Empty code"
    
    # Try esbuild first (if available)
    if _check_esbuild():
        return _validate_with_esbuild(code)
    
    # Fallback: Python-based validation (always works, good enough)
    logger.info("[JSX_VALIDATOR] Using Python fallback validation")
    return _fallback_validate(code)


def _validate_with_esbuild(code: str) -> Tuple[bool, Optional[str]]:
    """Validate using esbuild (when available)."""
    # Write code to temp file
    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.tsx', 
        delete=False,
        encoding='utf-8'
    ) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        esbuild_path = _get_esbuild_path()
        if not esbuild_path:
            return _fallback_validate(code)
        
        # Run esbuild to parse/transform (not bundle)
        # The file already has .tsx extension, so esbuild will infer the loader
        result = subprocess.run(
            [
                esbuild_path,
                temp_path,
                '--format=esm',
                '--jsx=preserve',  # Don't transform JSX, just validate syntax
                '--log-level=error',
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.debug("[JSX_VALIDATOR] Code is valid")
            return True, None
        else:
            # Extract meaningful error from stderr
            error = _parse_esbuild_error(result.stderr)
            logger.warning(f"[JSX_VALIDATOR] Invalid code: {error}")
            return False, error
            
    except subprocess.TimeoutExpired:
        logger.error("[JSX_VALIDATOR] esbuild timed out")
        return False, "Validation timed out"
    except Exception as e:
        logger.error(f"[JSX_VALIDATOR] Validation error: {e}")
        return False, str(e)
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass


def _parse_esbuild_error(stderr: str) -> str:
    """Extract a clean error message from esbuild stderr."""
    if not stderr:
        return "Unknown syntax error"
    
    lines = stderr.strip().split('\n')
    
    # esbuild format: "file.tsx:LINE:COL: error: MESSAGE"
    for line in lines:
        if 'error:' in line:
            # Extract just the error part
            parts = line.split('error:', 1)
            if len(parts) > 1:
                return f"Syntax error: {parts[1].strip()}"
    
    # Return first line if no standard error found
    return lines[0][:200] if lines else "Unknown syntax error"


def _fallback_validate(code: str) -> Tuple[bool, Optional[str]]:
    """
    Python-based validation when esbuild is not available.
    
    Catches:
    - Unbalanced braces/parentheses
    - Missing component closures (};)
    - Missing App component
    - Missing export
    - Unclosed arrow functions
    """
    import re
    errors = []
    
    # Check brace balance
    open_braces = code.count('{')
    close_braces = code.count('}')
    if open_braces != close_braces:
        diff = abs(open_braces - close_braces)
        if open_braces > close_braces:
            errors.append(f"Missing {diff} closing brace(s)")
        else:
            errors.append(f"Extra {diff} closing brace(s)")
    
    # Check parenthesis balance
    open_parens = code.count('(')
    close_parens = code.count(')')
    if open_parens != close_parens:
        diff = abs(open_parens - close_parens)
        if open_parens > close_parens:
            errors.append(f"Missing {diff} closing parenthesis")
        else:
            errors.append(f"Extra {diff} closing parenthesis")
    
    # Check for required patterns
    if 'function App' not in code and 'const App' not in code:
        errors.append("Missing App component")
    
    if 'export default' not in code:
        errors.append("Missing export default")
    
    # Check for unclosed arrow functions
    # Pattern: `const X = (...) => {` should have matching `};`
    arrow_funcs = re.findall(r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{', code)
    for func_name in arrow_funcs:
        # Check if there's a proper closure pattern after this function
        # This is a heuristic - look for `};\n\n` or `};\nexport` patterns
        pattern = rf'const\s+{func_name}\s*=.*?(\}};)'
        if not re.search(pattern, code, re.DOTALL):
            # More lenient check - just ensure }; exists somewhere after the function
            func_start = code.find(f'const {func_name}')
            if func_start != -1:
                after_func = code[func_start:]
                # Count braces in this function's scope
                depth = 0
                found_closure = False
                for i, char in enumerate(after_func):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            # Check if followed by ;
                            remaining = after_func[i:i+2]
                            if remaining == '};':
                                found_closure = True
                            break
                
                if not found_closure and depth != 0:
                    errors.append(f"Component '{func_name}' may be missing closing '}}; '")
    
    # Check for obviously broken JSX
    # Pattern: `<div>` without `</div>` (simple check)
    open_divs = len(re.findall(r'<div[\s>]', code))
    close_divs = len(re.findall(r'</div>', code))
    if open_divs > close_divs:
        errors.append(f"Unclosed <div> tag(s): {open_divs} open, {close_divs} close")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, None


def is_valid_jsx(code: str) -> bool:
    """
    Simple boolean check if code is valid.
    
    Use validate_jsx() if you need the error message.
    """
    valid, _ = validate_jsx(code)
    return valid


def transform_jsx(code: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate AND transform JSX/TSX to browser-compatible JavaScript.
    
    This replaces _convert_to_browser_react() with a proper transformation.
    
    Args:
        code: The JSX/TSX code
        
    Returns:
        Tuple of (success, transformed_code, error)
    """
    if not code or not code.strip():
        return False, code, "Empty code"
    
    if not _check_esbuild():
        logger.warning("[JSX_VALIDATOR] esbuild not available for transform")
        return False, code, "esbuild not available"
    
    # Write code to temp file
    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.tsx', 
        delete=False,
        encoding='utf-8'
    ) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        esbuild_path = _get_esbuild_path()
        if not esbuild_path:
            return False, code, "esbuild not available"
        
        # Transform TypeScript/JSX to plain JavaScript
        result = subprocess.run(
            [
                esbuild_path,
                temp_path,
                '--format=iife',  # Immediately invoked, works in browser
                '--jsx=automatic',  # Modern JSX transform
                '--jsx-import-source=react',
                '--target=es2020',
                '--log-level=error',
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            transformed = result.stdout
            logger.info(f"[JSX_VALIDATOR] Transformed {len(code)} bytes to {len(transformed)} bytes")
            return True, transformed, None
        else:
            error = _parse_esbuild_error(result.stderr)
            logger.warning(f"[JSX_VALIDATOR] Transform failed: {error}")
            return False, code, error
            
    except Exception as e:
        logger.error(f"[JSX_VALIDATOR] Transform error: {e}")
        return False, code, str(e)
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


# Self-test on module load
if __name__ == "__main__":
    # Test with valid code
    valid_code = """
    const App = () => {
        return <div>Hello World</div>;
    };
    export default App;
    """
    
    valid, error = validate_jsx(valid_code)
    print(f"Valid code test: valid={valid}, error={error}")
    
    # Test with invalid code
    invalid_code = """
    const App = () => {
        return <div>Missing closing
    };
    export default App;
    """
    
    valid, error = validate_jsx(invalid_code)
    print(f"Invalid code test: valid={valid}, error={error}")
