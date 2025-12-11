from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LLMConfigViewSet, ChatWidgetViewSet, ChatSessionViewSet,
    PublicWidgetView, PublicChatView
)

router = DefaultRouter()
router.register(r'widgets', ChatWidgetViewSet, basename='chat-widget')
router.register(r'sessions', ChatSessionViewSet, basename='chat-session')

urlpatterns = [
    path('', include(router.urls)),
    
    # LLM config endpoints
    path('llm/config/', LLMConfigViewSet.as_view({'get': 'config'}), name='llm-config'),
    path('llm/config/update/', LLMConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='llm-config-update'),
    path('llm/models/', LLMConfigViewSet.as_view({'get': 'models'}), name='llm-models'),
    
    # Public widget endpoints (for embedded widgets)
    path('public/<uuid:widget_id>/', PublicWidgetView.as_view(), name='public-widget-config'),
    path('public/<uuid:widget_id>/<str:action>/', PublicChatView.as_view(), name='public-chat'),
]






