"""
Celery tasks for deployment
"""
import os
from celery import shared_task
from django.utils import timezone
from django.conf import settings


def broadcast_deploy_message(project_id, content):
    """Helper to broadcast deployment messages"""
    from django.core.cache import cache
    
    messages_key = f'project_messages_{project_id}'
    existing = cache.get(messages_key, [])
    
    existing.append({
        'id': f'{project_id}_deploy_{len(existing)}',
        'type': 'action',
        'content': content,
        'timestamp': timezone.now().isoformat()
    })
    cache.set(messages_key, existing, timeout=3600)


def use_render_deployer():
    """Check if we should use Render deployer (cloud deployment)"""
    # Use Render if RENDER_API_KEY is configured or running on Render
    return bool(
        os.environ.get('RENDER') or 
        os.environ.get('RENDER_API_KEY') or
        getattr(settings, 'RENDER_API_KEY', '')
    )


def verify_deployment(url: str, max_attempts: int = 20, interval: int = 15) -> bool:
    """
    Verify that a deployed site is actually working.

    Checks:
    1. HTML page returns 200
    2. JS bundle is accessible
    3. JS bundle is large enough (not an error stub)
    4. No build errors in content
    """
    import requests
    import time
    import re

    for attempt in range(max_attempts):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                time.sleep(interval)
                continue

            html = resp.text
            js_match = re.search(r"src=[\"']([^\"']+\.js)[\"']", html)
            if not js_match:
                time.sleep(interval)
                continue

            js_path = js_match.group(1)
            if not js_path.startswith("http"):
                js_url = url.rstrip("/") + "/" + js_path.lstrip("/")
            else:
                js_url = js_path

            js_resp = requests.get(js_url, timeout=10)
            if js_resp.status_code != 200 or len(js_resp.content) < 10000:
                time.sleep(interval)
                continue

            if "Vite build error" in html or "Module not found" in js_resp.text:
                return False

            return True
        except Exception:
            time.sleep(interval)
            continue
    return False


@shared_task(bind=True, max_retries=2)
def deploy_app_task(self, project_id, use_v2=True):
    """
    Deploy a project as a React app

    Args:
        project_id: Project to deploy
        use_v2: Use V2 fast deployer (default True for Docker, ignored for Render)
    """
    from apps.projects.models import Project
    from django.core.cache import cache
    from .validators import (
        validate_frontend_code,
        validate_build_locally,
        CodeValidationError
    )

    try:
        project = Project.objects.get(id=project_id)
        project.status = 'deploying'
        project.save()

        broadcast_deploy_message(project_id, '[DEPLOY] Starting deployment...')

        # Step 1: Static code validation
        try:
            code_dict = validate_frontend_code(project)
            broadcast_deploy_message(project_id, '[OK] Static validation passed')
        except CodeValidationError as e:
            broadcast_deploy_message(project_id, f'[ERROR] Static validation failed: {str(e)}')
            project.status = 'error'
            project.save()
            return {
                'status': 'error',
                'message': f'Static validation failed: {str(e)}'
            }

        # Step 2: Local build validation (catches errors in ~5s instead of 15min on Render)
        if use_render_deployer():
            broadcast_deploy_message(project_id, '[BUILD] Running local build test...')
            build_result = validate_build_locally(code_dict, project.name or "app")

            if not build_result.get('success'):
                error_msg = build_result.get('error', 'Build failed')
                details = build_result.get('details', '')

                broadcast_deploy_message(
                    project_id,
                    f'[ERROR] Local build failed: {error_msg}'
                )

                # Save error details to project for debugging
                project.status = 'error'
                project.save()

                return {
                    'status': 'error',
                    'message': f'Build validation failed: {error_msg}',
                    'details': details
                }

            broadcast_deploy_message(project_id, '[OK] Local build passed - deploying to cloud')

        # Check if we should use Render or Docker
        if use_render_deployer():
            # Deploy to Render.com
            from .render_deployer import RenderDeployer
            deployer = RenderDeployer()
            
            broadcast_deploy_message(project_id, '☁️ Deploying to Render.com...')
            
            result = deployer.deploy_react_app(project)
            deployment_url = result['url']

            broadcast_deploy_message(project_id, '[VERIFY] Checking deployment...')
            verified = verify_deployment(deployment_url)

            if not verified:
                broadcast_deploy_message(project_id, '[ERROR] Deployment verification failed')
                project.status = 'verification_failed'
                project.deployment_url = ''
                project.save()
                return {
                    'status': 'error',
                    'message': 'Deployment verification failed - build may have errors'
                }

            broadcast_deploy_message(project_id, f'[OK] Verified at {deployment_url}')

            # Update project
            project.deployment_url = deployment_url
            project.subdomain = result.get('branch', '')
            project.status = 'deployed'
            project.deployed_at = timezone.now()
            project.save()

            return {
                'status': 'success',
                'project_id': project_id,
                'deployment_url': deployment_url
            }
        else:
            # Use Docker deployer (local development)
            from .react_deployer import ReactDeployer
            from .docker_manager import DomainManager
            
            if use_v2:
                from .v2.fast_deployer import FastReactDeployer
                deployer = FastReactDeployer()
            else:
                deployer = ReactDeployer()
            
            domain_mgr = DomainManager()
            
            broadcast_deploy_message(project_id, '🐳 Building React app...')
            
            # Deploy React app
            container_id = deployer.deploy_react_app(project)
            
            broadcast_deploy_message(project_id, '🌐 Configuring routing...')
            
            # Assign subdomain
            subdomain = domain_mgr.assign_subdomain(project)
            deployment_url = domain_mgr.get_full_url(subdomain)
            
            broadcast_deploy_message(project_id, f'✅ Deployed at {deployment_url}')
            
            # Update project
            project.container_id = container_id
            project.subdomain = subdomain
            project.deployment_url = deployment_url
            project.status = 'deployed'
            project.deployed_at = timezone.now()
            project.save()
            
            return {
                'status': 'success',
                'project_id': project_id,
                'deployment_url': deployment_url
            }
        
    except Exception as e:
        error_msg = str(e)[:200]
        broadcast_deploy_message(project_id, f'❌ Deployment failed: {error_msg}')
        
        try:
            project = Project.objects.get(id=project_id)
            project.status = 'ready'  # Keep ready, deployment failed
            project.save()
        except:
            pass
        
        # Retry once
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=15)
        
        return {'status': 'error', 'message': error_msg}


@shared_task
def undeploy_app_task(project_id):
    """
    Stop and remove deployment for a project
    """
    from apps.projects.models import Project
    
    try:
        project = Project.objects.get(id=project_id)
        
        if not project.container_id:
            return {'status': 'error', 'message': 'No deployment to stop'}
        
        # Initialize deployer
        deployer = ReactDeployer()
        domain_mgr = DomainManager()
        
        # Stop container
        deployer.stop_container(project.container_id)
        
        # Remove routing (handled automatically by Traefik)
        if project.subdomain:
            domain_mgr.remove_routing(project.subdomain)
        
        # Update project
        project.status = 'ready'
        project.container_id = ''
        project.deployment_url = ''
        project.save()
        
        return {
            'status': 'success',
            'message': 'App undeployed successfully'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@shared_task
def check_deployments_health():
    """
    Periodic task to check health of all deployments
    """
    from apps.projects.models import Project
    
    docker_mgr = DockerManager()
    deployed_projects = Project.objects.filter(status='deployed')
    
    for project in deployed_projects:
        if project.container_id:
            status = docker_mgr.get_container_status(project.container_id)
            
            if status['status'] == 'not_found':
                # Container is gone, update project
                project.status = 'failed'
                project.save()

