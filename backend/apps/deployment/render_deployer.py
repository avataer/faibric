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
            # Generate unique branch name for this project
            branch_name = self._get_branch_name(project)
            
            # Extract and prepare the code
            frontend_code = self._extract_frontend_code(project)
            
            # Push code to GitHub branch
            self._push_to_github(branch_name, frontend_code, project)
            
            # Create or update Render static site
            site_url = self._create_render_site(branch_name, project)
            
            return {
                'success': True,
                'url': site_url,
                'branch': branch_name
            }
            
        except Exception as e:
            print(f"❌ Render deployment error: {str(e)}")
            raise Exception(f"Failed to deploy to Render: {str(e)}")
    
    def _get_branch_name(self, project):
        """Generate unique branch name for project"""
        import re
        username = project.user.username.lower()
        # Remove all non-alphanumeric chars except hyphen
        username = re.sub(r'[^a-z0-9-]', '', username)[:15]
        
        project_slug = project.name.lower()
        # Remove all non-alphanumeric chars except hyphen
        project_slug = re.sub(r'[^a-z0-9-]', '', project_slug.replace(' ', '-'))[:20]
        
        return f"app-{username}-{project_slug}-{project.id}"
    
    def _extract_frontend_code(self, project):
        """Extract frontend code from project"""
        if not project.frontend_code:
            return self._default_app(project)

        try:
            if isinstance(project.frontend_code, str):
                # Try JSON first (new format)
                try:
                    code_dict = json.loads(project.frontend_code)
                except json.JSONDecodeError:
                    # Fall back to ast.literal_eval (old format)
                    import ast
                    code_dict = ast.literal_eval(project.frontend_code)
            else:
                code_dict = project.frontend_code

            return {
                'App.tsx': code_dict.get('App.tsx', self._default_app_tsx()),
                'components': code_dict.get('components', {})
            }
        except Exception as e:
            print(f"Failed to parse frontend code: {e}")
            return self._default_app(project)
    
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
        
        print(f"✅ Pushed to GitHub: {self.github_repo}#{branch_name}")
    
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
        
        # package.json
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
                "@types/react": "^18.2.0",
                "@types/react-dom": "^18.2.0",
                "@vitejs/plugin-react": "^4.2.0",
                "vite": "^5.0.0"
            }
        }, indent=2)
        
        # vite.config.ts
        files['vite.config.ts'] = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
"""
        
        # index.html
        files['index.html'] = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project.name}</title>
    <style>* {{ margin: 0; padding: 0; box-sizing: border-box; }}</style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""
        
        # src/main.tsx
        files['src/main.tsx'] = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""
        
        # src/App.tsx
        files['src/App.tsx'] = frontend_code['App.tsx']
        
        # Components
        for comp_name, comp_code in frontend_code.get('components', {}).items():
            files[f'src/components/{comp_name}.tsx'] = comp_code
        
        return files
    
    def _create_render_site(self, branch_name, project):
        """Create Render static site for the app"""
        if not self.render_api_key:
            raise Exception("RENDER_API_KEY not configured")
        
        headers = {
            'Authorization': f'Bearer {self.render_api_key}',
            'Content-Type': 'application/json'
        }
        
        # Generate service name
        service_name = f"app-{project.id}-{project.name[:20].lower().replace(' ', '-')}"
        
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
                "pullRequestPreviewsEnabled": "no"
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
        
        print(f"✅ Created Render site: {url}")
        return url
    
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
                    print(f"✅ Triggered redeploy for {service_name}")
                    return
    
    def _default_app(self, project):
        return {
            'App.tsx': self._default_app_tsx(),
            'components': {
                'Welcome': self._default_welcome(project)
            }
        }
    
    def _default_app_tsx(self):
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
          🚀 {project.name}
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
