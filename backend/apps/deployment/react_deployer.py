"""
React + Vite deployment system for AI-generated apps
Deploys actual React code with hot-reload support
"""
import docker
import tarfile
import json
from io import BytesIO
from django.conf import settings


class ReactDeployer:
    """Deploy AI-generated React apps with Vite"""
    
    def __init__(self):
        import os
        os.environ.pop('DOCKER_HOST', None)
        self.client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
    
    def deploy_react_app(self, project):
        """Deploy a React app from AI-generated code"""
        username = self._sanitize(project.user.username)
        project_name = self._sanitize(project.name)
        container_name = f"app-{username}-{project_name}-{project.id}"
        subdomain = f"{username}-{project_name}"
        
        try:
            # Extract AI-generated frontend code
            frontend_code = self._extract_frontend_code(project)
            
            # Create Vite project structure
            build_context = self._create_vite_context(frontend_code, project)
            
            # Build Docker image
            image_tag = f"faibric-react-{project.id}:latest"
            print(f"Building React app image {image_tag}...")
            
            image, logs = self.client.images.build(
                fileobj=build_context,
                custom_context=True,
                tag=image_tag,
                rm=True
            )
            
            for log in logs:
                if 'stream' in log:
                    print(log['stream'].strip())
            
            # Create and start container
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
                mem_limit='512m',
                cpu_quota=100000,
                restart_policy={"Name": "unless-stopped"},
            )
            
            print(f"React app deployed: {container.id}")
            return container.id
            
        except Exception as e:
            print(f"React deployment error: {str(e)}")
            raise Exception(f"Failed to deploy React app: {str(e)}")
    
    def update_app_component(self, project, component_name, new_code):
        """Hot-update a component in a running app"""
        try:
            username = self._sanitize(project.user.username)
            project_name = self._sanitize(project.name)
            container_name = f"app-{username}-{project_name}-{project.id}"
            
            container = self.client.containers.get(container_name)
            
            # Write new component code to container
            file_path = f"/app/src/components/{component_name}.tsx"
            
            # Create tar with updated file
            tar_stream = BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                file_data = new_code.encode('utf-8')
                tarinfo = tarfile.TarInfo(name=f'src/components/{component_name}.tsx')
                tarinfo.size = len(file_data)
                tar.addfile(tarinfo, BytesIO(file_data))
            
            tar_stream.seek(0)
            container.put_archive('/app', tar_stream)
            
            print(f"Hot-updated component: {component_name}")
            return True
            
        except Exception as e:
            print(f"Hot-update error: {str(e)}")
            return False
    
    def _extract_frontend_code(self, project):
        """Extract and parse AI-generated frontend code"""
        if not project.frontend_code:
            return self._generate_default_app(project)
        
        # Parse the frontend_code string (it's stored as a string representation of a dict)
        try:
            if isinstance(project.frontend_code, str):
                # Try to evaluate it safely
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
            return self._generate_default_app(project)
    
    def _generate_default_app(self, project):
        """Generate a minimal working React app"""
        return {
            'App.tsx': self._default_app_tsx(),
            'components': {
                'Welcome': self._default_welcome_component(project)
            }
        }
    
    def _default_app_tsx(self):
        """Default App.tsx"""
        return """import React from 'react';
import Welcome from './components/Welcome';

function App() {
  return (
    <div className="app">
      <Welcome />
    </div>
  );
}

export default App;
"""
    
    def _default_welcome_component(self, project):
        """Default welcome component"""
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
      fontFamily: 'system-ui, sans-serif',
      padding: '20px',
      textAlign: 'center'
    }}}}>
      <div>
        <h1 style={{{{ fontSize: '48px', marginBottom: '20px' }}}}>
          🚀 {project.name}
        </h1>
        <p style={{{{ fontSize: '24px', opacity: 0.9 }}}}>
          {project.description}
        </p>
        <p style={{{{ fontSize: '16px', marginTop: '20px', opacity: 0.7 }}}}>
          ✨ Powered by Faibric AI
        </p>
      </div>
    </div>
  );
}}

export default Welcome;
"""
    
    def _create_vite_context(self, frontend_code, project):
        """Create a complete Vite project build context"""
        
        # Dockerfile for React + Vite (PRODUCTION BUILD)
        dockerfile = """FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy project files
COPY . .

# Build for production
RUN npm run build

# Production stage with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
"""
        
        # package.json
        package_json = {
            "name": f"faibric-app-{project.id}",
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
                "react-router-dom": "^6.20.0"
            },
            "devDependencies": {
                "@types/react": "^18.2.43",
                "@types/react-dom": "^18.2.17",
                "@vitejs/plugin-react": "^4.2.1",
                "vite": "^5.0.8"
            }
        }
        
        # vite.config.ts
        vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    hmr: {
      clientPort: 5173
    }
  }
})
"""
        
        # index.html
        index_html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project.name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""
        
        # main.tsx
        main_tsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""
        
        # Create tar archive
        context = BytesIO()
        with tarfile.open(fileobj=context, mode='w') as tar:
            # Add Dockerfile
            self._add_file_to_tar(tar, 'Dockerfile', dockerfile)
            
            # Add package.json
            self._add_file_to_tar(tar, 'package.json', json.dumps(package_json, indent=2))
            
            # Add vite.config.ts
            self._add_file_to_tar(tar, 'vite.config.ts', vite_config)
            
            # Add index.html
            self._add_file_to_tar(tar, 'index.html', index_html)
            
            # Add src/main.tsx
            self._add_file_to_tar(tar, 'src/main.tsx', main_tsx)
            
            # Add src/App.tsx
            self._add_file_to_tar(tar, 'src/App.tsx', frontend_code['App.tsx'])
            
            # Add components
            for comp_name, comp_code in frontend_code['components'].items():
                self._add_file_to_tar(tar, f'src/components/{comp_name}.tsx', comp_code)
        
        context.seek(0)
        return context
    
    def _add_file_to_tar(self, tar, filename, content):
        """Add a file to tar archive"""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(content)
        tar.addfile(tarinfo, BytesIO(content))
    
    def _sanitize(self, text):
        """Sanitize text for Docker names"""
        return text.lower().replace(' ', '-').replace('_', '-')
    
    def stop_container(self, container_id):
        """Stop and remove a container"""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove()
            return True
        except docker.errors.NotFound:
            return False
        except Exception as e:
            print(f"Error stopping container: {e}")
            return False

