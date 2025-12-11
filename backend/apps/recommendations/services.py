"""
Recommendation services for event ingestion and API.
"""
import logging
from typing import List, Dict, Optional
from datetime import timedelta

from django.utils import timezone
from django.db import transaction

from .models import (
    ItemCatalog,
    UserProfile,
    UserEvent,
    RecommendationRequest,
    ABExperiment,
)
from .algorithms import HybridRecommender

logger = logging.getLogger(__name__)


class EventIngestionService:
    """
    Service for ingesting user events.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def get_or_create_user(self, external_user_id: str) -> UserProfile:
        """
        Get or create a user profile.
        """
        user, created = UserProfile.objects.get_or_create(
            tenant_id=self.tenant_id,
            external_user_id=external_user_id,
            defaults={
                'last_active_at': timezone.now()
            }
        )
        
        if not created:
            user.last_active_at = timezone.now()
            user.save(update_fields=['last_active_at'])
        
        return user
    
    def get_or_create_item(
        self,
        external_id: str,
        name: str = None,
        **attributes
    ) -> Optional[ItemCatalog]:
        """
        Get or create an item in the catalog.
        """
        defaults = {
            'name': name or external_id,
            'is_active': True,
        }
        
        # Add optional attributes
        if 'category' in attributes:
            defaults['category'] = attributes['category']
        if 'price' in attributes:
            defaults['price'] = attributes['price']
        if 'tags' in attributes:
            defaults['tags'] = attributes['tags']
        if 'item_type' in attributes:
            defaults['item_type'] = attributes['item_type']
        
        item, created = ItemCatalog.objects.get_or_create(
            tenant_id=self.tenant_id,
            external_id=external_id,
            defaults=defaults
        )
        
        return item
    
    @transaction.atomic
    def track_event(
        self,
        external_user_id: str,
        external_item_id: str,
        event_type: str,
        value: float = None,
        metadata: Dict = None,
        session_id: str = None,
        source: str = None,
        item_name: str = None,
        item_attributes: Dict = None
    ) -> UserEvent:
        """
        Track a user event.
        """
        # Get or create user and item
        user = self.get_or_create_user(external_user_id)
        item = self.get_or_create_item(
            external_item_id,
            name=item_name,
            **(item_attributes or {})
        )
        
        if not item:
            raise ValueError(f"Could not find or create item: {external_item_id}")
        
        # Create event
        event = UserEvent.objects.create(
            tenant_id=self.tenant_id,
            user=user,
            item=item,
            event_type=event_type,
            value=value,
            metadata=metadata or {},
            session_id=session_id or '',
            source=source or '',
        )
        
        # Update item stats
        if event_type == 'view':
            item.view_count += 1
            item.save(update_fields=['view_count'])
        elif event_type == 'purchase':
            item.purchase_count += 1
            item.save(update_fields=['purchase_count'])
        elif event_type == 'rating' and value:
            item.rating_sum += value
            item.rating_count += 1
            item.save(update_fields=['rating_sum', 'rating_count'])
        
        # Update user stats
        if event_type == 'view':
            user.total_views += 1
            user.save(update_fields=['total_views'])
        elif event_type == 'purchase':
            user.total_purchases += 1
            user.save(update_fields=['total_purchases'])
        elif event_type == 'rating':
            user.total_ratings += 1
            user.save(update_fields=['total_ratings'])
        
        return event
    
    def track_batch(self, events: List[Dict]) -> Dict:
        """
        Track multiple events in batch.
        """
        created = 0
        errors = []
        
        for event_data in events:
            try:
                self.track_event(**event_data)
                created += 1
            except Exception as e:
                errors.append({
                    'event': event_data,
                    'error': str(e)
                })
        
        return {
            'created': created,
            'errors': errors,
            'total': len(events)
        }


class RecommendationService:
    """
    Main service for getting recommendations.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.recommender = HybridRecommender(tenant_id)
    
    def _log_request(
        self,
        user_id: str,
        strategy: str,
        recommendations: List[Dict],
        context_item_id: str = None,
        model_id: str = None,
        response_time_ms: int = None,
        experiment_id: str = None,
        variant: str = None
    ) -> RecommendationRequest:
        """
        Log a recommendation request for analytics.
        """
        user = None
        context_item = None
        
        if user_id:
            try:
                user = UserProfile.objects.get(
                    tenant_id=self.tenant_id,
                    external_user_id=user_id
                )
            except UserProfile.DoesNotExist:
                pass
        
        if context_item_id:
            try:
                context_item = ItemCatalog.objects.get(
                    id=context_item_id,
                    tenant_id=self.tenant_id
                )
            except ItemCatalog.DoesNotExist:
                pass
        
        request = RecommendationRequest.objects.create(
            tenant_id=self.tenant_id,
            user=user,
            strategy=strategy,
            context_item=context_item,
            recommended_items=[
                {'item_id': r['item_id'], 'score': r.get('score', 0)}
                for r in recommendations
            ],
            response_time_ms=response_time_ms,
            experiment_id=experiment_id or '',
            variant=variant or '',
        )
        
        return request
    
    def get_recommendations(
        self,
        strategy: str,
        user_id: str = None,
        item_id: str = None,
        category: str = None,
        limit: int = 10,
        log_request: bool = True,
        **kwargs
    ) -> Dict:
        """
        Get recommendations using the specified strategy.
        """
        import time
        start_time = time.time()
        
        # Convert external user ID to internal
        internal_user_id = None
        if user_id:
            try:
                user_profile = UserProfile.objects.get(
                    tenant_id=self.tenant_id,
                    external_user_id=user_id
                )
                internal_user_id = str(user_profile.id)
            except UserProfile.DoesNotExist:
                # Create user profile for cold start
                user_profile = UserProfile.objects.create(
                    tenant_id=self.tenant_id,
                    external_user_id=user_id
                )
                internal_user_id = str(user_profile.id)
        
        # Get recommendations
        recommendations = self.recommender.get_recommendations(
            strategy=strategy,
            user_id=internal_user_id,
            item_id=item_id,
            category=category,
            limit=limit,
            **kwargs
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Log request
        if log_request:
            self._log_request(
                user_id=user_id,
                strategy=strategy,
                recommendations=recommendations,
                context_item_id=item_id,
                response_time_ms=response_time,
            )
        
        return {
            'strategy': strategy,
            'count': len(recommendations),
            'items': recommendations,
            'response_time_ms': response_time,
        }
    
    def get_personalized(
        self,
        user_id: str,
        limit: int = 10,
        **kwargs
    ) -> Dict:
        """
        Get personalized recommendations for a user.
        """
        return self.get_recommendations(
            strategy='personalized',
            user_id=user_id,
            limit=limit,
            **kwargs
        )
    
    def get_similar_items(
        self,
        item_id: str,
        limit: int = 10,
        **kwargs
    ) -> Dict:
        """
        Get items similar to a given item.
        """
        return self.get_recommendations(
            strategy='similar_items',
            item_id=item_id,
            limit=limit,
            **kwargs
        )
    
    def get_trending(
        self,
        category: str = None,
        limit: int = 10,
        **kwargs
    ) -> Dict:
        """
        Get trending items.
        """
        return self.get_recommendations(
            strategy='trending',
            category=category,
            limit=limit,
            **kwargs
        )
    
    def get_popular(
        self,
        category: str = None,
        limit: int = 10,
        **kwargs
    ) -> Dict:
        """
        Get popular items.
        """
        return self.get_recommendations(
            strategy='popular',
            category=category,
            limit=limit,
            **kwargs
        )
    
    def track_recommendation_click(
        self,
        request_id: str,
        item_id: str
    ) -> bool:
        """
        Track when a user clicks on a recommended item.
        """
        try:
            request = RecommendationRequest.objects.get(id=request_id)
            if item_id not in request.items_clicked:
                request.items_clicked.append(item_id)
                request.save(update_fields=['items_clicked'])
            return True
        except RecommendationRequest.DoesNotExist:
            return False
    
    def track_recommendation_purchase(
        self,
        request_id: str,
        item_id: str
    ) -> bool:
        """
        Track when a user purchases a recommended item.
        """
        try:
            request = RecommendationRequest.objects.get(id=request_id)
            if item_id not in request.items_purchased:
                request.items_purchased.append(item_id)
                request.save(update_fields=['items_purchased'])
            return True
        except RecommendationRequest.DoesNotExist:
            return False


class CatalogService:
    """
    Service for managing the item catalog.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def upsert_item(
        self,
        external_id: str,
        name: str,
        **attributes
    ) -> ItemCatalog:
        """
        Create or update a catalog item.
        """
        defaults = {
            'name': name,
            'is_active': True,
        }
        
        # Add optional attributes
        optional_fields = [
            'description', 'category', 'subcategory', 'item_type',
            'price', 'currency', 'image_url', 'url', 'tags', 'attributes'
        ]
        
        for field in optional_fields:
            if field in attributes:
                defaults[field] = attributes[field]
        
        item, created = ItemCatalog.objects.update_or_create(
            tenant_id=self.tenant_id,
            external_id=external_id,
            defaults=defaults
        )
        
        return item
    
    def bulk_upsert(self, items: List[Dict]) -> Dict:
        """
        Bulk create or update catalog items.
        """
        created = 0
        updated = 0
        errors = []
        
        for item_data in items:
            try:
                external_id = item_data.pop('external_id')
                name = item_data.pop('name')
                
                item, was_created = ItemCatalog.objects.update_or_create(
                    tenant_id=self.tenant_id,
                    external_id=external_id,
                    defaults={'name': name, **item_data}
                )
                
                if was_created:
                    created += 1
                else:
                    updated += 1
                    
            except Exception as e:
                errors.append({
                    'item': item_data,
                    'error': str(e)
                })
        
        return {
            'created': created,
            'updated': updated,
            'errors': errors,
            'total': len(items)
        }
    
    def delete_item(self, external_id: str) -> bool:
        """
        Soft delete a catalog item.
        """
        try:
            item = ItemCatalog.objects.get(
                tenant_id=self.tenant_id,
                external_id=external_id
            )
            item.is_active = False
            item.save(update_fields=['is_active'])
            return True
        except ItemCatalog.DoesNotExist:
            return False







