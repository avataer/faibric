"""
Hybrid Recommendation Algorithm.
Combines collaborative filtering, content-based filtering, and popularity.
"""
import logging
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class HybridRecommender:
    """
    Combines multiple recommendation strategies for better results.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        
        # Import algorithms
        from .collaborative import CollaborativeFiltering
        from .content_based import ContentBasedFiltering
        from .popularity import PopularityRecommender, TrendingRecommender
        
        self.collaborative = CollaborativeFiltering(tenant_id)
        self.content_based = ContentBasedFiltering(tenant_id)
        self.popularity = PopularityRecommender(tenant_id)
        self.trending = TrendingRecommender(tenant_id)
        
        # Default weights for combining algorithms
        self.weights = {
            'collaborative': 0.4,
            'content_based': 0.3,
            'popularity': 0.2,
            'trending': 0.1,
        }
    
    def set_weights(self, weights: Dict[str, float]):
        """
        Set custom weights for recommendation algorithms.
        """
        self.weights = weights
    
    def recommend_for_user(
        self,
        user_id: str,
        limit: int = 10,
        strategy_weights: Dict[str, float] = None,
        category: str = None,
        exclude_ids: List[str] = None
    ) -> List[Dict]:
        """
        Get hybrid recommendations for a user.
        Combines multiple strategies.
        """
        weights = strategy_weights or self.weights
        exclude_ids = set(exclude_ids or [])
        
        all_recommendations = defaultdict(lambda: {
            'scores': {},
            'reasons': [],
            'item': None
        })
        
        # Get recommendations from each algorithm
        if weights.get('collaborative', 0) > 0:
            try:
                collab_recs = self.collaborative.recommend_for_user(
                    user_id, limit=limit * 2
                )
                for rec in collab_recs:
                    if rec['item_id'] not in exclude_ids:
                        item_id = rec['item_id']
                        all_recommendations[item_id]['scores']['collaborative'] = rec['score']
                        all_recommendations[item_id]['reasons'].append(rec['reason'])
                        all_recommendations[item_id]['item'] = rec
            except Exception as e:
                logger.warning(f"Collaborative filtering failed: {e}")
        
        if weights.get('content_based', 0) > 0:
            try:
                content_recs = self.content_based.recommend_for_user(
                    user_id, limit=limit * 2
                )
                for rec in content_recs:
                    if rec['item_id'] not in exclude_ids:
                        item_id = rec['item_id']
                        all_recommendations[item_id]['scores']['content_based'] = rec['score']
                        all_recommendations[item_id]['reasons'].append(rec['reason'])
                        if not all_recommendations[item_id]['item']:
                            all_recommendations[item_id]['item'] = rec
            except Exception as e:
                logger.warning(f"Content-based filtering failed: {e}")
        
        if weights.get('popularity', 0) > 0:
            try:
                popular_recs = self.popularity.get_popular_items(
                    limit=limit * 2,
                    category=category,
                    exclude_ids=list(exclude_ids)
                )
                for rec in popular_recs:
                    item_id = rec['item_id']
                    all_recommendations[item_id]['scores']['popularity'] = rec['score']
                    all_recommendations[item_id]['reasons'].append(rec['reason'])
                    if not all_recommendations[item_id]['item']:
                        all_recommendations[item_id]['item'] = rec
            except Exception as e:
                logger.warning(f"Popularity recommender failed: {e}")
        
        if weights.get('trending', 0) > 0:
            try:
                trending_recs = self.trending.get_trending(
                    limit=limit * 2,
                    category=category
                )
                for rec in trending_recs:
                    if rec['item_id'] not in exclude_ids:
                        item_id = rec['item_id']
                        all_recommendations[item_id]['scores']['trending'] = rec['score']
                        all_recommendations[item_id]['reasons'].append(rec['reason'])
                        if not all_recommendations[item_id]['item']:
                            all_recommendations[item_id]['item'] = rec
            except Exception as e:
                logger.warning(f"Trending recommender failed: {e}")
        
        # Combine scores with normalization
        final_recommendations = []
        
        for item_id, data in all_recommendations.items():
            if not data['item']:
                continue
            
            # Normalize scores for each algorithm
            normalized_scores = {}
            for algo, score in data['scores'].items():
                # Simple normalization (could be improved with global stats)
                normalized_scores[algo] = min(score / 100, 1.0) if score > 1 else score
            
            # Weighted combination
            final_score = sum(
                normalized_scores.get(algo, 0) * weight
                for algo, weight in weights.items()
            )
            
            rec = data['item'].copy()
            rec['final_score'] = final_score
            rec['component_scores'] = data['scores']
            rec['reasons'] = list(set(data['reasons']))
            
            final_recommendations.append(rec)
        
        # Sort by final score
        final_recommendations.sort(key=lambda x: x['final_score'], reverse=True)
        
        return final_recommendations[:limit]
    
    def get_similar_items(
        self,
        item_id: str,
        limit: int = 10,
        include_also_bought: bool = True
    ) -> List[Dict]:
        """
        Get items similar to a given item.
        Combines content-based similarity with "also bought" data.
        """
        all_recommendations = {}
        
        # Content-based similar items
        try:
            content_similar = self.content_based.find_similar_items(item_id, limit=limit * 2)
            for rec in content_similar:
                all_recommendations[rec['item_id']] = {
                    **rec,
                    'sources': ['content_similarity']
                }
        except Exception as e:
            logger.warning(f"Content similarity failed: {e}")
        
        # Also bought items
        if include_also_bought:
            try:
                also_bought = self.collaborative.get_also_bought(item_id, limit=limit)
                for rec in also_bought:
                    if rec['item_id'] in all_recommendations:
                        all_recommendations[rec['item_id']]['score'] += rec['score'] * 0.5
                        all_recommendations[rec['item_id']]['sources'].append('also_bought')
                    else:
                        all_recommendations[rec['item_id']] = {
                            **rec,
                            'sources': ['also_bought']
                        }
            except Exception as e:
                logger.warning(f"Also bought failed: {e}")
        
        # Sort and return
        recommendations = sorted(
            all_recommendations.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        return recommendations[:limit]
    
    def get_personalized(
        self,
        user_id: str,
        limit: int = 10,
        diversity_factor: float = 0.3
    ) -> List[Dict]:
        """
        Get personalized recommendations with diversity.
        """
        # Get base recommendations
        recommendations = self.recommend_for_user(user_id, limit=limit * 2)
        
        if len(recommendations) <= limit:
            return recommendations
        
        # Apply diversity (category-based)
        selected = []
        categories_seen = set()
        
        for rec in recommendations:
            category = rec.get('category', '')
            
            # Score penalty for repeated categories
            if category in categories_seen:
                rec['final_score'] *= (1 - diversity_factor)
            else:
                categories_seen.add(category)
        
        # Re-sort and return
        recommendations.sort(key=lambda x: x['final_score'], reverse=True)
        
        return recommendations[:limit]
    
    def get_recommendations(
        self,
        strategy: str,
        user_id: str = None,
        item_id: str = None,
        category: str = None,
        limit: int = 10,
        **kwargs
    ) -> List[Dict]:
        """
        Unified recommendation API.
        """
        if strategy == 'personalized' and user_id:
            return self.get_personalized(user_id, limit=limit, **kwargs)
        
        elif strategy == 'similar_items' and item_id:
            return self.get_similar_items(item_id, limit=limit, **kwargs)
        
        elif strategy == 'also_bought' and item_id:
            return self.collaborative.get_also_bought(item_id, limit=limit)
        
        elif strategy == 'trending':
            return self.trending.get_trending(limit=limit, category=category)
        
        elif strategy == 'popular':
            return self.popularity.get_popular_items(limit=limit, category=category)
        
        elif strategy == 'new_arrivals':
            return self.trending.get_new_arrivals(limit=limit, category=category)
        
        elif strategy == 'top_rated':
            return self.popularity.get_top_rated(limit=limit, category=category)
        
        elif strategy == 'best_sellers':
            days = kwargs.get('days', 30)
            return self.popularity.get_best_sellers(limit=limit, days=days, category=category)
        
        elif strategy == 'for_you' and user_id:
            return self.recommend_for_user(user_id, limit=limit, category=category)
        
        else:
            # Default to popular items
            return self.popularity.get_popular_items(limit=limit, category=category)







