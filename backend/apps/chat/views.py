from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.tenants.permissions import TenantPermission
from .models import ChatWidget, ChatSession, ChatMessage, LLMConfig
from .serializers import (
    LLMConfigSerializer, LLMConfigUpdateSerializer,
    ChatWidgetSerializer, ChatWidgetCreateSerializer,
    ChatSessionSerializer, ChatSessionListSerializer,
    ChatMessageSerializer,
    PublicWidgetConfigSerializer, StartSessionSerializer,
    SendMessageSerializer, RateMessageSerializer, EscalateSerializer
)
from .services import ChatService, WidgetService
from .llm_providers import get_available_models


class LLMConfigViewSet(viewsets.ViewSet):
    """ViewSet for managing LLM configuration."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_config(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        config, _ = LLMConfig.objects.get_or_create(tenant=tenant)
        return config
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """Get LLM configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = LLMConfigSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_config(self, request):
        """Update LLM configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = LLMConfigUpdateSerializer(
            config,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(LLMConfigSerializer(config).data)
    
    @action(detail=False, methods=['get'])
    def models(self, request):
        """Get available LLM models."""
        return Response(get_available_models())


class ChatWidgetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chat widgets."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ChatWidgetCreateSerializer
        return ChatWidgetSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return ChatWidget.objects.none()
        return ChatWidget.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
    
    def create(self, request, *args, **kwargs):
        """Override create to return full widget serializer with ID."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return full serializer with ID and embed_code
        widget = serializer.instance
        output_serializer = ChatWidgetSerializer(widget)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def embed_code(self, request, pk=None):
        """Get embed code for a widget."""
        widget = self.get_object()
        return Response({
            'embed_code': WidgetService.get_widget_embed_code(widget)
        })
    
    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get sessions for a widget."""
        widget = self.get_object()
        sessions = widget.sessions.all()[:50]
        serializer = ChatSessionListSerializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get widget statistics."""
        widget = self.get_object()
        from django.db.models import Avg, Count, Sum
        from django.utils import timezone
        
        today = timezone.now().date()
        week_ago = today - timezone.timedelta(days=7)
        
        sessions = widget.sessions.all()
        recent_sessions = sessions.filter(started_at__date__gte=week_ago)
        
        return Response({
            'total_sessions': sessions.count(),
            'active_sessions': sessions.filter(is_active=True).count(),
            'escalated_sessions': sessions.filter(escalated=True).count(),
            'sessions_this_week': recent_sessions.count(),
            'avg_messages_per_session': sessions.annotate(
                msg_count=Count('messages')
            ).aggregate(avg=Avg('msg_count'))['avg'] or 0,
            'total_messages': ChatMessage.objects.filter(
                session__widget=widget
            ).count(),
        })


class ChatSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing chat sessions."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChatSessionListSerializer
        return ChatSessionSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return ChatSession.objects.none()
        return ChatSession.objects.filter(
            widget__tenant=tenant
        ).annotate(
            message_count=Count('messages')
        )


# Public API views (for widget clients)

class PublicWidgetView(APIView):
    """Public endpoint to get widget configuration."""
    permission_classes = [AllowAny]
    
    def get(self, request, widget_id):
        try:
            widget = ChatWidget.objects.get(id=widget_id, is_active=True)
            config = WidgetService.get_widget_config(widget)
            return Response(config)
        except ChatWidget.DoesNotExist:
            return Response(
                {'error': 'Widget not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PublicChatView(APIView):
    """Public endpoint for chat interactions."""
    permission_classes = [AllowAny]
    
    def post(self, request, widget_id, action):
        """Handle chat actions."""
        try:
            widget = ChatWidget.objects.get(id=widget_id, is_active=True)
        except ChatWidget.DoesNotExist:
            return Response(
                {'error': 'Widget not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        service = ChatService(widget)
        
        if action == 'start':
            return self._start_session(request, service)
        elif action == 'send':
            return self._send_message(request, service)
        elif action == 'rate':
            return self._rate_message(request, service)
        elif action == 'escalate':
            return self._escalate_session(request, service)
        elif action == 'end':
            return self._end_session(request, service)
        else:
            return Response(
                {'error': 'Unknown action'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _start_session(self, request, service):
        """Start a new chat session."""
        serializer = StartSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Get client info
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        if not ip:
            ip = request.META.get('REMOTE_ADDR')
        
        session = service.get_or_create_session(
            visitor_id=data['visitor_id'],
            page_url=data.get('page_url', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=ip,
            metadata=data.get('metadata', {})
        )
        
        # Update user info if provided
        if data.get('user_email'):
            session.user_email = data['user_email']
        if data.get('user_name'):
            session.user_name = data['user_name']
        session.save()
        
        return Response({
            'session_id': str(session.id),
            'messages': service.get_session_messages(session),
            'welcome_message': service.widget.welcome_message
        })
    
    def _send_message(self, request, service):
        """Send a message and get AI response."""
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            session = ChatSession.objects.get(
                id=data['session_id'],
                widget=service.widget,
                is_active=True
            )
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found or ended'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            response_msg = service.send_message(session, data['message'])
            
            return Response({
                'message': {
                    'id': str(response_msg.id),
                    'role': response_msg.role,
                    'content': response_msg.content,
                    'timestamp': response_msg.created_at.isoformat()
                }
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _rate_message(self, request, service):
        """Rate a message."""
        serializer = RateMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        service.rate_message(str(data['message_id']), data['helpful'])
        return Response({'success': True})
    
    def _escalate_session(self, request, service):
        """Escalate to human support."""
        serializer = EscalateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            session = ChatSession.objects.get(
                id=data['session_id'],
                widget=service.widget
            )
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        service.escalate_session(session, data.get('reason', ''))
        return Response({
            'success': True,
            'message': 'Your request has been escalated to our support team.'
        })
    
    def _end_session(self, request, service):
        """End a chat session."""
        session_id = request.data.get('session_id')
        if not session_id:
            return Response(
                {'error': 'session_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = ChatSession.objects.get(
                id=session_id,
                widget=service.widget
            )
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        service.end_session(session)
        return Response({'success': True})


# Count for models
from django.db.models import Count

