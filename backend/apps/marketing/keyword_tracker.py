"""
Keyword rank tracking service.
Tracks search engine rankings for specified keywords.
"""
import logging
from datetime import timedelta
from typing import Optional

import httpx
from django.conf import settings
from django.utils import timezone

from .models import Keyword, KeywordRanking, Competitor

logger = logging.getLogger(__name__)


class KeywordRankTracker:
    """
    Tracks keyword rankings using SerpAPI or similar services.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'SERP_API_KEY', None)
        self.base_url = 'https://serpapi.com/search'
        self.enabled = bool(self.api_key)
    
    async def _search_serpapi(
        self,
        keyword: str,
        location: str = 'United States',
        num_results: int = 100
    ) -> dict:
        """
        Perform a search using SerpAPI.
        Returns the parsed search results.
        """
        if not self.enabled:
            logger.warning("SerpAPI not configured, using mock data")
            return self._get_mock_results(keyword)
        
        params = {
            'q': keyword,
            'location': location,
            'api_key': self.api_key,
            'engine': 'google',
            'num': num_results,
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"SerpAPI error for '{keyword}': {e}")
            return {'error': str(e)}
    
    def _get_mock_results(self, keyword: str) -> dict:
        """
        Generate mock search results for testing.
        """
        import hashlib
        import random
        
        # Use keyword hash for consistent mock results
        seed = int(hashlib.md5(keyword.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        domains = [
            'example.com', 'competitor1.com', 'competitor2.com',
            'wikipedia.org', 'medium.com', 'reddit.com',
            'stackoverflow.com', 'github.com', 'producthunt.com',
            'techcrunch.com', 'forbes.com', 'business.com'
        ]
        random.shuffle(domains)
        
        results = []
        for i, domain in enumerate(domains[:10]):
            results.append({
                'position': i + 1,
                'title': f"{keyword.title()} - {domain}",
                'link': f"https://{domain}/{keyword.replace(' ', '-')}",
                'snippet': f"Learn about {keyword} at {domain}. The best resource for {keyword} information.",
                'domain': domain,
            })
        
        return {
            'organic_results': results,
            'search_information': {
                'total_results': random.randint(1000000, 50000000),
                'time_taken_displayed': 0.5,
            }
        }
    
    def _extract_rankings(
        self,
        search_results: dict,
        domains_to_track: list
    ) -> dict:
        """
        Extract rankings for specific domains from search results.
        """
        rankings = {}
        
        organic_results = search_results.get('organic_results', [])
        
        for result in organic_results:
            domain = result.get('domain', '')
            
            # Normalize domain
            domain = domain.lower().replace('www.', '')
            
            for track_domain in domains_to_track:
                track_domain_normalized = track_domain.lower().replace('www.', '')
                
                if track_domain_normalized in domain or domain in track_domain_normalized:
                    if track_domain not in rankings:
                        rankings[track_domain] = {
                            'position': result.get('position'),
                            'title': result.get('title', ''),
                            'url': result.get('link', ''),
                            'snippet': result.get('snippet', ''),
                        }
        
        # Fill in missing domains as not ranked
        for domain in domains_to_track:
            if domain not in rankings:
                rankings[domain] = {
                    'position': None,
                    'title': '',
                    'url': '',
                    'snippet': '',
                }
        
        return rankings
    
    async def check_keyword(self, keyword: Keyword) -> list:
        """
        Check rankings for a keyword and all tracked domains.
        Returns list of KeywordRanking objects created.
        """
        # Collect domains to track
        domains_to_track = [keyword.your_domain]
        
        if keyword.track_competitors:
            competitors = Competitor.objects.filter(
                tenant=keyword.tenant,
                is_active=True
            )
            async for competitor in competitors:
                domains_to_track.append(competitor.domain)
        
        # Perform search
        search_results = await self._search_serpapi(keyword.keyword)
        
        if 'error' in search_results:
            logger.error(f"Search failed for '{keyword.keyword}': {search_results['error']}")
            return []
        
        # Extract rankings
        rankings_data = self._extract_rankings(search_results, domains_to_track)
        
        # Create KeywordRanking records
        created_rankings = []
        
        for domain, ranking_info in rankings_data.items():
            # Get previous ranking for trend calculation
            previous_ranking = await KeywordRanking.objects.filter(
                keyword=keyword,
                domain=domain
            ).order_by('-created_at').afirst()
            
            previous_position = previous_ranking.position if previous_ranking else None
            
            # Calculate position change
            position_change = 0
            if previous_position and ranking_info['position']:
                position_change = previous_position - ranking_info['position']  # Positive = improved
            
            ranking = await KeywordRanking.objects.acreate(
                keyword=keyword,
                domain=domain,
                position=ranking_info['position'],
                title=ranking_info['title'][:500] if ranking_info['title'] else '',
                url=ranking_info['url'],
                snippet=ranking_info['snippet'][:2000] if ranking_info['snippet'] else '',
                previous_position=previous_position,
                position_change=position_change,
            )
            
            created_rankings.append(ranking)
        
        # Update keyword last checked time
        keyword.last_checked_at = timezone.now()
        await keyword.asave(update_fields=['last_checked_at'])
        
        return created_rankings
    
    async def check_all_keywords(self, tenant_id: str) -> dict:
        """
        Check rankings for all active keywords in a tenant.
        """
        from apps.tenants.models import Tenant
        
        tenant = await Tenant.objects.aget(id=tenant_id)
        keywords = [k async for k in tenant.keywords.filter(is_active=True)]
        
        results = {
            'tenant': str(tenant_id),
            'keywords_checked': 0,
            'rankings_created': 0,
            'errors': [],
        }
        
        for keyword in keywords:
            try:
                rankings = await self.check_keyword(keyword)
                results['keywords_checked'] += 1
                results['rankings_created'] += len(rankings)
            except Exception as e:
                results['errors'].append(f"Error checking '{keyword.keyword}': {str(e)}")
        
        return results


def check_keyword_sync(keyword: Keyword) -> list:
    """
    Synchronous wrapper for checking a single keyword.
    Use this in Celery tasks.
    """
    import asyncio
    
    tracker = KeywordRankTracker()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(tracker.check_keyword(keyword))


def check_all_keywords_sync(tenant_id: str) -> dict:
    """
    Synchronous wrapper for checking all keywords.
    Use this in Celery tasks.
    """
    import asyncio
    
    tracker = KeywordRankTracker()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(tracker.check_all_keywords(tenant_id))


class RankingAnalyzer:
    """
    Analyzes keyword ranking trends and performance.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def get_ranking_summary(self, days: int = 30) -> dict:
        """
        Get summary of ranking performance over the specified period.
        """
        from django.db.models import Avg, Min, Max, Count
        from apps.tenants.models import Tenant
        
        tenant = Tenant.objects.get(id=self.tenant_id)
        since = timezone.now() - timedelta(days=days)
        
        keywords = tenant.keywords.filter(is_active=True)
        
        summary = {
            'period_days': days,
            'keywords_tracked': keywords.count(),
            'your_rankings': [],
            'competitor_rankings': [],
        }
        
        # Get your domain rankings
        for keyword in keywords:
            your_rankings = KeywordRanking.objects.filter(
                keyword=keyword,
                domain=keyword.your_domain,
                created_at__gte=since
            ).order_by('-created_at')
            
            if your_rankings.exists():
                latest = your_rankings.first()
                oldest = your_rankings.last()
                
                avg_position = your_rankings.filter(
                    position__isnull=False
                ).aggregate(Avg('position'))['position__avg']
                
                summary['your_rankings'].append({
                    'keyword': keyword.keyword,
                    'current_position': latest.position,
                    'previous_position': oldest.position if oldest != latest else None,
                    'average_position': round(avg_position, 1) if avg_position else None,
                    'trend': latest.position_change,
                })
        
        # Get competitor rankings summary
        competitors = Competitor.objects.filter(
            tenant=tenant,
            is_active=True
        )
        
        for competitor in competitors:
            comp_rankings = []
            
            for keyword in keywords:
                if not keyword.track_competitors:
                    continue
                
                rankings = KeywordRanking.objects.filter(
                    keyword=keyword,
                    domain=competitor.domain,
                    created_at__gte=since
                ).order_by('-created_at')
                
                if rankings.exists():
                    latest = rankings.first()
                    comp_rankings.append({
                        'keyword': keyword.keyword,
                        'position': latest.position,
                        'trend': latest.position_change,
                    })
            
            if comp_rankings:
                summary['competitor_rankings'].append({
                    'competitor': competitor.name,
                    'domain': competitor.domain,
                    'rankings': comp_rankings,
                })
        
        return summary
    
    def get_ranking_trends(self, keyword_id: str, days: int = 30) -> dict:
        """
        Get detailed ranking trends for a specific keyword.
        """
        keyword = Keyword.objects.get(id=keyword_id)
        since = timezone.now() - timedelta(days=days)
        
        # Get your domain history
        your_history = list(KeywordRanking.objects.filter(
            keyword=keyword,
            domain=keyword.your_domain,
            created_at__gte=since
        ).order_by('created_at').values('created_at', 'position'))
        
        # Get competitor histories
        competitor_histories = {}
        
        competitors = Competitor.objects.filter(
            tenant=keyword.tenant,
            is_active=True
        )
        
        for competitor in competitors:
            history = list(KeywordRanking.objects.filter(
                keyword=keyword,
                domain=competitor.domain,
                created_at__gte=since
            ).order_by('created_at').values('created_at', 'position'))
            
            if history:
                competitor_histories[competitor.name] = history
        
        return {
            'keyword': keyword.keyword,
            'your_domain': keyword.your_domain,
            'period_days': days,
            'your_history': your_history,
            'competitor_histories': competitor_histories,
        }









