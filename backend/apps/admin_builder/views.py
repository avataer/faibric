from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.tenants.permissions import TenantPermission
from .models import (
    AdminBuilderConfig, AdminPage, Widget, DataSource, ExportedAdmin
)
from .serializers import (
    AdminBuilderConfigSerializer,
    AdminPageSerializer, AdminPageListSerializer, AdminPageCreateSerializer,
    WidgetSerializer, WidgetCreateSerializer,
    DataSourceSerializer, DataSourceCreateSerializer,
    AdminTemplateSerializer, ApplyTemplateSerializer,
    ExportedAdminSerializer, ExportRequestSerializer,
    WIDGET_TYPES
)
from .services import AdminBuilderService


class AdminBuilderConfigViewSet(viewsets.ViewSet):
    """ViewSet for admin builder configuration."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_config(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        config, _ = AdminBuilderConfig.objects.get_or_create(tenant=tenant)
        return config
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        return Response(AdminBuilderConfigSerializer(config).data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_config(self, request):
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = AdminBuilderConfigSerializer(
            config, data=request.data, partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminPageViewSet(viewsets.ModelViewSet):
    """ViewSet for admin pages."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AdminPageListSerializer
        if self.action == 'create':
            return AdminPageCreateSerializer
        return AdminPageSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return AdminPage.objects.none()
        return AdminPage.objects.filter(tenant=tenant).prefetch_related('widgets')
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a page."""
        page = self.get_object()
        page.publish()
        return Response(AdminPageSerializer(page).data)
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish a page."""
        page = self.get_object()
        page.is_published = False
        page.save(update_fields=['is_published'])
        return Response(AdminPageSerializer(page).data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a page."""
        page = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        # Create new page
        new_page = AdminPage.objects.create(
            tenant=tenant,
            name=f"{page.name} (Copy)",
            slug=f"{page.slug}-copy",
            title=page.title,
            description=page.description,
            icon=page.icon,
            page_type=page.page_type,
            layout=page.layout,
            nav_order=page.nav_order + 1,
            is_published=False
        )
        
        # Duplicate widgets
        for widget in page.widgets.all():
            Widget.objects.create(
                page=new_page,
                name=widget.name,
                widget_type=widget.widget_type,
                config=widget.config,
                style=widget.style,
                data_source=widget.data_source,
                data_query=widget.data_query
            )
        
        return Response(AdminPageSerializer(new_page).data, status=status.HTTP_201_CREATED)


class WidgetViewSet(viewsets.ModelViewSet):
    """ViewSet for widgets."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return WidgetCreateSerializer
        return WidgetSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Widget.objects.none()
        return Widget.objects.filter(page__tenant=tenant)
    
    def create(self, request, *args, **kwargs):
        page_id = request.data.get('page_id')
        if not page_id:
            return Response({'error': 'page_id required'}, status=400)
        
        tenant = getattr(request, 'tenant', None)
        try:
            page = AdminPage.objects.get(id=page_id, tenant=tenant)
        except AdminPage.DoesNotExist:
            return Response({'error': 'Page not found'}, status=404)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(page=page)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available widget types."""
        return Response(WIDGET_TYPES)


class DataSourceViewSet(viewsets.ModelViewSet):
    """ViewSet for data sources."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DataSourceCreateSerializer
        return DataSourceSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return DataSource.objects.none()
        return DataSource.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['get'])
    def fetch(self, request, pk=None):
        """Fetch data from a data source."""
        ds = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        service = AdminBuilderService(tenant)
        data = service.fetch_data_source(ds)
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available data source types."""
        return Response([
            {'type': 'api', 'name': 'External API', 'icon': '🌐'},
            {'type': 'database', 'name': 'Database Collection', 'icon': '🗄️'},
            {'type': 'static', 'name': 'Static Data', 'icon': '📦'},
            {'type': 'checkout_orders', 'name': 'Orders', 'icon': '📦'},
            {'type': 'checkout_products', 'name': 'Products', 'icon': '🏷️'},
            {'type': 'cabinet_users', 'name': 'Users', 'icon': '👥'},
            {'type': 'cabinet_tickets', 'name': 'Support Tickets', 'icon': '🎫'},
            {'type': 'storage_files', 'name': 'Files', 'icon': '📁'},
            {'type': 'analytics_events', 'name': 'Analytics Events', 'icon': '📈'},
        ])


class TemplateViewSet(viewsets.ViewSet):
    """ViewSet for admin templates."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def list(self, request):
        """List all templates."""
        tenant = getattr(request, 'tenant', None)
        service = AdminBuilderService(tenant)
        
        category = request.query_params.get('category')
        templates = service.get_templates(category)
        
        serializer = AdminTemplateSerializer(templates, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get a specific template."""
        tenant = getattr(request, 'tenant', None)
        service = AdminBuilderService(tenant)
        
        template = service.get_template(pk)
        if not template:
            return Response({'error': 'Template not found'}, status=404)
        
        serializer = AdminTemplateSerializer(template)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def apply(self, request):
        """Apply a template to create pages."""
        tenant = getattr(request, 'tenant', None)
        
        serializer = ApplyTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = AdminBuilderService(tenant)
        
        try:
            pages = service.apply_template(serializer.validated_data['template_slug'])
            return Response({
                'success': True,
                'pages_created': len(pages),
                'pages': AdminPageListSerializer(pages, many=True).data
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get template categories."""
        return Response([
            {'slug': 'dashboard', 'name': 'Dashboard', 'icon': '📊'},
            {'slug': 'ecommerce', 'name': 'E-Commerce', 'icon': '🛒'},
            {'slug': 'crm', 'name': 'CRM', 'icon': '💼'},
            {'slug': 'cms', 'name': 'Content Management', 'icon': '📝'},
            {'slug': 'analytics', 'name': 'Analytics', 'icon': '📈'},
            {'slug': 'project', 'name': 'Project Management', 'icon': '📋'},
            {'slug': 'hr', 'name': 'HR Management', 'icon': '👔'},
            {'slug': 'finance', 'name': 'Finance', 'icon': '💰'},
            {'slug': 'support', 'name': 'Support/Helpdesk', 'icon': '🎫'},
            {'slug': 'social', 'name': 'Social Media', 'icon': '📱'},
        ])


class ExportViewSet(viewsets.ViewSet):
    """ViewSet for exporting admin panels."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def list(self, request):
        """List previous exports."""
        tenant = getattr(request, 'tenant', None)
        exports = ExportedAdmin.objects.filter(tenant=tenant)
        serializer = ExportedAdminSerializer(exports, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def create_export(self, request):
        """Create a new export."""
        tenant = getattr(request, 'tenant', None)
        
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = AdminBuilderService(tenant)
        export = service.export_to_react(serializer.validated_data.get('name'))
        
        return Response(ExportedAdminSerializer(export).data, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, pk=None):
        """Get an export with code."""
        tenant = getattr(request, 'tenant', None)
        
        try:
            export = ExportedAdmin.objects.get(id=pk, tenant=tenant)
        except ExportedAdmin.DoesNotExist:
            return Response({'error': 'Export not found'}, status=404)
        
        return Response({
            **ExportedAdminSerializer(export).data,
            'code': export.code
        })







