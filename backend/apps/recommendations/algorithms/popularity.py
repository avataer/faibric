"""
Popularity and Trending Recommendation Algorithms.
Simple but effective baselines for cold-start and general recommendations.
"""
import logging
from typing import List, Dict
from datetime import timedelta

from django.db.models import Count, Sum, Avg, F
from django.utils import timezone

logger = logging.getLogger(__name__)


class PopularityRecommender:
    """
    Recommends popular items based on views, purchases, and ratings.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def get_popular_items(
        self,
        limit: int = 10,
        category: str = None,
        item_type: str = None,
        exclude_ids: List[str] = None
    ) -> List[Dict]:
        """
        Get most popular items.
        """
        from apps.recommendations.models import ItemCatalog
        
        qs = ItemCatalog.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True
        )
        
        if category:
            qs = qs.filter(category=category)
        
        if item_type:
            qs = qs.filter(item_type=item_type)
        
        if exclude_ids:
            qs = qs.exclude(id__in=exclude_ids)
        
        # Score by weighted combination
        items = qs.annotate(
            popularity_score=F('purchase_count') * 5 + F('view_count') * 0.1
        ).order_by('-popularity_score')[:limit]
        
        return [
            {
                'item_id': str(item.id),
                'external_id': item.external_id,
                'name': item.name,
                'category': item.category,
                'score': item.popularity_score,
                'purchase_count': item.purchase_count,
                'view_count': item.view_count,
                'reason': 'Popular item',
            }
            for item in items
        ]
    
    def get_top_rated(
        self,
        limit: int = 10,
        min_ratings: int = 5,
        category: str = None
    ) -> List[Dict]:
        """
        Get top-rated items with minimum rating threshold.
        """
        from apps.recommendations.models import ItemCatalog
        
        qs = ItemCatalog.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True,
            rating_count__gte=min_ratings
        )
        
        if category:
            qs = qs.filter(category=category)
        
        # Order by average rating
        items = qs.annotate(
            avg_rating=F('rating_sum') / F('rating_count')
        ).order_by('-avg_rating', '-rating_count')[:limit]
        
        return [
            {
                'item_id': str(item.id),
                'external_id': item.external_id,
                'name': item.name,
                'score': item.avg_rating,
                'rating_count': item.rating_count,
                'reason': 'Top rated',
            }
            for item in items
        ]
    
    def get_best_sellers(
        self,
        limit: int = 10,
        days: int = 30,
        category: str = None
    ) -> List[Dict]:
        """
        Get best-selling items in recent period.
        """
        from apps.recommendations.models import UserEvent, ItemCatalog
        
        since = timezone.now() - timedelta(days=days)
        
        # Count recent purchases per item
        purchase_counts = UserEvent.objects.filter(
            tenant_id=self.tenant_id,
            event_type='purchase',
            timestamp__gte=since
        ).values('item_id').annotate(
            purchase_count=Count('id')
        ).order_by('-purchase_count')
        
        if category:
            item_ids = ItemCatalog.objects.filter(
                tenant_id=self.tenant_id,
                category=category
            ).values_list('id', flat=True)
            purchase_counts = purchase_counts.filter(item_id__in=item_ids)
        
        purchase_counts = purchase_counts[:limit]
        
        # Fetch item details
        item_ids = [pc['item_id'] for pc in purchase_counts]
        items = ItemCatalog.objects.filter(id__in=item_ids)
        item_map = {item.id: item for item in items}
        
        recommendations = []
        for pc in purchase_counts:
            item = item_map.get(pc['item_id'])
            if item:
                recommendations.append({
                    'item_id': str(item.id),
                    'external_id': item.external_id,
                    'name': item.name,
                    'score': pc['purchase_count'],
                    'reason': f'Best seller in last {days} days',
                })
        
        return recommendations


class TrendingRecommender:
    """
    Recommends items that are trending (growing in popularity).
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def get_trending(
        self,
        limit: int = 10,
        window_days: int = 7,
        comparison_days: int = 30,
        category: str = None
    ) -> List[Dict]:
        """
        Get trending items (items with growing interaction rate).
        """
        from apps.recommendations.models import UserEvent, ItemCatalog
        
        now = timezone.now()
        recent_start = now - timedelta(days=window_days)
        comparison_start = now - timedelta(days=comparison_days)
        
        # Get recent event counts
        recent_events = UserEvent.objects.filter(
            tenant_id=self.tenant_id,
            timestamp__gte=recent_start,
            event_type__in=['view', 'click', 'purchase']
        ).values('item_id').annotate(
            recent_count=Count('id')
        )
        
        # Get comparison period counts
        comparison_events = UserEvent.objects.filter(
            tenant_id=self.tenant_id,
            timestamp__gte=comparison_start,
            timestamp__lt=recent_start,
            event_type__in=['view', 'click', 'purchase']
        ).values('item_id').annotate(
            comparison_count=Count('id')
        )
        
        # Calculate trend scores
        recent_map = {e['item_id']: e['recent_count'] for e in recent_events}
        comparison_map = {e['item_id']: e['comparison_count'] for e in comparison_events}
        
        trend_scores = []
        
        for item_id, recent_count in recent_map.items():
            comparison_count = comparison_map.get(item_id, 0)
            
            # Calculate trend score (rate of change)
            # Normalize by window sizes
            recent_rate = recent_count / window_days
            comparison_rate = comparison_count / (comparison_days - window_days) if comparison_days > window_days else 0
            
            if comparison_rate > 0:
                trend_score = (recent_rate - comparison_rate) / comparison_rate
            else:
                trend_score = recent_rate  # New items get their rate as score
            
            if trend_score > 0:  # Only include growing items
                trend_scores.append({
                    'item_id': item_id,
                    'trend_score': trend_score,
                    'recent_count': recent_count,
                    'comparison_count': comparison_count,
                })
        
        # Sort by trend score
        trend_scores.sort(key=lambda x: x['trend_score'], reverse=True)
        trend_scores = trend_scores[:limit]
        
        # Fetch item details
        item_ids = [ts['item_id'] for ts in trend_scores]
        
        qs = ItemCatalog.objects.filter(
            id__in=item_ids,
            is_active=True
        )
        
        if category:
            qs = qs.filter(category=category)
        
        item_map = {item.id: item for item in qs}
        
        recommendations = []
        for ts in trend_scores:
            item = item_map.get(ts['item_id'])
            if item:
                change_pct = int(ts['trend_score'] * 100)
                recommendations.append({
                    'item_id': str(item.id),
                    'external_id': item.external_id,
                    'name': item.name,
                    'score': ts['trend_score'],
                    'trend_change': change_pct,
                    'reason': f'Trending (↑{change_pct}%)',
                })
        
        return recommendations
    
    def get_new_arrivals(
        self,
        limit: int = 10,
        days: int = 14,
        category: str = None
    ) -> List[Dict]:
        """
        Get new items added recently.
        """
        from apps.recommendations.models import ItemCatalog
        
        since = timezone.now() - timedelta(days=days)
        
        qs = ItemCatalog.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True,
            created_at__gte=since
        )
        
        if category:
            qs = qs.filter(category=category)
        
        # Order by newest with some popularity weight
        items = qs.annotate(
            score=F('purchase_count') * 5 + F('view_count') * 0.1 + 10
        ).order_by('-created_at', '-score')[:limit]
        
        return [
            {
                'item_id': str(item.id),
                'external_id': item.external_id,
                'name': item.name,
                'score': item.score,
                'created_at': item.created_at.isoformat(),
                'reason': 'New arrival',
            }
            for item in items
        ]
    
    def get_rising_stars(
        self,
        limit: int = 10,
        min_age_days: int = 7,
        max_age_days: int = 30
    ) -> List[Dict]:
        """
        Get items that are new but gaining traction quickly.
        """
        from apps.recommendations.models import ItemCatalog, UserEvent
        
        now = timezone.now()
        min_date = now - timedelta(days=max_age_days)
        max_date = now - timedelta(days=min_age_days)
        
        # Get items in the age range
        items = ItemCatalog.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True,
            created_at__gte=min_date,
            created_at__lte=max_date
        )
        
        # Get their event counts
        event_counts = UserEvent.objects.filter(
            tenant_id=self.tenant_id,
            item_id__in=items.values_list('id', flat=True)
        ).values('item_id').annotate(
            event_count=Count('id'),
            purchase_count=Count('id', filter=models.Q(event_type='purchase'))
        )
        
        event_map = {
            ec['item_id']: {
                'events': ec['event_count'],
                'purchases': ec['purchase_count']
            }
            for ec in event_counts
        }
        
        # Score by events per day since creation
        scored_items = []
        for item in items:
            age_days = (now - item.created_at).days or 1
            events = event_map.get(item.id, {'events': 0, 'purchases': 0})
            
            # Score: events per day + purchases bonus
            score = (events['events'] / age_days) + (events['purchases'] * 2)
            
            if score > 0:
                scored_items.append({
                    'item_id': str(item.id),
                    'external_id': item.external_id,
                    'name': item.name,
                    'score': score,
                    'age_days': age_days,
                    'events': events['events'],
                    'reason': 'Rising star',
                })
        
        scored_items.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_items[:limit]


# Import for type hints
from django.db import models






