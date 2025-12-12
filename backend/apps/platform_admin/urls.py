"""
URL patterns for Faibric Platform Admin.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PlatformDashboardView,
    PlatformMetricsViewSet,
    FunnelViewSet,
    AdCampaignViewSet,
    SystemHealthView,
    TenantListView,
)

router = DefaultRouter()
router.register(r'metrics', PlatformMetricsViewSet, basename='platform-metrics')
router.register(r'funnels', FunnelViewSet, basename='funnels')
router.register(r'ads', AdCampaignViewSet, basename='ad-campaigns')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', PlatformDashboardView.as_view(), name='platform-dashboard'),
    path('health/', SystemHealthView.as_view(), name='system-health'),
    path('tenants/', TenantListView.as_view(), name='tenant-list'),
]









