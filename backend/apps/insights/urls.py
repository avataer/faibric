"""
URL patterns for Customer Insights API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    InputLoggingViewSet,
    InsightsDashboardView,
    CustomerInputAdminViewSet,
    AdminFixViewSet,
    CustomerHealthViewSet,
    InsightReportViewSet,
    CustomerFixView,
)

router = DefaultRouter()

# Customer-facing (logging inputs)
router.register(r'inputs', InputLoggingViewSet, basename='input-logging')

# Admin-only
router.register(r'admin/inputs', CustomerInputAdminViewSet, basename='admin-inputs')
router.register(r'admin/fixes', AdminFixViewSet, basename='admin-fixes')
router.register(r'admin/health', CustomerHealthViewSet, basename='customer-health')
router.register(r'admin/reports', InsightReportViewSet, basename='insight-reports')

urlpatterns = [
    path('', include(router.urls)),
    
    # Admin dashboard
    path('admin/dashboard/', InsightsDashboardView.as_view(), name='insights-dashboard'),
    
    # Customer view of their fixes
    path('fixes/<uuid:fix_id>/', CustomerFixView.as_view(), name='customer-fix'),
]









