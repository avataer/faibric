"""
No Emojis Validator

Detects emoji characters in content.
Returns (passed, message) tuple.
"""

import re

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Misc Symbols and Pictographs
    "\U0001F680-\U0001F6FF"  # Transport and Map
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "\U00002600-\U000026FF"  # Misc symbols
    "\U0001F1E0-\U0001F1FF"  # Flags
    "]+",
    flags=re.UNICODE
)


def validate(content: str, file_path: str) -> tuple[bool, str]:
    """
    Check content for emojis.
    Returns (passed, message).
    """
    # Skip binary files
    binary_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.ttf')
    if file_path.endswith(binary_extensions):
        return True, ""

    match = EMOJI_PATTERN.search(content)
    if match:
        emoji = match.group()
        line_num = content[:match.start()].count('\n') + 1
        return False, f"Emoji found at line {line_num}: {emoji}. Use text labels like [OK], [ERROR] instead."

    return True, ""
