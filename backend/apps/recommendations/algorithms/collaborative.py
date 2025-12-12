"""
Collaborative Filtering Recommendation Algorithm.
Uses user-item interactions to find similar users and recommend items.
"""
import logging
from collections import defaultdict
from typing import List, Dict, Optional, Set
import math

from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class CollaborativeFiltering:
    """
    Collaborative filtering using user-based and item-based approaches.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.min_common_items = 3  # Minimum items in common for similarity
        self.min_user_events = 5   # Minimum events for a user to be included
    
    def _get_user_item_matrix(
        self,
        event_types: List[str] = None,
        days: int = 90
    ) -> Dict[str, Dict[str, float]]:
        """
        Build user-item interaction matrix.
        Returns: {user_id: {item_id: score}}
        """
        from apps.recommendations.models import UserEvent
        
        if event_types is None:
            event_types = ['view', 'click', 'purchase', 'rating']
        
        since = timezone.now() - timedelta(days=days)
        
        events = UserEvent.objects.filter(
            tenant_id=self.tenant_id,
            event_type__in=event_types,
            timestamp__gte=since
        ).values('user_id', 'item_id', 'event_type', 'value')
        
        # Weight by event type
        event_weights = {
            'view': 1.0,
            'click': 2.0,
            'add_to_cart': 3.0,
            'favorite': 4.0,
            'purchase': 5.0,
            'rating': lambda v: v if v else 3.0,  # Use rating value
        }
        
        matrix = defaultdict(lambda: defaultdict(float))
        
        for event in events:
            user_id = str(event['user_id'])
            item_id = str(event['item_id'])
            event_type = event['event_type']
            
            weight = event_weights.get(event_type, 1.0)
            if callable(weight):
                weight = weight(event.get('value'))
            
            matrix[user_id][item_id] += weight
        
        return dict(matrix)
    
    def _compute_user_similarity(
        self,
        user1_items: Dict[str, float],
        user2_items: Dict[str, float]
    ) -> float:
        """
        Compute cosine similarity between two users.
        """
        common_items = set(user1_items.keys()) & set(user2_items.keys())
        
        if len(common_items) < self.min_common_items:
            return 0.0
        
        # Cosine similarity
        dot_product = sum(
            user1_items[item] * user2_items[item]
            for item in common_items
        )
        
        norm1 = math.sqrt(sum(v ** 2 for v in user1_items.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in user2_items.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar_users(
        self,
        user_id: str,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Find users most similar to the given user.
        """
        matrix = self._get_user_item_matrix()
        
        if user_id not in matrix:
            return []
        
        target_items = matrix[user_id]
        
        similarities = []
        for other_user_id, other_items in matrix.items():
            if other_user_id == user_id:
                continue
            
            if len(other_items) < self.min_user_events:
                continue
            
            similarity = self._compute_user_similarity(target_items, other_items)
            
            if similarity > 0:
                similarities.append({
                    'user_id': other_user_id,
                    'similarity': similarity,
                    'common_items': len(set(target_items.keys()) & set(other_items.keys())),
                })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similarities[:top_k]
    
    def recommend_for_user(
        self,
        user_id: str,
        limit: int = 10,
        exclude_interacted: bool = True
    ) -> List[Dict]:
        """
        Get recommendations for a user based on similar users.
        """
        from apps.recommendations.models import ItemCatalog
        
        matrix = self._get_user_item_matrix()
        
        if user_id not in matrix:
            # Cold start - return popular items
            return self._get_popular_items(limit)
        
        user_items = set(matrix[user_id].keys())
        similar_users = self.find_similar_users(user_id, top_k=50)
        
        if not similar_users:
            return self._get_popular_items(limit)
        
        # Aggregate item scores from similar users
        item_scores = defaultdict(float)
        
        for similar in similar_users:
            other_user_id = similar['user_id']
            similarity = similar['similarity']
            
            for item_id, score in matrix[other_user_id].items():
                if exclude_interacted and item_id in user_items:
                    continue
                
                item_scores[item_id] += similarity * score
        
        # Sort by score
        sorted_items = sorted(
            item_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        # Fetch item details
        item_ids = [item_id for item_id, _ in sorted_items]
        items = ItemCatalog.objects.filter(
            id__in=item_ids,
            is_active=True
        )
        item_map = {str(item.id): item for item in items}
        
        recommendations = []
        for item_id, score in sorted_items:
            if item_id in item_map:
                item = item_map[item_id]
                recommendations.append({
                    'item_id': item_id,
                    'external_id': item.external_id,
                    'name': item.name,
                    'score': score,
                    'reason': 'Users similar to you also liked this',
                })
        
        return recommendations
    
    def _get_popular_items(self, limit: int = 10) -> List[Dict]:
        """
        Fallback to popular items for cold start.
        """
        from apps.recommendations.models import ItemCatalog
        
        items = ItemCatalog.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True
        ).order_by('-purchase_count', '-view_count')[:limit]
        
        return [
            {
                'item_id': str(item.id),
                'external_id': item.external_id,
                'name': item.name,
                'score': item.purchase_count + item.view_count * 0.1,
                'reason': 'Popular item',
            }
            for item in items
        ]
    
    def get_also_bought(
        self,
        item_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find items frequently bought together with the given item.
        """
        from apps.recommendations.models import UserEvent, ItemCatalog
        
        # Find users who purchased this item
        purchasers = UserEvent.objects.filter(
            tenant_id=self.tenant_id,
            item_id=item_id,
            event_type='purchase'
        ).values_list('user_id', flat=True).distinct()
        
        if not purchasers:
            return []
        
        # Find other items these users purchased
        co_purchases = UserEvent.objects.filter(
            tenant_id=self.tenant_id,
            user_id__in=list(purchasers),
            event_type='purchase'
        ).exclude(
            item_id=item_id
        ).values('item_id').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        item_ids = [cp['item_id'] for cp in co_purchases]
        items = ItemCatalog.objects.filter(id__in=item_ids, is_active=True)
        item_map = {item.id: item for item in items}
        
        recommendations = []
        for cp in co_purchases:
            item = item_map.get(cp['item_id'])
            if item:
                recommendations.append({
                    'item_id': str(item.id),
                    'external_id': item.external_id,
                    'name': item.name,
                    'score': cp['count'],
                    'reason': 'Frequently bought together',
                })
        
        return recommendations
    
    def train_model(self) -> Dict:
        """
        Pre-compute and cache collaborative filtering data.
        """
        from apps.recommendations.models import RecommendationModel
        
        matrix = self._get_user_item_matrix()
        
        # Compute item-item similarities (for item-based CF)
        item_users = defaultdict(set)
        for user_id, items in matrix.items():
            for item_id in items:
                item_users[item_id].add(user_id)
        
        # Store model
        model = RecommendationModel.objects.create(
            tenant_id=self.tenant_id,
            name='Collaborative Filtering',
            model_type='collaborative',
            status='training',
            training_started_at=timezone.now(),
        )
        
        model.training_users_count = len(matrix)
        model.training_items_count = len(item_users)
        model.training_events_count = sum(len(items) for items in matrix.values())
        
        # Store item popularity for fallback
        model.model_data = {
            'item_popularity': {
                item_id: len(users)
                for item_id, users in item_users.items()
            }
        }
        
        model.status = 'ready'
        model.training_completed_at = timezone.now()
        model.save()
        
        return {
            'model_id': str(model.id),
            'users': model.training_users_count,
            'items': model.training_items_count,
            'events': model.training_events_count,
        }









