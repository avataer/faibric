from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.tenants.permissions import TenantPermission
from .models import (
    ForumConfig, Category, Board, Thread, Post,
    Report, UserBan
)
from .serializers import (
    ForumConfigSerializer, CategorySerializer,
    BoardSerializer, BoardCreateSerializer,
    ThreadListSerializer, ThreadDetailSerializer, ThreadCreateSerializer,
    PostSerializer, PostCreateSerializer,
    ReportSerializer, ReportCreateSerializer,
    UserBanSerializer, ReactSerializer
)
from .services import ForumService


class ForumConfigViewSet(viewsets.ViewSet):
    """ViewSet for managing forum configuration."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_config(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        config, _ = ForumConfig.objects.get_or_create(tenant=tenant)
        return config
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """Get forum configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = ForumConfigSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_config(self, request):
        """Update forum configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = ForumConfigSerializer(
            config,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing categories."""
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Category.objects.none()
        return Category.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class BoardViewSet(viewsets.ModelViewSet):
    """ViewSet for managing boards."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BoardCreateSerializer
        return BoardSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Board.objects.none()
        return Board.objects.filter(tenant=tenant).select_related('category')
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['get'])
    def threads(self, request, pk=None):
        """Get threads in a board."""
        board = self.get_object()
        page = int(request.query_params.get('page', 1))
        
        tenant = getattr(request, 'tenant', None)
        service = ForumService(tenant)
        threads = service.get_threads(board, page)
        
        serializer = ThreadListSerializer(threads, many=True)
        return Response(serializer.data)


class ThreadViewSet(viewsets.ModelViewSet):
    """ViewSet for managing threads."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ThreadDetailSerializer
        if self.action == 'create':
            return ThreadCreateSerializer
        return ThreadListSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Thread.objects.none()
        return Thread.objects.filter(
            board__tenant=tenant,
            is_deleted=False
        ).select_related('board')
    
    def retrieve(self, request, *args, **kwargs):
        """Get thread with posts."""
        thread = self.get_object()
        
        tenant = getattr(request, 'tenant', None)
        service = ForumService(tenant)
        
        # Get posts
        posts = service.get_posts(thread)
        
        serializer = ThreadDetailSerializer(thread, context={'request': request})
        data = serializer.data
        data['posts'] = PostSerializer(
            posts, many=True, context={'request': request}
        ).data
        
        return Response(data)
    
    def create(self, request, *args, **kwargs):
        """Create a new thread."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        board_id = request.data.get('board_id')
        if not board_id:
            return Response({'error': 'board_id required'}, status=400)
        
        try:
            board = Board.objects.get(id=board_id, tenant=tenant, is_active=True)
        except Board.DoesNotExist:
            return Response({'error': 'Board not found'}, status=404)
        
        serializer = ThreadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        service = ForumService(tenant)
        
        try:
            thread = service.create_thread(
                board=board,
                title=data['title'],
                content=data['content'],
                author_id=data['author_id'],
                author_name=data['author_name'],
                author_avatar=data.get('author_avatar', '')
            )
            
            return Response(
                ThreadDetailSerializer(thread).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """Add a reply to the thread."""
        thread = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        author_id = request.headers.get('X-User-Id') or request.data.get('author_id')
        author_name = request.data.get('author_name', 'Anonymous')
        
        if not author_id:
            return Response({'error': 'author_id required'}, status=400)
        
        service = ForumService(tenant)
        
        try:
            post = service.create_post(
                thread=thread,
                content=data['content'],
                author_id=author_id,
                author_name=author_name,
                author_avatar=request.data.get('author_avatar', ''),
                parent_id=str(data.get('parent_id')) if data.get('parent_id') else None
            )
            
            return Response(
                PostSerializer(post, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """Lock/unlock thread."""
        thread = self.get_object()
        thread.is_locked = not thread.is_locked
        thread.save(update_fields=['is_locked'])
        return Response({'is_locked': thread.is_locked})
    
    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Pin/unpin thread."""
        thread = self.get_object()
        thread.is_pinned = not thread.is_pinned
        thread.save(update_fields=['is_pinned'])
        return Response({'is_pinned': thread.is_pinned})


class PostViewSet(viewsets.ModelViewSet):
    """ViewSet for managing posts."""
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Post.objects.none()
        return Post.objects.filter(
            thread__board__tenant=tenant,
            is_deleted=False
        )
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """React to a post."""
        post = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        serializer = ReactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = request.headers.get('X-User-Id') or request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=400)
        
        service = ForumService(tenant)
        post = service.react_to_post(
            post=post,
            user_id=user_id,
            reaction_type=serializer.validated_data['reaction_type']
        )
        
        return Response({
            'upvotes': post.upvotes,
            'downvotes': post.downvotes,
            'score': post.score
        })


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing reports."""
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Report.objects.none()
        return Report.objects.filter(tenant=tenant)
    
    def create(self, request, *args, **kwargs):
        """Create a report."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        reporter_id = request.headers.get('X-User-Id') or request.data.get('reporter_id')
        reporter_name = request.data.get('reporter_name', 'Anonymous')
        
        if not reporter_id:
            return Response({'error': 'reporter_id required'}, status=400)
        
        thread = None
        post = None
        
        if data.get('thread_id'):
            try:
                thread = Thread.objects.get(id=data['thread_id'])
            except Thread.DoesNotExist:
                return Response({'error': 'Thread not found'}, status=404)
        
        if data.get('post_id'):
            try:
                post = Post.objects.get(id=data['post_id'])
            except Post.DoesNotExist:
                return Response({'error': 'Post not found'}, status=404)
        
        service = ForumService(tenant)
        report = service.create_report(
            reporter_id=reporter_id,
            reporter_name=reporter_name,
            reason=data['reason'],
            description=data.get('description', ''),
            thread=thread,
            post=post
        )
        
        return Response(
            ReportSerializer(report).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a report."""
        report = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        resolved_by = request.data.get('resolved_by', 'admin')
        status_val = request.data.get('status', 'resolved')
        notes = request.data.get('notes', '')
        
        service = ForumService(tenant)
        report = service.resolve_report(report, resolved_by, status_val, notes)
        
        return Response(ReportSerializer(report).data)


class UserBanViewSet(viewsets.ModelViewSet):
    """ViewSet for managing bans."""
    serializer_class = UserBanSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return UserBan.objects.none()
        return UserBan.objects.filter(tenant=tenant)
    
    def create(self, request, *args, **kwargs):
        """Ban a user."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        service = ForumService(tenant)
        
        ban = service.ban_user(
            user_id=request.data.get('user_id'),
            user_name=request.data.get('user_name'),
            reason=request.data.get('reason'),
            banned_by=request.data.get('banned_by', 'admin'),
            is_permanent=request.data.get('is_permanent', False),
            expires_at=request.data.get('expires_at')
        )
        
        return Response(
            UserBanSerializer(ban).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def unban(self, request, pk=None):
        """Unban a user."""
        ban = self.get_object()
        tenant = getattr(request, 'tenant', None)
        
        service = ForumService(tenant)
        service.unban_user(ban.user_id)
        
        return Response({'success': True})


# ============= PUBLIC API (for customer's apps) =============

class PublicForumView(APIView):
    """Public endpoint for forum access."""
    permission_classes = [AllowAny]
    
    def _get_tenant(self, request):
        from apps.projects.models import Project
        
        app_id = request.headers.get('X-Faibric-App-Id')
        if not app_id:
            return None
        
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            return project.tenant
        except Project.DoesNotExist:
            return None
    
    def get(self, request, action=None, **kwargs):
        """Handle GET requests."""
        tenant = self._get_tenant(request)
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        service = ForumService(tenant)
        
        if action == 'boards':
            boards = service.get_boards()
            return Response(BoardSerializer(boards, many=True).data)
        
        elif action == 'board':
            board_id = kwargs.get('id')
            board = service.get_board(board_id)
            if not board:
                return Response({'error': 'Board not found'}, status=404)
            
            page = int(request.query_params.get('page', 1))
            threads = service.get_threads(board, page)
            
            return Response({
                'board': BoardSerializer(board).data,
                'threads': ThreadListSerializer(threads, many=True).data
            })
        
        elif action == 'thread':
            thread_id = kwargs.get('id')
            thread = service.get_thread(thread_id)
            if not thread:
                return Response({'error': 'Thread not found'}, status=404)
            
            posts = service.get_posts(thread)
            
            return Response({
                'thread': ThreadDetailSerializer(thread).data,
                'posts': PostSerializer(
                    posts, many=True, context={'request': request}
                ).data
            })
        
        return Response({'error': 'Unknown action'}, status=400)
    
    def post(self, request, action=None, **kwargs):
        """Handle POST requests."""
        tenant = self._get_tenant(request)
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        service = ForumService(tenant)
        user_id = request.headers.get('X-User-Id')
        
        if action == 'create_thread':
            board_id = request.data.get('board_id')
            if not board_id:
                return Response({'error': 'board_id required'}, status=400)
            
            board = service.get_board(board_id)
            if not board:
                return Response({'error': 'Board not found'}, status=404)
            
            try:
                thread = service.create_thread(
                    board=board,
                    title=request.data.get('title'),
                    content=request.data.get('content'),
                    author_id=user_id or request.data.get('author_id'),
                    author_name=request.data.get('author_name', 'Anonymous'),
                    author_avatar=request.data.get('author_avatar', '')
                )
                return Response(
                    ThreadDetailSerializer(thread).data,
                    status=status.HTTP_201_CREATED
                )
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        
        elif action == 'reply':
            thread_id = kwargs.get('id')
            thread = service.get_thread(thread_id)
            if not thread:
                return Response({'error': 'Thread not found'}, status=404)
            
            try:
                post = service.create_post(
                    thread=thread,
                    content=request.data.get('content'),
                    author_id=user_id or request.data.get('author_id'),
                    author_name=request.data.get('author_name', 'Anonymous'),
                    author_avatar=request.data.get('author_avatar', ''),
                    parent_id=request.data.get('parent_id')
                )
                return Response(
                    PostSerializer(post, context={'request': request}).data,
                    status=status.HTTP_201_CREATED
                )
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        
        elif action == 'react':
            post_id = kwargs.get('id')
            try:
                post = Post.objects.get(id=post_id)
            except Post.DoesNotExist:
                return Response({'error': 'Post not found'}, status=404)
            
            if not user_id:
                return Response({'error': 'X-User-Id required'}, status=400)
            
            post = service.react_to_post(
                post=post,
                user_id=user_id,
                reaction_type=request.data.get('reaction_type', 'upvote')
            )
            
            return Response({
                'upvotes': post.upvotes,
                'downvotes': post.downvotes,
                'score': post.score
            })
        
        elif action == 'report':
            try:
                service.create_report(
                    reporter_id=user_id or request.data.get('reporter_id'),
                    reporter_name=request.data.get('reporter_name', 'Anonymous'),
                    reason=request.data.get('reason'),
                    description=request.data.get('description', ''),
                    thread=Thread.objects.get(id=request.data['thread_id']) if request.data.get('thread_id') else None,
                    post=Post.objects.get(id=request.data['post_id']) if request.data.get('post_id') else None
                )
                return Response({'success': True})
            except Exception as e:
                return Response({'error': str(e)}, status=400)
        
        return Response({'error': 'Unknown action'}, status=400)







