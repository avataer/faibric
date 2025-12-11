"""
Search service for code library.
Supports semantic search, keyword search, and hybrid search.
"""
import logging
import re
from typing import List, Optional

from django.db.models import Q, F, Value
from django.db.models.functions import Greatest
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)

from .models import LibraryItem, LibraryCategory
from .embeddings import EmbeddingService, embed_query_sync

logger = logging.getLogger(__name__)


class LibrarySearchService:
    """
    Search service for the code library.
    """
    
    def __init__(self, tenant_id: str = None):
        self.tenant_id = tenant_id
        self.embedding_service = EmbeddingService()
    
    def _get_base_queryset(self):
        """Get base queryset filtered by tenant and visibility."""
        qs = LibraryItem.objects.filter(is_active=True)
        
        if self.tenant_id:
            # Include tenant-specific and public items
            qs = qs.filter(
                Q(tenant_id=self.tenant_id) | Q(is_public=True) | Q(tenant__isnull=True)
            )
        else:
            # Only public/global items
            qs = qs.filter(Q(is_public=True) | Q(tenant__isnull=True))
        
        return qs.exclude(is_deprecated=True)
    
    def keyword_search(
        self,
        query: str,
        item_type: str = None,
        language: str = None,
        category_id: str = None,
        limit: int = 20
    ) -> List[dict]:
        """
        Search using keywords and trigram similarity.
        """
        qs = self._get_base_queryset()
        
        # Apply filters
        if item_type:
            qs = qs.filter(item_type=item_type)
        if language:
            qs = qs.filter(language=language)
        if category_id:
            qs = qs.filter(category_id=category_id)
        
        # Extract keywords from query
        keywords = [k.strip().lower() for k in query.split() if len(k.strip()) > 2]
        
        if not keywords:
            return []
        
        # Build search conditions
        q_filter = Q()
        for keyword in keywords:
            q_filter |= Q(name__icontains=keyword)
            q_filter |= Q(description__icontains=keyword)
            q_filter |= Q(keywords__contains=[keyword])
            q_filter |= Q(tags__contains=[keyword])
            q_filter |= Q(code__icontains=keyword)
        
        results = qs.filter(q_filter).order_by('-quality_score', '-usage_count')[:limit]
        
        return [
            {
                'id': str(item.id),
                'name': item.name,
                'slug': item.slug,
                'item_type': item.item_type,
                'language': item.language,
                'description': item.description[:200] if item.description else '',
                'quality_score': item.quality_score,
                'usage_count': item.usage_count,
                'keywords': item.keywords,
                'match_type': 'keyword',
            }
            for item in results
        ]
    
    def semantic_search(
        self,
        query: str,
        item_type: str = None,
        language: str = None,
        category_id: str = None,
        limit: int = 20,
        min_score: float = 0.5
    ) -> List[dict]:
        """
        Search using semantic similarity (embeddings).
        """
        # Get query embedding
        query_embedding = embed_query_sync(query)
        
        if not query_embedding:
            logger.warning("Failed to generate query embedding")
            return []
        
        qs = self._get_base_queryset()
        
        # Apply filters
        if item_type:
            qs = qs.filter(item_type=item_type)
        if language:
            qs = qs.filter(language=language)
        if category_id:
            qs = qs.filter(category_id=category_id)
        
        # Filter to items with embeddings
        qs = qs.exclude(embedding__isnull=True)
        
        # Get all candidates
        candidates = list(qs.values(
            'id', 'name', 'slug', 'item_type', 'language',
            'description', 'quality_score', 'usage_count',
            'keywords', 'embedding'
        ))
        
        # Calculate similarities
        results = self.embedding_service.find_similar(
            query_embedding,
            candidates,
            top_k=limit,
            min_score=min_score
        )
        
        # Format results
        return [
            {
                'id': str(r['id']),
                'name': r['name'],
                'slug': r['slug'],
                'item_type': r['item_type'],
                'language': r['language'],
                'description': r['description'][:200] if r['description'] else '',
                'quality_score': r['quality_score'],
                'usage_count': r['usage_count'],
                'keywords': r['keywords'],
                'similarity_score': r['similarity_score'],
                'match_type': 'semantic',
            }
            for r in results
        ]
    
    def hybrid_search(
        self,
        query: str,
        item_type: str = None,
        language: str = None,
        category_id: str = None,
        limit: int = 20,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4
    ) -> List[dict]:
        """
        Combine semantic and keyword search for best results.
        """
        # Get results from both methods
        semantic_results = self.semantic_search(
            query, item_type, language, category_id, limit=limit * 2
        )
        keyword_results = self.keyword_search(
            query, item_type, language, category_id, limit=limit * 2
        )
        
        # Merge and score
        all_results = {}
        
        for result in semantic_results:
            result_id = result['id']
            score = result.get('similarity_score', 0.5) * semantic_weight
            all_results[result_id] = {
                **result,
                'combined_score': score,
                'has_semantic': True,
                'has_keyword': False,
            }
        
        for result in keyword_results:
            result_id = result['id']
            keyword_score = 0.7 * keyword_weight  # Base score for keyword match
            
            if result_id in all_results:
                all_results[result_id]['combined_score'] += keyword_score
                all_results[result_id]['has_keyword'] = True
            else:
                all_results[result_id] = {
                    **result,
                    'combined_score': keyword_score,
                    'has_semantic': False,
                    'has_keyword': True,
                }
        
        # Sort by combined score
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )
        
        return sorted_results[:limit]
    
    def search(
        self,
        query: str,
        method: str = 'hybrid',
        **kwargs
    ) -> List[dict]:
        """
        Main search entry point.
        """
        if method == 'semantic':
            return self.semantic_search(query, **kwargs)
        elif method == 'keyword':
            return self.keyword_search(query, **kwargs)
        else:
            return self.hybrid_search(query, **kwargs)
    
    def get_related_items(
        self,
        item_id: str,
        limit: int = 5
    ) -> List[dict]:
        """
        Find items related to a given item.
        """
        try:
            item = LibraryItem.objects.get(id=item_id)
        except LibraryItem.DoesNotExist:
            return []
        
        if item.embedding:
            # Use semantic similarity
            qs = self._get_base_queryset().exclude(id=item_id)
            
            candidates = list(qs.exclude(embedding__isnull=True).values(
                'id', 'name', 'slug', 'item_type', 'language',
                'description', 'quality_score', 'usage_count',
                'keywords', 'embedding'
            ))
            
            results = self.embedding_service.find_similar(
                item.embedding,
                candidates,
                top_k=limit,
                min_score=0.6
            )
            
            return [
                {
                    'id': str(r['id']),
                    'name': r['name'],
                    'item_type': r['item_type'],
                    'similarity_score': r['similarity_score'],
                }
                for r in results
            ]
        
        # Fallback to keyword-based
        qs = self._get_base_queryset().exclude(id=item_id)
        
        # Match by keywords or category
        q_filter = Q()
        for keyword in (item.keywords or []):
            q_filter |= Q(keywords__contains=[keyword])
        
        if item.category_id:
            q_filter |= Q(category_id=item.category_id)
        
        q_filter |= Q(item_type=item.item_type, language=item.language)
        
        results = qs.filter(q_filter).order_by('-quality_score')[:limit]
        
        return [
            {
                'id': str(r.id),
                'name': r.name,
                'item_type': r.item_type,
                'similarity_score': 0.5,  # Placeholder
            }
            for r in results
        ]


class AutoComplete:
    """
    Auto-complete suggestions for library search.
    """
    
    def __init__(self, tenant_id: str = None):
        self.tenant_id = tenant_id
    
    def get_suggestions(
        self,
        prefix: str,
        limit: int = 10
    ) -> List[str]:
        """
        Get auto-complete suggestions for a search prefix.
        """
        if len(prefix) < 2:
            return []
        
        qs = LibraryItem.objects.filter(is_active=True)
        
        if self.tenant_id:
            qs = qs.filter(
                Q(tenant_id=self.tenant_id) | Q(is_public=True) | Q(tenant__isnull=True)
            )
        
        # Get matching names
        names = list(
            qs.filter(name__istartswith=prefix)
            .values_list('name', flat=True)
            .distinct()[:limit]
        )
        
        # Get matching keywords
        # Note: This is a simplified approach; a proper solution would use a dedicated search index
        
        return names[:limit]


def search_library_sync(
    query: str,
    tenant_id: str = None,
    **kwargs
) -> List[dict]:
    """
    Synchronous wrapper for library search.
    """
    service = LibrarySearchService(tenant_id)
    return service.search(query, **kwargs)






