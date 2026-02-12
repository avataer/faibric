"""
Render.com Deployer - Deploy generated apps to Render as static sites

Strategy:
1. Push generated code to GitHub (branch per app)
2. Create Render static site via API
3. Return the deployment URL
"""
import os
import json
import base64
import hashlib
import requests
from django.conf import settings

from .url_generator import url_generator


class RenderDeployer:
    """
    Deploy React apps to Render.com via their API
    """
    
    def __init__(self):
        self.render_api = "https://api.render.com/v1"
        self.github_api = "https://api.github.com"
    
    @property
    def render_api_key(self):
        """Get API key - always read fresh from env."""
        return os.environ.get('RENDER_API_KEY', '') or getattr(settings, 'RENDER_API_KEY', '')
    
    @property
    def github_token(self):
        """Get token - always read fresh from env."""
        token = os.environ.get('GITHUB_TOKEN', '')
        if not token:
            token = getattr(settings, 'GITHUB_TOKEN', '')
        # Debug log
        import logging
        logging.getLogger(__name__).info(f"github_token property: {'FOUND' if token else 'MISSING'} (len={len(token) if token else 0})")
        return token
    
    @property
    def github_repo(self):
        """Get repo - always read fresh from env."""
        return os.environ.get('GITHUB_APPS_REPO', '') or getattr(settings, 'GITHUB_APPS_REPO', 'avataer/faibric-apps')
    
    @property
    def render_owner_id(self):
        """Get owner ID - always read fresh from env."""
        return os.environ.get('RENDER_OWNER_ID', '') or getattr(settings, 'RENDER_OWNER_ID', '')
    
    def deploy_react_app(self, project):
        """Deploy React app to Render.com"""
        try:
            # Check if a Render service already exists for this project
            # If so, use its branch to push updates (not a new random branch)
            existing_branch = self._get_existing_service_branch(project)
            if existing_branch:
                branch_name = existing_branch
            else:
                branch_name = self._get_branch_name(project)
            
            # Extract and prepare the code
            frontend_code = self._extract_frontend_code(project)
            
            # Push code to GitHub branch
            self._push_to_github(branch_name, frontend_code, project)
            
            # Create or update Render static site
            render_url = self._create_render_site(branch_name, project)

            # Generate the canonical faibric.com URL (for reference)
            canonical_url = url_generator.generate_url(slug=branch_name)

            # BYPASS: Return Render URL directly to avoid SSL rate limits on faibric.com
            # The faibric.com subdomains have hit Let's Encrypt rate limits
            # Return render_url as primary URL until rate limit resets
            return {
                'success': True,
                'url': render_url,  # Return Render URL directly (bypass faibric.com SSL issues)
                'canonical_url': canonical_url,  # Keep faibric.com URL for reference
                'branch': branch_name
            }
            
        except Exception as e:
            print(f"[ERROR] Render deployment error: {str(e)}")
            raise Exception(f"Failed to deploy to Render: {str(e)}")
    
    def _get_branch_name(self, project):
        """
        Generate unique branch name for project.
        
        Uses centralized URL generator - SINGLE SOURCE OF TRUTH.
        Format: app{random_lowercase_alphanumeric}
        """
        return url_generator.generate_branch(project.id)
    
    def _extract_frontend_code(self, project):
        """Extract frontend code from project"""
        if not project.frontend_code:
            raise ValueError("No frontend code found - cannot deploy")

        try:
            if isinstance(project.frontend_code, str):
                try:
                    code_dict = json.loads(project.frontend_code)
                except json.JSONDecodeError:
                    import ast
                    code_dict = ast.literal_eval(project.frontend_code)
            else:
                code_dict = project.frontend_code

            if not code_dict.get('App.jsx') and not code_dict.get('App.tsx'):
                raise ValueError("Frontend code missing App.jsx")

            return {
                'App.jsx': code_dict.get('App.jsx') or code_dict.get('App.tsx', ''),
                'components': code_dict.get('components', {})
            }
        except Exception as e:
            raise ValueError(f"Failed to parse frontend code: {e}")
    
    def _push_to_github(self, branch_name, frontend_code, project):
        """Push generated code to GitHub branch"""
        if not self.github_token:
            raise Exception("GITHUB_TOKEN not configured")
        
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        owner, repo = self.github_repo.split('/')
        
        # Ensure repo exists (create if needed)
        self._ensure_repo_exists(owner, repo, headers)
        
        # Get or create branch from main
        base_sha = self._get_or_create_branch(owner, repo, branch_name, headers)
        
        # Create tree with all files
        tree = self._create_file_tree(owner, repo, frontend_code, project, headers)
        
        # Create commit
        commit_sha = self._create_commit(owner, repo, tree, base_sha, 
                                         f"Deploy {project.name}", headers)
        
        # Update branch ref
        self._update_branch_ref(owner, repo, branch_name, commit_sha, headers)
        
        print(f"[OK] Pushed to GitHub: {self.github_repo}#{branch_name}")
    
    def _ensure_repo_exists(self, owner, repo, headers):
        """Ensure the apps repository exists"""
        resp = requests.get(f"{self.github_api}/repos/{owner}/{repo}", headers=headers)
        if resp.status_code == 404:
            # Create the repo
            resp = requests.post(
                f"{self.github_api}/user/repos",
                headers=headers,
                json={
                    'name': repo,
                    'private': False,
                    'auto_init': True,
                    'description': 'Faibric generated apps'
                }
            )
            if resp.status_code not in [200, 201]:
                raise Exception(f"Failed to create repo: {resp.text}")
    
    def _get_or_create_branch(self, owner, repo, branch_name, headers):
        """Get existing branch or create from main"""
        # Try to get the branch
        resp = requests.get(
            f"{self.github_api}/repos/{owner}/{repo}/git/ref/heads/{branch_name}",
            headers=headers
        )
        
        if resp.status_code == 200:
            return resp.json()['object']['sha']
        
        # Get main branch SHA
        resp = requests.get(
            f"{self.github_api}/repos/{owner}/{repo}/git/ref/heads/main",
            headers=headers
        )
        
        if resp.status_code != 200:
            # Try master if main doesn't exist
            resp = requests.get(
                f"{self.github_api}/repos/{owner}/{repo}/git/ref/heads/master",
                headers=headers
            )
        
        if resp.status_code != 200:
            raise Exception(f"Could not find main/master branch: {resp.text}")
        
        main_sha = resp.json()['object']['sha']
        
        # Create new branch
        resp = requests.post(
            f"{self.github_api}/repos/{owner}/{repo}/git/refs",
            headers=headers,
            json={
                'ref': f'refs/heads/{branch_name}',
                'sha': main_sha
            }
        )
        
        if resp.status_code not in [200, 201]:
            raise Exception(f"Failed to create branch: {resp.text}")
        
        return main_sha
    
    def _create_file_tree(self, owner, repo, frontend_code, project, headers):
        """Create Git tree with all files"""
        files = self._generate_all_files(frontend_code, project)
        
        blobs = []
        for path, content in files.items():
            # Create blob
            resp = requests.post(
                f"{self.github_api}/repos/{owner}/{repo}/git/blobs",
                headers=headers,
                json={
                    'content': content,
                    'encoding': 'utf-8'
                }
            )
            if resp.status_code not in [200, 201]:
                raise Exception(f"Failed to create blob for {path}: {resp.text}")
            
            blobs.append({
                'path': path,
                'mode': '100644',
                'type': 'blob',
                'sha': resp.json()['sha']
            })
        
        # Create tree
        resp = requests.post(
            f"{self.github_api}/repos/{owner}/{repo}/git/trees",
            headers=headers,
            json={'tree': blobs}
        )
        
        if resp.status_code not in [200, 201]:
            raise Exception(f"Failed to create tree: {resp.text}")
        
        return resp.json()['sha']
    
    def _create_commit(self, owner, repo, tree_sha, parent_sha, message, headers):
        """Create a commit"""
        resp = requests.post(
            f"{self.github_api}/repos/{owner}/{repo}/git/commits",
            headers=headers,
            json={
                'message': message,
                'tree': tree_sha,
                'parents': [parent_sha]
            }
        )
        
        if resp.status_code not in [200, 201]:
            raise Exception(f"Failed to create commit: {resp.text}")
        
        return resp.json()['sha']
    
    def _update_branch_ref(self, owner, repo, branch_name, commit_sha, headers):
        """Update branch to point to new commit"""
        resp = requests.patch(
            f"{self.github_api}/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
            headers=headers,
            json={
                'sha': commit_sha,
                'force': True
            }
        )
        
        if resp.status_code not in [200, 201]:
            raise Exception(f"Failed to update branch: {resp.text}")
    
    def _generate_all_files(self, frontend_code, project):
        """Generate all files needed for the React app"""
        files = {}
        
        # package.json - Plain JavaScript (no TypeScript per Base44 lessons)
        files['package.json'] = json.dumps({
            "name": f"app-{project.id}",
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0"
            },
            "devDependencies": {
                "@vitejs/plugin-react": "^4.2.0",
                "vite": "^5.0.0",
                "tailwindcss": "^3.4.0",
                "postcss": "^8.4.0",
                "autoprefixer": "^10.4.0"
            }
        }, indent=2)
        
        # vite.config.js (plain JavaScript)
        files['vite.config.js'] = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
"""
        
        # tailwind.config.js - CRITICAL for styling!
        files['tailwind.config.js'] = """/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
"""
        
        # postcss.config.js - Required for Tailwind
        files['postcss.config.js'] = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""
        
        # No tsconfig.json - using plain JavaScript per Base44 lessons
        # LLMs produce more reliable JS than TS

        # index.html - with SPA routing handler for 404 redirects
        files['index.html'] = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{self._generate_title(project.name)}</title>
    <style>* {{ margin: 0; padding: 0; box-sizing: border-box; }}</style>
    <script>
      // Handle SPA redirect from 404.html
      (function(){{
        var redirect = sessionStorage.redirect;
        delete sessionStorage.redirect;
        if (redirect && redirect !== location.href) {{
          history.replaceState(null, null, redirect);
        }}
      }})();
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""
        
        # src/index.css - Tailwind base styles
        files['src/index.css'] = """@tailwind base;
@tailwind components;
@tailwind utilities;

/* Base styles */
body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
"""
        
        # src/main.jsx - MUST import index.css for Tailwind to work!
        files['src/main.jsx'] = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""
        
        # src/App.jsx - with admin panel injection
        app_code = frontend_code.get('App.jsx') or frontend_code.get('App.tsx', '')

        # Inject admin panel if not present
        if 'isAdminRoute' not in app_code:
            app_code = self._inject_admin_panel(app_code, project)

        # CRITICAL: Add React import for Vite builds
        # Modular composer generates code with React.useState() etc expecting React as global
        # Vite requires explicit import
        if not app_code.strip().startswith('import React'):
            app_code = "import React from 'react';\n\n" + app_code

        files['src/App.jsx'] = app_code

        # Components - use .jsx extension
        for comp_name, comp_code in frontend_code.get('components', {}).items():
            # Strip any existing extension and add .jsx
            clean_name = comp_name.replace('.tsx', '').replace('.jsx', '').replace('.js', '')
            files[f'src/components/{clean_name}.jsx'] = comp_code
        
        # render.yaml - SPA routing configuration (used by Blueprint deploys)
        files['render.yaml'] = f"""services:
  - type: web
    name: app-{project.id}
    env: static
    buildCommand: npm install && npm run build
    staticPublishPath: ./dist
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
"""
        
        # CRITICAL: _redirects file for Render static site SPA routing
        # This file must be in public/ so Vite copies it to dist/
        # Without this, routes like /faibric return 404
        files['public/_redirects'] = """/* /index.html 200"""
        
        # Also add a 404.html that redirects to index.html (fallback for some hosts)
        files['public/404.html'] = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Redirecting...</title>
  <script>
    // SPA redirect: store the original path and redirect to /
    sessionStorage.redirect = location.href;
    location.replace('/');
  </script>
</head>
<body></body>
</html>"""
        
        return files
    
    def _generate_title(self, project_name: str) -> str:
        """
        Generate a professional page title from the project name/prompt.
        """
        import re
        
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
        
        if len(clean) > 50:
            clean = clean[:50]
            last_space = clean.rfind(' ')
            if last_space > 20:
                clean = clean[:last_space]
        
        clean = clean.strip().title()
        
        if len(clean) < 3:
            clean = "My App"
        
        return clean
    
    def _inject_admin_panel(self, code: str, project) -> str:
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
        # Pattern: function App, const App =, const App: Type =, export default function App
        # NOTE: Must handle TypeScript type annotations like "const App: React.FC = () =>"
        app_patterns = [
            (r'export\s+default\s+function\s+App', 'function _OriginalApp'),
            (r'function\s+App\s*\(', 'function _OriginalApp('),
            (r'const\s+App:\s*[^=]+\s*=', 'const _OriginalApp = '),  # Remove TypeScript type annotation
            (r'const\s+App\s*=', 'const _OriginalApp ='),  # Plain: const App =
        ]

        renamed = False
        for pattern, replacement in app_patterns:
            if re.search(pattern, code):
                code = re.sub(pattern, replacement, code, count=1)
                renamed = True
                break

        if not renamed:
            print("[ADMIN] WARNING: Could not find App to rename")
            return code

        # Remove any existing export default App
        code = re.sub(r'export\s+default\s+App\s*;?\s*$', '', code, flags=re.MULTILINE)

        # Get session token for the builder feature
        session_token = ""
        api_url = "https://faibric-api.onrender.com"
        site_url = ""
        try:
            # Try to get session token from project's linked session
            session = project.landingsession_set.first()
            if session:
                session_token = session.session_token
            site_url = project.deployment_url or ""
        except Exception as e:
            print(f"[ADMIN] Could not get session token: {e}")

        # Add the admin wrapper at the end of the file
        admin_wrapper = f'''

// FAIBRIC ADMIN PANEL WRAPPER with BUILDER
const FAIBRIC_SESSION_TOKEN = "{session_token}";
const FAIBRIC_API_URL = "{api_url}";
const FAIBRIC_SITE_URL = "{site_url}";

function FaibricBuilder() {{
  const [messages, setMessages] = React.useState([
    {{ role: "system", content: "Welcome! Describe what changes you want to make to your website." }}
  ]);
  const [input, setInput] = React.useState("");
  const [isBuilding, setIsBuilding] = React.useState(false);
  const [buildProgress, setBuildProgress] = React.useState(0);
  const [previewUrl, setPreviewUrl] = React.useState(window.location.origin);
  const [iframeKey, setIframeKey] = React.useState(0);
  const messagesEndRef = React.useRef(null);

  // Scroll to bottom when messages change
  React.useEffect(() => {{
    messagesEndRef.current?.scrollIntoView({{ behavior: "smooth" }});
  }}, [messages]);

  // Poll for build status
  React.useEffect(() => {{
    if (!isBuilding || !FAIBRIC_SESSION_TOKEN) return;

    const poll = setInterval(async () => {{
      try {{
        const res = await fetch(FAIBRIC_API_URL + "/api/onboarding/status/" + FAIBRIC_SESSION_TOKEN + "/");
        const data = await res.json();

        if (data.build_progress) setBuildProgress(data.build_progress);

        // Check for new events
        if (data.events && data.events.length > 0) {{
          const latestEvent = data.events[0];
          if (latestEvent.event_data?.message) {{
            setMessages(prev => {{
              const lastMsg = prev[prev.length - 1];
              if (lastMsg?.content !== latestEvent.event_data.message) {{
                return [...prev, {{ role: "system", content: latestEvent.event_data.message }}];
              }}
              return prev;
            }});
          }}
        }}

        if (data.status === "deployed") {{
          setIsBuilding(false);
          setBuildProgress(100);
          if (data.deployment_url) {{
            setPreviewUrl(data.deployment_url);
            setIframeKey(k => k + 1);
          }}
          setMessages(prev => [...prev, {{ role: "system", content: "Changes deployed! Refreshing preview..." }}]);
          clearInterval(poll);
        }}
      }} catch (e) {{
        console.error("Poll error:", e);
      }}
    }}, 2000);

    return () => clearInterval(poll);
  }}, [isBuilding]);

  const handleSend = async () => {{
    if (!input.trim() || isBuilding) return;

    const userMessage = input.trim();
    setMessages(prev => [...prev, {{ role: "user", content: userMessage }}]);
    setInput("");
    setIsBuilding(true);
    setBuildProgress(10);

    if (!FAIBRIC_SESSION_TOKEN) {{
      setMessages(prev => [...prev, {{ role: "system", content: "Builder not configured. Please contact support." }}]);
      setIsBuilding(false);
      return;
    }}

    try {{
      const res = await fetch(FAIBRIC_API_URL + "/api/onboarding/modify/", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          session_token: FAIBRIC_SESSION_TOKEN,
          request: userMessage
        }})
      }});

      const data = await res.json();

      if (data.success) {{
        setMessages(prev => [...prev, {{
          role: "assistant",
          content: data.mode === "modify"
            ? "Got it! Applying your changes..."
            : "Starting fresh build with your new request..."
        }}]);
      }} else {{
        setMessages(prev => [...prev, {{ role: "system", content: "Error: " + (data.error || "Failed to submit") }}]);
        setIsBuilding(false);
      }}
    }} catch (e) {{
      setMessages(prev => [...prev, {{ role: "system", content: "Connection error. Please try again." }}]);
      setIsBuilding(false);
    }}
  }};

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {{/* LEFT: Chat Panel */}}
      <div className="w-2/5 min-w-[350px] flex flex-col border-r border-gray-200 bg-white">
        {{/* Chat Header */}}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="font-semibold text-lg">Faibric Builder</h3>
          {{isBuilding && (
            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
              Building... {{buildProgress}}%
            </span>
          )}}
        </div>

        {{/* Messages */}}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {{messages.map((msg, i) => (
            <div key={{i}} className={{`flex ${{msg.role === "user" ? "justify-end" : "justify-start"}}`}}>
              <div className={{`max-w-[80%] p-3 rounded-lg ${{
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : msg.role === "assistant"
                    ? "bg-gray-100 text-gray-800 border border-gray-200"
                    : "bg-gray-50 text-gray-600 italic text-sm"
              }}`}}>
                {{msg.content}}
              </div>
            </div>
          ))}}
          <div ref={{messagesEndRef}} />
        </div>

        {{/* Input */}}
        <div className="p-4 border-t border-gray-200">
          <div className="flex gap-2">
            <input
              type="text"
              value={{input}}
              onChange={{(e) => setInput(e.target.value)}}
              onKeyDown={{(e) => e.key === "Enter" && !isBuilding && handleSend()}}
              placeholder={{isBuilding ? "Building in progress..." : "Describe changes you want..."}}
              disabled={{isBuilding}}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            <button
              onClick={{handleSend}}
              disabled={{!input.trim() || isBuilding}}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {{/* RIGHT: Preview Panel */}}
      <div className="flex-1 flex flex-col bg-gray-50">
        {{/* Preview Header */}}
        <div className="p-4 border-b border-gray-200 bg-white flex items-center justify-between">
          <h3 className="font-semibold">Live Preview</h3>
          <div className="flex gap-2">
            <button
              onClick={{() => setIframeKey(k => k + 1)}}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100"
            >
              Refresh
            </button>
            <button
              onClick={{() => window.open(previewUrl, "_blank")}}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100"
            >
              Open in Tab
            </button>
          </div>
        </div>

        {{/* Preview iframe */}}
        <div className="flex-1 p-4">
          <iframe
            key={{iframeKey}}
            src={{previewUrl}}
            className="w-full h-full border border-gray-200 rounded-lg bg-white"
            title="Website Preview"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
        </div>
      </div>
    </div>
  );
}}

function FaibricAdmin() {{
  const [adminAuth, setAdminAuth] = React.useState(!!localStorage.getItem("faibric_admin_token"));
  const [adminView, setAdminView] = React.useState("overview");
  const passRef = React.useRef(null);

  const login = () => {{
    const p = passRef.current?.value || "";
    if (p === (localStorage.getItem("faibric_admin_pass") || "faibric123")) {{
      localStorage.setItem("faibric_admin_token", "1");
      setAdminAuth(true);
    }} else alert("Wrong password");
  }};

  if (!adminAuth) {{
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-white p-8 rounded-xl shadow-xl max-w-md w-full">
          <h1 className="text-2xl font-bold mb-4 text-center">Faibric Admin</h1>
          <input ref={{passRef}} type="password" placeholder="Password"
            onKeyDown={{(e) => e.key === "Enter" && login()}}
            className="w-full p-3 border rounded-lg mb-4" autoFocus />
          <button onClick={{login}} className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold">Login</button>
          <a href="/" className="block text-center text-gray-500 text-sm mt-4">Back to App</a>
        </div>
      </div>
    );
  }}

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <nav className="bg-gray-900 text-white p-4 flex justify-between items-center">
        <div className="flex gap-4">
          <span className="font-bold">Faibric Admin</span>
          {{["overview", "builder", "settings"].map(v => (
            <button key={{v}} onClick={{() => setAdminView(v)}}
              className={{"px-3 py-1 rounded " + (adminView === v ? "bg-blue-600" : "hover:bg-gray-700")}}>
              {{v.charAt(0).toUpperCase() + v.slice(1)}}
            </button>
          ))}}
        </div>
        <div className="flex gap-4">
          <a href="/" className="hover:underline">View App</a>
          <button onClick={{() => {{localStorage.removeItem("faibric_admin_token"); setAdminAuth(false)}}}} className="text-red-400">Logout</button>
        </div>
      </nav>

      {{adminView === "builder" ? (
        <FaibricBuilder />
      ) : (
        <main className="p-6 max-w-4xl mx-auto flex-1">
          {{adminView === "overview" && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white p-6 rounded-xl shadow">
                  <p className="text-gray-500">Page Views</p>
                  <p className="text-3xl font-bold">{{parseInt(localStorage.getItem("faibric_views") || "0")}}</p>
                </div>
                <div className="bg-white p-6 rounded-xl shadow">
                  <p className="text-gray-500">Sessions</p>
                  <p className="text-3xl font-bold">{{parseInt(localStorage.getItem("faibric_sessions") || "0")}}</p>
                </div>
              </div>
              <div className="mt-6 bg-white p-6 rounded-xl shadow">
                <h3 className="font-semibold mb-2">Quick Actions</h3>
                <button
                  onClick={{() => setAdminView("builder")}}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Open Builder
                </button>
              </div>
            </div>
          )}}
          {{adminView === "settings" && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Settings</h2>
              <div className="bg-white p-6 rounded-xl shadow">
                <h3 className="font-semibold mb-2">Change Password</h3>
                <input type="password" placeholder="New password"
                  onBlur={{(e) => {{if(e.target.value){{localStorage.setItem("faibric_admin_pass",e.target.value); alert("Saved!")}}}}}}
                  className="w-full p-2 border rounded" />
              </div>
            </div>
          )}}
        </main>
      )}}
    </div>
  );
}}

// Main App with admin routing
function App() {{
  // Track page view
  React.useEffect(() => {{
    const v = parseInt(localStorage.getItem("faibric_views") || "0") + 1;
    localStorage.setItem("faibric_views", v.toString());
    if (!sessionStorage.getItem("faibric_session")) {{
      sessionStorage.setItem("faibric_session", "1");
      localStorage.setItem("faibric_sessions", (parseInt(localStorage.getItem("faibric_sessions") || "0") + 1).toString());
    }}
  }}, []);

  // Check if admin route
  if (window.location.pathname.includes("/faibric")) {{
    return <FaibricAdmin />;
  }}

  return <_OriginalApp />;
}}

export default App;
'''

        code = code + admin_wrapper
        print("[ADMIN] Injected admin panel wrapper with Builder")
        return code
    
    def _get_existing_service_branch(self, project):
        """Get the GitHub branch of an existing Render service for this project.

        Returns the branch name if the service exists, None otherwise.
        This ensures modifications push to the SAME branch the Render service
        is watching, not a new random branch.
        """
        if not self.render_api_key:
            return None

        headers = {
            'Authorization': f'Bearer {self.render_api_key}',
            'Content-Type': 'application/json'
        }

        import re
        slug = project.name[:20].lower().replace(' ', '-')
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        service_name = f"app-{project.id}-{slug}"

        resp = requests.get(
            f"{self.render_api}/services?name={service_name}&limit=1",
            headers=headers
        )

        if resp.status_code == 200:
            services = resp.json()
            for item in services:
                svc = item.get('service', {})
                if svc.get('name') == service_name:
                    branch = svc.get('branch')
                    if branch:
                        print(f"[RENDER] Found existing service branch: {branch}")
                        return branch

        return None

    def _create_render_site(self, branch_name, project):
        """Create Render static site for the app"""
        if not self.render_api_key:
            raise Exception("RENDER_API_KEY not configured")
        
        headers = {
            'Authorization': f'Bearer {self.render_api_key}',
            'Content-Type': 'application/json'
        }
        
        # Generate service name - sanitize to only allow alphanumeric and hyphens
        import re
        slug = project.name[:20].lower().replace(' ', '-')
        slug = re.sub(r'[^a-z0-9-]', '', slug)  # Remove all non-alphanumeric except hyphens
        slug = re.sub(r'-+', '-', slug)  # Collapse multiple hyphens
        slug = slug.strip('-')  # Remove leading/trailing hyphens
        service_name = f"app-{project.id}-{slug}"
        
        # Check if service already exists
        existing_url = self._get_existing_service(service_name, headers)
        if existing_url:
            # Trigger redeploy
            self._trigger_redeploy(service_name, headers)
            return existing_url
        
        # Create new static site
        owner, repo = self.github_repo.split('/')
        
        payload = {
            "type": "static_site",
            "name": service_name,
            "ownerId": self.render_owner_id,
            "repo": f"https://github.com/{self.github_repo}",
            "branch": branch_name,
            "autoDeploy": "yes",
            "serviceDetails": {
                "buildCommand": "npm install && npm run build",
                "publishPath": "dist",
                "pullRequestPreviewsEnabled": "no",
                # SPA routing: rewrite all routes to index.html
                # This enables /faibric admin panel and other client-side routes
                "routes": [
                    {
                        "type": "rewrite",
                        "source": "/*",
                        "destination": "/index.html"
                    }
                ]
            }
        }
        
        resp = requests.post(
            f"{self.render_api}/services",
            headers=headers,
            json=payload
        )
        
        if resp.status_code not in [200, 201]:
            raise Exception(f"Failed to create Render site: {resp.text}")
        
        data = resp.json()
        service_id = data.get('id')
        
        # Get the URL
        url = data.get('serviceDetails', {}).get('url', f"https://{service_name}.onrender.com")
        
        print(f"[OK] Created Render site: {url}")
        
        # NOTE: Verification is now done in BuildService._wait_and_verify_deployment()
        # This allows faster response and more accurate status tracking
        
        return url
    
    def _verify_deployment(self, url, service_id, headers, max_wait=180):
        """
        Wait for deployment to complete and verify the site works.
        
        FIX #5: TRUE VERIFICATION
        Checks that:
        1. Deploy status is 'live'
        2. HTML page returns 200
        3. JS bundle is accessible (not 404)
        4. JS bundle size > 10KB (not a stub/error page)
        """
        import time
        import re
        
        print(f"[wait] Waiting for build to complete...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            # Check deploy status via Render API
            resp = requests.get(
                f"{self.render_api}/services/{service_id}/deploys?limit=1",
                headers=headers
            )
            
            if resp.status_code == 200:
                deploys = resp.json()
                if deploys:
                    status = deploys[0].get('status', '')
                    if status == 'live':
                        print(f"[OK] Deploy is live, verifying JS bundle...")
                        
                        # TRUE VERIFICATION: Check JS bundle exists AND has content
                        try:
                            html_resp = requests.get(url, timeout=15)
                            if html_resp.status_code == 200:
                                # Extract JS path
                                js_match = re.search(r'/assets/index-[^"\']+\.js', html_resp.text)
                                if js_match:
                                    js_url = url.rstrip('/') + js_match.group()
                                    # Use GET to check size, not HEAD
                                    js_resp = requests.get(js_url, timeout=15)
                                    if js_resp.status_code == 200:
                                        js_size = len(js_resp.content)
                                        # FIX #5: Verify bundle is > 10KB (real app, not stub)
                                        if js_size > 10240:
                                            print(f"[OK] JS bundle verified! ({js_size} bytes)")
                                            return True
                                        else:
                                            print(f"[WARN] JS bundle too small ({js_size} bytes), waiting...")
                                    else:
                                        print(f"[WARN] JS bundle returned {js_resp.status_code}, waiting...")
                                else:
                                    print(f"[WARN] No JS bundle found in HTML, waiting...")
                            else:
                                print(f"[WARN] HTML returned {html_resp.status_code}, waiting...")
                        except Exception as e:
                            print(f"[WARN] Verification failed: {e}, waiting...")
                        
                    elif status == 'build_failed':
                        print(f"[ERROR] Build failed!")
                        break
                    elif status in ['canceled', 'deactivated']:
                        print(f"[ERROR] Build {status}!")
                        break
                    else:
                        print(f"[wait] Build status: {status}...")
            
            time.sleep(8)
        
        print(f"[WARN] Could not verify deployment within {max_wait}s")
        return False
    
    def _get_existing_service(self, service_name, headers):
        """Check if service already exists and return its URL"""
        resp = requests.get(
            f"{self.render_api}/services?name={service_name}&limit=1",
            headers=headers
        )
        
        if resp.status_code == 200:
            services = resp.json()
            for item in services:
                svc = item.get('service', {})
                if svc.get('name') == service_name:
                    return svc.get('serviceDetails', {}).get('url')
        
        return None
    
    def _trigger_redeploy(self, service_name, headers):
        """Trigger redeploy of existing service"""
        # Find service ID
        resp = requests.get(
            f"{self.render_api}/services?name={service_name}&limit=1",
            headers=headers
        )
        
        if resp.status_code == 200:
            services = resp.json()
            for item in services:
                svc = item.get('service', {})
                if svc.get('name') == service_name:
                    service_id = svc.get('id')
                    # Trigger deploy
                    requests.post(
                        f"{self.render_api}/services/{service_id}/deploys",
                        headers=headers,
                        json={}
                    )
                    print(f"[OK] Triggered redeploy for {service_name}")
                    return
    
    def _default_app(self, project):
        return {
            'App.jsx': self._default_app_jsx(),
            'components': {
                'Welcome': self._default_welcome(project)
            }
        }

    def _default_app_jsx(self):
        return """import React from 'react';
import Welcome from './components/Welcome';

function App() {
  return <Welcome />;
}

export default App;
"""
    
    def _default_welcome(self, project):
        desc = project.description[:100] if project.description else 'Built with Faibric AI'
        return f"""import React from 'react';

function Welcome() {{
  return (
    <div style={{{{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: 'white',
      fontFamily: 'system-ui',
      textAlign: 'center',
      padding: '20px'
    }}}}>
      <div>
        <h1 style={{{{ fontSize: '48px', marginBottom: '20px' }}}}>
          [launch] {project.name}
        </h1>
        <p style={{{{ fontSize: '20px', opacity: 0.9 }}}}>
          {desc}
        </p>
      </div>
    </div>
  );
}}

export default Welcome;
"""


# Singleton instance
_render_deployer = None

def get_render_deployer() -> RenderDeployer:
    """Get or create RenderDeployer instance."""
    global _render_deployer
    if _render_deployer is None:
        _render_deployer = RenderDeployer()
    return _render_deployer

# Deploy trigger: 1767337890
