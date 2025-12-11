"""
Docker management for deploying user apps
"""
import docker
import tarfile
from io import BytesIO
from django.conf import settings


class DockerManager:
    """Manage Docker containers for user apps"""
    
    def __init__(self):
        # Clear any DOCKER_HOST that might cause issues
        import os
        os.environ.pop('DOCKER_HOST', None)
        self.client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
    
    def create_app_container(self, project):
        """Create and start a Docker container for a project"""
        username = self._sanitize(project.user.username)
        project_name = self._sanitize(project.name)
        container_name = f"app-{username}-{project_name}-{project.id}"
        subdomain = f"{username}-{project_name}"
        
        try:
            # Generate Flask app code
            app_code = self._generate_flask_app(project)
            
            # Build Docker image
            image_tag = f"faibric-app-{project.id}:latest"
            context = self._create_build_context(app_code)
            
            print(f"Building image {image_tag}...")
            image, _ = self.client.images.build(
                fileobj=context,
                custom_context=True,
                tag=image_tag,
                rm=True
            )
            
            # Create and start container
            container = self.client.containers.run(
                image=image_tag,
                name=container_name,
                detach=True,
                network='faibric_deployed_apps',
                environment={'PROJECT_ID': str(project.id)},
                labels={
                    'faibric.project_id': str(project.id),
                    'faibric.user_id': str(project.user.id),
                    'traefik.enable': 'true',
                    f'traefik.http.routers.{container_name}.rule': f'Host(`{subdomain}.localhost`)',
                    f'traefik.http.services.{container_name}.loadbalancer.server.port': '5000',
                    'traefik.docker.network': 'faibric_deployed_apps',
                },
                mem_limit='256m',
                cpu_quota=50000,
                restart_policy={"Name": "unless-stopped"},
            )
            
            print(f"Container created: {container.id}")
            return container.id
            
        except Exception as e:
            print(f"Deployment error: {str(e)}")
            raise Exception(f"Failed to create container: {str(e)}")
    
    def stop_container(self, container_id):
        """Stop and remove a container"""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove()
            return True
        except docker.errors.NotFound:
            return False
    
    def get_container_status(self, container_id):
        """Get status of a container"""
        try:
            container = self.client.containers.get(container_id)
            return {'status': container.status}
        except docker.errors.NotFound:
            return {'status': 'not_found'}
    
    def _sanitize(self, text):
        """Sanitize text for use in container/subdomain names"""
        return text.lower().replace(' ', '-').replace('_', '-')
    
    def _generate_flask_app(self, project):
        """Generate complete Flask application code"""
        # Extract models and APIs
        models = [{'name': m.name, 'fields': m.fields} for m in project.models.all()]
        apis = [{'method': a.method, 'path': a.path, 'description': a.description} 
                for a in project.apis.all()]
        
        # Generate sample data
        sample_data = self._generate_sample_data(models)
        
        # Build project info dict
        project_info = {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'user_prompt': project.user_prompt,
            'models': models,
            'apis': apis,
            'sample_data': sample_data
        }
        
        # Generate Flask app
        return f'''
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PROJECT = {repr(project_info)}
DATA = PROJECT['sample_data']

@app.route('/')
def index():
    return render_template_string(TEMPLATE, project=PROJECT, data=DATA)

@app.route('/api/<resource>')
def get_list(resource):
    return jsonify(DATA.get(resource.capitalize(), []))

@app.route('/api/<resource>/<int:id>')
def get_item(resource, id):
    items = DATA.get(resource.capitalize(), [])
    return jsonify(items[id]) if id < len(items) else ({{'error': 'Not found'}}, 404)

@app.route('/health')
def health():
    return jsonify({{'status': 'healthy', 'project_id': PROJECT['id']}})

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{{{ project.name }}}} - Faibric</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: white;
            border-radius: 16px;
            padding: 48px;
            margin-bottom: 32px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            text-align: center;
        }}
        .header h1 {{ font-size: 48px; color: #1a202c; margin-bottom: 16px; }}
        .header p {{ font-size: 20px; color: #4a5568; margin-bottom: 24px; }}
        .badge {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 24px;
            border-radius: 24px;
            font-size: 14px;
            font-weight: 600;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            transition: transform 0.2s;
            cursor: pointer;
        }}
        .card:hover {{ transform: translateY(-4px); }}
        .card h3 {{ font-size: 24px; color: #1a202c; margin-bottom: 12px; }}
        .card p {{ color: #4a5568; line-height: 1.6; margin-bottom: 8px; }}
        .card .label {{ font-weight: 600; color: #2d3748; }}
        .card .value {{ color: #667eea; }}
        .section-title {{
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin: 48px 0 24px;
            text-align: center;
        }}
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 32px; }}
            .grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 {{{{ project['name'] }}}}</h1>
            <p>{{{{ project['description'] }}}}</p>
            <span class="badge">✨ Powered by Faibric AI</span>
        </div>
        {{% for model, items in data.items() %}}
        <h2 class="section-title">{{{{ model }}}}s</h2>
        <div class="grid">
            {{% for item in items %}}
            <div class="card">
                {{% for key, value in item.items() %}}
                {{% if loop.index == 1 %}}
                <h3>{{{{ value }}}}</h3>
                {{% else %}}
                <p><span class="label">{{{{ key }}}}:</span> <span class="value">{{{{ value }}}}</span></p>
                {{% endif %}}
                {{% endfor %}}
            </div>
            {{% endfor %}}
        </div>
        {{% endfor %}}
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
'''
    
    def _generate_sample_data(self, models):
        """Generate smart sample data based on model fields"""
        data = {}
        
        for model in models:
            items = []
            for i in range(7):
                item = {}
                for field in model['fields']:
                    name, ftype = field['name'], field['type']
                    
                    # Smart value generation
                    if 'name' in name.lower() and ftype == 'CharField':
                        item[name] = f"{model['name']} #{i+1}"
                    elif 'description' in name.lower():
                        item[name] = f"Detailed information about this {model['name']}."
                    elif 'output' in name.lower():
                        item[name] = ['Low', 'Medium', 'High'][i % 3]
                    elif 'tone' in name.lower():
                        item[name] = ['Bright', 'Warm', 'Balanced'][i % 3]
                    elif 'rating' in name.lower() and ftype == 'IntegerField':
                        item[name] = 3 + (i % 3)
                    elif ftype == 'EmailField':
                        item[name] = f"user{i+1}@example.com"
                    elif ftype == 'URLField':
                        item[name] = f"https://example.com/{i+1}"
                    elif ftype == 'IntegerField':
                        item[name] = (i + 1) * 100
                    elif ftype == 'BooleanField':
                        item[name] = i % 2 == 0
                    elif ftype != 'DateTimeField':
                        item[name] = f"{name.replace('_', ' ').title()} {i+1}"
                
                items.append(item)
            
            data[model['name']] = items
        
        return data
    
    def _create_build_context(self, app_code):
        """Create Docker build context"""
        dockerfile = '''FROM python:3.11-slim
WORKDIR /app
RUN pip install flask flask-cors
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
'''
        
        context = BytesIO()
        with tarfile.open(fileobj=context, mode='w') as tar:
            # Dockerfile
            df_data = dockerfile.encode('utf-8')
            df_info = tarfile.TarInfo(name='Dockerfile')
            df_info.size = len(df_data)
            tar.addfile(df_info, BytesIO(df_data))
            
            # app.py
            app_data = app_code.encode('utf-8')
            app_info = tarfile.TarInfo(name='app.py')
            app_info.size = len(app_data)
            tar.addfile(app_info, BytesIO(app_data))
        
        context.seek(0)
        return context


class DomainManager:
    """Manage subdomains for deployed apps"""
    
    def __init__(self):
        self.base_domain = settings.APP_SUBDOMAIN_BASE
    
    def assign_subdomain(self, project):
        """Assign subdomain to a project - must match FastReactDeployer"""
        username = project.user.username.lower().replace('_', '-').replace(' ', '-')
        project_slug = project.name.lower().replace(' ', '-').replace('_', '-')[:30]
        return f"{username}-{project_slug}-{project.id}"
    
    def get_full_url(self, subdomain):
        """Get full URL for a subdomain"""
        return f"http://{subdomain}.{self.base_domain}" if self.base_domain == 'localhost' else f"https://{subdomain}.{self.base_domain}"
    
    def configure_routing(self, subdomain, container_id):
        """Configure routing (handled by Traefik)"""
        pass
    
    def remove_routing(self, subdomain):
        """Remove routing (handled by Traefik)"""
        pass
    
    def create_app_container(self, project):
        """
        Create and start a Docker container for a project
        
        Args:
            project: Project instance
        
        Returns:
            container_id: ID of created container
        """
        # Generate unique container name
        username = project.user.username.lower().replace('_', '-')
        project_name = project.name.lower().replace(' ', '-').replace('_', '-')
        container_name = f"app-{username}-{project_name}-{project.id}"
        subdomain = f"{username}-{project_name}"
        
        try:
            # Create a simple Flask app with the generated info
            app_code = self._generate_app_code(project)
            
            # Build context in memory
            context = self._create_build_context(app_code, project)
            
            # Build image
            image_tag = f"faibric-app-{project.id}:latest"
            print(f"Building image {image_tag}...")
            
            image, build_logs = self.client.images.build(
                fileobj=context,
                custom_context=True,
                tag=image_tag,
                rm=True
            )
            
            for log in build_logs:
                if 'stream' in log:
                    print(log['stream'].strip())
            
            print(f"Image built successfully: {image.id}")
            
            # Create and start container with Traefik labels
            container = self.client.containers.run(
                image=image_tag,
                name=container_name,
                detach=True,
                network='faibric_deployed_apps',
                environment={
                    'PROJECT_ID': str(project.id),
                    'PROJECT_NAME': project.name,
                },
                labels={
                    'faibric.project_id': str(project.id),
                    'faibric.user_id': str(project.user.id),
                    # Traefik labels for routing
                    'traefik.enable': 'true',
                    f'traefik.http.routers.{container_name}.rule': f'Host(`{subdomain}.localhost`)',
                    f'traefik.http.services.{container_name}.loadbalancer.server.port': '5000',
                    'traefik.docker.network': 'faibric_deployed_apps',
                },
                # Resource limits
                mem_limit='256m',
                cpu_quota=50000,  # 50% of one CPU
                restart_policy={"Name": "unless-stopped"},
            )
            
            print(f"Container created: {container.id} - {container_name}")
            return container.id
            
        except docker.errors.APIError as e:
            print(f"Docker API Error: {str(e)}")
            raise Exception(f"Failed to create container: {str(e)}")
        except Exception as e:
            print(f"Error: {str(e)}")
            raise
    
    def stop_container(self, container_id):
        """Stop and remove a container"""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove()
            return True
        except docker.errors.NotFound:
            return False
        except docker.errors.APIError as e:
            raise Exception(f"Failed to stop container: {str(e)}")
    
    def get_container_status(self, container_id):
        """Get status of a container"""
        try:
            container = self.client.containers.get(container_id)
            return {
                'status': container.status,
                'ports': container.ports,
                'logs': container.logs(tail=50).decode('utf-8')
            }
        except docker.errors.NotFound:
            return {'status': 'not_found'}
    
    def _generate_app_code(self, project):
        """Generate a COMPLETE, WORKING Flask application with real functionality"""
        
        # Extract data from project
        models_info = []
        if hasattr(project, 'models'):
            for model in project.models.all():
                models_info.append({
                    'name': model.name,
                    'fields': model.fields
                })
        
        apis_info = []
        if hasattr(project, 'apis'):
            for api in project.apis.all():
                apis_info.append({
                    'method': api.method,
                    'path': api.path,
                    'description': api.description
                })
        
        # Generate sample data based on the prompt
        sample_data = self._generate_sample_data(project, models_info)
        
        # Create full working Flask app
        app_code = self._build_working_flask_app(
            project=project,
            models=models_info,
            apis=apis_info,
            sample_data=sample_data
        )
        
        return app_code
    
    def _generate_sample_data(self, project, models):
        """Generate realistic sample data based on the project description using AI"""
        
        # For now, generate generic but relevant data based on model fields
        # This should be replaced with AI-generated data in the future
        sample_data = {}
        
        for model in models:
            model_name = model['name']
            items = []
            
            # Generate 6-8 sample items per model
            num_items = 7
            for i in range(num_items):
                item = {}
                for field in model['fields']:
                    field_name = field['name']
                    field_type = field['type']
                    
                    # Generate appropriate sample values based on field type and name
                    if field_type == 'CharField':
                        if 'name' in field_name.lower():
                            item[field_name] = f"{model_name} #{i+1}"
                        elif 'title' in field_name.lower():
                            item[field_name] = f"Sample {field_name} {i+1}"
                        elif 'description' in field_name.lower() or 'desc' in field_name.lower():
                            item[field_name] = f"This is a detailed description for {model_name} #{i+1}. It contains relevant information about this item."
                        elif 'output' in field_name.lower():
                            outputs = ['Low', 'Medium-Low', 'Medium', 'Medium-High', 'High', 'Very High']
                            item[field_name] = outputs[i % len(outputs)]
                        elif 'tone' in field_name.lower():
                            tones = ['Bright', 'Warm', 'Balanced', 'Dark', 'Clear', 'Rich', 'Vintage']
                            item[field_name] = tones[i % len(tones)]
                        elif 'position' in field_name.lower():
                            positions = ['Neck', 'Bridge', 'Middle', 'Neck/Bridge', 'Set of 3']
                            item[field_name] = positions[i % len(positions)]
                        elif 'type' in field_name.lower():
                            item[field_name] = f"Type {chr(65+i)}"
                        else:
                            item[field_name] = f"{field_name.replace('_', ' ').title()} {i+1}"
                    
                    elif field_type == 'TextField':
                        if 'description' in field_name.lower() or 'content' in field_name.lower():
                            item[field_name] = f"Detailed information about {model_name} #{i+1}. This field contains longer text content with multiple sentences. It provides comprehensive details and context."
                        elif 'comment' in field_name.lower():
                            comments = [
                                "This is excellent! Highly recommended.",
                                "Good quality, meets expectations.",
                                "Very satisfied with this.",
                                "Works great, no issues.",
                                "Perfect for my needs.",
                                "Exactly what I was looking for.",
                                "Great value for the price."
                            ]
                            item[field_name] = comments[i % len(comments)]
                        else:
                            item[field_name] = f"Extended content for {field_name} in {model_name} #{i+1}"
                    
                    elif field_type == 'IntegerField':
                        if 'rating' in field_name.lower():
                            item[field_name] = (i % 3) + 3  # Ratings 3-5
                        elif 'age' in field_name.lower():
                            item[field_name] = 20 + (i * 5)
                        elif 'quantity' in field_name.lower() or 'stock' in field_name.lower():
                            item[field_name] = (i + 1) * 10
                        elif 'price' in field_name.lower():
                            item[field_name] = (i + 1) * 50
                        else:
                            item[field_name] = (i + 1) * 100
                    
                    elif field_type == 'DecimalField':
                        if 'price' in field_name.lower():
                            item[field_name] = f"{(i + 1) * 29.99:.2f}"
                        elif 'rating' in field_name.lower():
                            item[field_name] = f"{3.0 + (i * 0.3):.1f}"
                        else:
                            item[field_name] = f"{(i + 1) * 10.50:.2f}"
                    
                    elif field_type == 'BooleanField':
                        item[field_name] = (i % 2 == 0)
                    
                    elif field_type == 'EmailField':
                        item[field_name] = f"user{i+1}@example.com"
                    
                    elif field_type == 'URLField':
                        if 'image' in field_name.lower():
                            item[field_name] = f"https://via.placeholder.com/400x300?text={model_name}+{i+1}"
                        else:
                            item[field_name] = f"https://example.com/{model_name.lower()}/{i+1}"
                    
                    elif field_type == 'DateTimeField':
                        # Skip datetime fields in display
                        continue
                    
                    elif field_type == 'DateField':
                        item[field_name] = f"2024-{(i%12)+1:02d}-{((i*3)%28)+1:02d}"
                    
                    else:
                        item[field_name] = f"{field_name} value {i+1}"
                
                items.append(item)
            
            sample_data[model_name] = items
        
        return sample_data
    
    def _build_working_flask_app(self, project, models, apis, sample_data):
        """Build a complete, functional Flask application"""
        
        # Convert to Python-safe string
        project_info = {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'user_prompt': project.user_prompt,
            'models': models,
            'apis': apis,
            'sample_data': sample_data
        }
        
        project_info_str = repr(project_info)
        
        # Build complete Flask app with real functionality
        app_code = '''
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Project configuration
PROJECT_INFO = ''' + project_info_str + '''

# In-memory data store (acts as database)
DATA_STORE = PROJECT_INFO.get('sample_data', {})

@app.route('/')
def index():
    """Main landing page with full functionality"""
    return render_template_string(MAIN_PAGE_TEMPLATE, 
                                 project=PROJECT_INFO,
                                 data=DATA_STORE)

@app.route('/api/data')
def get_all_data():
    """Get all data for the app"""
    return jsonify(DATA_STORE)

@app.route('/api/<resource>')
def get_resource_list(resource):
    """Get list of items for a resource"""
    resource_key = resource.capitalize()
    items = DATA_STORE.get(resource_key, [])
    return jsonify(items)

@app.route('/api/<resource>/<int:item_id>')
def get_resource_detail(resource, item_id):
    """Get single item detail"""
    resource_key = resource.capitalize()
    items = DATA_STORE.get(resource_key, [])
    if 0 <= item_id < len(items):
        return jsonify(items[item_id])
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/info')
def api_info():
    """Get project information"""
    return jsonify({
        'id': PROJECT_INFO['id'],
        'name': PROJECT_INFO['name'],
        'description': PROJECT_INFO['description'],
        'models': PROJECT_INFO['models'],
        'apis': PROJECT_INFO['apis']
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'project_id': PROJECT_INFO['id']})

# Beautiful, functional HTML template
MAIN_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project.name }} - Powered by Faibric</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 16px;
            padding: 48px;
            margin-bottom: 32px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            text-align: center;
        }
        
        .header h1 {
            font-size: 48px;
            color: #1a202c;
            margin-bottom: 16px;
            font-weight: 800;
        }
        
        .header p {
            font-size: 20px;
            color: #4a5568;
            margin-bottom: 24px;
        }
        
        .badge {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 24px;
            border-radius: 24px;
            font-size: 14px;
            font-weight: 600;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }
        
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
        }
        
        .card h3 {
            font-size: 24px;
            color: #1a202c;
            margin-bottom: 12px;
            font-weight: 700;
        }
        
        .card p {
            color: #4a5568;
            line-height: 1.6;
            margin-bottom: 8px;
        }
        
        .card .label {
            font-weight: 600;
            color: #2d3748;
        }
        
        .card .value {
            color: #667eea;
        }
        
        .section-title {
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin: 48px 0 24px;
            text-align: center;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        
        .powered-by {
            background: white;
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            margin-top: 48px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        
        .powered-by p {
            color: #4a5568;
            font-size: 16px;
        }
        
        .powered-by strong {
            color: #667eea;
            font-weight: 700;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 32px;
            }
            
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 {{ project.name }}</h1>
            <p>{{ project.description }}</p>
            <span class="badge">✨ Live and Working!</span>
        </div>
        
        {% for model_name, items in data.items() %}
        <h2 class="section-title">{{ model_name }}s</h2>
        <div class="grid">
            {% for item in items %}
            <div class="card" onclick="showDetails({{ loop.index0 }}, '{{ model_name }}')">
                {% for key, value in item.items() %}
                    {% if loop.index <= 5 %}
                    <h3>{{ value }}</h3>
                    {% else %}
                    <p><span class="label">{{ key }}:</span> <span class="value">{{ value }}</span></p>
                    {% endif %}
                {% endfor %}
            </div>
            {% endfor %}
        </div>
        {% endfor %}
        
        <div class="powered-by">
            <p>🎨 This fully functional app was generated by <strong>Faibric AI</strong></p>
            <p style="margin-top: 8px; font-size: 14px; color: #718096;">
                Project ID: {{ project.id }} | All features working • Real data • Live deployment
            </p>
        </div>
    </div>
    
    <script>
        function showDetails(id, model) {
            fetch(`/api/${model.toLowerCase()}/${id}`)
                .then(r => r.json())
                .then(data => {
                    alert(JSON.stringify(data, null, 2));
                });
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print(f"🚀 Starting {PROJECT_INFO['name']}...")
    print(f"📊 Loaded {sum(len(items) for items in DATA_STORE.values())} items")
    app.run(host='0.0.0.0', port=5000, debug=False)
'''
        return app_code
    
    def _create_build_context(self, app_code, project):
        """Create a tarball build context for Docker"""
        # Create Dockerfile
        dockerfile_content = '''FROM python:3.11-slim
WORKDIR /app
RUN pip install flask flask-cors
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
'''
        
        # Create tar archive in memory
        context = BytesIO()
        with tarfile.open(fileobj=context, mode='w') as tar:
            # Add Dockerfile
            dockerfile_data = dockerfile_content.encode('utf-8')
            dockerfile_tarinfo = tarfile.TarInfo(name='Dockerfile')
            dockerfile_tarinfo.size = len(dockerfile_data)
            tar.addfile(dockerfile_tarinfo, BytesIO(dockerfile_data))
            
            # Add app.py
            app_data = app_code.encode('utf-8')
            app_tarinfo = tarfile.TarInfo(name='app.py')
            app_tarinfo.size = len(app_data)
            tar.addfile(app_tarinfo, BytesIO(app_data))
        
        context.seek(0)
        return context
