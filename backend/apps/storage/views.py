from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import FileResponse
from io import BytesIO

from apps.tenants.permissions import TenantPermission
from .models import StorageConfig, Folder, File, StorageUsage
from .serializers import (
    StorageConfigSerializer, StorageConfigUpdateSerializer,
    FolderSerializer, FolderCreateSerializer,
    FileSerializer, FileUploadSerializer,
    StorageUsageSerializer,
    PublicFileUploadSerializer
)
from .services import StorageService


class StorageConfigViewSet(viewsets.ViewSet):
    """ViewSet for managing storage configuration."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_config(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        config, _ = StorageConfig.objects.get_or_create(tenant=tenant)
        return config
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """Get storage configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = StorageConfigSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_config(self, request):
        """Update storage configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = StorageConfigUpdateSerializer(
            config,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(StorageConfigSerializer(config).data)


class FolderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing folders."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FolderCreateSerializer
        return FolderSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Folder.objects.none()
        return Folder.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['get'])
    def contents(self, request, pk=None):
        """Get folder contents."""
        folder = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        service = StorageService(tenant)
        contents = service.list_folder(folder)
        
        return Response({
            'folder': FolderSerializer(folder).data,
            'folders': FolderSerializer(contents['folders'], many=True).data,
            'files': FileSerializer(contents['files'], many=True).data
        })
    
    @action(detail=True, methods=['delete'])
    def delete_recursive(self, request, pk=None):
        """Delete folder and all contents."""
        folder = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        service = StorageService(tenant)
        try:
            service.delete_folder(folder, recursive=True)
            return Response({'success': True})
        except ValueError as e:
            return Response({'error': str(e)}, status=400)


class FileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing files."""
    permission_classes = [IsAuthenticated, TenantPermission]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = FileSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return File.objects.none()
        return File.objects.filter(tenant=tenant, is_deleted=False)
    
    def create(self, request, *args, **kwargs):
        """Upload a file."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        uploaded_file = data['file']
        folder = None
        
        if data.get('folder_id'):
            try:
                folder = Folder.objects.get(id=data['folder_id'], tenant=tenant)
            except Folder.DoesNotExist:
                return Response({'error': 'Folder not found'}, status=404)
        
        service = StorageService(tenant)
        
        try:
            file = service.upload_file(
                file=uploaded_file.file,
                filename=uploaded_file.name,
                content_type=uploaded_file.content_type,
                folder=folder,
                owner_id=request.data.get('owner_id', ''),
                owner_type=request.data.get('owner_type', 'user'),
                is_public=data.get('is_public', False)
            )
            
            return Response(
                FileSerializer(file).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a file."""
        file = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        service = StorageService(tenant)
        content = service.download_file(file)
        
        if content is None:
            return Response({'error': 'File not found'}, status=404)
        
        response = FileResponse(
            BytesIO(content),
            content_type=file.content_type
        )
        response['Content-Disposition'] = f'attachment; filename="{file.original_name}"'
        return response
    
    @action(detail=True, methods=['get'])
    def url(self, request, pk=None):
        """Get a signed URL for the file."""
        file = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        expires_in = int(request.query_params.get('expires_in', 3600))
        
        service = StorageService(tenant)
        url = service.get_file_url(file, expires_in)
        
        return Response({
            'url': url,
            'expires_in': expires_in
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete a file."""
        file = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        permanent = request.query_params.get('permanent', 'false').lower() == 'true'
        
        service = StorageService(tenant)
        service.delete_file(file, permanent=permanent)
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class StorageUsageView(APIView):
    """View for storage usage."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get(self, request):
        """Get storage usage."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        service = StorageService(tenant)
        usage = service.get_usage()
        
        return Response(StorageUsageSerializer(usage).data)
    
    def post(self, request):
        """Recalculate storage usage."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        service = StorageService(tenant)
        usage = service.recalculate_usage()
        
        return Response(StorageUsageSerializer(usage).data)


# ============= PUBLIC API (for customer's apps) =============

class PublicStorageView(APIView):
    """Public endpoint for file operations."""
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def _get_tenant(self, request):
        from apps.projects.models import Project
        
        app_id = request.headers.get('X-Faibric-App-Id')
        if not app_id:
            return None
        
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            return project.tenant
        except Project.DoesNotExist:
            return None
    
    def get(self, request, action=None, file_id=None):
        """Handle GET requests."""
        tenant = self._get_tenant(request)
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        service = StorageService(tenant)
        user_id = request.headers.get('X-User-Id')
        
        if action == 'list':
            folder_id = request.query_params.get('folder_id')
            folder = None
            if folder_id:
                folder = service.get_folder(folder_id)
            
            contents = service.list_folder(folder)
            
            # Filter by owner if user_id provided
            files = contents['files']
            if user_id:
                files = [f for f in files if f.owner_id == user_id or f.is_public]
            
            return Response({
                'folders': FolderSerializer(contents['folders'], many=True).data,
                'files': FileSerializer(files, many=True).data
            })
        
        elif action == 'download' and file_id:
            file = service.get_file(file_id)
            if not file:
                return Response({'error': 'File not found'}, status=404)
            
            # Check access
            if not file.is_public and file.owner_id != user_id:
                return Response({'error': 'Access denied'}, status=403)
            
            content = service.download_file(file)
            if content is None:
                return Response({'error': 'File not found'}, status=404)
            
            response = FileResponse(
                BytesIO(content),
                content_type=file.content_type
            )
            response['Content-Disposition'] = f'attachment; filename="{file.original_name}"'
            return response
        
        elif action == 'url' and file_id:
            file = service.get_file(file_id)
            if not file:
                return Response({'error': 'File not found'}, status=404)
            
            # Check access
            if not file.is_public and file.owner_id != user_id:
                return Response({'error': 'Access denied'}, status=403)
            
            url = service.get_file_url(file)
            return Response({'url': url, 'file': FileSerializer(file).data})
        
        return Response({'error': 'Unknown action'}, status=400)
    
    def post(self, request, action=None, **kwargs):
        """Handle POST requests (upload)."""
        tenant = self._get_tenant(request)
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        user_id = request.headers.get('X-User-Id', '')
        
        if action == 'upload':
            if 'file' not in request.FILES:
                return Response({'error': 'No file provided'}, status=400)
            
            uploaded_file = request.FILES['file']
            folder_id = request.data.get('folder_id')
            
            service = StorageService(tenant)
            
            folder = None
            if folder_id:
                folder = service.get_folder(folder_id)
            
            try:
                file = service.upload_file(
                    file=uploaded_file.file,
                    filename=uploaded_file.name,
                    content_type=uploaded_file.content_type,
                    folder=folder,
                    owner_id=user_id,
                    owner_type='user',
                    is_public=request.data.get('is_public', 'false').lower() == 'true'
                )
                
                return Response(
                    FileSerializer(file).data,
                    status=status.HTTP_201_CREATED
                )
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        
        return Response({'error': 'Unknown action'}, status=400)
    
    def delete(self, request, action=None, file_id=None):
        """Handle DELETE requests."""
        tenant = self._get_tenant(request)
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        if action == 'delete' and file_id:
            service = StorageService(tenant)
            file = service.get_file(file_id)
            
            if not file:
                return Response({'error': 'File not found'}, status=404)
            
            # Check ownership
            user_id = request.headers.get('X-User-Id')
            if file.owner_id != user_id:
                return Response({'error': 'Access denied'}, status=403)
            
            service.delete_file(file)
            return Response({'success': True})
        
        return Response({'error': 'Unknown action'}, status=400)









