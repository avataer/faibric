from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from apps.tenants.permissions import TenantPermission
from .models import (
    CabinetConfig, EndUser, SupportTicket,
    TicketMessage, Notification, Activity
)
from .serializers import (
    CabinetConfigSerializer, EndUserSerializer, EndUserProfileUpdateSerializer,
    RegisterSerializer, LoginSerializer, ChangePasswordSerializer,
    PasswordResetRequestSerializer, PasswordResetSerializer,
    SupportTicketSerializer, SupportTicketListSerializer,
    CreateTicketSerializer, ReplyToTicketSerializer,
    NotificationSerializer, ActivitySerializer, DashboardSerializer
)
from .services import CabinetAuthService, CabinetService


class CabinetConfigViewSet(viewsets.ViewSet):
    """ViewSet for cabinet configuration (admin)."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_config(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        config, _ = CabinetConfig.objects.get_or_create(tenant=tenant)
        return config
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        return Response(CabinetConfigSerializer(config).data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_config(self, request):
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = CabinetConfigSerializer(
            config, data=request.data, partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ============= PUBLIC API (for customer's apps) =============

class PublicCabinetAuthView(APIView):
    """Public authentication endpoints for end-users."""
    authentication_classes = []  # Bypass JWT auth
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
    
    def post(self, request, action=None):
        tenant = self._get_tenant(request)
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        auth_service = CabinetAuthService(tenant)
        
        if action == 'register':
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            try:
                user = auth_service.register(
                    email=data['email'],
                    password=data['password'],
                    first_name=data.get('first_name', ''),
                    last_name=data.get('last_name', '')
                )
                
                # Auto-login if not requiring verification
                if user.is_verified:
                    result = auth_service.login(
                        email=data['email'],
                        password=data['password'],
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    return Response(result, status=status.HTTP_201_CREATED)
                
                return Response({
                    'message': 'Registration successful. Please verify your email.',
                    'user_id': str(user.id)
                }, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        
        elif action == 'login':
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            try:
                result = auth_service.login(
                    email=data['email'],
                    password=data['password'],
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                if not result:
                    return Response({'error': 'Invalid credentials'}, status=401)
                
                return Response(result)
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        
        elif action == 'logout':
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            auth_service.logout(token)
            return Response({'success': True})
        
        elif action == 'verify-email':
            token = request.data.get('token')
            if not token:
                return Response({'error': 'Token required'}, status=400)
            
            if auth_service.verify_email(token):
                return Response({'success': True})
            return Response({'error': 'Invalid or expired token'}, status=400)
        
        elif action == 'request-password-reset':
            serializer = PasswordResetRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            auth_service.request_password_reset(serializer.validated_data['email'])
            return Response({'message': 'If the email exists, a reset link has been sent.'})
        
        elif action == 'reset-password':
            serializer = PasswordResetSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            try:
                if auth_service.reset_password(data['token'], data['new_password']):
                    return Response({'success': True})
                return Response({'error': 'Invalid or expired token'}, status=400)
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        
        return Response({'error': 'Unknown action'}, status=400)


class PublicCabinetView(APIView):
    """Public cabinet endpoints for end-users."""
    authentication_classes = []  # Bypass JWT auth, we use custom cabinet auth
    permission_classes = [AllowAny]
    
    def _get_context(self, request):
        from apps.projects.models import Project
        
        app_id = request.headers.get('X-Faibric-App-Id')
        if not app_id:
            return None, None, None
        
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            tenant = project.tenant
        except Project.DoesNotExist:
            return None, None, None
        
        # Validate session token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return tenant, None, None
        
        auth_service = CabinetAuthService(tenant)
        user = auth_service.validate_session(token)
        
        return tenant, user, CabinetService(tenant, user) if user else None
    
    def get(self, request, action=None, **kwargs):
        tenant, user, service = self._get_context(request)
        
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        if action == 'config':
            config, _ = CabinetConfig.objects.get_or_create(tenant=tenant)
            return Response({
                'cabinet_name': config.cabinet_name,
                'logo_url': config.logo_url,
                'primary_color': config.primary_color,
                'orders_enabled': config.orders_enabled,
                'subscriptions_enabled': config.subscriptions_enabled,
                'files_enabled': config.files_enabled,
                'support_enabled': config.support_enabled,
                'notifications_enabled': config.notifications_enabled,
                'allow_registration': config.allow_registration
            })
        
        # Below actions require authentication
        if not user or not service:
            return Response({'error': 'Authentication required'}, status=401)
        
        if action == 'me':
            return Response(EndUserSerializer(user).data)
        
        elif action == 'dashboard':
            data = service.get_dashboard_data()
            return Response(data)
        
        elif action == 'activities':
            limit = int(request.query_params.get('limit', 20))
            activities = service.get_activities(limit)
            return Response(ActivitySerializer(activities, many=True).data)
        
        elif action == 'notifications':
            unread_only = request.query_params.get('unread', 'false').lower() == 'true'
            notifications = service.get_notifications(unread_only)
            return Response(NotificationSerializer(notifications, many=True).data)
        
        elif action == 'tickets':
            status_filter = request.query_params.get('status')
            tickets = service.get_tickets(status_filter)
            return Response(SupportTicketListSerializer(tickets, many=True).data)
        
        elif action == 'ticket':
            ticket_id = kwargs.get('id')
            ticket = service.get_ticket(ticket_id)
            if not ticket:
                return Response({'error': 'Ticket not found'}, status=404)
            return Response(SupportTicketSerializer(ticket).data)
        
        elif action == 'orders':
            orders = service.get_orders()
            from apps.checkout.serializers import OrderSerializer
            return Response(OrderSerializer(orders, many=True).data)
        
        elif action == 'order':
            order_id = kwargs.get('id')
            order = service.get_order(order_id)
            if not order:
                return Response({'error': 'Order not found'}, status=404)
            from apps.checkout.serializers import OrderSerializer
            return Response(OrderSerializer(order).data)
        
        return Response({'error': 'Unknown action'}, status=400)
    
    def post(self, request, action=None, **kwargs):
        tenant, user, service = self._get_context(request)
        
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        if not user or not service:
            return Response({'error': 'Authentication required'}, status=401)
        
        if action == 'update-profile':
            serializer = EndUserProfileUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            user = service.update_profile(**serializer.validated_data)
            return Response(EndUserSerializer(user).data)
        
        elif action == 'change-password':
            serializer = ChangePasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            try:
                service.change_password(data['current_password'], data['new_password'])
                return Response({'success': True})
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        
        elif action == 'create-ticket':
            serializer = CreateTicketSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            ticket = service.create_ticket(
                subject=data['subject'],
                message=data['message'],
                category=data.get('category', ''),
                priority=data.get('priority', 'medium'),
                related_order_id=data.get('related_order_id', '')
            )
            return Response(
                SupportTicketSerializer(ticket).data,
                status=status.HTTP_201_CREATED
            )
        
        elif action == 'reply-ticket':
            ticket_id = kwargs.get('id')
            ticket = service.get_ticket(ticket_id)
            if not ticket:
                return Response({'error': 'Ticket not found'}, status=404)
            
            serializer = ReplyToTicketSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            try:
                service.reply_to_ticket(ticket, serializer.validated_data['message'])
                return Response(SupportTicketSerializer(ticket).data)
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        
        elif action == 'read-notification':
            notification_id = kwargs.get('id')
            if service.mark_notification_read(notification_id):
                return Response({'success': True})
            return Response({'error': 'Notification not found'}, status=404)
        
        elif action == 'read-all-notifications':
            count = service.mark_all_notifications_read()
            return Response({'marked_read': count})
        
        return Response({'error': 'Unknown action'}, status=400)

