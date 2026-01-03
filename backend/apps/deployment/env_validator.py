"""
Environment Variable Validator for Faibric

ENFORCES required environment variables are set.
This prevents silent failures where critical tokens disappear.

Called at startup to validate ALL required vars are present.
"""

import os
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


# Required environment variables with descriptions
REQUIRED_ENV_VARS = {
    # Critical for hybrid deployment
    'VERCEL_TOKEN': {
        'required': True,
        'description': 'Vercel API token for fast static deploys (30-60s)',
        'how_to_get': 'https://vercel.com/account/tokens',
        'fallback_behavior': 'Falls back to Render (slower 2-5min deploys)',
    },
    'RENDER_API_KEY': {
        'required': True,
        'description': 'Render API key for backend and fallback deploys',
        'how_to_get': 'https://dashboard.render.com/u/settings#api-keys',
        'fallback_behavior': 'Deployment will fail completely',
    },
    'GITHUB_TOKEN': {
        'required': True,
        'description': 'GitHub token for pushing app code to repos',
        'how_to_get': 'https://github.com/settings/tokens',
        'fallback_behavior': 'Cannot push code to GitHub for Render deploys',
    },
    'ANTHROPIC_API_KEY': {
        'required': True,
        'description': 'Claude API key for AI code generation',
        'how_to_get': 'https://console.anthropic.com/settings/keys',
        'fallback_behavior': 'AI generation will fail',
    },
}

# Optional but recommended vars
OPTIONAL_ENV_VARS = {
    'VERCEL_TEAM_ID': {
        'description': 'Vercel team ID (auto-detected if not set)',
    },
    'GITHUB_APPS_REPO': {
        'description': 'GitHub repo for app deployments',
        'default': 'avataer/faibric-apps',
    },
}


class EnvValidationResult:
    """Result of environment validation."""
    
    def __init__(self):
        self.missing_required: List[str] = []
        self.missing_optional: List[str] = []
        self.present: List[str] = []
        self.warnings: List[str] = []
    
    @property
    def is_valid(self) -> bool:
        return len(self.missing_required) == 0
    
    def to_dict(self) -> dict:
        return {
            'valid': self.is_valid,
            'missing_required': self.missing_required,
            'missing_optional': self.missing_optional,
            'present': self.present,
            'warnings': self.warnings,
        }


def validate_environment() -> EnvValidationResult:
    """
    Validate all required environment variables are set.
    
    Returns:
        EnvValidationResult with details of what's missing
    """
    result = EnvValidationResult()
    
    # Check required vars
    for var_name, var_info in REQUIRED_ENV_VARS.items():
        value = os.environ.get(var_name, '')
        
        if value:
            result.present.append(var_name)
            # Log success at startup
            logger.info(f"[ENV] {var_name}: SET (length={len(value)})")
        else:
            result.missing_required.append(var_name)
            # Log prominent warning
            logger.error(f"[ENV] MISSING REQUIRED: {var_name}")
            logger.error(f"  Description: {var_info['description']}")
            logger.error(f"  How to get: {var_info['how_to_get']}")
            logger.error(f"  Fallback: {var_info['fallback_behavior']}")
            result.warnings.append(
                f"MISSING {var_name}: {var_info['fallback_behavior']}"
            )
    
    # Check optional vars
    for var_name, var_info in OPTIONAL_ENV_VARS.items():
        value = os.environ.get(var_name, '')
        if not value:
            result.missing_optional.append(var_name)
            logger.warning(f"[ENV] Optional not set: {var_name} - {var_info['description']}")
    
    # Summary
    if result.is_valid:
        logger.info(f"[ENV] All {len(result.present)} required environment variables are set")
    else:
        logger.critical(
            f"[ENV] CRITICAL: {len(result.missing_required)} required environment variables are MISSING!"
        )
        for var in result.missing_required:
            logger.critical(f"[ENV]   - {var}")
    
    return result


def check_vercel_configured() -> Tuple[bool, str]:
    """
    Quick check if Vercel is configured.
    
    Returns:
        (is_configured: bool, message: str)
    """
    token = os.environ.get('VERCEL_TOKEN', '')
    
    if not token:
        return False, "VERCEL_TOKEN not set - hybrid deploys will use Render only"
    
    if len(token) < 10:
        return False, f"VERCEL_TOKEN looks invalid (too short: {len(token)} chars)"
    
    return True, f"VERCEL_TOKEN configured ({len(token)} chars)"


def get_deployment_status() -> Dict:
    """
    Get current deployment configuration status.
    Used for /api/health/ and debugging.
    """
    vercel_ok, vercel_msg = check_vercel_configured()
    
    return {
        'vercel': {
            'configured': vercel_ok,
            'message': vercel_msg,
        },
        'render': {
            'configured': bool(os.environ.get('RENDER_API_KEY')),
        },
        'github': {
            'configured': bool(os.environ.get('GITHUB_TOKEN')),
            'repo': os.environ.get('GITHUB_APPS_REPO', 'NOT SET'),
        },
        'ai': {
            'configured': bool(os.environ.get('ANTHROPIC_API_KEY')),
        }
    }


# Run validation at module import (startup)
def _startup_check():
    """Run at Django startup to validate environment."""
    try:
        result = validate_environment()
        
        if not result.is_valid:
            # Print to stderr as well for visibility
            import sys
            print("\n" + "="*60, file=sys.stderr)
            print("FAIBRIC ENVIRONMENT ERROR", file=sys.stderr)
            print("="*60, file=sys.stderr)
            for warning in result.warnings:
                print(f"  {warning}", file=sys.stderr)
            print("="*60 + "\n", file=sys.stderr)
    except Exception as e:
        logger.warning(f"[ENV] Startup check failed: {e}")


# Run on import
_startup_check()

