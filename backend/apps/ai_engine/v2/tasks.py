"""
V2 Celery tasks - Faster generation with single-shot AI
"""
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from .generator import AIGeneratorV2


def broadcast_progress(project_id, msg_type, message):
    """Broadcast generation progress to Redis"""
    messages_key = f'project_messages_{project_id}'
    existing = cache.get(messages_key, [])
    
    existing.append({
        'id': f'{project_id}_{len(existing)}',
        'type': msg_type,
        'content': message,
        'timestamp': timezone.now().isoformat()
    })
    
    cache.set(messages_key, existing, timeout=3600)


@shared_task(bind=True, max_retries=2)
def generate_app_v2_task(self, project_id):
    """
    V2 generation task - Single-shot, much faster
    """
    from apps.projects.models import Project
    
    try:
        project = Project.objects.get(id=project_id)
        project.status = 'generating'
        project.save()
        
        broadcast_progress(project_id, "action", "🚀 Starting V2 generation...")
        
        # Initialize V2 generator
        generator = AIGeneratorV2()
        
        # Single-shot generation
        result = generator.generate_app(
            user_prompt=project.user_prompt,
            project_id=project_id
        )
        
        # Store the result
        app_type = result.get('app_type', 'website')
        
        # Handle different response formats
        # Format 1: {"components": {"App": "...", "components/X": "..."}}
        # Format 2: {"frontend": {"App": "...", "components/X": "..."}} (webapp)
        if 'frontend' in result:
            components = result['frontend']
        else:
            components = result.get('components', {})
        
        # Build frontend_code structure (compatible with deployer)
        frontend_code = {
            'App.tsx': '',
            'components': {}
        }
        
        for name, code in components.items():
            # Clean the component name
            clean_name = name.replace('components/', '')
            
            # Fix missing imports - CRITICAL for build to succeed
            if 'import ' not in code:
                # Detect needed imports
                imports = ["import React"]
                if 'useState' in code:
                    imports.append(", { useState")
                    if 'useEffect' in code:
                        imports[0] = "import React, { useState, useEffect }"
                    else:
                        imports[0] = "import React, { useState }"
                elif 'useEffect' in code:
                    imports[0] = "import React, { useEffect }"
                else:
                    imports[0] = "import React"
                imports[0] += " from 'react';\n\n"
                code = imports[0] + code
            
            # Ensure export default exists
            if 'export default' not in code and 'function App' in code:
                code = code + "\n\nexport default App;"
            
            if clean_name == 'App' or name == 'App':
                frontend_code['App.tsx'] = code
            else:
                frontend_code['components'][clean_name] = code
        
        # Fallback if no App.tsx found
        if not frontend_code['App.tsx'] and frontend_code['components']:
            first_comp = list(frontend_code['components'].keys())[0]
            frontend_code['App.tsx'] = f"""import React from 'react';
import {first_comp} from './components/{first_comp}';

function App() {{
  return <{first_comp} />;
}}

export default App;
"""
        
        # Save to project
        project.frontend_code = str(frontend_code)
        project.ai_analysis = {
            'app_type': app_type,
            'title': result.get('title', project.name),
            'requires_backend': result.get('requires_backend', False),
            'generation_version': 'v2'
        }
        project.status = 'ready'
        project.save()
        
        broadcast_progress(project_id, "success", "🎉 Generation complete! Deploying...")
        
        # Auto-deploy
        from apps.deployment.tasks import deploy_app_task
        deploy_app_task.delay(project_id)
        
        return {
            'status': 'success',
            'project_id': project_id,
            'app_type': app_type
        }
        
    except Exception as e:
        error_msg = str(e)[:200]
        broadcast_progress(project_id, "error", f"❌ Error: {error_msg}")
        
        try:
            project = Project.objects.get(id=project_id)
            project.status = 'failed'
            project.ai_analysis = project.ai_analysis or {}
            project.ai_analysis['error'] = error_msg
            project.save()
        except:
            pass
        
        # Retry once
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)
        
        return {'status': 'failed', 'error': error_msg}


@shared_task
def quick_modify_task(project_id, user_request):
    """
    Quick modification task - Update existing app
    """
    from apps.projects.models import Project
    from apps.deployment.tasks import deploy_app_task
    import ast
    
    try:
        project = Project.objects.get(id=project_id)
        
        broadcast_progress(project_id, "action", f"💬 You: {user_request}")
        
        # Parse existing code
        if isinstance(project.frontend_code, str):
            code_dict = ast.literal_eval(project.frontend_code)
        else:
            code_dict = project.frontend_code
        
        # Get main component code
        if code_dict.get('components'):
            main_component = list(code_dict['components'].keys())[0]
            current_code = code_dict['components'][main_component]
        else:
            current_code = code_dict.get('App.tsx', '')
            main_component = None
        
        if not current_code:
            raise ValueError("No code to modify")
        
        # Modify with AI
        generator = AIGeneratorV2()
        new_code = generator.modify_app(
            current_code=current_code,
            user_request=user_request,
            project_id=project_id
        )
        
        # Update code
        if main_component:
            code_dict['components'][main_component] = new_code
        else:
            code_dict['App.tsx'] = new_code
        
        project.frontend_code = str(code_dict)
        project.status = 'deploying'
        project.save()
        
        broadcast_progress(project_id, "thinking", "🚀 Redeploying...")
        
        # Remove old container and redeploy
        if project.container_id:
            from apps.deployment.react_deployer import ReactDeployer
            deployer = ReactDeployer()
            try:
                deployer.client.containers.get(project.container_id).remove(force=True)
            except:
                pass
        
        deploy_app_task.delay(project_id)
        
        return {'status': 'success'}
        
    except Exception as e:
        broadcast_progress(project_id, "error", f"❌ Failed: {str(e)[:100]}")
        return {'status': 'error', 'message': str(e)}

