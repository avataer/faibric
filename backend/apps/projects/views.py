from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Project, ProjectVersion, CustomerAPIKey
from .serializers import (
    ProjectSerializer, ProjectListSerializer,
    ProjectCreateSerializer, ProjectVersionSerializer
)
from apps.ai_engine.v3.tasks import generate_app_v3_task, quick_modify_v3_task
from apps.tenants.permissions import TenantPermission

# Progress calculation constants
PROGRESS_PER_MESSAGE = 5
MAX_PROGRESS_GENERATING = 95


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing projects.
    All projects are scoped to the current tenant for security isolation.
    """
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        elif self.action == 'create':
            return ProjectCreateSerializer
        return ProjectSerializer
    
    def get_queryset(self):
        """Filter projects by current tenant AND user"""
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return Project.objects.filter(tenant=tenant, user=self.request.user)
        # Fallback: filter by user only (for backwards compatibility)
        return Project.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Check if user has reached max apps limit
        user = self.request.user
        if self.get_queryset().count() >= user.max_apps:
            raise serializers.ValidationError(
                f"You have reached the maximum number of apps ({user.max_apps})"
            )

        # Get current tenant from request
        tenant = getattr(self.request, 'tenant', None)

        project = serializer.save(user=user, tenant=tenant)

        # Start V3 generation (component-based, fast)
        generate_app_v3_task.delay(project.id)
    
    @action(detail=True, methods=['post'])
    def quick_update(self, request, pk=None):
        """Quick update - modify and redeploy using V3 generator"""
        project = self.get_object()
        user_request = request.data.get('user_prompt')

        if not user_request:
            return Response({'error': 'user_prompt is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Set status to deploying immediately
        project.status = 'deploying'
        project.save()

        # Use async V3 modification task
        quick_modify_v3_task.delay(project.id, user_request)

        return Response({'status': 'success', 'message': 'Update in progress...'})
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate project with updated prompt using V3 generator"""
        from django.core.cache import cache
        from django.utils import timezone
        from apps.projects.models import GeneratedModel, GeneratedAPI
        
        project = self.get_object()
        
        new_prompt = request.data.get('user_prompt')
        if new_prompt:
            # Broadcast user message
            messages_key = f'project_messages_{project.id}'
            existing_messages = cache.get(messages_key, [])
            
            existing_messages.append({
                'id': f'{project.id}_user_{len(existing_messages)}',
                'type': 'action',
                'content': f'💬 You: {new_prompt}',
                'timestamp': timezone.now().isoformat()
            })
            cache.set(messages_key, existing_messages, timeout=3600)
            
            # Delete old generated models/APIs
            GeneratedModel.objects.filter(project=project).delete()
            GeneratedAPI.objects.filter(project=project).delete()
            
            # Undeploy if deployed
            if project.container_id:
                from apps.deployment.tasks import undeploy_app_task
                undeploy_app_task.delay(project.id)
            
            # Update prompt and regenerate with V3
            project.user_prompt = f"{project.user_prompt}\n\nADDITIONAL REQUEST: {new_prompt}"
            project.status = 'building'
            project.save()

            # Use V3 generation
            generate_app_v3_task.delay(project.id)

            return Response({'message': 'Regeneration started'})
        
        return Response(
            {'error': 'user_prompt is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish/deploy the project"""
        project = self.get_object()
        
        if project.status != 'ready':
            return Response(
                {'error': 'Project must be in ready state to publish'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger deployment
        from apps.deployment.tasks import deploy_app_task
        deploy_app_task.delay(project.id)
        
        return Response({'message': 'Deployment started'})
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish/stop the deployed project"""
        project = self.get_object()
        
        if project.status != 'deployed':
            return Response(
                {'error': 'Project is not deployed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger undeployment
        from apps.deployment.tasks import undeploy_app_task
        undeploy_app_task.delay(project.id)
        
        return Response({'message': 'Undeployment started'})
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get real-time generation progress with message history"""
        from django.core.cache import cache
        
        # Get message history
        messages = cache.get(f'project_messages_{pk}', [])
        progress_data = cache.get(f'project_progress_{pk}')
        
        # Calculate progress based on project status
        project = self.get_object()
        progress_percent = 0
        if project.status == 'building':
            progress_percent = min(len(messages) * PROGRESS_PER_MESSAGE, MAX_PROGRESS_GENERATING)
        elif project.status == 'ready':
            progress_percent = MAX_PROGRESS_GENERATING
        elif project.status == 'deployed':
            progress_percent = 100
        
        # Get current step from last message or progress data
        current_step = 'Initializing...'
        if messages and len(messages) > 0:
            current_step = messages[-1].get('content', 'Processing...')
        elif progress_data:
            if isinstance(progress_data, dict):
                current_step = progress_data.get('message', 'Processing...')
            elif isinstance(progress_data, list) and len(progress_data) > 0:
                current_step = progress_data[-1].get('message', 'Processing...')
        
        return Response({
            'messages': messages,
            'progress': progress_percent,
            'status': project.status,
            'current_step': current_step
        })
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get all versions of a project"""
        project = self.get_object()
        versions = ProjectVersion.objects.filter(project=project)
        serializer = ProjectVersionSerializer(versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """Create a new version snapshot"""
        project = self.get_object()
        
        # Create snapshot
        snapshot = {
            'database_schema': project.database_schema,
            'api_code': project.api_code,
            'frontend_code': project.frontend_code,
            'ai_analysis': project.ai_analysis,
        }
        
        # Auto-increment version
        last_version = project.versions.first()
        if last_version:
            version_num = int(last_version.version.split('.')[-1]) + 1
            version = f"1.{version_num}"
        else:
            version = "1.0"
        
        version_obj = ProjectVersion.objects.create(
            project=project,
            version=version,
            snapshot=snapshot,
            notes=request.data.get('notes', '')
        )
        
        serializer = ProjectVersionSerializer(version_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get', 'post'])
    def api_keys(self, request, pk=None):
        """
        Manage customer API keys for data integrations.
        
        GET: List all API keys for this project (masked)
        POST: Add a new API key
        """
        project = self.get_object()
        
        if request.method == 'GET':
            keys = CustomerAPIKey.objects.filter(project=project)
            return Response({
                'api_keys': [
                    {
                        'id': key.id,
                        'service': key.service,
                        'service_name': key.service_name or key.get_service_display(),
                        'status': key.status,
                        'masked_key': key.mask_key(),
                        'last_used': key.last_used_at,
                        'call_count': key.call_count,
                    }
                    for key in keys
                ],
                'available_services': [
                    {'id': s[0], 'name': s[1]} 
                    for s in CustomerAPIKey.SERVICE_CHOICES
                ]
            })
        
        elif request.method == 'POST':
            service = request.data.get('service')
            api_key = request.data.get('api_key')
            
            if not service or not api_key:
                return Response(
                    {'error': 'service and api_key are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create or update
            key_obj, created = CustomerAPIKey.objects.update_or_create(
                project=project,
                service=service,
                defaults={
                    'api_key': api_key,
                    'service_name': request.data.get('service_name', ''),
                    'base_url': request.data.get('base_url', ''),
                    'status': 'pending',
                }
            )
            
            # Mark as active - validation happens on first use via gateway
            key_obj.status = 'active'
            key_obj.save()
            
            return Response({
                'success': True,
                'message': f'API key for {service} {"added" if created else "updated"}',
                'key': {
                    'id': key_obj.id,
                    'service': key_obj.service,
                    'status': key_obj.status,
                    'masked_key': key_obj.mask_key(),
                }
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], url_path='api_keys/(?P<key_id>[^/.]+)')
    def delete_api_key(self, request, pk=None, key_id=None):
        """Delete an API key"""
        project = self.get_object()
        
        try:
            key = CustomerAPIKey.objects.get(id=key_id, project=project)
            service = key.service
            key.delete()
            return Response({
                'success': True,
                'message': f'API key for {service} deleted'
            })
        except CustomerAPIKey.DoesNotExist:
            return Response(
                {'error': 'API key not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def data_sources(self, request, pk=None):
        """
        Get status of all data sources for this project.
        
        Used by the frontend Settings view to show connection status.
        """
        project = self.get_object()
        customer_keys = {k.service: k for k in CustomerAPIKey.objects.filter(project=project)}
        
        from apps.gateway.services import SERVICES, get_api_key
        
        sources = []
        for service_id, config in SERVICES.items():
            # Check if it's a free service (no auth needed)
            is_free = config.get('auth_type') == 'none'
            
            # Check if customer has provided a key
            customer_key = customer_keys.get(service_id)
            
            # Check if platform has a key configured
            platform_key = bool(get_api_key(config)) if config.get('env_key') else False
            
            sources.append({
                'id': service_id,
                'name': config['name'],
                'docs': config.get('docs', ''),
                'free_tier': config.get('free_tier', ''),
                'is_free': is_free,
                'status': 'connected' if (is_free or customer_key or platform_key) else 'not_connected',
                'customer_key': bool(customer_key),
                'requires_key': config.get('auth_type') != 'none',
            })
        
        return Response({
            'data_sources': sources,
            'connected_count': sum(1 for s in sources if s['status'] == 'connected'),
            'total_count': len(sources),
        })


from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import hashlib


@method_decorator(csrf_exempt, name='dispatch')
class PublicBuilderView(APIView):
    """
    Public API for the embedded builder in deployed apps.
    
    Uses a project token for authentication (embedded in deployed app).
    Allows customers to modify their apps through the admin panel.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Modify and redeploy a project.
        
        Request body:
        {
            "project_token": "sha256 hash of project id + secret",
            "project_id": 123,
            "modification": "make the background red"
        }
        
        Returns:
        {
            "status": "building" | "complete" | "error",
            "message": "...",
            "url": "new deployment URL"
        }
        """
        from apps.onboarding.models import LandingSession
        from apps.code_library.component_pipeline import build_compact_app
        from apps.deployment.vercel_deployer import get_vercel_deployer
        import logging
        
        logger = logging.getLogger(__name__)
        
        project_id = request.data.get('project_id')
        project_token = request.data.get('project_token')
        modification = request.data.get('modification', '').strip()
        
        if not project_id or not modification:
            return Response({
                'status': 'error',
                'message': 'project_id and modification are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate project token
        # Token = sha256(project_id + BUILDER_SECRET)
        from django.conf import settings
        expected_token = hashlib.sha256(
            f"{project_id}{settings.BUILDER_SECRET}".encode()
        ).hexdigest()[:16]
        
        if project_token != expected_token:
            return Response({
                'status': 'error',
                'message': 'Invalid project token'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Find the project by ID
            project = Project.objects.get(id=project_id)
            
            # Update the prompt with the modification
            original_prompt = project.user_prompt or project.name
            new_prompt = f"{original_prompt}\n\nMODIFICATION REQUEST: {modification}"
            
            logger.info(f"[BUILDER] Modifying project {project_id}: {modification}")
            
            # Determine if this needs real data
            data_keywords = ['stock', 'crypto', 'bitcoin', 'price', 'weather', 'api', 
                             'tracker', 'live', 'real-time', 'monitor', 'dashboard']
            needs_data = any(kw in new_prompt.lower() for kw in data_keywords)
            
            # Generate new code with the modification
            app_code = build_compact_app(new_prompt, needs_data)
            
            # Save the new code
            project.frontend_code = app_code
            project.user_prompt = new_prompt
            project.status = 'deploying'
            project.save()
            
            # Redeploy to Vercel
            vercel = get_vercel_deployer()
            project_name = project.name.lower().replace(' ', '-')[:50]
            
            result = vercel.deploy_static_app(project_name, app_code, str(project.id))
            
            if result.get('success'):
                # Update project with new URL
                project.deployment_url = result.get('url', '')
                project.status = 'deployed'
                project.save()
                
                logger.info(f"[BUILDER] Redeployed project {project_id}: {result.get('url')}")
                
                return Response({
                    'status': 'complete',
                    'message': f'Applied: {modification}',
                    'url': result.get('url')
                })
            else:
                project.status = 'failed'
                project.save()
                
                return Response({
                    'status': 'error',
                    'message': f"Deployment failed: {result.get('error', 'Unknown error')}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Project.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"[BUILDER] Error modifying project {project_id}: {e}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

