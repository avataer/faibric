"""
Gateway Only Validator

Detects direct external API calls that should use the gateway proxy.
Returns (passed, message) tuple.
"""

import re

# Allowed domains (don't need gateway)
ALLOWED_DOMAINS = [
    'localhost',
    '127.0.0.1',
    'api.faibric.com',
    'faibric.com',
    'cdn.tailwindcss.com',
    'unpkg.com',
    'cdnjs.cloudflare.com',
    'fonts.googleapis.com',
    'fonts.gstatic.com',
    'picsum.photos',
    'onrender.com',
    'vercel.app',
]


def _is_allowed(url: str) -> bool:
    """Check if URL is to an allowed domain."""
    for domain in ALLOWED_DOMAINS:
        if domain in url:
            return True
    return False


def validate(content: str, file_path: str) -> tuple[bool, str]:
    """
    Check content for direct external API calls.
    Only checks JavaScript and Python files.
    Returns (passed, message).
    """
    if not file_path.endswith(('.js', '.jsx', '.ts', '.tsx', '.py')):
        return True, ""

    # Patterns for external API calls
    patterns = [
        r'fetch\s*\(\s*[\'"`](https?://[^\'"` ]+)[\'"`]',
        r'axios\.(?:get|post|put|delete|patch)\s*\(\s*[\'"`](https?://[^\'"` ]+)[\'"`]',
        r'requests\.(?:get|post|put|delete|patch)\s*\(\s*[\'"`](https?://[^\'"` ]+)[\'"`]',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            url = match.group(1)
            if not _is_allowed(url):
                line_num = content[:match.start()].count('\n') + 1
                return False, f"Direct API call at line {line_num}: {url[:50]}. Use Gateway API instead."

    return True, ""
