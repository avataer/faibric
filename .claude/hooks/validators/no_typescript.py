"""
No TypeScript Validator

Detects TypeScript syntax in .js/.jsx files.
Returns (passed, message) tuple.
"""

import re

TYPESCRIPT_PATTERNS = [
    # Type annotations on variables
    (r'(?:const|let|var)\s+\w+\s*:\s*(?:string|number|boolean|any|void|null|undefined|object|never|unknown)',
     'Type annotation on variable'),

    # Type annotations on function parameters
    (r'\(\s*\w+\s*:\s*(?:string|number|boolean|any|void|React\.\w+)',
     'Type annotation on parameter'),

    # Return type annotations
    (r'\)\s*:\s*(?:string|number|boolean|void|JSX\.Element|React\.\w+)\s*(?:=>|\{)',
     'Return type annotation'),

    # React.FC type
    (r':\s*React\.FC(?:<[^>]*>)?',
     'React.FC type annotation'),

    # Generic types on hooks
    (r'(?:useState|useRef|useMemo|useCallback|useReducer)<[^>]+>',
     'Generic type on React hook'),

    # Interface declarations
    (r'^\s*interface\s+\w+\s*(?:<[^>]*>)?\s*\{',
     'Interface declaration'),

    # Type declarations
    (r'^\s*type\s+\w+\s*(?:<[^>]*>)?\s*=',
     'Type declaration'),

    # Type imports
    (r'import\s+type\s+',
     'Type import'),

    # As type casts
    (r'\s+as\s+(?:string|number|boolean|any|const|unknown|never)(?:\[\])?\s*[;\),]',
     'Type cast'),
]


def validate(content: str, file_path: str) -> tuple[bool, str]:
    """
    Check content for TypeScript syntax.
    Only checks .js and .jsx files.
    Returns (passed, message).
    """
    if not file_path.endswith(('.js', '.jsx')):
        return True, ""

    for pattern, description in TYPESCRIPT_PATTERNS:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            line_num = content[:match.start()].count('\n') + 1
            return False, f"TypeScript detected at line {line_num}: {description}. Use plain JavaScript."

    return True, ""
