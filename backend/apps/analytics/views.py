from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count

from apps.tenants.permissions import TenantPermission
from .models import AnalyticsConfig, Event, Funnel, FunnelStep, UserProfile
from .serializers import (
    AnalyticsConfigSerializer, TrackEventSerializer, IdentifyUserSerializer,
    EventSerializer, FunnelSerializer, FunnelCreateSerializer,
    FunnelStatsSerializer, UserProfileSerializer, FunnelTemplateSerializer
)
from .services import AnalyticsProxy, FunnelAnalyzer, FUNNEL_TEMPLATES


class AnalyticsConfigViewSet(viewsets.ViewSet):
    """
    ViewSet for managing analytics configuration.
    """
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_config(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        config, _ = AnalyticsConfig.objects.get_or_create(tenant=tenant)
        return config
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """Get analytics configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = AnalyticsConfigSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_config(self, request):
        """Update analytics configuration."""
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = AnalyticsConfigSerializer(
            config,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)


class TrackEventView(APIView):
    """
    Public endpoint for tracking events from customer's apps.
    Identified by X-Faibric-App-Id header.
    """
    permission_classes = [AllowAny]  # Public endpoint
    
    def post(self, request):
        # Get app/tenant from header
        from apps.tenants.models import Tenant
        from apps.projects.models import Project
        
        app_id = request.headers.get('X-Faibric-App-Id')
        if not app_id:
            return Response(
                {'error': 'X-Faibric-App-Id header required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find tenant from project
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            tenant = project.tenant
        except Project.DoesNotExist:
            return Response(
                {'error': 'Invalid app ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not tenant:
            return Response(
                {'error': 'App has no tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TrackEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Determine distinct_id
        distinct_id = data.get('distinct_id') or data.get('user_id') or data.get('anonymous_id')
        
        # Create event
        event = Event.objects.create(
            tenant=tenant,
            event_name=data['event'],
            distinct_id=distinct_id,
            anonymous_id=data.get('anonymous_id', ''),
            user_id=data.get('user_id', ''),
            properties=data.get('properties', {}),
            context=data.get('context', {}),
            timestamp=data.get('timestamp', timezone.now()),
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        # Update user profile
        profile, _ = UserProfile.objects.get_or_create(
            tenant=tenant,
            distinct_id=distinct_id,
        )
        profile.total_events += 1
        profile.save(update_fields=['total_events', 'last_seen'])
        
        # Forward to analytics services
        try:
            config = AnalyticsConfig.objects.get(tenant=tenant)
            proxy = AnalyticsProxy(config)
            proxy.track_event(event)
        except AnalyticsConfig.DoesNotExist:
            pass
        
        # Process funnels
        FunnelAnalyzer.process_event_for_funnels(event)
        
        return Response({'success': True, 'event_id': str(event.id)})
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class IdentifyUserView(APIView):
    """
    Identify a user and set their profile properties.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from apps.tenants.models import Tenant
        from apps.projects.models import Project
        
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
        
        serializer = IdentifyUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        distinct_id = data.get('distinct_id') or data.get('user_id')
        
        # Update user profile
        profile, created = UserProfile.objects.get_or_create(
            tenant=tenant,
            distinct_id=distinct_id,
        )
        
        # Merge traits
        profile.properties.update(data.get('traits', {}))
        profile.save()
        
        # Forward to analytics services
        try:
            config = AnalyticsConfig.objects.get(tenant=tenant)
            proxy = AnalyticsProxy(config)
            proxy.identify_user(distinct_id, data.get('traits', {}))
        except AnalyticsConfig.DoesNotExist:
            pass
        
        return Response({'success': True})


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing tracked events.
    """
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Event.objects.none()
        return Event.objects.filter(tenant=tenant)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent events."""
        events = self.get_queryset()[:50]
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get event statistics."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        events = Event.objects.filter(
            tenant=tenant,
            timestamp__gte=start_date
        )
        
        # Count by event name
        by_name = events.values('event_name').annotate(
            count=Count('id')
        ).order_by('-count')[:20]
        
        # Count by day
        from django.db.models.functions import TruncDate
        by_day = events.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return Response({
            'total_events': events.count(),
            'unique_users': events.values('distinct_id').distinct().count(),
            'by_event_name': list(by_name),
            'by_day': list(by_day),
        })


class FunnelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing funnels.
    """
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FunnelCreateSerializer
        return FunnelSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Funnel.objects.none()
        return Funnel.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get funnel statistics."""
        funnel = self.get_object()
        days = int(request.query_params.get('days', 30))
        
        stats = FunnelAnalyzer.get_funnel_stats(funnel, days)
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def templates(self, request):
        """Get available funnel templates."""
        templates = [
            {
                'template_name': key,
                'name': val['name'],
                'description': val['description'],
                'steps': val['steps']
            }
            for key, val in FUNNEL_TEMPLATES.items()
        ]
        return Response(templates)
    
    @action(detail=False, methods=['post'])
    def create_from_template(self, request):
        """Create a funnel from a template."""
        template_name = request.data.get('template_name')
        if template_name not in FUNNEL_TEMPLATES:
            return Response(
                {'error': 'Invalid template name'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        template = FUNNEL_TEMPLATES[template_name]
        
        # Create funnel
        funnel = Funnel.objects.create(
            tenant=tenant,
            name=template['name'],
            description=template['description'],
            template_name=template_name,
        )
        
        # Create steps
        for i, step in enumerate(template['steps']):
            FunnelStep.objects.create(
                funnel=funnel,
                order=i + 1,
                name=step['name'],
                event_name=step['event_name'],
                property_filters=step.get('property_filters', {}),
            )
        
        serializer = FunnelSerializer(funnel)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing tracked user profiles.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return UserProfile.objects.none()
        return UserProfile.objects.filter(tenant=tenant)
    
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """Get events for a user."""
        profile = self.get_object()
        events = Event.objects.filter(
            tenant=profile.tenant,
            distinct_id=profile.distinct_id
        )[:100]
        
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

