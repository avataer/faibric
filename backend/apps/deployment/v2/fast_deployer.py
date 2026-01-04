"""
V2 Fast Deployer - Optimized for speed

Instead of building from scratch every time, we:
1. Use a pre-built base image
2. Only copy the changed files
3. Use npm cache for faster builds
"""
import docker
import tarfile
import json
import hashlib
from io import BytesIO
from django.conf import settings

from ..url_generator import url_generator


class FastReactDeployer:
    """
    Optimized React deployer with caching and faster builds
    """
    
    def __init__(self):
        import os
        os.environ.pop('DOCKER_HOST', None)
        self.client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
        self.base_image = self._ensure_base_image()
    
    def _ensure_base_image(self):
        """Ensure we have base images with pre-installed dependencies"""
        deps_tag = "faibric-deps:latest"
        
        try:
            self.client.images.get(deps_tag)
            return deps_tag
        except docker.errors.ImageNotFound:
            # Build deps image with all npm packages pre-installed
            print(f"Building dependency cache image {deps_tag}...")
            
            # This image has all dependencies pre-installed
            package_json = {
                "name": "faibric-deps",
                "private": True,
                "version": "1.0.0",
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build"},
                "dependencies": {
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0",
                    "react-router-dom": "^6.20.0",
                    "recharts": "^2.10.0",
                    "lucide-react": "^0.294.0",
                    "clsx": "^2.0.0",
                    "date-fns": "^2.30.0",
                    "@supabase/supabase-js": "^2.39.0"
                },
                "devDependencies": {
                    "@types/react": "^18.2.0",
                    "@types/react-dom": "^18.2.0",
                    "@vitejs/plugin-react": "^4.2.0",
                    "vite": "^5.0.0",
                    "tailwindcss": "^3.3.0",
                    "postcss": "^8.4.0",
                    "autoprefixer": "^10.4.0"
                }
            }
            
            dockerfile = """FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps
"""
            
            context = BytesIO()
            with tarfile.open(fileobj=context, mode='w') as tar:
                df_data = dockerfile.encode('utf-8')
                df_info = tarfile.TarInfo(name='Dockerfile')
                df_info.size = len(df_data)
                tar.addfile(df_info, BytesIO(df_data))
                
                pkg_data = json.dumps(package_json, indent=2).encode('utf-8')
                pkg_info = tarfile.TarInfo(name='package.json')
                pkg_info.size = len(pkg_data)
                tar.addfile(pkg_info, BytesIO(pkg_data))
            context.seek(0)
            
            self.client.images.build(
                fileobj=context,
                custom_context=True,
                tag=deps_tag,
                rm=True
            )
            print(f"[OK] Dependency cache image built")
            return deps_tag
    
    def deploy_react_app(self, project):
        """Deploy React app with optimized build"""
        # Use centralized URL generator - SINGLE SOURCE OF TRUTH
        subdomain = url_generator.generate_slug(project.id)
        container_name = subdomain
        
        try:
            # Stop existing container if any
            try:
                old_container = self.client.containers.get(container_name)
                old_container.remove(force=True)
            except docker.errors.NotFound:
                pass
            
            # Extract frontend code
            frontend_code = self._extract_frontend_code(project)
            
            # Build Docker context
            build_context = self._create_optimized_context(frontend_code, project)
            
            # Build image
            image_tag = f"faibric-app-{project.id}:{self._get_code_hash(frontend_code)[:8]}"
            
            print(f"Building optimized React app {image_tag}...")
            image, logs = self.client.images.build(
                fileobj=build_context,
                custom_context=True,
                tag=image_tag,
                rm=True,
                cache_from=[f"faibric-app-{project.id}:latest"]  # Use cache
            )
            
            # Tag as latest for cache
            image.tag(f"faibric-app-{project.id}", "latest")
            
            # Run container
            container = self.client.containers.run(
                image=image_tag,
                name=container_name,
                detach=True,
                network='faibric_deployed_apps',
                environment={
                    'PROJECT_ID': str(project.id),
                    'VITE_PROJECT_NAME': project.name,
                },
                labels={
                    'faibric.project_id': str(project.id),
                    'faibric.user_id': str(project.user.id),
                    'traefik.enable': 'true',
                    f'traefik.http.routers.{container_name}.rule': f'Host(`{subdomain}.localhost`)',
                    f'traefik.http.services.{container_name}.loadbalancer.server.port': '80',
                    'traefik.docker.network': 'faibric_deployed_apps',
                },
                mem_limit='256m',
                cpu_quota=50000,
                restart_policy={"Name": "unless-stopped"},
            )
            
            print(f"[OK] App deployed: {container.id[:12]}")
            return container.id
            
        except Exception as e:
            print(f"[ERROR] Deployment error: {str(e)}")
            raise Exception(f"Failed to deploy: {str(e)}")
    
    def _extract_frontend_code(self, project):
        """Extract and parse frontend code from project"""
        if not project.frontend_code:
            return self._default_app(project)
        
        try:
            import ast
            if isinstance(project.frontend_code, str):
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
          {project.description[:100] if project.description else 'Built with Faibric AI'}
        </p>
      </div>
    </div>
  );
}}

export default Welcome;
"""
    
    def _create_optimized_context(self, frontend_code, project):
        """Create build context with optimizations"""
        
        # Optimized Dockerfile - uses pre-built base image for faster builds
        dockerfile = """# Stage 1: Build with cached dependencies
FROM faibric-deps:latest AS builder
WORKDIR /app

# Just copy source and build (dependencies already in base image)
COPY . .
RUN npm run build 2>/dev/null || (npm install --legacy-peer-deps && npm run build)

# Stage 2: Lightweight production image
FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve@14
COPY --from=builder /app/dist ./dist
EXPOSE 80
CMD ["serve", "-s", "dist", "-l", "80"]
"""
        
        # Enhanced package.json with powerful libraries
        package_json = {
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
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.20.0",
                "recharts": "^2.10.0",
                "lucide-react": "^0.294.0",
                "clsx": "^2.0.0",
                "date-fns": "^2.30.0",
                "@supabase/supabase-js": "^2.39.0"
            },
            "devDependencies": {
                "@types/react": "^18.2.0",
                "@types/react-dom": "^18.2.0",
                "@vitejs/plugin-react": "^4.2.0",
                "vite": "^5.0.0",
                "tailwindcss": "^3.3.0",
                "postcss": "^8.4.0",
                "autoprefixer": "^10.4.0"
            }
        }
        
        # Vite config with Tailwind
        vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  css: {
    postcss: './postcss.config.js',
  },
})
"""
        
        # Tailwind config
        tailwind_config = """/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'SF Pro Text', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
"""
        
        # PostCSS config
        postcss_config = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""
        
        # Global CSS with Tailwind directives
        global_css = """@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', system-ui, sans-serif;
}
"""
        
        # Get Supabase credentials from settings
        from django.conf import settings
        supabase_url = getattr(settings, 'SUPABASE_URL', '') or ''
        supabase_anon_key = getattr(settings, 'SUPABASE_ANON_KEY', '') or ''
        
        # index.html - inject FAIBRIC_APP_ID, auth helpers, and Supabase config
        index_html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project.name}</title>
    <style>* {{ margin: 0; padding: 0; box-sizing: border-box; }}</style>
    <script>
      window.FAIBRIC_APP_ID = {project.id};
      
      // Supabase configuration (if available)
      window.SUPABASE_URL = '{supabase_url}';
      window.SUPABASE_ANON_KEY = '{supabase_anon_key}';
      
      // Simple auth helpers (localStorage-based fallback, upgrades to Supabase if configured)
      window.FaibricAuth = {{
        _user: null,
        getUser: function() {{
          if (this._user) return this._user;
          return JSON.parse(localStorage.getItem('faibric_user') || 'null');
        }},
        login: async function(email, password) {{
          // If Supabase is configured, use it
          if (window.SUPABASE_URL && window.supabase) {{
            const {{ data, error }} = await window.supabase.auth.signInWithPassword({{ email, password }});
            if (error) throw error;
            this._user = data.user;
            return data.user;
          }}
          // Fallback to localStorage simulation
          const user = {{ id: Date.now().toString(), email, name: email.split('@')[0] }};
          localStorage.setItem('faibric_user', JSON.stringify(user));
          this._user = user;
          return user;
        }},
        signUp: async function(email, password) {{
          if (window.SUPABASE_URL && window.supabase) {{
            const {{ data, error }} = await window.supabase.auth.signUp({{ email, password }});
            if (error) throw error;
            return data.user;
          }}
          return this.login(email, password);
        }},
        logout: async function() {{
          if (window.SUPABASE_URL && window.supabase) {{
            await window.supabase.auth.signOut();
          }}
          localStorage.removeItem('faibric_user');
          this._user = null;
        }},
        isLoggedIn: function() {{
          return !!this.getUser();
        }},
        onAuthStateChange: function(callback) {{
          if (window.supabase) {{
            return window.supabase.auth.onAuthStateChange(callback);
          }}
          // Fallback: just call with current state
          callback('INITIAL', this.getUser());
          return {{ data: {{ subscription: {{ unsubscribe: () => {{}} }} }} }};
        }},
      }};
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""
        
        # main.tsx with CSS import and Supabase initialization
        main_tsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import { createClient } from '@supabase/supabase-js'
import App from './App'
import './index.css'

// Initialize Supabase if configured
declare global {
  interface Window {
    SUPABASE_URL: string;
    SUPABASE_ANON_KEY: string;
    supabase: any;
    FAIBRIC_APP_ID: number;
    FaibricAuth: any;
  }
}

if (window.SUPABASE_URL && window.SUPABASE_ANON_KEY) {
  window.supabase = createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY);
  console.log('Supabase initialized');
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""
        
        # Create tar archive with all config files
        context = BytesIO()
        with tarfile.open(fileobj=context, mode='w') as tar:
            self._add_file(tar, 'Dockerfile', dockerfile)
            self._add_file(tar, 'package.json', json.dumps(package_json, indent=2))
            self._add_file(tar, 'vite.config.ts', vite_config)
            self._add_file(tar, 'tailwind.config.js', tailwind_config)
            self._add_file(tar, 'postcss.config.js', postcss_config)
            self._add_file(tar, 'index.html', index_html)
            self._add_file(tar, 'src/main.tsx', main_tsx)
            self._add_file(tar, 'src/index.css', global_css)
            self._add_file(tar, 'src/App.tsx', frontend_code['App.tsx'])
            
            for comp_name, comp_code in frontend_code['components'].items():
                self._add_file(tar, f'src/components/{comp_name}.tsx', comp_code)
        
        context.seek(0)
        return context
    
    def _add_file(self, tar, filename, content):
        """Add a file to tar archive"""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        info = tarfile.TarInfo(name=filename)
        info.size = len(content)
        tar.addfile(info, BytesIO(content))
    
    def _sanitize(self, text):
        """Sanitize text for Docker names"""
        return text.lower().replace(' ', '-').replace('_', '-')[:20]
    
    def _get_code_hash(self, frontend_code):
        """Get hash of frontend code for caching"""
        content = json.dumps(frontend_code, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def stop_container(self, container_id):
        """Stop and remove a container"""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove()
            return True
        except docker.errors.NotFound:
            return False
        except Exception as e:
            print(f"Error stopping container: {e}")
            return False

