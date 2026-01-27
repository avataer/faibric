"""
Vercel Deployer for Faibric

Fast static hosting for "Version Zero" deployments.
Deploy times: 30-60 seconds vs Render's 5-10 minutes.

Use Vercel for:
- Initial static React apps
- Landing pages
- Dashboards (frontend only)

Keep Render for:
- Gateway API backend
- Databases
- Long-running workers
"""

import os
import json
import time
import logging
import requests
import base64
from typing import Dict, Optional, Tuple
from pathlib import Path

from django.conf import settings

from .url_generator import url_generator

logger = logging.getLogger(__name__)


def get_faibric_api_url() -> str:
    """
    Get the Faibric API URL for Vercel-deployed sites.

    Vercel-deployed sites are always accessed remotely from users' browsers,
    so they always need the production API URL. Localhost would not be
    accessible from a user's browser visiting a Vercel deployment.

    The localhost URL is only appropriate when the site itself is served
    locally during development (e.g., via local_preview.py), not here.
    """
    return "https://faibric-api.onrender.com"

# Vercel API
VERCEL_API_URL = "https://api.vercel.com"
VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN")
VERCEL_TEAM_ID = os.environ.get("VERCEL_TEAM_ID")  # Optional, for team deployments


class VercelDeployer:
    """
    Deploy static React apps to Vercel for fast initial visibility.
    
    Vercel advantages:
    - 30-60 second deploys (vs 5-10 min on Render)
    - Instant preview URLs
    - Global CDN
    - Free hobby tier
    """
    
    def __init__(self):
        self.token = VERCEL_TOKEN
        self._team_id = VERCEL_TEAM_ID
        self._team_id_fetched = False
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @property
    def team_id(self) -> Optional[str]:
        """Get team ID, auto-detecting from user's default team if not set."""
        if self._team_id:
            return self._team_id
        
        if self._team_id_fetched:
            return self._team_id
        
        # Try to get user's default team
        if self.token:
            try:
                response = requests.get(
                    f"{VERCEL_API_URL}/v2/user",
                    headers=self.headers,
                    timeout=10
                )
                if response.status_code == 200:
                    user_data = response.json().get('user', {})
                    self._team_id = user_data.get('defaultTeamId')
                    if self._team_id:
                        logger.info(f"[VERCEL] Auto-detected team ID: {self._team_id}")
            except Exception as e:
                logger.warning(f"[VERCEL] Could not fetch team ID: {e}")
        
        self._team_id_fetched = True
        return self._team_id
    
    @property
    def is_configured(self) -> bool:
        """Check if Vercel is configured."""
        return bool(self.token)
    
    def deploy_static_app(
        self,
        project_name: str,
        app_code: str,
        project_id: str = None,
        generated_images: Dict[str, bytes] = None,
        session_token: str = None,
        user_prompt: str = ""
    ) -> Dict:
        """
        Deploy a static React app to Vercel.
        
        Returns:
            {
                'success': bool,
                'url': str,  # The deployed URL
                'deployment_id': str,
                'deploy_time_seconds': float,
                'provider': 'vercel'
            }
        """
        if not self.is_configured:
            return {
                'success': False,
                'error': 'Vercel not configured. Set VERCEL_TOKEN env var.',
                'provider': 'vercel'
            }
        
        start_time = time.time()
        if generated_images is None:
            generated_images = {}

        try:
            # Step 1: Generate all files for the React app
            # Pass project_id, session_token, and user_prompt for color enforcement
            files = self._generate_files(app_code, project_name, project_id, generated_images, session_token, user_prompt)
            
            # Step 2: Create deployment via Vercel API
            # Pass project_id for URL generation
            deployment = self._create_deployment(project_name, files, int(project_id) if project_id else None)
            
            if not deployment.get('id'):
                return {
                    'success': False,
                    'error': deployment.get('error', 'Deployment creation failed'),
                    'provider': 'vercel'
                }
            
            # Step 2.5: Disable SSO protection so URL is publicly accessible
            # Get the project name from deployment response
            project_slug = deployment.get('name', '')
            if project_slug:
                self._disable_sso_protection(project_slug)
                
                # Step 2.6: Add faibric.com subdomain to the project
                faibric_subdomain = f"{project_slug}.{url_generator.domain}"
                self._add_custom_domain(project_slug, faibric_subdomain)
            
            # Step 3: Wait for deployment to be ready
            wait_result = self._wait_for_ready(deployment['id'])
            
            deploy_time = time.time() - start_time
            
            if not wait_result.get('success'):
                # Build failed - return the error for AI retry
                return {
                    'success': False,
                    'error': wait_result.get('error', 'Build failed'),
                    'build_error': wait_result.get('build_error'),  # Specific error for AI
                    'deployment_id': deployment['id'],
                    'provider': 'vercel',
                    'deploy_time_seconds': deploy_time
                }
            
            vercel_url = wait_result.get('url')
            if vercel_url:
                # CRITICAL: Verify the deployment actually works before reporting success
                verification = self._verify_deployment(vercel_url)
                
                if not verification['valid']:
                    logger.error(f"[VERCEL] Deployment verification FAILED: {verification['error']}")
                    return {
                        'success': False,
                        'error': f"Deployment verification failed: {verification['error']}",
                        'url': vercel_url,
                        'deployment_id': deployment['id'],
                        'provider': 'vercel'
                    }
                
                # Generate the canonical faibric.com URL
                # The slug is the Vercel project name (e.g., "app7x3km9p2wq")
                slug = deployment.get('name', '')
                canonical_url = url_generator.generate_url(slug=slug) if slug else vercel_url
                
                logger.info(f"[VERCEL] Deployed and VERIFIED {project_name} in {deploy_time:.1f}s")
                logger.info(f"[VERCEL]   Vercel URL: {vercel_url}")
                logger.info(f"[VERCEL]   Canonical URL: {canonical_url}")
                
                # BYPASS: Return Vercel URL directly to avoid SSL rate limits on faibric.com
                return {
                    'success': True,
                    'url': vercel_url,  # Return Vercel URL directly (bypass faibric.com SSL issues)
                    'canonical_url': canonical_url,  # Keep faibric.com URL for reference
                    'deployment_id': deployment['id'],
                    'deploy_time_seconds': deploy_time,
                    'provider': 'vercel',
                    'verified': True
                }
            else:
                return {
                    'success': False,
                    'error': 'Deployment timed out',
                    'deployment_id': deployment['id'],
                    'provider': 'vercel'
                }
                
        except Exception as e:
            logger.error(f"[VERCEL] Deployment failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'vercel'
            }
    
    def _generate_files(
        self,
        app_code: str,
        project_name: str,
        project_id: str = None,
        generated_images: Dict[str, bytes] = None,
        session_token: str = None,
        user_prompt: str = ""
    ) -> list:
        """
        Generate files for instant static deployment.

        Strategy: Use CDN-based React + Tailwind for INSTANT deploys (no build step).
        This gives us 5-10 second deploys instead of 60+ seconds for Vite builds.

        The app runs exactly the same - just loaded from CDN instead of bundled.
        """
        import hashlib

        if generated_images is None:
            generated_images = {}

        files = []
        
        # Convert TypeScript-style React to browser-compatible JSX
        # The app_code uses TypeScript syntax, we need to adapt it for browser
        browser_app = self._convert_to_browser_react(app_code)

        # Inject Faibric admin panel
        browser_app = self._inject_admin_panel(browser_app)

        # CRITICAL: Apply color enforcement AFTER admin panel injection
        # The admin panel has default gray/blue colors that must be replaced
        # if the user requested specific colors (brown/cream, etc.)
        if user_prompt:
            from apps.ai_engine.v2.generator import AIGeneratorV2
            gen = AIGeneratorV2()
            browser_app = gen._apply_color_enforcement(browser_app, user_prompt)
            logger.info(f"[VERCEL] Applied color enforcement for: {user_prompt[:50]}")

        # Generate project token for builder API (legacy, kept for backward compatibility)
        project_token = ""
        if project_id:
            project_token = hashlib.sha256(
                f"{project_id}faibric_builder_secret".encode()
            ).hexdigest()[:16]

        # Detect if Supabase is used in the code (auto-added by DatabaseIntegrator)
        needs_supabase = 'supabase' in browser_app.lower() or 'SUPABASE_URL' in browser_app

        # index.html with CDN React + Tailwind + TypeScript support
        # INJECT: Project ID, project token, and session_token for the builder to work
        # session_token is the REAL token used by /api/onboarding/modify/ API
        supabase_script = '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>' if needs_supabase else ''

        # Visual editing script for click-to-edit functionality
        from .visual_edit_script import get_visual_edit_script
        visual_edit_script = get_visual_edit_script()

        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{self._generate_title(project_name)}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    {supabase_script}
    <script>
        // Faibric Builder Configuration
        window.FAIBRIC_PROJECT_ID = "{project_id or ''}";
        window.FAIBRIC_PROJECT_TOKEN = "{project_token}";
        window.FAIBRIC_SESSION_TOKEN = "{session_token or ''}";
        window.FAIBRIC_API_URL = "{get_faibric_api_url()}";
    </script>
    <style>
        body {{ margin: 0; font-family: system-ui, -apple-system, sans-serif; }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel" data-presets="react,typescript">
{browser_app}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(React.createElement(App));
    </script>
    {visual_edit_script}
</body>
</html>'''
        
        files.append(self._file("index.html", index_html))
        
        # vercel.json for SPA routing - enables /faibric admin panel
        # All routes go to index.html so React can handle routing
        # No X-Frame-Options to allow iframe embedding in Faibric Studio Live Preview
        vercel_config = '''{
  "rewrites": [
    { "source": "/(.*)", "destination": "/" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" }
      ]
    }
  ]
}'''
        files.append(self._file("vercel.json", vercel_config))

        # Add AI-generated images if any
        for filename, image_bytes in generated_images.items():
            # Add image to images/ directory
            image_path = f"images/{filename}"
            files.append(self._file_binary(image_path, image_bytes))
            logger.info(f"[VERCEL] Added AI image: {image_path} ({len(image_bytes)} bytes)")

        return files

    def _fix_apostrophes_in_strings(self, code: str) -> str:
        """
        Fix apostrophes inside single-quoted strings that break JavaScript.

        Problem: 'Tuscany's finest wine' - the apostrophe ends the string early
        Solution: Convert to double quotes or escape the apostrophe

        Strategy: Find single-quoted strings containing apostrophes and convert to double quotes
        """
        import re

        # Pattern to find single-quoted strings (non-greedy, handles escaped quotes)
        # This is complex because we need to handle nested quotes carefully

        def fix_string(match):
            full_match = match.group(0)
            content = match.group(1)

            # If the content contains an unescaped apostrophe, convert to double quotes
            # Count apostrophes - if odd number, there's a problem
            if "'" in content and not content.startswith("\\'"):
                # Convert to double-quoted string
                # First escape any existing double quotes in the content
                new_content = content.replace('"', '\\"')
                return f'"{new_content}"'

            return full_match

        # Find problematic patterns - single quoted strings with apostrophes inside
        # This regex finds 'text's more text' patterns
        # Look for: ' followed by text, then 's (possessive), then more text, then '
        problematic_pattern = r"'([^']*?[a-zA-Z]'s[^']*?)'"

        # Replace problematic strings
        fixed_code = re.sub(problematic_pattern, lambda m: f'"{m.group(1)}"', code)

        # Also fix common contractions: don't, won't, can't, it's, etc.
        contraction_pattern = r"'([^']*?(?:n't|'re|'ve|'ll|'d|'m)[^']*?)'"
        fixed_code = re.sub(contraction_pattern, lambda m: f'"{m.group(1)}"', fixed_code)

        if fixed_code != code:
            logger.info("[VERCEL] Fixed apostrophes in single-quoted strings")

        return fixed_code

    def _generate_title(self, project_name: str) -> str:
        """
        Generate a professional page title from the project name/prompt.
        
        Rules:
        - Max 50 characters
        - Capitalize first letter of each word
        - Remove "I need", "Build me", "Create a" etc.
        - If still too long, use first meaningful phrase
        """
        import re
        
        # Remove common prompt prefixes
        clean = project_name
        prefixes_to_remove = [
            r'^I am a\s+',
            r'^I need a?\s+',
            r'^Build me a?\s+',
            r'^Create a?\s+',
            r'^Make me a?\s+',
            r'^I want a?\s+',
            r'^A?\s*need a?\s+',
        ]
        for prefix in prefixes_to_remove:
            clean = re.sub(prefix, '', clean, flags=re.IGNORECASE)
        
        # Take first 50 chars and find a natural break point
        if len(clean) > 50:
            # Try to break at a space
            clean = clean[:50]
            last_space = clean.rfind(' ')
            if last_space > 20:
                clean = clean[:last_space]
        
        # Title case
        clean = clean.strip().title()
        
        # If empty or too short, use generic
        if len(clean) < 3:
            clean = "My App"
        
        return clean
    
    def _convert_to_browser_react(self, code: str) -> str:
        """
        Convert TypeScript/module React code to browser-compatible JavaScript.

        PHASE 1 ZERO-TRANSFORM: If code is already browser-ready (from library),
        skip transformation entirely to prevent regex corruption.

        Detection: Library-composed code has these markers:
        - "LIBRARY COMPONENTS" comment header
        - No TypeScript syntax (interface, type annotations, generics)
        - Already uses React.useState (not useState)
        """
        import re

        # ZERO-TRANSFORM CHECK: Is this library-composed code?
        is_library_composed = "LIBRARY COMPONENTS" in code
        has_typescript = bool(re.search(r'^interface\s+\w+\s*\{', code, re.MULTILINE)) or \
                         bool(re.search(r'^type\s+\w+\s*=', code, re.MULTILINE)) or \
                         bool(re.search(r':\s*React\.FC<', code))

        if is_library_composed and not has_typescript:
            logger.info("[VERCEL] ZERO-TRANSFORM: Library code detected, skipping regex transformation")
            # Only do minimal cleanup - remove imports and exports
            code = re.sub(r'^import\s+.*$', '', code, flags=re.MULTILINE)
            code = re.sub(r'export\s+default\s+\w+;?\s*$', '', code, flags=re.MULTILINE)
            code = re.sub(r'^export\s+(?=const|let|var|function|class)', '', code, flags=re.MULTILINE)
            code = re.sub(r'\n\s*\n\s*\n+', '\n\n', code)
            return code.strip()

        logger.info("[VERCEL] Applying TypeScript transformation (non-library code)")

        # Remove import lines
        code = re.sub(r'^import\s+.*$', '', code, flags=re.MULTILINE)
        
        # Remove export statements
        code = re.sub(r'export\s+default\s+\w+;?\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'export\s+default\s+function', 'function', code)
        code = re.sub(r'^export\s+(?=const|let|var|function|class)', '', code, flags=re.MULTILINE)
        
        # Remove interface declarations - SINGLE LINE ONLY to avoid corruption
        # DO NOT use re.DOTALL - it causes catastrophic matching across components
        code = re.sub(r'^interface\s+\w+\s*\{[^}\n]*\}\s*$', '', code, flags=re.MULTILINE)
        
        # Remove type declarations
        code = re.sub(r'^type\s+\w+\s*=\s*[^;]+;\s*$', '', code, flags=re.MULTILINE)
        
        # Remove React.FC type annotations (these appear after const Name)
        code = re.sub(r':\s*React\.FC(?:<[^>]*>)?\s*=', ' =', code)
        
        # Remove TypeScript generics from React hooks ONLY
        # useState<string>("") -> useState("")
        # Match: hookName<...>(  where ... can contain nested <>
        def remove_hook_generic(match):
            before = match.group(1)
            hook = match.group(2)
            rest = match.group(3)
            # Find balanced closing >
            depth = 1
            i = 0
            while i < len(rest) and depth > 0:
                if rest[i] == '<':
                    depth += 1
                elif rest[i] == '>':
                    depth -= 1
                i += 1
            after = rest[i:]
            # Return without the generic, ensure ( follows
            if after.startswith('('):
                return f'{before}React.{hook}{after}'
            else:
                return f'{before}React.{hook}({after.lstrip(">(")}'
        
        # Apply to React hooks with generics
        hooks = ['useState', 'useRef', 'useMemo', 'useCallback', 'useReducer', 'useContext', 'useEffect']
        for hook in hooks:
            pattern = rf'(^|[^\w.])(?:React\.)?({hook})<(.+)'
            iterations = 0
            while re.search(pattern, code) and iterations < 20:
                code = re.sub(pattern, remove_hook_generic, code, count=1)
                iterations += 1
        
        # Convert remaining plain hooks to React.hookName
        code = re.sub(r'(?<![.\w])useState\s*\(', 'React.useState(', code)
        code = re.sub(r'(?<![.\w])useEffect\s*\(', 'React.useEffect(', code)
        code = re.sub(r'(?<![.\w])useRef\s*\(', 'React.useRef(', code)
        code = re.sub(r'(?<![.\w])useMemo\s*\(', 'React.useMemo(', code)
        code = re.sub(r'(?<![.\w])useCallback\s*\(', 'React.useCallback(', code)
        
        # Remove function parameter type annotations - but ONLY in function signatures
        # SAFE approach: Only match parameter lists that look like function params (after = or =>)
        # Pattern: word followed by : and a simple type, in function-like contexts
        # DO NOT apply to all parentheses - that corrupts JSX expressions
        code = re.sub(r'(\w+)\s*:\s*(string|number|boolean|any|void)(?=\s*[,\)])', r'\1', code)
        
        # Remove arrow function return type annotations
        # ): Type => becomes ) =>
        # SAFE: Only match simple type names, not complex expressions
        code = re.sub(r'\)\s*:\s*(?:JSX\.Element|React\.ReactNode|void|null|string|number|boolean|any)\s*=>', ') =>', code)
        
        # Remove variable type annotations ONLY for simple patterns
        # const x: string = -> const x =
        # But NOT const x: { name: "foo" } = (that's valid JS destructuring type)
        code = re.sub(r'(const|let|var)\s+(\w+)\s*:\s*(?:string|number|boolean|any|null|undefined|React\.\w+|\w+\[\])\s*=', r'\1 \2 =', code)
        
        # Remove 'as Type' casts
        code = re.sub(r'\s+as\s+(?:string|number|boolean|any|const|unknown|never)(?:\[\])?(?!["\'\w])', '', code)
        
        # Fix React.React.useState -> React.useState
        code = re.sub(r'React\.React\.', 'React.', code)
        
        # Clean up empty lines
        code = re.sub(r'\n\s*\n\s*\n+', '\n\n', code)
        
        return code.strip()
    
    def _inject_admin_panel(self, code: str) -> str:
        """
        Inject Faibric admin panel as a WRAPPER around the original App.

        Strategy: Rename App to _OriginalApp, create new App that wraps it.
        This is SAFER than injecting code inside the function.

        Features:
        - Overview: Page views and sessions
        - Builder: Chat interface (LEFT) + Live preview (RIGHT)
        - Settings: Password management
        """
        import re

        # Skip if already has admin panel
        if 'FaibricAdmin' in code or 'isAdminRoute' in code:
            return code

        # Find the App function/component and rename it
        app_patterns = [
            (r'function\s+App\s*\(', 'function _OriginalApp('),
            (r'const\s+App\s*=', 'const _OriginalApp ='),
        ]

        renamed = False
        for pattern, replacement in app_patterns:
            if re.search(pattern, code):
                code = re.sub(pattern, replacement, code, count=1)
                renamed = True
                break

        if not renamed:
            return code

        # Add the admin wrapper at the end with Builder functionality
        admin_wrapper = '''

// FAIBRIC ADMIN PANEL WITH BUILDER
// API URL is injected from window.FAIBRIC_API_URL (set in HTML head)
const FAIBRIC_API_URL = window.FAIBRIC_API_URL || "https://faibric-api.onrender.com";

// Service configuration for integrations
const INTEGRATION_SERVICES = [
  { id: "openweather", name: "OpenWeather", description: "Weather data API", docsUrl: "https://openweathermap.org/api" },
  { id: "alpha_vantage", name: "Alpha Vantage", description: "Stock market data", docsUrl: "https://www.alphavantage.co/documentation/" },
  { id: "finnhub", name: "Finnhub", description: "Real-time stock data", docsUrl: "https://finnhub.io/docs/api" },
  { id: "newsapi", name: "News API", description: "News headlines and articles", docsUrl: "https://newsapi.org/docs" },
  { id: "stripe", name: "Stripe", description: "Payment processing", docsUrl: "https://stripe.com/docs/api" },
  { id: "shopify", name: "Shopify", description: "E-commerce platform", docsUrl: "https://shopify.dev/docs/api" },
];

function FaibricIntegrations() {
  const [integrations, setIntegrations] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(null);
  const [error, setError] = React.useState("");
  const [success, setSuccess] = React.useState("");
  const [apiKeys, setApiKeys] = React.useState({});
  const [showKey, setShowKey] = React.useState({});

  const projectId = window.FAIBRIC_PROJECT_ID;

  const fetchIntegrations = async () => {
    if (!projectId) {
      setLoading(false);
      setError("Project ID not configured");
      return;
    }
    try {
      const res = await fetch(FAIBRIC_API_URL + "/api/projects/" + projectId + "/api-keys/");
      if (res.ok) {
        const data = await res.json();
        setIntegrations(data.api_keys || []);
        // Pre-fill existing keys (masked)
        const keys = {};
        (data.api_keys || []).forEach(k => {
          keys[k.service] = k.masked_key || "";
        });
        setApiKeys(keys);
      }
      setError("");
    } catch (e) {
      setError("Failed to load integrations");
    }
    setLoading(false);
  };

  React.useEffect(() => { fetchIntegrations(); }, []);

  const handleSave = async (serviceId) => {
    const key = apiKeys[serviceId];
    if (!key || !key.trim()) {
      setError("Please enter an API key");
      return;
    }
    setSaving(serviceId);
    setError("");
    setSuccess("");
    try {
      const res = await fetch(FAIBRIC_API_URL + "/api/projects/" + projectId + "/api-keys/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service: serviceId, api_key: key.trim() })
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setSuccess(serviceId + " API key saved successfully");
        fetchIntegrations();
      }
    } catch (e) {
      setError("Failed to save API key");
    }
    setSaving(null);
  };

  const handleDelete = async (serviceId) => {
    if (!confirm("Are you sure you want to remove the " + serviceId + " API key?")) return;
    setSaving(serviceId);
    setError("");
    setSuccess("");
    try {
      const res = await fetch(FAIBRIC_API_URL + "/api/projects/" + projectId + "/api-keys/" + serviceId + "/", {
        method: "DELETE"
      });
      if (res.ok) {
        setSuccess(serviceId + " API key removed");
        setApiKeys(prev => ({ ...prev, [serviceId]: "" }));
        fetchIntegrations();
      } else {
        setError("Failed to delete API key");
      }
    } catch (e) {
      setError("Failed to delete API key");
    }
    setSaving(null);
  };

  const handleVerify = async (serviceId) => {
    setSaving(serviceId);
    setError("");
    setSuccess("");
    try {
      const res = await fetch(FAIBRIC_API_URL + "/api/projects/" + projectId + "/api-keys/" + serviceId + "/verify/", {
        method: "POST"
      });
      const data = await res.json();
      if (data.status === "active") {
        setSuccess(serviceId + " connection verified");
      } else {
        setError(data.error || "Verification failed");
      }
      fetchIntegrations();
    } catch (e) {
      setError("Failed to verify connection");
    }
    setSaving(null);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "active": return "bg-green-100 text-green-800";
      case "pending": return "bg-yellow-100 text-yellow-800";
      case "invalid": return "bg-red-100 text-red-800";
      case "expired": return "bg-gray-100 text-gray-600";
      default: return "bg-gray-100 text-gray-600";
    }
  };

  const getIntegrationStatus = (serviceId) => {
    const integration = integrations.find(i => i.service === serviceId);
    return integration ? integration.status : null;
  };

  if (loading) return <div className="text-center py-8">Loading integrations...</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">Integrations</h2>
      <p className="text-gray-600 mb-6">Connect third-party services to unlock real data in your app.</p>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}

      <div className="space-y-4">
        {INTEGRATION_SERVICES.map((service) => {
          const status = getIntegrationStatus(service.id);
          const hasKey = integrations.some(i => i.service === service.id);
          const isSaving = saving === service.id;

          return (
            <div key={service.id} className="bg-white p-6 rounded-xl shadow">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-lg">{service.name}</h3>
                    {status && (
                      <span className={"px-2 py-1 rounded-full text-xs font-medium " + getStatusColor(status)}>
                        {status}
                      </span>
                    )}
                  </div>
                  <p className="text-gray-500 text-sm">{service.description}</p>
                </div>
                <a
                  href={service.docsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 text-sm hover:underline"
                >
                  Get API Key
                </a>
              </div>

              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showKey[service.id] ? "text" : "password"}
                    value={apiKeys[service.id] || ""}
                    onChange={(e) => setApiKeys(prev => ({ ...prev, [service.id]: e.target.value }))}
                    placeholder="Enter your API key"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10"
                    disabled={isSaving}
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(prev => ({ ...prev, [service.id]: !prev[service.id] }))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showKey[service.id] ? "Hide" : "Show"}
                  </button>
                </div>
                <button
                  onClick={() => handleSave(service.id)}
                  disabled={isSaving || !apiKeys[service.id]}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSaving ? "..." : "Save"}
                </button>
                {hasKey && (
                  <>
                    <button
                      onClick={() => handleVerify(service.id)}
                      disabled={isSaving}
                      className="px-4 py-2 border border-green-500 text-green-600 rounded-lg hover:bg-green-50 disabled:opacity-50"
                    >
                      Verify
                    </button>
                    <button
                      onClick={() => handleDelete(service.id)}
                      disabled={isSaving}
                      className="px-4 py-2 border border-red-500 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
                    >
                      Remove
                    </button>
                  </>
                )}
              </div>

              {hasKey && status === "active" && (
                <div className="mt-3 text-sm text-green-600">
                  Connected and working
                </div>
              )}
              {hasKey && status === "invalid" && (
                <div className="mt-3 text-sm text-red-600">
                  API key is invalid. Please check and update.
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FaibricBuilder() {
  const [messages, setMessages] = React.useState([
    { role: "system", content: "Welcome! Describe what changes you want to make to your website." }
  ]);
  const [input, setInput] = React.useState("");
  const [isBuilding, setIsBuilding] = React.useState(false);
  const [buildProgress, setBuildProgress] = React.useState(0);
  const [previewUrl, setPreviewUrl] = React.useState(window.location.origin);
  const [iframeKey, setIframeKey] = React.useState(0);
  const messagesEndRef = React.useRef(null);

  // Scroll to bottom when messages change
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Poll for build status
  React.useEffect(() => {
    const token = window.FAIBRIC_SESSION_TOKEN || window.FAIBRIC_PROJECT_TOKEN;
    if (!isBuilding || !token) return;

    const poll = setInterval(async () => {
      try {
        const res = await fetch(FAIBRIC_API_URL + "/api/onboarding/status/" + token + "/");
        const data = await res.json();

        if (data.build_progress) setBuildProgress(data.build_progress);

        // Check for new events
        if (data.events && data.events.length > 0) {
          const latestEvent = data.events[0];
          if (latestEvent.event_data?.message) {
            setMessages(prev => {
              const lastMsg = prev[prev.length - 1];
              if (lastMsg?.content !== latestEvent.event_data.message) {
                return [...prev, { role: "system", content: latestEvent.event_data.message }];
              }
              return prev;
            });
          }
        }

        if (data.status === "deployed") {
          setIsBuilding(false);
          setBuildProgress(100);
          if (data.deployment_url) {
            setPreviewUrl(data.deployment_url);
            setIframeKey(k => k + 1);
          }
          setMessages(prev => [...prev, { role: "system", content: "Changes deployed! Refreshing preview..." }]);
          clearInterval(poll);
        }
      } catch (e) {
        console.error("Poll error:", e);
      }
    }, 2000);

    return () => clearInterval(poll);
  }, [isBuilding]);

  const handleSend = async () => {
    if (!input.trim() || isBuilding) return;

    const userMessage = input.trim();
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setInput("");
    setIsBuilding(true);
    setBuildProgress(10);

    const token = window.FAIBRIC_SESSION_TOKEN || window.FAIBRIC_PROJECT_TOKEN;
    if (!token) {
      setMessages(prev => [...prev, { role: "system", content: "Builder not configured. Please contact support." }]);
      setIsBuilding(false);
      return;
    }

    try {
      const res = await fetch(FAIBRIC_API_URL + "/api/onboarding/modify/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_token: token,
          request: userMessage
        })
      });

      const data = await res.json();

      if (data.success) {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: data.mode === "modify"
            ? "Got it! Applying your changes..."
            : "Starting fresh build with your new request..."
        }]);
      } else {
        setMessages(prev => [...prev, { role: "system", content: "Error: " + (data.error || "Failed to submit") }]);
        setIsBuilding(false);
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: "system", content: "Connection error. Please try again." }]);
      setIsBuilding(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* LEFT: Chat Panel */}
      <div className="w-2/5 min-w-[350px] flex flex-col border-r border-gray-200 bg-white">
        {/* Chat Header */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="font-semibold text-lg">Faibric Builder</h3>
          {isBuilding && (
            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
              Building... {buildProgress}%
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] p-3 rounded-lg ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : msg.role === "assistant"
                    ? "bg-gray-100 text-gray-800 border border-gray-200"
                    : "bg-gray-50 text-gray-600 italic text-sm"
              }`}>
                {msg.content}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !isBuilding && handleSend()}
              placeholder={isBuilding ? "Building in progress..." : "Describe changes you want..."}
              disabled={isBuilding}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isBuilding}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT: Preview Panel */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {/* Preview Header */}
        <div className="p-4 border-b border-gray-200 bg-white flex items-center justify-between">
          <h3 className="font-semibold">Live Preview</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setIframeKey(k => k + 1)}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100"
            >
              Refresh
            </button>
            <button
              onClick={() => window.open(previewUrl, "_blank")}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100"
            >
              Open in Tab
            </button>
          </div>
        </div>

        {/* Preview iframe */}
        <div className="flex-1 p-4">
          <iframe
            key={iframeKey}
            src={previewUrl}
            className="w-full h-full border border-gray-200 rounded-lg bg-white"
            title="Website Preview"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
        </div>
      </div>
    </div>
  );
}

function FaibricDomains() {
  const [domains, setDomains] = React.useState([]);
  const [newDomain, setNewDomain] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [adding, setAdding] = React.useState(false);
  const [error, setError] = React.useState("");

  const projectId = window.FAIBRIC_PROJECT_ID;

  const fetchDomains = async () => {
    if (!projectId) {
      setLoading(false);
      setError("Project ID not configured");
      return;
    }
    try {
      const res = await fetch(FAIBRIC_API_URL + "/api/services/domains/" + projectId + "/");
      const data = await res.json();
      setDomains(data.domains || []);
      setError("");
    } catch (e) {
      setError("Failed to load domains");
    }
    setLoading(false);
  };

  React.useEffect(() => { fetchDomains(); }, []);

  const handleAdd = async () => {
    if (!newDomain.trim()) return;
    setAdding(true);
    setError("");
    try {
      const res = await fetch(FAIBRIC_API_URL + "/api/services/domains/" + projectId + "/add/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: newDomain.trim().toLowerCase() })
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setNewDomain("");
        fetchDomains();
      }
    } catch (e) {
      setError("Failed to add domain");
    }
    setAdding(false);
  };

  const handleVerify = async (domain) => {
    try {
      const res = await fetch(FAIBRIC_API_URL + "/api/services/domains/" + projectId + "/" + domain + "/verify/", {
        method: "POST"
      });
      const data = await res.json();
      if (data.is_verified) {
        fetchDomains();
      } else {
        setError("Domain not yet verified. Please check DNS records.");
      }
    } catch (e) {
      setError("Failed to verify domain");
    }
  };

  const handleRemove = async (domain) => {
    if (!confirm("Are you sure you want to remove " + domain + "?")) return;
    try {
      await fetch(FAIBRIC_API_URL + "/api/services/domains/" + projectId + "/" + domain + "/remove/", {
        method: "DELETE"
      });
      fetchDomains();
    } catch (e) {
      setError("Failed to remove domain");
    }
  };

  if (loading) return <div className="text-center py-8">Loading domains...</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Custom Domains</h2>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="bg-white p-6 rounded-xl shadow mb-6">
        <h3 className="font-semibold mb-3">Add New Domain</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !adding && handleAdd()}
            placeholder="example.com"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={adding}
          />
          <button
            onClick={handleAdd}
            disabled={!newDomain.trim() || adding}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {adding ? "Adding..." : "Add Domain"}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Domain</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">SSL</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {domains.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                  No custom domains configured. Add one above.
                </td>
              </tr>
            ) : domains.map((d) => (
              <tr key={d.domain}>
                <td className="px-6 py-4 font-medium">{d.domain}</td>
                <td className="px-6 py-4">
                  {d.is_verified ? (
                    <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-sm">Verified</span>
                  ) : (
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm">Pending</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <span className={"px-2 py-1 rounded-full text-sm " +
                    (d.ssl_status === "active" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600")}>
                    {d.ssl_status || "pending"}
                  </span>
                </td>
                <td className="px-6 py-4 text-right space-x-2">
                  {!d.is_verified && (
                    <button
                      onClick={() => handleVerify(d.domain)}
                      className="px-3 py-1 text-sm border border-blue-500 text-blue-600 rounded hover:bg-blue-50"
                    >
                      Verify
                    </button>
                  )}
                  <button
                    onClick={() => handleRemove(d.domain)}
                    className="px-3 py-1 text-sm border border-red-500 text-red-600 rounded hover:bg-red-50"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {domains.some(d => !d.is_verified) && (
        <div className="mt-6 bg-blue-50 p-4 rounded-lg">
          <h4 className="font-semibold text-blue-800 mb-2">DNS Configuration</h4>
          <p className="text-sm text-blue-700 mb-2">
            Add a CNAME record pointing your domain to <code className="bg-blue-100 px-1 rounded">cname.vercel-dns.com</code>
          </p>
          <p className="text-sm text-gray-600">
            DNS changes can take up to 48 hours to propagate.
          </p>
        </div>
      )}
    </div>
  );
}

function FaibricAdmin() {
  const [auth, setAuth] = React.useState(!!localStorage.getItem("faibric_admin_token"));
  const [view, setView] = React.useState("overview");
  const passRef = React.useRef(null);

  const login = () => {
    if ((passRef.current?.value || "") === (localStorage.getItem("faibric_admin_pass") || "faibric123")) {
      localStorage.setItem("faibric_admin_token", "1");
      setAuth(true);
    } else alert("Wrong password");
  };

  if (!auth) return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="bg-white p-8 rounded-xl shadow-xl max-w-md w-full">
        <h1 className="text-2xl font-bold mb-4 text-center">Faibric Admin</h1>
        <input ref={passRef} type="password" placeholder="Password"
          onKeyDown={(e) => e.key === "Enter" && login()}
          className="w-full p-3 border rounded-lg mb-4" autoFocus />
        <button onClick={login} className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold">Login</button>
        <a href="/" className="block text-center text-gray-500 text-sm mt-4">Back to App</a>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <nav className="bg-gray-900 text-white p-4 flex justify-between items-center">
        <div className="flex gap-4">
          <span className="font-bold">Faibric Admin</span>
          {["overview", "builder", "integrations", "domains", "settings"].map(v => (
            <button key={v} onClick={() => setView(v)}
              className={"px-3 py-1 rounded " + (view === v ? "bg-blue-600" : "hover:bg-gray-700")}>
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex gap-4">
          <a href="/" className="hover:underline">View App</a>
          <button onClick={() => {localStorage.removeItem("faibric_admin_token"); setAuth(false)}} className="text-red-400">Logout</button>
        </div>
      </nav>

      {view === "builder" ? (
        <FaibricBuilder />
      ) : (
        <main className="p-6 max-w-4xl mx-auto flex-1">
          {view === "overview" && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white p-6 rounded-xl shadow">
                  <p className="text-gray-500">Page Views</p>
                  <p className="text-3xl font-bold">{parseInt(localStorage.getItem("faibric_views") || "0")}</p>
                </div>
                <div className="bg-white p-6 rounded-xl shadow">
                  <p className="text-gray-500">Sessions</p>
                  <p className="text-3xl font-bold">{parseInt(localStorage.getItem("faibric_sessions") || "0")}</p>
                </div>
              </div>
              <div className="mt-6 bg-white p-6 rounded-xl shadow">
                <h3 className="font-semibold mb-2">Quick Actions</h3>
                <button
                  onClick={() => setView("builder")}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Open Builder
                </button>
              </div>
            </div>
          )}
          {view === "integrations" && <FaibricIntegrations />}
          {view === "domains" && <FaibricDomains />}
          {view === "settings" && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Settings</h2>
              <div className="bg-white p-6 rounded-xl shadow">
                <h3 className="font-semibold mb-2">Change Password</h3>
                <input type="password" placeholder="New password"
                  onBlur={(e) => {if(e.target.value){localStorage.setItem("faibric_admin_pass",e.target.value); alert("Saved!")}}}
                  className="w-full p-2 border rounded" />
              </div>
            </div>
          )}
        </main>
      )}
    </div>
  );
}

function App() {
  React.useEffect(() => {
    const v = parseInt(localStorage.getItem("faibric_views") || "0") + 1;
    localStorage.setItem("faibric_views", v.toString());
    if (!sessionStorage.getItem("faibric_session")) {
      sessionStorage.setItem("faibric_session", "1");
      localStorage.setItem("faibric_sessions", (parseInt(localStorage.getItem("faibric_sessions") || "0") + 1).toString());
    }
  }, []);

  if (window.location.pathname.includes("/faibric")) return <FaibricAdmin />;
  return <_OriginalApp />;
}
'''

        return code + admin_wrapper
    
    def _file(self, path: str, content: str) -> dict:
        """Create a file object for Vercel API."""
        return {
            "file": path,
            "data": base64.b64encode(content.encode()).decode(),
            "encoding": "base64"  # Tell Vercel to decode the base64
        }

    def _file_binary(self, path: str, content: bytes) -> dict:
        """Create a binary file object for Vercel API (for images)."""
        return {
            "file": path,
            "data": base64.b64encode(content).decode(),
            "encoding": "base64"
        }

    def _create_deployment(self, project_name: str, files: list, project_id: int = None) -> dict:
        """Create a deployment via Vercel API."""
        
        # Use centralized URL generator for slug (ONLY lowercase + numbers)
        # This is the SINGLE SOURCE OF TRUTH for URL generation
        clean_name = url_generator.generate_slug(project_id)
        logger.info(f"[VERCEL] Using generated slug: {clean_name}")
        
        # Static deployment - no build, no npm install
        # Just serve the HTML file directly
        payload = {
            "name": clean_name,
            "files": files,
            "target": "production",  # Make it a production deployment
            "projectSettings": {
                "framework": None,  # Static site, no framework
                "buildCommand": "",  # No build needed
                "outputDirectory": ".",  # Serve from root
                "installCommand": ""  # No install needed
            }
        }
        
        # Add team ID if configured
        params = {"skipAutoDetectionConfirmation": "1"}  # Skip framework detection
        if self.team_id:
            params["teamId"] = self.team_id
        
        response = requests.post(
            f"{VERCEL_API_URL}/v13/deployments",
            headers=self.headers,
            params=params,
            json=payload,
            timeout=60
        )
        
        if response.status_code in (200, 201):
            return response.json()
        else:
            logger.error(f"[VERCEL] API error: {response.status_code} - {response.text}")
            return {"error": f"API error: {response.status_code}"}
    
    def _verify_deployment(self, url: str) -> dict:
        """
        Verify the deployed app actually works.
        
        CRITICAL: This is the LAST LINE OF DEFENSE before showing a URL to user.
        If this passes, the URL MUST work when opened in a browser.
        
        Checks:
        1. URL returns HTTP 200
        2. Content is valid HTML (not base64)
        3. Contains React app structure
        4. No JavaScript syntax errors that would crash Babel
        5. No duplicate variable declarations (causes Babel to fail)
        6. Balanced braces/parentheses
        
        Returns: {'valid': bool, 'error': str or None}
        """
        import re
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                return {'valid': False, 'error': f'HTTP {response.status_code}'}
            
            content = response.text
            
            # Check 1: Content should start with HTML doctype
            if not content.strip().startswith('<!DOCTYPE html>'):
                if content.strip()[:20].isalnum():
                    return {'valid': False, 'error': 'Content is base64 encoded, not HTML'}
                return {'valid': False, 'error': 'Content is not valid HTML'}
            
            # Check 2: Should contain React app structure
            if 'function App' not in content and 'const App' not in content:
                return {'valid': False, 'error': 'No App component found'}
            
            # Check 3: Should have React imports from CDN
            if 'react.production.min.js' not in content:
                return {'valid': False, 'error': 'React CDN not included'}
            
            # Check 4: Check for obvious JavaScript syntax errors
            broken_pattern = r'const\s+\w+\s*,\s*\w+\s*,'
            if re.search(broken_pattern, content):
                return {'valid': False, 'error': 'JavaScript syntax error: broken object literals'}
            
            # Check 5: Verify Babel presets
            if 'data-presets="react,typescript"' not in content:
                return {'valid': False, 'error': 'Missing TypeScript Babel preset'}
            
            # NEW Check 6: Detect DUPLICATE variable declarations (causes Babel crash)
            # Look for common admin panel variables being declared multiple times
            critical_vars = ['isAdminRoute', 'adminAuth', 'adminView', 'renderDashboard', 'renderLogin']
            for var in critical_vars:
                pattern = f'const \\[{var}'
                matches = re.findall(pattern, content)
                if len(matches) > 1:
                    return {'valid': False, 'error': f'Duplicate declaration of {var} ({len(matches)} times) - will crash Babel'}
            
            # Check for duplicate function declarations
            func_pattern = r'const (renderDashboard|renderLogin|doLogin|doLogout|sendChat)\s*='
            func_matches = re.findall(func_pattern, content)
            func_counts = {}
            for f in func_matches:
                func_counts[f] = func_counts.get(f, 0) + 1
            for f, count in func_counts.items():
                if count > 1:
                    return {'valid': False, 'error': f'Duplicate function {f} ({count} times) - will crash Babel'}
            
            # NEW Check 7: Balanced braces (approximate check)
            open_braces = content.count('{')
            close_braces = content.count('}')
            if abs(open_braces - close_braces) > 5:  # Allow small imbalance for edge cases
                return {'valid': False, 'error': f'Severely unbalanced braces: {open_braces} open, {close_braces} close'}
            
            # NEW Check 8: Balanced parentheses
            open_parens = content.count('(')
            close_parens = content.count(')')
            if abs(open_parens - close_parens) > 5:
                return {'valid': False, 'error': f'Severely unbalanced parentheses: {open_parens} open, {close_parens} close'}
            
            return {'valid': True, 'error': None}
            
        except requests.RequestException as e:
            return {'valid': False, 'error': f'Network error: {str(e)}'}
        except Exception as e:
            return {'valid': False, 'error': f'Verification error: {str(e)}'}
    
    def _disable_sso_protection(self, project_name: str):
        """Disable SSO protection so deployments are publicly accessible."""
        try:
            # Find project by name
            params = {"teamId": self.team_id} if self.team_id else {}
            resp = requests.get(
                f"{VERCEL_API_URL}/v9/projects/{project_name}",
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if resp.status_code == 200:
                project_id = resp.json().get('id')
                
                # Disable SSO protection
                update_resp = requests.patch(
                    f"{VERCEL_API_URL}/v9/projects/{project_id}",
                    headers=self.headers,
                    params=params,
                    json={"ssoProtection": None},
                    timeout=10
                )
                
                if update_resp.status_code == 200:
                    logger.info(f"[VERCEL] Disabled SSO protection for {project_name}")
        except Exception as e:
            logger.warning(f"[VERCEL] Could not disable SSO protection: {e}")
    
    def _add_custom_domain(self, project_name: str, domain: str):
        """
        Add a custom domain (e.g., app123.faibric.com) to a Vercel project.
        
        This enables the app to be accessed via faibric.com subdomain.
        """
        try:
            params = {"teamId": self.team_id} if self.team_id else {}
            
            # Add domain to project
            resp = requests.post(
                f"{VERCEL_API_URL}/v10/projects/{project_name}/domains",
                headers=self.headers,
                params=params,
                json={"name": domain},
                timeout=15
            )
            
            if resp.status_code in (200, 201):
                logger.info(f"[VERCEL] Added custom domain: {domain}")
                # Issue SSL certificate for the domain
                self._issue_ssl_certificate(domain)
            elif resp.status_code == 409:
                # Domain already exists, that's fine
                logger.info(f"[VERCEL] Domain already configured: {domain}")
            else:
                error = resp.json().get('error', {}).get('message', resp.text)
                logger.warning(f"[VERCEL] Could not add domain {domain}: {error}")
        except Exception as e:
            logger.warning(f"[VERCEL] Error adding custom domain: {e}")
    
    def _issue_ssl_certificate(self, domain: str):
        """
        Request an SSL certificate for a domain from Vercel/Let's Encrypt.
        
        This is required for HTTPS to work on custom domains.
        """
        try:
            params = {"teamId": self.team_id} if self.team_id else {}
            
            resp = requests.post(
                f"{VERCEL_API_URL}/v6/certs",
                headers=self.headers,
                params=params,
                json={"domains": [domain]},
                timeout=30
            )
            
            if resp.status_code in (200, 201):
                cert_data = resp.json()
                logger.info(f"[VERCEL] SSL certificate issued for {domain}, expires: {cert_data.get('expiration')}")
            else:
                error = resp.json().get('error', {}).get('message', resp.text)
                logger.warning(f"[VERCEL] Could not issue SSL cert for {domain}: {error}")
        except Exception as e:
            logger.warning(f"[VERCEL] Error issuing SSL certificate: {e}")
    
    def _wait_for_ready(self, deployment_id: str, timeout: int = 180) -> dict:
        """
        Wait for deployment to be ready.
        
        Returns:
            dict with keys:
            - success: bool
            - url: str (if success)
            - error: str (if failed)
            - build_error: str (specific build error message if available)
        """
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
        
        start = time.time()
        while time.time() - start < timeout:
            response = requests.get(
                f"{VERCEL_API_URL}/v13/deployments/{deployment_id}",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                state = data.get("readyState", data.get("state"))
                
                if state == "READY":
                    # Return the production URL
                    url = data.get("url")
                    if url and not url.startswith("http"):
                        url = f"https://{url}"
                    return {"success": True, "url": url}
                    
                elif state in ("ERROR", "CANCELED"):
                    # Try to get the build error details
                    build_error = self._get_build_error(deployment_id)
                    logger.error(f"[VERCEL] Deployment failed: {state}")
                    if build_error:
                        logger.error(f"[VERCEL] Build error: {build_error}")
                    return {
                        "success": False,
                        "error": f"Build {state.lower()}",
                        "build_error": build_error
                    }
                else:
                    # Still building
                    logger.debug(f"[VERCEL] State: {state}")
            
            time.sleep(3)
        
        logger.error(f"[VERCEL] Deployment timed out after {timeout}s")
        return {"success": False, "error": "Deployment timed out"}
    
    def _get_build_error(self, deployment_id: str) -> Optional[str]:
        """Fetch build logs to extract error message."""
        try:
            params = {}
            if self.team_id:
                params["teamId"] = self.team_id
            
            # Get deployment events/logs
            response = requests.get(
                f"{VERCEL_API_URL}/v2/deployments/{deployment_id}/events",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                events = response.json()
                # Look for error events
                for event in reversed(events):  # Most recent first
                    if event.get("type") == "error":
                        return event.get("text", event.get("payload", {}).get("text", ""))
                    # Also check for build output with errors
                    text = event.get("text", "")
                    if "error" in text.lower() or "Error:" in text:
                        return text
            
            return None
        except Exception as e:
            logger.warning(f"[VERCEL] Could not fetch build error: {e}")
            return None
    
    def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a deployment."""
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
        
        response = requests.delete(
            f"{VERCEL_API_URL}/v13/deployments/{deployment_id}",
            headers=self.headers,
            params=params,
            timeout=30
        )
        
        return response.status_code in (200, 204)


# Singleton instance
_vercel_deployer = None

def get_vercel_deployer() -> VercelDeployer:
    """Get or create VercelDeployer instance."""
    global _vercel_deployer
    if _vercel_deployer is None:
        _vercel_deployer = VercelDeployer()
    return _vercel_deployer

