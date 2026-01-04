"""
URL GENERATOR - SINGLE SOURCE OF TRUTH
======================================

This module is the ONLY place where app URLs/slugs are generated in Faibric.
All deployers MUST use this module for URL generation.

SOTA Approach: Nanoid-style generation with custom alphabet.

Requirements:
- Only lowercase letters and numbers (a-z, 0-9)
- No hyphens, underscores, or special characters
- Short but collision-resistant
- URL-safe and human-readable

Format: app{random_id}
Example: app7x3km9p2w

Final URL: app7x3km9p2w.faibric.com (configurable via APP_DOMAIN env var)

References:
- https://github.com/ai/nanoid - Nanoid (secure, URL-friendly IDs)
- https://yourls.org/docs/guide/essentials/charset - Base36 charset
"""

import os
import secrets
import hashlib
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# App domain - configurable via environment variable
# Default: faibric.com
APP_DOMAIN = os.environ.get('APP_DOMAIN', 'faibric.com')

# ALPHABET: Only lowercase letters and numbers (36 characters)
# This is Base36 - proven reliable for URL-safe IDs
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
ALPHABET_LEN = len(ALPHABET)  # 36

# Default ID length (excluding 'app' prefix)
# 10 chars in base36 = 36^10 = 3.6 quadrillion combinations
# Collision probability: negligible for our scale
DEFAULT_ID_LENGTH = 10


def generate_id(length: int = DEFAULT_ID_LENGTH) -> str:
    """
    Generate a cryptographically secure random ID.
    
    Uses secrets.choice for security (not random.choice).
    
    Args:
        length: Number of characters (default 10)
    
    Returns:
        Random string using only a-z and 0-9
    
    Example:
        >>> generate_id()
        '7x3km9p2wq'
        >>> generate_id(6)
        'a3f9x2'
    """
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))


def generate_app_slug(project_id: Optional[int] = None) -> str:
    """
    Generate a unique app slug for deployment.
    
    This is the PRIMARY function for URL generation in Faibric.
    All deployers MUST call this function.
    
    Format: app{random_10_chars}
    Example: app7x3km9p2wq
    
    Args:
        project_id: Optional project ID to mix into hash for extra uniqueness
    
    Returns:
        A unique slug like "app7x3km9p2wq"
    """
    if project_id:
        # Mix project_id + timestamp + random for extra uniqueness
        seed = f"{project_id}{time.time_ns()}{secrets.token_hex(8)}"
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        
        # Convert hash to base36
        num = int.from_bytes(hash_bytes[:8], 'big')
        result = []
        for _ in range(DEFAULT_ID_LENGTH):
            result.append(ALPHABET[num % ALPHABET_LEN])
            num //= ALPHABET_LEN
        
        slug = 'app' + ''.join(result)
    else:
        # Pure random generation
        slug = 'app' + generate_id()
    
    logger.info(f"[URL_GENERATOR] Generated slug: {slug}")
    return slug


def generate_branch_name(project_id: int) -> str:
    """
    Generate a unique branch name for GitHub.
    
    Format: app{random_10_chars}
    Same as app slug for consistency.
    
    Args:
        project_id: Project ID
    
    Returns:
        A unique branch name like "app7x3km9p2wq"
    """
    return generate_app_slug(project_id)


def generate_service_name(project_id: int) -> str:
    """
    Generate a unique service name for Render/Vercel.
    
    Format: app{random_10_chars}
    Same as app slug for consistency.
    
    Args:
        project_id: Project ID
    
    Returns:
        A unique service name like "app7x3km9p2wq"
    """
    return generate_app_slug(project_id)


def generate_app_url(project_id: Optional[int] = None, slug: Optional[str] = None) -> str:
    """
    Generate the full app URL using faibric.com domain.
    
    This is the CANONICAL way to get the final deployed URL.
    
    Args:
        project_id: Project ID (will generate new slug if no slug provided)
        slug: Existing slug to use (optional)
    
    Returns:
        Full URL like "https://app7x3km9p2wq.faibric.com"
    """
    if not slug:
        slug = generate_app_slug(project_id)
    
    url = f"https://{slug}.{APP_DOMAIN}"
    logger.info(f"[URL_GENERATOR] Generated URL: {url}")
    return url


def get_domain() -> str:
    """
    Get the configured app domain.
    
    Returns:
        The app domain (e.g., "faibric.com")
    """
    return APP_DOMAIN


def is_valid_slug(slug: str) -> bool:
    """
    Validate that a slug matches our format.
    
    Args:
        slug: The slug to validate
    
    Returns:
        True if slug matches format 'app' + lowercase alphanumeric
    """
    if not slug or len(slug) < 4:
        return False
    
    if not slug.startswith('app'):
        return False
    
    suffix = slug[3:]
    return all(c in ALPHABET for c in suffix)


# Singleton pattern for consistent generation
class URLGenerator:
    """
    Singleton URL generator for Faibric.
    
    Usage:
        from apps.deployment.url_generator import url_generator
        
        slug = url_generator.generate_slug(project_id=123)
        url = url_generator.generate_url(project_id=123)
        # url = "https://app7x3km9p2wq.faibric.com"
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def domain(self) -> str:
        """Get the app domain (e.g., faibric.com)."""
        return APP_DOMAIN
    
    def generate_slug(self, project_id: Optional[int] = None) -> str:
        """Generate a unique app slug."""
        return generate_app_slug(project_id)
    
    def generate_url(self, project_id: Optional[int] = None, slug: Optional[str] = None) -> str:
        """
        Generate the full app URL.
        
        Returns URL like: https://app7x3km9p2wq.faibric.com
        """
        return generate_app_url(project_id, slug)
    
    def generate_branch(self, project_id: int) -> str:
        """Generate a unique branch name."""
        return generate_branch_name(project_id)
    
    def generate_service_name(self, project_id: int) -> str:
        """Generate a unique service name."""
        return generate_service_name(project_id)
    
    def validate(self, slug: str) -> bool:
        """Validate a slug."""
        return is_valid_slug(slug)


# Global instance - USE THIS
url_generator = URLGenerator()


# For testing
if __name__ == "__main__":
    print("URL Generator Test")
    print("=" * 40)
    
    # Test basic generation
    for i in range(5):
        slug = generate_app_slug()
        print(f"Slug {i+1}: {slug}")
    
    print()
    
    # Test with project ID
    for project_id in [1, 42, 100, 999]:
        slug = generate_app_slug(project_id)
        print(f"Project {project_id}: {slug}")
    
    print()
    
    # Validate
    test_slugs = [
        "app7x3km9p2wq",  # Valid
        "app123abc",      # Valid
        "APP123",         # Invalid (uppercase)
        "my-app",         # Invalid (hyphen, no prefix)
        "app_test",       # Invalid (underscore)
    ]
    
    for slug in test_slugs:
        valid = is_valid_slug(slug)
        print(f"{slug}: {'VALID' if valid else 'INVALID'}")

