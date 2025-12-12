"""
URL patterns for marketing analysis API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CompetitorViewSet,
    CompetitorChangeViewSet,
    KeywordViewSet,
    MarketingConfigViewSet,
    MarketingDashboardViewSet,
    MarketingReportViewSet,
    ReportTemplateViewSet,
)

router = DefaultRouter()
router.register(r'config', MarketingConfigViewSet, basename='marketing-config')
router.register(r'competitors', CompetitorViewSet, basename='competitors')
router.register(r'changes', CompetitorChangeViewSet, basename='competitor-changes')
router.register(r'keywords', KeywordViewSet, basename='keywords')
router.register(r'reports', MarketingReportViewSet, basename='marketing-reports')
router.register(r'templates', ReportTemplateViewSet, basename='report-templates')
router.register(r'dashboard', MarketingDashboardViewSet, basename='marketing-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]









