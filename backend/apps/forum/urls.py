from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ForumConfigViewSet, CategoryViewSet, BoardViewSet,
    ThreadViewSet, PostViewSet, ReportViewSet, UserBanViewSet,
    PublicForumView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'boards', BoardViewSet, basename='board')
router.register(r'threads', ThreadViewSet, basename='thread')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'bans', UserBanViewSet, basename='ban')

urlpatterns = [
    path('', include(router.urls)),
    
    # Config
    path('config/', ForumConfigViewSet.as_view({'get': 'config'}), name='forum-config'),
    path('config/update/', ForumConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='forum-config-update'),
    
    # Public API (for customer's apps)
    path('public/boards/', PublicForumView.as_view(), {'action': 'boards'}, name='public-boards'),
    path('public/boards/<uuid:id>/', PublicForumView.as_view(), {'action': 'board'}, name='public-board'),
    path('public/threads/<uuid:id>/', PublicForumView.as_view(), {'action': 'thread'}, name='public-thread'),
    path('public/threads/create/', PublicForumView.as_view(), {'action': 'create_thread'}, name='public-create-thread'),
    path('public/threads/<uuid:id>/reply/', PublicForumView.as_view(), {'action': 'reply'}, name='public-reply'),
    path('public/posts/<uuid:id>/react/', PublicForumView.as_view(), {'action': 'react'}, name='public-react'),
    path('public/report/', PublicForumView.as_view(), {'action': 'report'}, name='public-report'),
]






