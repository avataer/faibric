"""
Celery tasks for deployment
"""
from celery import shared_task
from django.utils import timezone
from .react_deployer import ReactDeployer
from .docker_manager import DomainManager


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


@shared_task(bind=True, max_retries=2)
def deploy_app_task(self, project_id, use_v2=True):
    """
    Deploy a project as a React app
    
    Args:
        project_id: Project to deploy
        use_v2: Use V2 fast deployer (default True)
    """
    from apps.projects.models import Project
    from django.core.cache import cache
    
    try:
        project = Project.objects.get(id=project_id)
        project.status = 'deploying'
        project.save()
        
        broadcast_deploy_message(project_id, '🚀 Starting deployment...')
        
        # Choose deployer
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

