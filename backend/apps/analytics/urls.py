from django.urls import path, include
from django.http import HttpResponse
from rest_framework.routers import DefaultRouter
from .views import (
    AnalyticsConfigViewSet, TrackEventView, IdentifyUserView,
    EventViewSet, FunnelViewSet, UserProfileViewSet
)

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'funnels', FunnelViewSet, basename='funnel')
router.register(r'users', UserProfileViewSet, basename='user-profile')


def admin_dashboard_view(request):
    """Render the Faibric admin dashboard."""
    from .admin_dashboard import generate_admin_dashboard_html
    return HttpResponse(generate_admin_dashboard_html(), content_type='text/html')


urlpatterns = [
    path('', include(router.urls)),
    
    # FAIBRIC ADMIN DASHBOARD
    path('dashboard/', admin_dashboard_view, name='admin-dashboard'),
    
    # Config endpoints
    path('config/', AnalyticsConfigViewSet.as_view({'get': 'config'}), name='analytics-config'),
    path('config/update/', AnalyticsConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='analytics-config-update'),
    
    # Public tracking endpoints (for customer's apps)
    path('track/', TrackEventView.as_view(), name='analytics-track'),
    path('identify/', IdentifyUserView.as_view(), name='analytics-identify'),
]

