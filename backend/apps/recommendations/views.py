"""
API views for recommendations.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Q

from apps.tenants.models import Tenant, TenantMembership

from .models import (
    ItemCatalog,
    UserProfile,
    UserEvent,
    RecommendationModel,
    RecommendationRequest,
    ABExperiment,
)
from .serializers import (
    ItemCatalogSerializer,
    ItemCatalogCreateSerializer,
    UserProfileSerializer,
    UserEventSerializer,
    TrackEventSerializer,
    BatchTrackEventSerializer,
    RecommendationRequestSerializer,
    RecommendationResponseSerializer,
    RecommendationModelSerializer,
    ABExperimentSerializer,
    CatalogBulkUploadSerializer,
)
from .services import (
    EventIngestionService,
    RecommendationService,
    CatalogService,
)


class TenantMixin:
    """Mixin to filter querysets by tenant."""
    
    def get_tenant(self):
        tenant_id = self.request.headers.get('X-Tenant-ID')
        if tenant_id:
            return Tenant.objects.filter(id=tenant_id).first()
        
        membership = TenantMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).first()
        return membership.tenant if membership else None


class ItemCatalogViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for item catalog.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ItemCatalogCreateSerializer
        return ItemCatalogSerializer
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return ItemCatalog.objects.none()
        
        qs = ItemCatalog.objects.filter(tenant=tenant)
        
        # Filters
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        
        item_type = self.request.query_params.get('type')
        if item_type:
            qs = qs.filter(item_type=item_type)
        
        active = self.request.query_params.get('active')
        if active is not None:
            qs = qs.filter(is_active=active.lower() == 'true')
        
        return qs.order_by('-updated_at')
    
    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """Bulk upload catalog items."""
        serializer = CatalogBulkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        catalog_service = CatalogService(str(tenant.id))
        result = catalog_service.bulk_upsert(serializer.validated_data['items'])
        
        return Response(result)
    
    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """Get similar items."""
        item = self.get_object()
        tenant = self.get_tenant()
        
        limit = int(request.query_params.get('limit', 10))
        
        service = RecommendationService(str(tenant.id))
        result = service.get_similar_items(str(item.id), limit=limit)
        
        return Response(result)


class UserProfileViewSet(TenantMixin, viewsets.ReadOnlyModelViewSet):
    """
    API viewset for user profiles.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return UserProfile.objects.none()
        
        return UserProfile.objects.filter(tenant=tenant).order_by('-last_active_at')
    
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """Get user's recent events."""
        user = self.get_object()
        
        limit = int(request.query_params.get('limit', 50))
        events = UserEvent.objects.filter(user=user).order_by('-timestamp')[:limit]
        
        serializer = UserEventSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """Get recommendations for a user."""
        user = self.get_object()
        tenant = self.get_tenant()
        
        limit = int(request.query_params.get('limit', 10))
        
        service = RecommendationService(str(tenant.id))
        result = service.get_personalized(user.external_user_id, limit=limit)
        
        return Response(result)


class EventTrackingViewSet(TenantMixin, viewsets.ViewSet):
    """
    API viewset for event tracking.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def track(self, request):
        """Track a single event."""
        serializer = TrackEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        data = serializer.validated_data
        
        # Build item attributes if provided
        item_attributes = {}
        if data.get('item_category'):
            item_attributes['category'] = data['item_category']
        if data.get('item_price'):
            item_attributes['price'] = data['item_price']
        
        ingestion_service = EventIngestionService(str(tenant.id))
        
        try:
            event = ingestion_service.track_event(
                external_user_id=data['user_id'],
                external_item_id=data['item_id'],
                event_type=data['event_type'],
                value=data.get('value'),
                metadata=data.get('metadata'),
                session_id=data.get('session_id'),
                source=data.get('source'),
                item_name=data.get('item_name'),
                item_attributes=item_attributes if item_attributes else None
            )
            
            return Response({
                'success': True,
                'event_id': str(event.id),
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)
    
    @action(detail=False, methods=['post'])
    def batch(self, request):
        """Track multiple events in batch."""
        serializer = BatchTrackEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        ingestion_service = EventIngestionService(str(tenant.id))
        
        events = []
        for event_data in serializer.validated_data['events']:
            item_attributes = {}
            if event_data.get('item_category'):
                item_attributes['category'] = event_data['item_category']
            if event_data.get('item_price'):
                item_attributes['price'] = event_data['item_price']
            
            events.append({
                'external_user_id': event_data['user_id'],
                'external_item_id': event_data['item_id'],
                'event_type': event_data['event_type'],
                'value': event_data.get('value'),
                'metadata': event_data.get('metadata'),
                'session_id': event_data.get('session_id'),
                'source': event_data.get('source'),
                'item_name': event_data.get('item_name'),
                'item_attributes': item_attributes if item_attributes else None
            })
        
        result = ingestion_service.track_batch(events)
        
        return Response(result)


class RecommendationViewSet(TenantMixin, viewsets.ViewSet):
    """
    API viewset for getting recommendations.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get recommendations with specified strategy."""
        serializer = RecommendationRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        service = RecommendationService(str(tenant.id))
        
        result = service.get_recommendations(
            strategy=serializer.validated_data['strategy'],
            user_id=serializer.validated_data.get('user_id'),
            item_id=serializer.validated_data.get('item_id'),
            category=serializer.validated_data.get('category'),
            limit=serializer.validated_data.get('limit', 10),
        )
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def personalized(self, request):
        """Get personalized recommendations for a user."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=400)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        limit = int(request.query_params.get('limit', 10))
        
        service = RecommendationService(str(tenant.id))
        result = service.get_personalized(user_id, limit=limit)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def similar(self, request):
        """Get items similar to a given item."""
        item_id = request.query_params.get('item_id')
        if not item_id:
            return Response({'error': 'item_id required'}, status=400)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        limit = int(request.query_params.get('limit', 10))
        
        service = RecommendationService(str(tenant.id))
        result = service.get_similar_items(item_id, limit=limit)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending items."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        category = request.query_params.get('category')
        limit = int(request.query_params.get('limit', 10))
        
        service = RecommendationService(str(tenant.id))
        result = service.get_trending(category=category, limit=limit)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular items."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        category = request.query_params.get('category')
        limit = int(request.query_params.get('limit', 10))
        
        service = RecommendationService(str(tenant.id))
        result = service.get_popular(category=category, limit=limit)
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def track_click(self, request):
        """Track click on a recommendation."""
        request_id = request.data.get('request_id')
        item_id = request.data.get('item_id')
        
        if not request_id or not item_id:
            return Response({'error': 'request_id and item_id required'}, status=400)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        service = RecommendationService(str(tenant.id))
        success = service.track_recommendation_click(request_id, item_id)
        
        return Response({'success': success})


class RecommendationModelViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for recommendation models.
    """
    serializer_class = RecommendationModelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return RecommendationModel.objects.none()
        
        return RecommendationModel.objects.filter(tenant=tenant).order_by('-created_at')
    
    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['post'])
    def train(self, request, pk=None):
        """Train a recommendation model."""
        model = self.get_object()
        tenant = self.get_tenant()
        
        # Import the appropriate algorithm
        from .algorithms import CollaborativeFiltering
        
        if model.model_type == 'collaborative':
            algo = CollaborativeFiltering(str(tenant.id))
            result = algo.train_model()
            
            return Response({
                'success': True,
                'result': result,
            })
        
        return Response({
            'error': f'Training not implemented for {model.model_type}'
        }, status=400)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a model."""
        model = self.get_object()
        
        # Deactivate other models of same type
        RecommendationModel.objects.filter(
            tenant=model.tenant,
            model_type=model.model_type,
            is_active=True
        ).update(is_active=False)
        
        model.is_active = True
        model.save()
        
        return Response({'success': True})


class ABExperimentViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for A/B experiments.
    """
    serializer_class = ABExperimentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return ABExperiment.objects.none()
        
        return ABExperiment.objects.filter(tenant=tenant).order_by('-created_at')
    
    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start an experiment."""
        experiment = self.get_object()
        experiment.status = 'running'
        experiment.save()
        return Response({'status': 'running'})
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause an experiment."""
        experiment = self.get_object()
        experiment.status = 'paused'
        experiment.save()
        return Response({'status': 'paused'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete an experiment."""
        experiment = self.get_object()
        experiment.status = 'completed'
        experiment.save()
        return Response({'status': 'completed'})






