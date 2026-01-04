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

from .url_generator import url_generator

logger = logging.getLogger(__name__)

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
        project_id: str = None
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
        
        try:
            # Step 1: Generate all files for the React app
            # Pass project_id to inject builder config
            files = self._generate_files(app_code, project_name, project_id)
            
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
            
            # Step 3: Wait for deployment to be ready
            deployment_url = self._wait_for_ready(deployment['id'])
            
            deploy_time = time.time() - start_time
            
            if deployment_url:
                # CRITICAL: Verify the deployment actually works before reporting success
                verification = self._verify_deployment(deployment_url)
                
                if not verification['valid']:
                    logger.error(f"[VERCEL] Deployment verification FAILED: {verification['error']}")
                    return {
                        'success': False,
                        'error': f"Deployment verification failed: {verification['error']}",
                        'url': deployment_url,
                        'deployment_id': deployment['id'],
                        'provider': 'vercel'
                    }
                
                logger.info(f"[VERCEL] Deployed and VERIFIED {project_name} in {deploy_time:.1f}s: {deployment_url}")
                return {
                    'success': True,
                    'url': deployment_url,
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
    
    def _generate_files(self, app_code: str, project_name: str, project_id: str = None) -> list:
        """
        Generate files for instant static deployment.
        
        Strategy: Use CDN-based React + Tailwind for INSTANT deploys (no build step).
        This gives us 5-10 second deploys instead of 60+ seconds for Vite builds.
        
        The app runs exactly the same - just loaded from CDN instead of bundled.
        """
        import hashlib
        
        files = []
        
        # Convert TypeScript-style React to browser-compatible JSX
        # The app_code uses TypeScript syntax, we need to adapt it for browser
        browser_app = self._convert_to_browser_react(app_code)
        
        # Inject Faibric admin panel
        browser_app = self._inject_admin_panel(browser_app)
        
        # Generate project token for builder API
        project_token = ""
        if project_id:
            project_token = hashlib.sha256(
                f"{project_id}faibric_builder_secret".encode()
            ).hexdigest()[:16]
        
        # index.html with CDN React + Tailwind + TypeScript support
        # INJECT: Project ID and token for the builder to work
        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script>
        // Faibric Builder Configuration
        window.FAIBRIC_PROJECT_ID = "{project_id or ''}";
        window.FAIBRIC_PROJECT_TOKEN = "{project_token}";
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
</body>
</html>'''
        
        files.append(self._file("index.html", index_html))
        
        # vercel.json for SPA routing - enables /faibric admin panel
        # All routes go to index.html so React can handle routing
        # X-Frame-Options set to SAMEORIGIN to allow iframe in admin panel
        vercel_config = '''{
  "rewrites": [
    { "source": "/(.*)", "destination": "/" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "SAMEORIGIN" }
      ]
    }
  ]
}'''
        files.append(self._file("vercel.json", vercel_config))
        
        return files
    
    def _convert_to_browser_react(self, code: str) -> str:
        """
        Convert TypeScript/module React code to browser-compatible JavaScript.
        
        CAREFUL: Only remove TypeScript-specific syntax, not valid JS!
        Object literals like { name: "value" } must be preserved.
        """
        import re
        
        # Remove import lines
        code = re.sub(r'^import\s+.*$', '', code, flags=re.MULTILINE)
        
        # Remove export statements
        code = re.sub(r'export\s+default\s+\w+;?\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'export\s+default\s+function', 'function', code)
        code = re.sub(r'^export\s+(?=const|let|var|function|class)', '', code, flags=re.MULTILINE)
        
        # Remove interface declarations (multi-line) - be careful with braces
        code = re.sub(r'^interface\s+\w+\s*\{[^}]*\}\s*$', '', code, flags=re.MULTILINE | re.DOTALL)
        
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
        
        # Remove ONLY function parameter type annotations (in function signatures)
        # (param: Type) -> (param) but NOT inside objects
        # Pattern: word followed by : and a type, only inside parentheses
        code = re.sub(r'\(([^)]*)\)', lambda m: '(' + re.sub(r'(\w+)\s*:\s*(?:string|number|boolean|any|void|null|undefined|React\.\w+|\w+\[\]|Record<[^>]+>|Array<[^>]+>)(?=\s*[,\)=])', r'\1', m.group(1)) + ')', code)
        
        # Remove arrow function return type annotations
        # ): Type => becomes ) =>
        code = re.sub(r'\)\s*:\s*[\w\[\]<>,\s\|]+\s*=>', ') =>', code)
        
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
        
        # Add the admin wrapper at the end
        admin_wrapper = '''

// FAIBRIC ADMIN PANEL
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
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-gray-900 text-white p-4 flex justify-between">
        <div className="flex gap-4">
          <span className="font-bold">Faibric Admin</span>
          {["overview", "settings"].map(v => (
            <button key={v} onClick={() => setView(v)} 
              className={"px-3 py-1 rounded " + (view === v ? "bg-blue-600" : "hover:bg-gray-700")}>
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex gap-4">
          <a href="/">View App</a>
          <button onClick={() => {localStorage.removeItem("faibric_admin_token"); setAuth(false)}} className="text-red-400">Logout</button>
        </div>
      </nav>
      <main className="p-6 max-w-4xl mx-auto">
        {view === "overview" && (
          <div>
            <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white p-6 rounded-xl shadow">
                <p className="text-gray-500">Views</p>
                <p className="text-3xl font-bold">{parseInt(localStorage.getItem("faibric_views") || "0")}</p>
              </div>
              <div className="bg-white p-6 rounded-xl shadow">
                <p className="text-gray-500">Sessions</p>
                <p className="text-3xl font-bold">{parseInt(localStorage.getItem("faibric_sessions") || "0")}</p>
              </div>
            </div>
          </div>
        )}
        {view === "settings" && (
          <div>
            <h2 className="text-2xl font-bold mb-4">Settings</h2>
            <div className="bg-white p-6 rounded-xl shadow">
              <input type="password" placeholder="New password" 
                onBlur={(e) => {if(e.target.value){localStorage.setItem("faibric_admin_pass",e.target.value); alert("Saved!")}}}
                className="w-full p-2 border rounded" />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function App() {
  React.useEffect(() => {
    localStorage.setItem("faibric_views", (parseInt(localStorage.getItem("faibric_views") || "0") + 1).toString());
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
    
    def _wait_for_ready(self, deployment_id: str, timeout: int = 180) -> Optional[str]:
        """Wait for deployment to be ready and return the URL."""
        
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
                    return url
                elif state in ("ERROR", "CANCELED"):
                    logger.error(f"[VERCEL] Deployment failed: {state}")
                    return None
                else:
                    # Still building
                    logger.debug(f"[VERCEL] State: {state}")
            
            time.sleep(3)
        
        logger.error(f"[VERCEL] Deployment timed out after {timeout}s")
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

