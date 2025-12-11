"""
URL patterns for Onboarding API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LandingFlowView,
    EmailFlowView,
    ChangeEmailView,
    VerifyMagicLinkView,
    SessionStatusView,
    SessionAdminViewSet,
    DailyReportViewSet,
    AdminNotificationViewSet,
    FunnelDashboardView,
    ActivityTrackingView,
    FollowUpInputView,
    SessionDetailView,
    InputAnalyticsView,
    AllInputsView,
)

router = DefaultRouter()
router.register(r'admin/sessions', SessionAdminViewSet, basename='admin-sessions')
router.register(r'admin/reports', DailyReportViewSet, basename='daily-reports')
router.register(r'admin/notifications', AdminNotificationViewSet, basename='admin-notifications')

urlpatterns = [
    # Public landing flow
    path('start/', LandingFlowView.as_view(), name='landing-start'),
    path('email/', EmailFlowView.as_view(), name='landing-email'),
    path('email/change/', ChangeEmailView.as_view(), name='landing-change-email'),
    path('verify/', VerifyMagicLinkView.as_view(), name='verify-magic-link'),
    path('status/<str:session_token>/', SessionStatusView.as_view(), name='session-status'),
    
    # Activity tracking (called from frontend)
    path('activity/', ActivityTrackingView.as_view(), name='activity-tracking'),
    path('follow-up/', FollowUpInputView.as_view(), name='follow-up-input'),
    
    # Visual dashboard
    path('admin/funnel/', FunnelDashboardView.as_view(), name='funnel-dashboard'),
    
    # Admin detail views
    path('admin/session/<str:session_token>/', SessionDetailView.as_view(), name='session-detail'),
    path('admin/analytics/', InputAnalyticsView.as_view(), name='input-analytics'),
    path('admin/inputs/', AllInputsView.as_view(), name='all-inputs'),
    
    # Admin endpoints
    path('', include(router.urls)),
]

