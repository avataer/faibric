from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.tenants.permissions import TenantPermission
from .models import EmailList, Subscriber, EmailConfig
from .serializers import (
    EmailConfigSerializer, EmailConfigUpdateSerializer,
    EmailListSerializer, EmailListCreateSerializer,
    SubscriberSerializer, PublicSubscribeSerializer,
    UnsubscribeSerializer, ConfirmSubscriptionSerializer
)
from .services import EmailListService


class EmailConfigViewSet(viewsets.ViewSet):
    """
    ViewSet for managing email configuration.
    """
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_config(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        config, _ = EmailConfig.objects.get_or_create(tenant=tenant)
        return config
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """Get email configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = EmailConfigSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_config(self, request):
        """Update email configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = EmailConfigUpdateSerializer(
            config,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(EmailConfigSerializer(config).data)


class EmailListViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing email lists.
    """
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EmailListCreateSerializer
        return EmailListSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return EmailList.objects.none()
        return EmailList.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['get'])
    def subscribers(self, request, pk=None):
        """Get subscribers for a list."""
        email_list = self.get_object()
        subscribers = email_list.subscribers.all()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            subscribers = subscribers.filter(status=status_filter)
        
        serializer = SubscriberSerializer(subscribers[:100], many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get list statistics."""
        email_list = self.get_object()
        
        total = email_list.subscribers.count()
        subscribed = email_list.subscribers.filter(status='subscribed').count()
        pending = email_list.subscribers.filter(status='pending').count()
        unsubscribed = email_list.subscribers.filter(status='unsubscribed').count()
        
        return Response({
            'total': total,
            'subscribed': subscribed,
            'pending': pending,
            'unsubscribed': unsubscribed,
            'subscription_rate': (subscribed / total * 100) if total > 0 else 0
        })


class SubscriberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing subscribers.
    """
    serializer_class = SubscriberSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Subscriber.objects.none()
        return Subscriber.objects.filter(email_list__tenant=tenant)


class PublicSubscribeView(APIView):
    """
    Public endpoint for subscribing to email lists.
    Used by customer's apps.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from apps.projects.models import Project
        
        # Get app/tenant from header
        app_id = request.headers.get('X-Faibric-App-Id')
        if not app_id:
            return Response(
                {'error': 'X-Faibric-App-Id header required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            tenant = project.tenant
        except Project.DoesNotExist:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        if not tenant:
            return Response({'error': 'App has no tenant'}, status=400)
        
        serializer = PublicSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Find email list
        try:
            email_list = EmailList.objects.get(
                tenant=tenant,
                slug=data['list_slug'],
                is_active=True
            )
        except EmailList.DoesNotExist:
            return Response(
                {'error': 'Email list not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create email config
        config, _ = EmailConfig.objects.get_or_create(tenant=tenant)
        
        # Subscribe
        service = EmailListService(config)
        
        # Get client IP
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        if not ip:
            ip = request.META.get('REMOTE_ADDR')
        
        subscriber = service.subscribe(
            email_list=email_list,
            email=data['email'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            source=data.get('source', ''),
            ip_address=ip,
            custom_fields=data.get('custom_fields', {})
        )
        
        # Return appropriate message
        if email_list.double_optin and subscriber.status == 'pending':
            return Response({
                'success': True,
                'message': 'Please check your email to confirm your subscription',
                'status': 'pending'
            })
        
        return Response({
            'success': True,
            'message': 'Successfully subscribed',
            'status': 'subscribed'
        })


class PublicUnsubscribeView(APIView):
    """
    Public endpoint for unsubscribing.
    Uses token from unsubscribe link.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            subscriber = Subscriber.objects.select_related(
                'email_list__tenant'
            ).get(unsubscribe_token=data['token'])
        except Subscriber.DoesNotExist:
            return Response(
                {'error': 'Invalid unsubscribe token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get config and unsubscribe
        config, _ = EmailConfig.objects.get_or_create(
            tenant=subscriber.email_list.tenant
        )
        service = EmailListService(config)
        service.unsubscribe(data['token'], data.get('reason', ''))
        
        return Response({
            'success': True,
            'message': 'Successfully unsubscribed'
        })
    
    def get(self, request):
        """Handle GET request for unsubscribe link clicks."""
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Token required'}, status=400)
        
        try:
            subscriber = Subscriber.objects.get(unsubscribe_token=token)
            subscriber.unsubscribe()
            return Response({
                'success': True,
                'message': 'Successfully unsubscribed'
            })
        except Subscriber.DoesNotExist:
            return Response({'error': 'Invalid token'}, status=400)


class PublicConfirmView(APIView):
    """
    Public endpoint for confirming email subscription.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Handle confirmation link clicks."""
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Token required'}, status=400)
        
        try:
            subscriber = Subscriber.objects.select_related(
                'email_list__tenant'
            ).get(confirmation_token=token, status='pending')
        except Subscriber.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired confirmation token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Confirm and sync
        config, _ = EmailConfig.objects.get_or_create(
            tenant=subscriber.email_list.tenant
        )
        service = EmailListService(config)
        service.confirm_subscription(token)
        
        return Response({
            'success': True,
            'message': 'Email confirmed! You are now subscribed.'
        })

