from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CabinetConfigViewSet,
    PublicCabinetAuthView, PublicCabinetView
)

urlpatterns = [
    # Admin config
    path('config/', CabinetConfigViewSet.as_view({'get': 'config'}), name='cabinet-config'),
    path('config/update/', CabinetConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='cabinet-config-update'),
    
    # Public Auth API
    path('public/auth/register/', PublicCabinetAuthView.as_view(), {'action': 'register'}, name='cabinet-register'),
    path('public/auth/login/', PublicCabinetAuthView.as_view(), {'action': 'login'}, name='cabinet-login'),
    path('public/auth/logout/', PublicCabinetAuthView.as_view(), {'action': 'logout'}, name='cabinet-logout'),
    path('public/auth/verify-email/', PublicCabinetAuthView.as_view(), {'action': 'verify-email'}, name='cabinet-verify-email'),
    path('public/auth/request-password-reset/', PublicCabinetAuthView.as_view(), {'action': 'request-password-reset'}, name='cabinet-request-reset'),
    path('public/auth/reset-password/', PublicCabinetAuthView.as_view(), {'action': 'reset-password'}, name='cabinet-reset-password'),
    
    # Public Cabinet API
    path('public/config/', PublicCabinetView.as_view(), {'action': 'config'}, name='cabinet-public-config'),
    path('public/me/', PublicCabinetView.as_view(), {'action': 'me'}, name='cabinet-me'),
    path('public/dashboard/', PublicCabinetView.as_view(), {'action': 'dashboard'}, name='cabinet-dashboard'),
    path('public/activities/', PublicCabinetView.as_view(), {'action': 'activities'}, name='cabinet-activities'),
    
    # Profile
    path('public/update-profile/', PublicCabinetView.as_view(), {'action': 'update-profile'}, name='cabinet-update-profile'),
    path('public/change-password/', PublicCabinetView.as_view(), {'action': 'change-password'}, name='cabinet-change-password'),
    
    # Notifications
    path('public/notifications/', PublicCabinetView.as_view(), {'action': 'notifications'}, name='cabinet-notifications'),
    path('public/notifications/<uuid:id>/read/', PublicCabinetView.as_view(), {'action': 'read-notification'}, name='cabinet-read-notification'),
    path('public/notifications/read-all/', PublicCabinetView.as_view(), {'action': 'read-all-notifications'}, name='cabinet-read-all-notifications'),
    
    # Support Tickets
    path('public/tickets/', PublicCabinetView.as_view(), {'action': 'tickets'}, name='cabinet-tickets'),
    path('public/tickets/create/', PublicCabinetView.as_view(), {'action': 'create-ticket'}, name='cabinet-create-ticket'),
    path('public/tickets/<uuid:id>/', PublicCabinetView.as_view(), {'action': 'ticket'}, name='cabinet-ticket'),
    path('public/tickets/<uuid:id>/reply/', PublicCabinetView.as_view(), {'action': 'reply-ticket'}, name='cabinet-reply-ticket'),
    
    # Orders
    path('public/orders/', PublicCabinetView.as_view(), {'action': 'orders'}, name='cabinet-orders'),
    path('public/orders/<uuid:id>/', PublicCabinetView.as_view(), {'action': 'order'}, name='cabinet-order'),
]







