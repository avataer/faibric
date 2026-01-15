#!/usr/bin/env python3
"""Edit tool validator. Blocks emojis, TypeScript in JS files. Fail-closed."""

import json
import re
import sys


# Unicode emoji ranges
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-c
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    "\U00002702-\U000027B0"  # dingbats
    "\U00002300-\U000023FF"  # misc technical (includes some emoji)
    "\U0001F1E0-\U0001F1FF"  # flags
    "]+",
    re.UNICODE
)

# TypeScript syntax patterns that should not appear in .js/.jsx files
TYPESCRIPT_PATTERNS = [
    # Type annotations
    (r':\s*(string|number|boolean|any|void|never|unknown|object)\s*[=;,)\]]', "Type annotation"),
    (r':\s*\w+\[\]\s*[=;,)\]]', "Array type annotation"),
    (r':\s*Promise<', "Promise type annotation"),
    (r':\s*React\.\w+', "React type annotation"),
    (r':\s*\{[^}]*:\s*(string|number|boolean)', "Object type annotation"),

    # Generic type parameters
    (r'<[A-Z]\w*>\s*\(', "Generic type parameter"),
    (r'<[A-Z]\w*,\s*[A-Z]\w*>', "Multiple generic types"),

    # Interface and type declarations
    (r'\binterface\s+\w+\s*\{', "Interface declaration"),
    (r'\btype\s+\w+\s*=', "Type alias"),

    # as keyword for type casting
    (r'\bas\s+(string|number|boolean|any|unknown|\w+Type|\w+Props)', "Type casting with as"),

    # Function return types
    (r'\)\s*:\s*(string|number|boolean|void|Promise|React)', "Function return type"),

    # Non-null assertion
    (r'\w+!\s*[.;]', "Non-null assertion"),
]


def check_for_emojis(content):
    """Check if content contains emojis."""
    matches = EMOJI_PATTERN.findall(content)
    if matches:
        return True, f"Contains emojis: {matches[:3]}"
    return False, None


def check_for_typescript(content, file_path):
    """Check if JS/JSX file contains TypeScript syntax."""
    if not file_path:
        return False, None

    # Only check .js and .jsx files
    if not (file_path.endswith('.js') or file_path.endswith('.jsx')):
        return False, None

    for pattern, description in TYPESCRIPT_PATTERNS:
        if re.search(pattern, content):
            return True, f"TypeScript syntax in JS file: {description}"

    return False, None


def check_for_regex_jsx_fix(old_string, new_string):
    """Block regex-based JSX fixes that might break code."""
    # Detect suspicious JSX transformations
    suspicious_patterns = [
        # Self-closing to paired tags in bulk
        (r'<(\w+)\s*/>', r'<\1></\1>'),
        # Changing multiple attributes at once with regex-like patterns
        (r'\{\.\.\.(\w+)\}', r'\{...\1\}'),
    ]

    for old_pattern, new_pattern in suspicious_patterns:
        if re.search(old_pattern, old_string) and re.search(new_pattern, new_string):
            return True, "Suspicious regex-based JSX transformation"

    return False, None


def main():
    """Main validator entry point."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # Fail-closed: deny on parse error
        result = {
            "continueExecution": False,
            "message": f"Failed to parse input JSON: {e}"
        }
        print(json.dumps(result))
        return

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    old_string = tool_input.get("old_string", "")
    new_string = tool_input.get("new_string", "")

    # Check new_string for emojis
    has_emojis, emoji_reason = check_for_emojis(new_string)
    if has_emojis:
        result = {
            "continueExecution": False,
            "message": emoji_reason
        }
        print(json.dumps(result))
        return

    # Check for TypeScript in JS files
    has_ts, ts_reason = check_for_typescript(new_string, file_path)
    if has_ts:
        result = {
            "continueExecution": False,
            "message": ts_reason
        }
        print(json.dumps(result))
        return

    # Check for regex JSX fixes
    is_regex_fix, regex_reason = check_for_regex_jsx_fix(old_string, new_string)
    if is_regex_fix:
        result = {
            "continueExecution": False,
            "message": regex_reason
        }
        print(json.dumps(result))
        return

    # All checks passed
    result = {"continueExecution": True}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
