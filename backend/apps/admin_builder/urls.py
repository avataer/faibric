from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminBuilderConfigViewSet, AdminPageViewSet, WidgetViewSet,
    DataSourceViewSet, TemplateViewSet, ExportViewSet
)

router = DefaultRouter()
router.register(r'pages', AdminPageViewSet, basename='admin-page')
router.register(r'widgets', WidgetViewSet, basename='widget')
router.register(r'data-sources', DataSourceViewSet, basename='data-source')
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'exports', ExportViewSet, basename='export')

urlpatterns = [
    path('', include(router.urls)),
    
    # Config
    path('config/', AdminBuilderConfigViewSet.as_view({'get': 'config'}), name='admin-builder-config'),
    path('config/update/', AdminBuilderConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='admin-builder-config-update'),
]







