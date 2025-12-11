from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Template
from .serializers import TemplateSerializer, TemplateListSerializer
from apps.projects.models import Project


class TemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for browsing templates
    """
    queryset = Template.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TemplateListSerializer
        return TemplateSerializer
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def use_template(self, request, slug=None):
        """
        Create a new project from this template
        """
        template = self.get_object()
        
        project_name = request.data.get('name', f'{template.name} Project')
        description = request.data.get('description', template.description)
        
        # Check user's app limit
        user = request.user
        if Project.objects.filter(user=user).count() >= user.max_apps:
            return Response(
                {'error': f'You have reached the maximum number of apps ({user.max_apps})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create project from template
        project = Project.objects.create(
            user=user,
            name=project_name,
            description=description,
            template=template,
            user_prompt=f"Create {template.name}: {description}",
            database_schema=template.schema_template,
            status='ready'
        )
        
        # Increment usage count
        template.usage_count += 1
        template.save()
        
        from apps.projects.serializers import ProjectSerializer
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED
        )

