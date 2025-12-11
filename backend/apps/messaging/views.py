from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from apps.tenants.permissions import TenantPermission
from .models import (
    MessagingConfig, MessageTemplate, Message,
    InAppNotification, PushToken
)
from .serializers import (
    MessagingConfigSerializer, MessagingConfigUpdateSerializer,
    MessageTemplateSerializer, MessageSerializer,
    InAppNotificationSerializer, PushTokenSerializer,
    SendMessageSerializer, SendEmailSerializer, SendSMSSerializer,
    SendPushSerializer, SendInAppSerializer, RegisterPushTokenSerializer,
    PublicNotificationListSerializer, MarkNotificationReadSerializer,
    PublicPushTokenSerializer
)
from .services import MessagingService


class MessagingConfigViewSet(viewsets.ViewSet):
    """ViewSet for managing messaging configuration."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_config(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        config, _ = MessagingConfig.objects.get_or_create(tenant=tenant)
        return config
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """Get messaging configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = MessagingConfigSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_config(self, request):
        """Update messaging configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = MessagingConfigUpdateSerializer(
            config,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(MessagingConfigSerializer(config).data)


class MessageTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing message templates."""
    serializer_class = MessageTemplateSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return MessageTemplate.objects.none()
        return MessageTemplate.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Preview template with sample data."""
        template = self.get_object()
        context = request.data.get('context', {})
        rendered = template.render(context)
        return Response(rendered)


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing sent messages."""
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Message.objects.none()
        return Message.objects.filter(tenant=tenant)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get message statistics."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        from django.db.models import Count
        from django.utils import timezone
        
        today = timezone.now().date()
        week_ago = today - timezone.timedelta(days=7)
        
        messages = Message.objects.filter(tenant=tenant)
        recent = messages.filter(created_at__date__gte=week_ago)
        
        by_channel = recent.values('channel').annotate(count=Count('id'))
        by_status = recent.values('status').annotate(count=Count('id'))
        
        return Response({
            'total_messages': messages.count(),
            'messages_this_week': recent.count(),
            'by_channel': list(by_channel),
            'by_status': list(by_status),
        })


class SendMessageView(APIView):
    """API endpoint for sending messages."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def post(self, request):
        """Send a message across channels."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        service = MessagingService(tenant)
        
        results = service.send(
            recipient=data['recipient'],
            channels=data['channels'],
            template_slug=data.get('template_slug'),
            subject=data.get('subject', ''),
            body=data.get('body', ''),
            body_html=data.get('body_html', ''),
            context=data.get('context', {}),
            scheduled_at=data.get('scheduled_at')
        )
        
        return Response({
            'success': True,
            'messages': {
                channel: MessageSerializer(msg).data
                for channel, msg in results.items()
            }
        })


class SendEmailView(APIView):
    """Send a single email."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        service = MessagingService(tenant)
        message = service.send_email(**data)
        
        return Response({
            'success': message.status == 'sent',
            'message': MessageSerializer(message).data
        })


class SendSMSView(APIView):
    """Send a single SMS."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = SendSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        service = MessagingService(tenant)
        message = service.send_sms(**data)
        
        return Response({
            'success': message.status == 'sent',
            'message': MessageSerializer(message).data
        })


class SendPushView(APIView):
    """Send a push notification."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = SendPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        service = MessagingService(tenant)
        message = service.send_push(**data)
        
        return Response({
            'success': message.status == 'sent',
            'message': MessageSerializer(message).data
        })


class SendInAppView(APIView):
    """Create an in-app notification."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = SendInAppSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        service = MessagingService(tenant)
        notification = service.send_in_app(**data)
        
        return Response({
            'success': True,
            'notification': InAppNotificationSerializer(notification).data
        })


class PushTokenViewSet(viewsets.ModelViewSet):
    """ViewSet for managing push tokens."""
    serializer_class = PushTokenSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return PushToken.objects.none()
        return PushToken.objects.filter(tenant=tenant)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a push token."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = RegisterPushTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        service = MessagingService(tenant)
        token = service.register_push_token(**data)
        
        return Response(PushTokenSerializer(token).data)


# ============= PUBLIC API (for customer's apps) =============

class PublicNotificationsView(APIView):
    """Public endpoint for getting notifications."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get notifications for a user."""
        from apps.projects.models import Project
        
        # Authenticate via app ID
        app_id = request.headers.get('X-Faibric-App-Id')
        user_id = request.headers.get('X-User-Id')
        
        if not app_id or not user_id:
            return Response(
                {'error': 'X-Faibric-App-Id and X-User-Id headers required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            tenant = project.tenant
        except Project.DoesNotExist:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        if not tenant:
            return Response({'error': 'App has no tenant'}, status=400)
        
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        limit = min(int(request.query_params.get('limit', 50)), 100)
        
        service = MessagingService(tenant)
        notifications = service.get_notifications(user_id, unread_only, limit)
        
        return Response({
            'notifications': InAppNotificationSerializer(notifications, many=True).data,
            'unread_count': InAppNotification.objects.filter(
                tenant=tenant, user_id=user_id, is_read=False
            ).count()
        })
    
    def post(self, request):
        """Mark notification as read."""
        from apps.projects.models import Project
        
        app_id = request.headers.get('X-Faibric-App-Id')
        if not app_id:
            return Response({'error': 'X-Faibric-App-Id header required'}, status=400)
        
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            tenant = project.tenant
        except Project.DoesNotExist:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        if not tenant:
            return Response({'error': 'App has no tenant'}, status=400)
        
        action = request.data.get('action')
        service = MessagingService(tenant)
        
        if action == 'mark_read':
            notification_id = request.data.get('notification_id')
            success = service.mark_notification_read(notification_id)
            return Response({'success': success})
        
        elif action == 'mark_all_read':
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({'error': 'user_id required'}, status=400)
            count = service.mark_all_read(user_id)
            return Response({'success': True, 'marked_count': count})
        
        return Response({'error': 'Unknown action'}, status=400)


class PublicPushTokenView(APIView):
    """Public endpoint for registering push tokens."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Register a push token."""
        from apps.projects.models import Project
        
        app_id = request.headers.get('X-Faibric-App-Id')
        user_id = request.headers.get('X-User-Id')
        
        if not app_id or not user_id:
            return Response(
                {'error': 'X-Faibric-App-Id and X-User-Id headers required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            tenant = project.tenant
        except Project.DoesNotExist:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        if not tenant:
            return Response({'error': 'App has no tenant'}, status=400)
        
        serializer = PublicPushTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        service = MessagingService(tenant)
        token = service.register_push_token(
            user_id=user_id,
            token=data['token'],
            device_type=data['device_type'],
            device_name=data.get('device_name', '')
        )
        
        return Response({'success': True, 'token_id': str(token.id)})
    
    def delete(self, request):
        """Unregister a push token."""
        from apps.projects.models import Project
        
        app_id = request.headers.get('X-Faibric-App-Id')
        if not app_id:
            return Response({'error': 'X-Faibric-App-Id header required'}, status=400)
        
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            tenant = project.tenant
        except Project.DoesNotExist:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        if not tenant:
            return Response({'error': 'App has no tenant'}, status=400)
        
        token = request.data.get('token')
        if not token:
            return Response({'error': 'token required'}, status=400)
        
        service = MessagingService(tenant)
        success = service.unregister_push_token(token)
        
        return Response({'success': success})






