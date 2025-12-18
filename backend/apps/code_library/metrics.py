"""
Code Library Metrics - Track reuse ratio, duplicates, and system health.

Provides measurable checks for:
- Reuse vs. generate ratio
- Near-duplicate detection
- Retrieval quality
"""
import logging
import hashlib
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Avg, F

from . import constants

logger = logging.getLogger(__name__)


class ReuseMetrics:
    """
    Track and report reuse statistics.
    """
    
    @staticmethod
    def log_decision(
        session_token: str,
        decision: str,  # 'reused', 'generated', 'gray_zone'
        match_score: float,
        library_item_id: str = None,
        candidate_count: int = 0,
        threshold_used: float = None,
    ):
        """
        Log a reuse decision with structured fields.
        """
        log_data = {
            constants.LOG_FIELD_REUSE_DECISION: decision,
            constants.LOG_FIELD_MATCH_SCORE: match_score,
            constants.LOG_FIELD_LIBRARY_ITEM_ID: library_item_id,
            constants.LOG_FIELD_CANDIDATE_COUNT: candidate_count,
            constants.LOG_FIELD_THRESHOLD_USED: threshold_used or constants.REUSE_THRESHOLD_HIGH,
            'session_token': session_token,
            'timestamp': timezone.now().isoformat(),
        }
        
        # Structured log for parsing
        logger.info(f"[REUSE_METRIC] {log_data}")
        
        # Also store in database
        try:
            from .models import ReuseLog
            ReuseLog.objects.create(
                session_token=session_token,
                decision=decision,
                match_score=match_score,
                library_item_id=library_item_id,
                candidate_count=candidate_count,
            )
        except Exception as e:
            logger.warning(f"Failed to store reuse log: {e}")
    
    @staticmethod
    def get_reuse_ratio(days: int = 7) -> Dict:
        """
        Calculate reuse ratio over the past N days.
        Returns: {reused: int, generated: int, ratio: float}
        """
        try:
            from .models import ReuseLog
            since = timezone.now() - timedelta(days=days)
            
            stats = ReuseLog.objects.filter(
                created_at__gte=since
            ).values('decision').annotate(count=Count('id'))
            
            result = {'reused': 0, 'generated': 0, 'gray_zone': 0}
            for stat in stats:
                result[stat['decision']] = stat['count']
            
            total = result['reused'] + result['generated']
            result['ratio'] = result['reused'] / total if total > 0 else 0.0
            result['total'] = total
            result['period_days'] = days
            
            return result
        except Exception as e:
            logger.warning(f"Failed to get reuse ratio: {e}")
            return {'reused': 0, 'generated': 0, 'ratio': 0.0, 'error': str(e)}


class DuplicateDetector:
    """
    Detect near-duplicate code in the library.
    """
    
    @staticmethod
    def compute_code_hash(code: str) -> str:
        """Compute a normalized hash of code for duplicate detection."""
        # Normalize: remove whitespace, comments, lowercase
        normalized = re.sub(r'\s+', ' ', code.strip().lower())
        normalized = re.sub(r'//.*?$', '', normalized, flags=re.MULTILINE)
        normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    @staticmethod
    def compute_similarity(code1: str, code2: str) -> float:
        """
        Compute Jaccard similarity between two code snippets.
        """
        # Tokenize (simple word-based)
        tokens1 = set(re.findall(r'\w+', code1.lower()))
        tokens2 = set(re.findall(r'\w+', code2.lower()))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union)
    
    @classmethod
    def find_duplicates(cls, min_similarity: float = None) -> List[Tuple[str, str, float]]:
        """
        Find all near-duplicate pairs in the library.
        Returns list of (item_id_1, item_id_2, similarity_score)
        """
        min_similarity = min_similarity or constants.DUPLICATE_SIMILARITY_THRESHOLD
        
        from .models import LibraryItem
        
        items = list(LibraryItem.objects.filter(
            is_active=True
        ).values('id', 'code', 'name'))
        
        duplicates = []
        
        for i, item1 in enumerate(items):
            for item2 in items[i + 1:]:
                similarity = cls.compute_similarity(item1['code'], item2['code'])
                if similarity >= min_similarity:
                    duplicates.append((
                        str(item1['id']),
                        str(item2['id']),
                        similarity,
                        item1['name'],
                        item2['name'],
                    ))
        
        return sorted(duplicates, key=lambda x: x[2], reverse=True)
    
    @classmethod
    def check_for_duplicate(cls, new_code: str) -> Optional[Dict]:
        """
        Check if new code is a duplicate of existing library item.
        Returns the matching item if duplicate found, None otherwise.
        """
        from .models import LibraryItem
        
        items = LibraryItem.objects.filter(is_active=True, is_approved=True)
        
        for item in items:
            similarity = cls.compute_similarity(new_code, item.code)
            if similarity >= constants.DUPLICATE_SIMILARITY_THRESHOLD:
                return {
                    'is_duplicate': True,
                    'matching_item_id': str(item.id),
                    'matching_item_name': item.name,
                    'similarity': similarity,
                }
        
        return None


class RetrievalDiagnostics:
    """
    Diagnostics for understanding why items rank high/low.
    """
    
    @staticmethod
    def diagnose_query(query: str, top_k: int = 5) -> Dict:
        """
        Diagnose why candidates rank the way they do for a query.
        Returns detailed breakdown of scoring.
        """
        from .pipeline import LibrarySearcher
        from .models import LibraryItem
        
        searcher = LibrarySearcher()
        requirements = searcher.extract_requirements(query)
        
        # Build search keywords
        keywords = []
        keywords.append(requirements.get('site_type', ''))
        keywords.append(requirements.get('industry', ''))
        keywords.extend(requirements.get('sections_needed', []))
        keywords.extend(requirements.get('features', []))
        keywords = [k.lower() for k in keywords if k]
        
        items = LibraryItem.objects.filter(
            is_active=True,
            is_approved=True
        ).order_by('-quality_score', '-usage_count')
        
        diagnostics = []
        
        for item in items[:20]:  # Check top 20 candidates
            item_keywords = item.keywords.lower()
            item_tags = [t.lower() for t in (item.tags or [])]
            item_name = item.name.lower()
            item_desc = item.description.lower()
            
            breakdown = {
                'item_id': str(item.id),
                'item_name': item.name,
                'quality_score': item.quality_score,
                'usage_count': item.usage_count,
                'keyword_matches': [],
                'tag_matches': [],
                'score_components': [],
                'total_score': 0,
            }
            
            score = 0
            for kw in keywords:
                if kw in item_keywords or kw in item_name or kw in item_desc:
                    score += constants.KEYWORD_IN_TEXT_WEIGHT
                    breakdown['keyword_matches'].append(kw)
                    breakdown['score_components'].append(f"+{constants.KEYWORD_IN_TEXT_WEIGHT} (keyword: {kw})")
                
                if kw in item_tags:
                    score += constants.KEYWORD_IN_TAG_WEIGHT
                    breakdown['tag_matches'].append(kw)
                    breakdown['score_components'].append(f"+{constants.KEYWORD_IN_TAG_WEIGHT} (tag: {kw})")
            
            # Quality boost
            quality_boost = score * (constants.QUALITY_SCORE_BOOST_FACTOR + item.quality_score)
            breakdown['score_components'].append(f"x{1 + item.quality_score:.2f} (quality boost)")
            
            breakdown['raw_score'] = score
            breakdown['total_score'] = score * (constants.QUALITY_SCORE_BOOST_FACTOR + item.quality_score)
            
            if breakdown['total_score'] > 0:
                diagnostics.append(breakdown)
        
        # Sort by score
        diagnostics.sort(key=lambda x: x['total_score'], reverse=True)
        
        return {
            'query': query,
            'extracted_requirements': requirements,
            'search_keywords': keywords,
            'thresholds': {
                'reuse_high': constants.REUSE_THRESHOLD_HIGH,
                'reuse_low': constants.REUSE_THRESHOLD_LOW,
                'gray_zone': f"{constants.GRAY_ZONE_MIN} - {constants.GRAY_ZONE_MAX}",
            },
            'top_candidates': diagnostics[:top_k],
            'decision': _get_decision(diagnostics[0]['total_score'] if diagnostics else 0),
        }


def _get_decision(score: float) -> str:
    """Get decision based on score."""
    if score >= constants.REUSE_THRESHOLD_HIGH:
        return 'REUSE (confident)'
    elif score >= constants.GRAY_ZONE_MIN:
        return 'GRAY_ZONE (review needed)'
    else:
        return 'GENERATE (no match)'
