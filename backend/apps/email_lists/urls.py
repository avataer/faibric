from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmailConfigViewSet, EmailListViewSet, SubscriberViewSet,
    PublicSubscribeView, PublicUnsubscribeView, PublicConfirmView
)

router = DefaultRouter()
router.register(r'lists', EmailListViewSet, basename='email-list')
router.register(r'subscribers', SubscriberViewSet, basename='subscriber')

urlpatterns = [
    path('', include(router.urls)),
    
    # Config endpoints
    path('config/', EmailConfigViewSet.as_view({'get': 'config'}), name='email-config'),
    path('config/update/', EmailConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='email-config-update'),
    
    # Public endpoints (for customer's apps)
    path('subscribe/', PublicSubscribeView.as_view(), name='public-subscribe'),
    path('unsubscribe/', PublicUnsubscribeView.as_view(), name='public-unsubscribe'),
    path('confirm/', PublicConfirmView.as_view(), name='public-confirm'),
]

