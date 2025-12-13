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


def users_list_view(request):
    """Render the users list page."""
    from .admin_dashboard import generate_users_list_html
    return HttpResponse(generate_users_list_html(), content_type='text/html')


def user_detail_view(request, session_token):
    """Render user detail page with all logs."""
    from .admin_dashboard import generate_user_detail_html
    return HttpResponse(generate_user_detail_html(session_token), content_type='text/html')


def components_view(request):
    """Render components gallery page."""
    from .admin_dashboard import generate_components_html
    return HttpResponse(generate_components_html(), content_type='text/html')


def component_detail_view(request, component_id):
    """Render single component detail page."""
    from .admin_dashboard import generate_component_detail_html
    return HttpResponse(generate_component_detail_html(component_id), content_type='text/html')


def costs_view(request):
    """Render costs analysis page."""
    from .admin_dashboard import generate_costs_html
    return HttpResponse(generate_costs_html(), content_type='text/html')


urlpatterns = [
    path('', include(router.urls)),
    
    # FAIBRIC ADMIN DASHBOARD
    path('dashboard/', admin_dashboard_view, name='admin-dashboard'),
    path('dashboard/users/', users_list_view, name='admin-users'),
    path('dashboard/user/<str:session_token>', user_detail_view, name='admin-user-detail'),
    path('dashboard/components/', components_view, name='admin-components'),
    path('dashboard/component/<str:component_id>', component_detail_view, name='admin-component-detail'),
    path('dashboard/costs/', costs_view, name='admin-costs'),
    
    # Config endpoints
    path('config/', AnalyticsConfigViewSet.as_view({'get': 'config'}), name='analytics-config'),
    path('config/update/', AnalyticsConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='analytics-config-update'),
    
    # Public tracking endpoints (for customer's apps)
    path('track/', TrackEventView.as_view(), name='analytics-track'),
    path('identify/', IdentifyUserView.as_view(), name='analytics-identify'),
]

