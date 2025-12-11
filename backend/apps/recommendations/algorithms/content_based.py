"""
Content-Based Filtering Recommendation Algorithm.
Uses item attributes and embeddings to find similar items.
"""
import logging
import math
from typing import List, Dict, Optional
from collections import defaultdict

from django.utils import timezone

logger = logging.getLogger(__name__)


class ContentBasedFiltering:
    """
    Content-based filtering using item attributes and embeddings.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a ** 2 for a in vec1))
        norm2 = math.sqrt(sum(b ** 2 for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _jaccard_similarity(
        self,
        set1: set,
        set2: set
    ) -> float:
        """Compute Jaccard similarity between two sets."""
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _compute_attribute_similarity(
        self,
        item1_attrs: Dict,
        item2_attrs: Dict
    ) -> float:
        """
        Compute similarity based on item attributes.
        """
        if not item1_attrs or not item2_attrs:
            return 0.0
        
        scores = []
        
        # Compare categories
        if item1_attrs.get('category') and item2_attrs.get('category'):
            if item1_attrs['category'] == item2_attrs['category']:
                scores.append(1.0)
            else:
                scores.append(0.0)
        
        # Compare tags
        tags1 = set(item1_attrs.get('tags', []))
        tags2 = set(item2_attrs.get('tags', []))
        if tags1 or tags2:
            scores.append(self._jaccard_similarity(tags1, tags2))
        
        # Compare numeric attributes (e.g., price range)
        if 'price' in item1_attrs and 'price' in item2_attrs:
            price1 = item1_attrs['price']
            price2 = item2_attrs['price']
            if price1 and price2:
                # Price similarity (closer prices = higher similarity)
                price_diff = abs(price1 - price2)
                max_price = max(price1, price2)
                price_sim = 1 - (price_diff / max_price) if max_price > 0 else 1.0
                scores.append(price_sim)
        
        # Compare other string attributes
        string_attrs = ['color', 'size', 'brand', 'material']
        for attr in string_attrs:
            if attr in item1_attrs and attr in item2_attrs:
                if item1_attrs[attr] == item2_attrs[attr]:
                    scores.append(1.0)
                else:
                    scores.append(0.0)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def find_similar_items(
        self,
        item_id: str,
        limit: int = 10,
        use_embeddings: bool = True
    ) -> List[Dict]:
        """
        Find items similar to the given item.
        """
        from apps.recommendations.models import ItemCatalog
        
        try:
            target_item = ItemCatalog.objects.get(
                id=item_id,
                tenant_id=self.tenant_id
            )
        except ItemCatalog.DoesNotExist:
            return []
        
        # Get candidate items
        candidates = ItemCatalog.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True
        ).exclude(id=item_id)
        
        # Filter by same category first for efficiency
        if target_item.category:
            candidates = candidates.filter(category=target_item.category)
        
        candidates = candidates[:500]  # Limit for performance
        
        similarities = []
        
        target_attrs = {
            'category': target_item.category,
            'subcategory': target_item.subcategory,
            'tags': target_item.tags,
            'price': float(target_item.price) if target_item.price else None,
            **target_item.attributes
        }
        target_embedding = target_item.embedding
        
        for candidate in candidates:
            candidate_attrs = {
                'category': candidate.category,
                'subcategory': candidate.subcategory,
                'tags': candidate.tags,
                'price': float(candidate.price) if candidate.price else None,
                **candidate.attributes
            }
            
            # Compute attribute similarity
            attr_sim = self._compute_attribute_similarity(target_attrs, candidate_attrs)
            
            # Compute embedding similarity if available
            embed_sim = 0.0
            if use_embeddings and target_embedding and candidate.embedding:
                embed_sim = self._cosine_similarity(target_embedding, candidate.embedding)
            
            # Weighted combination
            if use_embeddings and target_embedding and candidate.embedding:
                total_sim = 0.4 * attr_sim + 0.6 * embed_sim
            else:
                total_sim = attr_sim
            
            if total_sim > 0.1:  # Minimum threshold
                similarities.append({
                    'item_id': str(candidate.id),
                    'external_id': candidate.external_id,
                    'name': candidate.name,
                    'score': total_sim,
                    'attribute_score': attr_sim,
                    'embedding_score': embed_sim,
                    'reason': f"Similar to {target_item.name}",
                })
        
        # Sort by score
        similarities.sort(key=lambda x: x['score'], reverse=True)
        
        return similarities[:limit]
    
    def recommend_for_user(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Recommend items based on user's interaction history.
        """
        from apps.recommendations.models import UserEvent, ItemCatalog
        
        # Get user's recent interactions
        recent_events = UserEvent.objects.filter(
            tenant_id=self.tenant_id,
            user_id=user_id,
            event_type__in=['purchase', 'rating', 'favorite', 'click']
        ).order_by('-timestamp')[:20]
        
        if not recent_events:
            # Cold start - return popular in diverse categories
            return self._get_diverse_popular(limit)
        
        # Get items user interacted with
        interacted_items = set()
        weighted_items = {}
        
        event_weights = {
            'purchase': 5.0,
            'rating': 4.0,
            'favorite': 3.0,
            'click': 1.0,
        }
        
        for event in recent_events:
            item_id = str(event.item_id)
            interacted_items.add(item_id)
            weight = event_weights.get(event.event_type, 1.0)
            weighted_items[item_id] = weighted_items.get(item_id, 0) + weight
        
        # Find similar items to user's top interactions
        top_items = sorted(
            weighted_items.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        all_recommendations = {}
        
        for item_id, item_weight in top_items:
            similar = self.find_similar_items(item_id, limit=10)
            
            for rec in similar:
                rec_id = rec['item_id']
                if rec_id in interacted_items:
                    continue
                
                # Weight by source item importance
                adjusted_score = rec['score'] * item_weight
                
                if rec_id in all_recommendations:
                    all_recommendations[rec_id]['score'] += adjusted_score
                else:
                    rec['score'] = adjusted_score
                    all_recommendations[rec_id] = rec
        
        # Sort and return
        recommendations = sorted(
            all_recommendations.values(),
            key=lambda x: x['score'],
            reverse=True
        )[:limit]
        
        for rec in recommendations:
            rec['reason'] = 'Based on items you liked'
        
        return recommendations
    
    def _get_diverse_popular(self, limit: int = 10) -> List[Dict]:
        """
        Get popular items from diverse categories.
        """
        from apps.recommendations.models import ItemCatalog
        
        # Get top categories
        categories = ItemCatalog.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True
        ).values('category').annotate(
            count=models.Count('id')
        ).order_by('-count')[:5]
        
        recommendations = []
        items_per_category = max(2, limit // len(categories)) if categories else limit
        
        for cat in categories:
            items = ItemCatalog.objects.filter(
                tenant_id=self.tenant_id,
                category=cat['category'],
                is_active=True
            ).order_by('-purchase_count')[:items_per_category]
            
            for item in items:
                recommendations.append({
                    'item_id': str(item.id),
                    'external_id': item.external_id,
                    'name': item.name,
                    'score': item.purchase_count,
                    'reason': f'Popular in {item.category}',
                })
        
        return recommendations[:limit]
    
    async def generate_item_embeddings(self, batch_size: int = 100) -> Dict:
        """
        Generate embeddings for all items in catalog.
        """
        from apps.recommendations.models import ItemCatalog
        from apps.code_library.embeddings import EmbeddingService
        
        embedding_service = EmbeddingService()
        
        items = ItemCatalog.objects.filter(
            tenant_id=self.tenant_id,
            embedding__isnull=True
        )[:batch_size]
        
        updated = 0
        
        for item in items:
            # Create text for embedding
            text = f"{item.name}. {item.description}. Category: {item.category}. Tags: {', '.join(item.tags or [])}"
            
            embedding = await embedding_service.embed_text(text)
            
            if embedding:
                item.embedding = embedding
                item.embedding_model = embedding_service.model
                await item.asave(update_fields=['embedding', 'embedding_model'])
                updated += 1
        
        return {
            'updated': updated,
            'remaining': items.count() - updated,
        }


# Import for type hints
from django.db import models






