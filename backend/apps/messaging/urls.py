from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MessagingConfigViewSet, MessageTemplateViewSet, MessageViewSet,
    PushTokenViewSet,
    SendMessageView, SendEmailView, SendSMSView, SendPushView, SendInAppView,
    PublicNotificationsView, PublicPushTokenView
)

router = DefaultRouter()
router.register(r'templates', MessageTemplateViewSet, basename='message-template')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'push-tokens', PushTokenViewSet, basename='push-token')

urlpatterns = [
    path('', include(router.urls)),
    
    # Config
    path('config/', MessagingConfigViewSet.as_view({'get': 'config'}), name='messaging-config'),
    path('config/update/', MessagingConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='messaging-config-update'),
    
    # Send endpoints
    path('send/', SendMessageView.as_view(), name='send-message'),
    path('send/email/', SendEmailView.as_view(), name='send-email'),
    path('send/sms/', SendSMSView.as_view(), name='send-sms'),
    path('send/push/', SendPushView.as_view(), name='send-push'),
    path('send/in-app/', SendInAppView.as_view(), name='send-in-app'),
    
    # Public API (for customer's apps)
    path('public/notifications/', PublicNotificationsView.as_view(), name='public-notifications'),
    path('public/push-token/', PublicPushTokenView.as_view(), name='public-push-token'),
]






