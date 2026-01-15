"""
No Regex for JSX Validator

Detects regex patterns that modify JSX/JavaScript code.
This is a bad practice that hides bugs instead of fixing them.
Returns (passed, message) tuple.
"""

import re

FORBIDDEN_PATTERNS = [
    # Python re.sub modifying JSX
    (r're\.sub\s*\([^)]*onClick', 'Regex modifying onClick handlers'),
    (r're\.sub\s*\([^)]*className', 'Regex modifying className'),
    (r're\.sub\s*\([^)]*handle[A-Z]\w*', 'Regex modifying handler functions'),
    (r're\.sub\s*\([^)]*undefined', 'Regex replacing undefined references'),
    (r're\.sub\s*\([^)]*<\s*\w+', 'Regex modifying JSX tags'),

    # JavaScript .replace modifying JSX
    (r'\.replace\s*\([^)]*onClick', 'String replace modifying onClick'),
    (r'\.replace\s*\([^)]*className', 'String replace modifying className'),
    (r'\.replace\s*\([^)]*<\s*\w+', 'String replace modifying JSX tags'),

    # Sed commands modifying JS/JSX
    (r"sed\s+.*'s/.*onClick", 'Sed modifying onClick handlers'),
    (r"sed\s+.*'s/.*className", 'Sed modifying className'),
]


def validate(content: str, file_path: str) -> tuple[bool, str]:
    """
    Check content for regex-based JSX modifications.
    Only checks Python and shell scripts.
    Returns (passed, message).
    """
    if not file_path.endswith(('.py', '.sh', '.bash')):
        return True, ""

    for pattern, description in FORBIDDEN_PATTERNS:
        match = re.search(pattern, content)
        if match:
            line_num = content[:match.start()].count('\n') + 1
            return False, f"Regex JSX fix at line {line_num}: {description}. Fix the AI prompt instead."

    return True, ""
