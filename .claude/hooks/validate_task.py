#!/usr/bin/env python3
"""Task tool validator. Blocks bypass instructions to subagents. Fail-closed."""

import json
import re
import sys


# Patterns that indicate bypass attempts in task prompts
BYPASS_PATTERNS = [
    # Direct bypass instructions
    (r'ignore\s+(previous\s+)?(instructions?|rules?|constraints?|guidelines?)', "Ignore instructions"),
    (r'disregard\s+(previous\s+)?(instructions?|rules?|constraints?)', "Disregard instructions"),
    (r'skip\s+(the\s+)?(validation|checks?|rules?|hooks?)', "Skip validation"),
    (r'bypass\s+(the\s+)?(validation|checks?|rules?|hooks?|security)', "Bypass validation"),
    (r'disable\s+(the\s+)?(validation|checks?|rules?|hooks?)', "Disable validation"),
    (r'turn\s+off\s+(validation|checks?|rules?|hooks?)', "Turn off validation"),

    # Override attempts
    (r'override\s+(the\s+)?(rules?|restrictions?|constraints?)', "Override rules"),
    (r'circumvent\s+(the\s+)?(rules?|restrictions?|validation)', "Circumvent rules"),
    (r'work\s+around\s+(the\s+)?(rules?|restrictions?|validation)', "Work around rules"),

    # Permission escalation
    (r'pretend\s+(you\s+)?(have|are)\s+(no\s+restrictions?|admin|root)', "Pretend permissions"),
    (r'act\s+as\s+if\s+(there\s+are\s+)?no\s+rules?', "Act without rules"),
    (r'assume\s+(you\s+)?(can|have)\s+(full|admin|root)\s+access', "Assume elevated access"),

    # Instruction injection
    (r'new\s+instructions?\s*:', "New instructions injection"),
    (r'system\s+prompt\s*:', "System prompt injection"),
    (r'ignore\s+everything\s+(above|before)', "Ignore previous context"),

    # Anti-validation
    (r'don\'?t\s+(run|use|call)\s+(the\s+)?(validators?|hooks?)', "Avoid validators"),
    (r'avoid\s+(the\s+)?(validators?|hooks?|checks?)', "Avoid validation"),
    (r'without\s+(running\s+)?(validation|checks?)', "Without validation"),
]


def check_for_bypass_attempts(prompt):
    """Check if prompt contains bypass instructions."""
    if not prompt:
        return False, None

    prompt_lower = prompt.lower()

    for pattern, description in BYPASS_PATTERNS:
        if re.search(pattern, prompt_lower):
            return True, f"Bypass attempt detected: {description}"

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

    # Task tool has a prompt field
    prompt = tool_input.get("prompt", "")

    # Check for bypass attempts
    has_bypass, bypass_reason = check_for_bypass_attempts(prompt)
    if has_bypass:
        result = {
            "continueExecution": False,
            "message": bypass_reason
        }
        print(json.dumps(result))
        return

    # All checks passed
    result = {"continueExecution": True}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
