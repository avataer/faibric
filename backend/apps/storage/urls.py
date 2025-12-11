from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StorageConfigViewSet, FolderViewSet, FileViewSet,
    StorageUsageView, PublicStorageView
)

router = DefaultRouter()
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'files', FileViewSet, basename='file')

urlpatterns = [
    path('', include(router.urls)),
    
    # Config
    path('config/', StorageConfigViewSet.as_view({'get': 'config'}), name='storage-config'),
    path('config/update/', StorageConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='storage-config-update'),
    
    # Usage
    path('usage/', StorageUsageView.as_view(), name='storage-usage'),
    
    # Public API (for customer's apps)
    path('public/list/', PublicStorageView.as_view(), {'action': 'list'}, name='public-storage-list'),
    path('public/upload/', PublicStorageView.as_view(), {'action': 'upload'}, name='public-storage-upload'),
    path('public/download/<uuid:file_id>/', PublicStorageView.as_view(), {'action': 'download'}, name='public-storage-download'),
    path('public/url/<uuid:file_id>/', PublicStorageView.as_view(), {'action': 'url'}, name='public-storage-url'),
    path('public/delete/<uuid:file_id>/', PublicStorageView.as_view(), {'action': 'delete'}, name='public-storage-delete'),
]







