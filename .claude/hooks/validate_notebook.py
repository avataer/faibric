#!/usr/bin/env python3
"""NotebookEdit validator. Same rules as Edit validator. Fail-closed."""

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

# TypeScript syntax patterns
TYPESCRIPT_PATTERNS = [
    (r':\s*(string|number|boolean|any|void|never|unknown|object)\s*[=;,)\]]', "Type annotation"),
    (r':\s*\w+\[\]\s*[=;,)\]]', "Array type annotation"),
    (r':\s*Promise<', "Promise type annotation"),
    (r'<[A-Z]\w*>\s*\(', "Generic type parameter"),
    (r'\binterface\s+\w+\s*\{', "Interface declaration"),
    (r'\btype\s+\w+\s*=', "Type alias"),
    (r'\bas\s+(string|number|boolean|any|unknown)', "Type casting with as"),
    (r'\)\s*:\s*(string|number|boolean|void|Promise)', "Function return type"),
    (r'\w+!\s*[.;]', "Non-null assertion"),
]


def check_for_emojis(content):
    """Check if content contains emojis."""
    matches = EMOJI_PATTERN.findall(content)
    if matches:
        return True, f"Contains emojis: {matches[:3]}"
    return False, None


def check_for_typescript(content, notebook_path):
    """Check if notebook cell contains TypeScript in a JS context."""
    if not notebook_path:
        return False, None

    # Only check JavaScript notebooks
    if not any(ext in notebook_path.lower() for ext in ['.js', 'javascript']):
        return False, None

    for pattern, description in TYPESCRIPT_PATTERNS:
        if re.search(pattern, content):
            return True, f"TypeScript syntax in JS notebook: {description}"

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
    notebook_path = tool_input.get("notebook_path", "")
    new_source = tool_input.get("new_source", "")

    # Check new_source for emojis
    has_emojis, emoji_reason = check_for_emojis(new_source)
    if has_emojis:
        result = {
            "continueExecution": False,
            "message": emoji_reason
        }
        print(json.dumps(result))
        return

    # Check for TypeScript in JS notebooks
    has_ts, ts_reason = check_for_typescript(new_source, notebook_path)
    if has_ts:
        result = {
            "continueExecution": False,
            "message": ts_reason
        }
        print(json.dumps(result))
        return

    # All checks passed
    result = {"continueExecution": True}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
