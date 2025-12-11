from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .tasks import generate_app_task, refine_code_task
from apps.projects.models import Project


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_app(request):
    """
    Start AI app generation from description
    """
    user_prompt = request.data.get('user_prompt')
    project_name = request.data.get('name', 'My App')
    
    if not user_prompt:
        return Response(
            {'error': 'user_prompt is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create project
    project = Project.objects.create(
        user=request.user,
        name=project_name,
        description=user_prompt[:500],  # First 500 chars
        user_prompt=user_prompt,
        status='generating'
    )
    
    # Start async generation
    generate_app_task.delay(project.id)
    
    return Response({
        'project_id': project.id,
        'status': 'generating',
        'message': 'App generation started'
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refine_code(request, project_id):
    """
    Refine specific code component based on feedback
    """
    component_type = request.data.get('component_type')  # 'model', 'api', 'ui'
    component_name = request.data.get('component_name')
    feedback = request.data.get('feedback')
    
    if not all([component_type, feedback]):
        return Response(
            {'error': 'component_type and feedback are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify project belongs to user
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Start async refinement
    refine_code_task.delay(project_id, component_type, component_name, feedback)
    
    return Response({
        'status': 'refining',
        'message': 'Code refinement started'
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generation_status(request, project_id):
    """
    Check status of app generation
    """
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response({
        'project_id': project.id,
        'status': project.status,
        'has_schema': project.database_schema is not None,
        'has_api': bool(project.api_code),
        'has_frontend': bool(project.frontend_code),
    })

