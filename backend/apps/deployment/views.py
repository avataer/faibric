from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.projects.models import Project
from .docker_manager import DockerManager


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deploy_project(request, project_id):
    """Deploy a project"""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if project.status == 'deployed':
        return Response(
            {'error': 'Project is already deployed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if project.status != 'ready':
        return Response(
            {'error': 'Project must be in ready state to deploy'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Start deployment
    from .tasks import deploy_app_task
    deploy_app_task.delay(project_id)
    
    return Response({
        'message': 'Deployment started',
        'project_id': project_id
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def undeploy_project(request, project_id):
    """Stop deployment of a project"""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if project.status != 'deployed':
        return Response(
            {'error': 'Project is not deployed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Start undeployment
    from .tasks import undeploy_app_task
    undeploy_app_task.delay(project_id)
    
    return Response({
        'message': 'Undeployment started',
        'project_id': project_id
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deployment_status(request, project_id):
    """Get deployment status"""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    response_data = {
        'project_id': project.id,
        'status': project.status,
        'deployment_url': project.deployment_url,
        'subdomain': project.subdomain,
    }
    
    if project.container_id:
        docker_mgr = DockerManager()
        container_status = docker_mgr.get_container_status(project.container_id)
        response_data['container'] = container_status
    
    return Response(response_data)

