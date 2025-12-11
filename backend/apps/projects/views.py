from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Project, ProjectVersion
from .serializers import (
    ProjectSerializer, ProjectListSerializer, 
    ProjectCreateSerializer, ProjectVersionSerializer
)
from apps.ai_engine.v3.tasks import generate_app_v3_task, quick_modify_v3_task
from apps.tenants.permissions import TenantPermission


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
        
        # Use V2 generation by default (faster, single-shot)
        from apps.ai_engine.v3.tasks import generate_app_v3_task
        generate_app_v3_task.delay(project.id)
    
    @action(detail=True, methods=['post'])
    def quick_update(self, request, pk=None):
        """Quick update - modify and redeploy using V2 generator"""
        from apps.ai_engine.v2.tasks import quick_modify_task
        
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
        """Regenerate project with updated prompt using V2 generator"""
        from django.core.cache import cache
        from django.utils import timezone
        from apps.projects.models import GeneratedModel, GeneratedAPI
        from apps.ai_engine.v3.tasks import generate_app_v3_task
        
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
            
            # Update prompt and regenerate with V2
            project.user_prompt = f"{project.user_prompt}\n\nADDITIONAL REQUEST: {new_prompt}"
            project.status = 'generating'
            project.save()
            
            # Use V2 generation
            generate_app_v3_task.delay(project.id)
            
            return Response({'message': 'Regeneration started with V2'})
        
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
        if project.status == 'generating':
            progress_percent = min(len(messages) * 5, 95)  # 5% per message, max 95%
        elif project.status == 'ready':
            progress_percent = 95
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

