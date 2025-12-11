"""
V3 Celery Tasks - Universal App Generation
"""
import logging
from celery import shared_task
from django.core.cache import cache

from .generator import UniversalGenerator
from apps.projects.models import Project
from apps.deployment.tasks import deploy_app_task

logger = logging.getLogger(__name__)


def send_progress(project_id: int, message: str, status: str = 'building'):
    """Send progress message to frontend via Redis"""
    cache_key = f"project_progress_{project_id}"
    messages = cache.get(cache_key, [])
    messages.append({
        'message': message,
        'status': status,
        'timestamp': __import__('datetime').datetime.now().isoformat()
    })
    cache.set(cache_key, messages, timeout=3600)
    logger.warning(f"📢 [{project_id}] {message}")


@shared_task(bind=True, max_retries=2)
def generate_app_v3_task(self, project_id: int):
    """
    V3 Generation Task - Uses Universal Gateway
    
    This is the main entry point for generating apps.
    All generated code uses the gateway for external data.
    """
    try:
        project = Project.objects.get(id=project_id)
        project.status = 'building'
        project.save()
        
        send_progress(project_id, "🚀 Starting generation...")
        
        generator = UniversalGenerator()
        
        # Analyze request
        send_progress(project_id, "🧠 Analyzing your request...")
        analysis = generator.analyze_request(project.user_prompt)
        
        app_type = analysis.get('app_type', 'website')
        services = analysis.get('suggested_services', [])
        
        if services:
            send_progress(project_id, f"🔌 Will use: {', '.join(services)}")
        
        send_progress(project_id, f"📋 Building a {app_type}...")
        
        # Generate
        send_progress(project_id, "🎨 Generating components...")
        result = generator.generate(project.user_prompt, project_id)
        
        # Store code
        components = result.get('components', {})
        app_code = components.get('App', '')
        
        frontend_code = {
            'App.tsx': app_code,
            'components': {k: v for k, v in components.items() if k != 'App'}
        }
        
        project.frontend_code = repr(frontend_code)
        project.status = 'ready'
        project.save()
        
        send_progress(project_id, f"✅ Generated {len(components)} component(s)")
        
        # Deploy
        send_progress(project_id, "🚀 Deploying...")
        deploy_app_task.delay(project_id)
        
        return {
            'status': 'success',
            'project_id': project_id,
            'app_type': app_type,
            'services_used': result.get('api_services', [])
        }
        
    except Project.DoesNotExist:
        logger.error(f"Project {project_id} not found")
        return {'status': 'error', 'message': 'Project not found'}
        
    except Exception as e:
        logger.error(f"Generation failed for {project_id}: {e}", exc_info=True)
        send_progress(project_id, f"❌ Error: {str(e)}", 'error')
        
        try:
            project = Project.objects.get(id=project_id)
            project.status = 'failed'
            project.save()
        except:
            pass
        
        raise self.retry(exc=e, countdown=5)


@shared_task
def quick_modify_v3_task(project_id: int, user_request: str):
    """
    Quick modification of existing app
    """
    try:
        project = Project.objects.get(id=project_id)
        
        send_progress(project_id, "✏️ Modifying app...")
        
        # Get current code
        import ast
        try:
            code_dict = ast.literal_eval(project.frontend_code)
            current_code = code_dict.get('App.tsx', '')
        except:
            current_code = project.frontend_code or ''
        
        if not current_code:
            send_progress(project_id, "⚠️ No existing code, generating from scratch...")
            return generate_app_v3_task(project_id)
        
        # Modify
        generator = UniversalGenerator()
        new_code = generator.modify(current_code, user_request, project_id)
        
        # Store
        frontend_code = {
            'App.tsx': new_code,
            'components': {}
        }
        
        project.frontend_code = repr(frontend_code)
        project.status = 'ready'
        project.save()
        
        send_progress(project_id, "✅ Code updated!")
        
        # Redeploy
        send_progress(project_id, "🚀 Redeploying...")
        
        # Stop old container first (if exists)
        import docker
        try:
            client = docker.from_env()
            container_name = f"app-{project.user.username.lower()}-{project.name.lower().replace(' ', '-')}-{project.id}"
            try:
                old_container = client.containers.get(container_name)
                old_container.stop()
                old_container.remove()
                logger.info(f"Removed old container: {container_name}")
            except docker.errors.NotFound:
                pass  # Container doesn't exist, that's fine
        except Exception as e:
            logger.warning(f"Could not remove old container: {e}")
        
        deploy_app_task.delay(project_id)
        
        return {'status': 'success', 'project_id': project_id}
        
    except Exception as e:
        logger.error(f"Modification failed: {e}", exc_info=True)
        send_progress(project_id, f"❌ Error: {str(e)}", 'error')
        return {'status': 'error', 'message': str(e)}

