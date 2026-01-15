"""
Code Complexity Detection

Per Base44 lessons: Run "refactoring tests" behind the scenes.
When code files exceed efficiency thresholds, signal the LLM to refactor
BEFORE implementing new features.

This prevents the common problem of increasingly unmaintainable code
as features layer on.
"""

import re
from typing import Dict, Tuple


def measure_complexity(code: str) -> Dict:
    """
    Measure code complexity metrics.

    Returns dict with metrics and a needs_refactor flag.

    Thresholds (per Base44 lessons):
    - Line count > 300: Too large, split into components
    - Nesting depth > 5: Too deeply nested, flatten
    - Function count > 15: Too many functions, modularize
    """
    if not code:
        return {
            'line_count': 0,
            'function_count': 0,
            'nesting_depth': 0,
            'component_count': 0,
            'needs_refactor': False,
            'refactor_reasons': []
        }

    lines = code.split('\n')
    line_count = len(lines)

    # Count functions (arrow functions and regular functions)
    arrow_functions = len(re.findall(r'=>\s*\{', code))
    regular_functions = len(re.findall(r'function\s+\w+', code))
    const_functions = len(re.findall(r'const\s+\w+\s*=\s*\([^)]*\)\s*=>', code))
    function_count = arrow_functions + regular_functions + const_functions

    # Count React components (PascalCase const declarations)
    component_count = len(re.findall(r'const\s+[A-Z][a-zA-Z]+\s*=', code))

    # Measure max nesting depth
    nesting_depth = max_nesting_depth(code)

    # Determine if refactoring is needed
    refactor_reasons = []

    if line_count > 300:
        refactor_reasons.append(f"Code too long ({line_count} lines > 300)")

    if nesting_depth > 5:
        refactor_reasons.append(f"Too deeply nested (depth {nesting_depth} > 5)")

    if function_count > 15:
        refactor_reasons.append(f"Too many functions ({function_count} > 15)")

    if component_count > 10:
        refactor_reasons.append(f"Too many components ({component_count} > 10)")

    return {
        'line_count': line_count,
        'function_count': function_count,
        'nesting_depth': nesting_depth,
        'component_count': component_count,
        'needs_refactor': len(refactor_reasons) > 0,
        'refactor_reasons': refactor_reasons
    }


def max_nesting_depth(code: str) -> int:
    """
    Count max brace nesting depth.

    Ignores braces in strings and comments.
    """
    depth = 0
    max_depth = 0
    in_string = False
    string_char = None
    in_comment = False
    in_block_comment = False
    prev_char = ''

    for i, char in enumerate(code):
        # Handle string state
        if not in_comment and not in_block_comment:
            if char in '"\'`' and prev_char != '\\':
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None

        # Handle comments
        if not in_string:
            if char == '/' and i + 1 < len(code):
                next_char = code[i + 1]
                if next_char == '/':
                    in_comment = True
                elif next_char == '*':
                    in_block_comment = True

            if char == '\n':
                in_comment = False

            if char == '/' and prev_char == '*':
                in_block_comment = False

        # Count braces only outside strings and comments
        if not in_string and not in_comment and not in_block_comment:
            if char == '{':
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == '}':
                depth = max(0, depth - 1)

        prev_char = char

    return max_depth


def get_refactor_prompt_injection(metrics: Dict) -> str:
    """
    Generate a prompt injection telling the AI to refactor.

    Only returns content if refactoring is needed.
    """
    if not metrics.get('needs_refactor'):
        return ""

    reasons = metrics.get('refactor_reasons', [])

    return f"""
REFACTORING REQUIRED (per Base44 best practices):

The existing code exceeds complexity thresholds:
{chr(10).join(f'- {r}' for r in reasons)}

BEFORE adding new features, you MUST:
1. Split large components into smaller, focused components
2. Extract repeated logic into utility functions
3. Flatten deeply nested code with early returns
4. Use composition over inheritance

Keep each component under 100 lines.
Keep nesting depth under 4 levels.
Keep function count under 10 per file.
"""


def check_and_warn(code: str, context: str = "") -> Tuple[bool, str]:
    """
    Check code complexity and return warning message if needed.

    Returns:
        Tuple of (needs_refactor, warning_message)
    """
    metrics = measure_complexity(code)

    if metrics['needs_refactor']:
        reasons = metrics['refactor_reasons']
        warning = f"[COMPLEXITY] {context}: Code needs refactoring - {', '.join(reasons)}"
        return True, warning

    return False, ""


# Integration with component pipeline
def should_refactor_before_feature(existing_code: str) -> bool:
    """
    Check if existing code should be refactored before adding features.

    Per Base44: "When code files exceed efficiency thresholds, the system
    signals the LLM to refactor BEFORE implementing new features."
    """
    metrics = measure_complexity(existing_code)
    return metrics['needs_refactor']
