"""
AI-powered analysis for competitor changes and marketing insights.
"""
import logging
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.utils import timezone

from .models import (
    Competitor,
    CompetitorChange,
    CompetitorSnapshot,
    Keyword,
    KeywordRanking,
    MarketingConfig,
)

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """
    Uses AI (OpenAI) to analyze competitor changes and generate insights.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.enabled = bool(self.api_key)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4')
    
    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Call OpenAI API to generate analysis.
        """
        if not self.enabled:
            logger.warning("OpenAI not configured, returning mock analysis")
            return self._get_mock_analysis(user_prompt)
        
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': self.model,
                        'messages': [
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': user_prompt},
                        ],
                        'max_tokens': max_tokens,
                        'temperature': 0.7,
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    def _get_mock_analysis(self, prompt: str) -> str:
        """
        Generate mock analysis for testing.
        """
        return """
## Competitor Analysis Summary

Based on the changes detected, here are the key insights:

### Key Observations
1. **Feature Updates**: Competitors are focusing on AI-powered automation features
2. **Pricing Strategy**: Some competitors have adjusted their pricing tiers
3. **Content Marketing**: Increased blog activity around industry trends

### Recommendations
1. Consider adding similar AI automation features to stay competitive
2. Review your pricing structure against competitors
3. Increase content output around trending topics

### Priority Actions
- [ ] Research AI automation implementation
- [ ] Conduct pricing analysis
- [ ] Create content calendar for next quarter

### Risk Assessment
- Medium risk of market share loss if AI features not addressed
- Low risk from pricing changes
- Opportunity in content marketing gap
"""
    
    async def analyze_change(self, change: CompetitorChange) -> dict:
        """
        Analyze a single competitor change and generate insights.
        """
        system_prompt = """You are a competitive intelligence analyst. 
Analyze the following competitor change and provide:
1. A concise summary (2-3 sentences)
2. Strategic recommendations (bullet points)
3. An importance score from 1-10

Format your response as JSON with keys: summary, recommendations (array), importance_score (integer)"""

        user_prompt = f"""
Competitor: {change.competitor.name} ({change.competitor.domain})
Change Type: {change.change_type}
Page: {change.page_type}
Title: {change.title}
Description: {change.description}

Analyze this change and provide strategic insights.
"""

        response = await self._call_openai(system_prompt, user_prompt, max_tokens=500)
        
        if not response:
            return {
                'summary': 'Analysis unavailable',
                'recommendations': [],
                'importance_score': 5,
            }
        
        # Try to parse as JSON
        try:
            import json
            # Find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        
        # Return as plain text summary
        return {
            'summary': response[:500],
            'recommendations': [],
            'importance_score': 5,
        }
    
    async def analyze_changes_batch(
        self,
        changes: list,
        competitor: Competitor
    ) -> dict:
        """
        Analyze a batch of changes for a competitor.
        """
        if not changes:
            return {
                'summary': 'No significant changes detected.',
                'insights': [],
                'recommendations': [],
            }
        
        system_prompt = """You are a competitive intelligence analyst.
Analyze the following competitor changes and provide:
1. An executive summary
2. Key insights (list)
3. Strategic recommendations (list)
4. Action items (list)

Be concise and actionable."""

        changes_text = "\n".join([
            f"- [{c.change_type}] {c.title}: {c.description}"
            for c in changes
        ])

        user_prompt = f"""
Competitor: {competitor.name} ({competitor.domain})

Recent Changes:
{changes_text}

Provide a strategic analysis of these changes.
"""

        response = await self._call_openai(system_prompt, user_prompt)
        
        if not response:
            return {
                'summary': f'Detected {len(changes)} changes from {competitor.name}.',
                'insights': [],
                'recommendations': [],
            }
        
        return {
            'summary': response,
            'insights': [],
            'recommendations': [],
        }
    
    async def generate_executive_summary(
        self,
        tenant_id: str,
        days: int = 7
    ) -> dict:
        """
        Generate an executive summary of all competitor activity.
        """
        from apps.tenants.models import Tenant
        
        tenant = await Tenant.objects.aget(id=tenant_id)
        since = timezone.now() - timedelta(days=days)
        
        # Gather all changes
        all_changes = []
        competitors = [c async for c in tenant.competitors.filter(is_active=True)]
        
        for competitor in competitors:
            changes = [c async for c in CompetitorChange.objects.filter(
                competitor=competitor,
                created_at__gte=since
            ).order_by('-importance_score')]
            
            if changes:
                all_changes.append({
                    'competitor': competitor.name,
                    'domain': competitor.domain,
                    'changes': [
                        {
                            'type': c.change_type,
                            'title': c.title,
                            'importance': c.importance_score,
                        }
                        for c in changes[:10]  # Top 10 changes per competitor
                    ]
                })
        
        # Gather keyword rankings
        ranking_summary = []
        keywords = [k async for k in tenant.keywords.filter(is_active=True)]
        
        for keyword in keywords:
            rankings = await KeywordRanking.objects.filter(
                keyword=keyword,
                domain=keyword.your_domain,
            ).order_by('-created_at').afirst()
            
            if rankings:
                ranking_summary.append({
                    'keyword': keyword.keyword,
                    'position': rankings.position,
                    'trend': rankings.position_change,
                })
        
        system_prompt = """You are a marketing strategist.
Create a brief executive summary for leadership that covers:
1. Key competitive developments
2. Search ranking performance
3. Top 3 recommendations for this week

Be concise (max 300 words) and focus on actionable insights."""

        user_prompt = f"""
Period: Last {days} days

Competitor Activity:
{self._format_changes(all_changes)}

Keyword Rankings:
{self._format_rankings(ranking_summary)}

Generate an executive summary for stakeholders.
"""

        response = await self._call_openai(system_prompt, user_prompt)
        
        return {
            'period_days': days,
            'competitors_tracked': len(competitors),
            'keywords_tracked': len(keywords),
            'total_changes': sum(len(c['changes']) for c in all_changes),
            'executive_summary': response or 'Summary generation unavailable.',
        }
    
    def _format_changes(self, changes_data: list) -> str:
        """Format changes for the AI prompt."""
        if not changes_data:
            return "No significant changes detected."
        
        lines = []
        for comp in changes_data:
            lines.append(f"\n{comp['competitor']}:")
            for change in comp['changes']:
                lines.append(f"  - [{change['type']}] {change['title']}")
        
        return "\n".join(lines)
    
    def _format_rankings(self, rankings: list) -> str:
        """Format rankings for the AI prompt."""
        if not rankings:
            return "No ranking data available."
        
        lines = []
        for r in rankings:
            trend = ""
            if r['trend'] > 0:
                trend = f" (↑{r['trend']})"
            elif r['trend'] < 0:
                trend = f" (↓{abs(r['trend'])})"
            
            pos = r['position'] if r['position'] else "Not ranked"
            lines.append(f"- {r['keyword']}: Position {pos}{trend}")
        
        return "\n".join(lines)


class InsightGenerator:
    """
    Generates insights from marketing data without AI.
    Uses rule-based analysis.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def get_competitor_insights(self, days: int = 30) -> list:
        """
        Generate rule-based insights from competitor data.
        """
        from apps.tenants.models import Tenant
        
        tenant = Tenant.objects.get(id=self.tenant_id)
        since = timezone.now() - timedelta(days=days)
        
        insights = []
        
        # Check for high-importance changes
        high_importance_changes = CompetitorChange.objects.filter(
            competitor__tenant=tenant,
            importance_score__gte=8,
            created_at__gte=since
        ).count()
        
        if high_importance_changes > 0:
            insights.append({
                'type': 'alert',
                'title': 'High-Priority Competitor Activity',
                'message': f'{high_importance_changes} significant competitor changes detected this period.',
                'priority': 'high',
            })
        
        # Check for pricing changes
        pricing_changes = CompetitorChange.objects.filter(
            competitor__tenant=tenant,
            change_type='pricing_change',
            created_at__gte=since
        ).count()
        
        if pricing_changes > 0:
            insights.append({
                'type': 'info',
                'title': 'Competitor Pricing Updates',
                'message': f'{pricing_changes} competitors have updated their pricing.',
                'priority': 'medium',
            })
        
        # Check for new features
        new_features = CompetitorChange.objects.filter(
            competitor__tenant=tenant,
            change_type='new_feature',
            created_at__gte=since
        ).count()
        
        if new_features > 0:
            insights.append({
                'type': 'info',
                'title': 'New Competitor Features',
                'message': f'{new_features} new features launched by competitors.',
                'priority': 'medium',
            })
        
        # Check for blog activity
        blog_posts = CompetitorChange.objects.filter(
            competitor__tenant=tenant,
            change_type='new_blog_post',
            created_at__gte=since
        ).count()
        
        if blog_posts > 5:
            insights.append({
                'type': 'opportunity',
                'title': 'Content Marketing Opportunity',
                'message': f'Competitors published {blog_posts} blog posts. Consider increasing your content output.',
                'priority': 'low',
            })
        
        return insights
    
    def get_ranking_insights(self, days: int = 30) -> list:
        """
        Generate insights from ranking data.
        """
        from apps.tenants.models import Tenant
        
        tenant = Tenant.objects.get(id=self.tenant_id)
        insights = []
        
        keywords = Keyword.objects.filter(tenant=tenant, is_active=True)
        
        improved = 0
        declined = 0
        top_3 = 0
        not_ranked = 0
        
        for keyword in keywords:
            latest = KeywordRanking.objects.filter(
                keyword=keyword,
                domain=keyword.your_domain
            ).order_by('-created_at').first()
            
            if not latest:
                continue
            
            if latest.position_change > 0:
                improved += 1
            elif latest.position_change < 0:
                declined += 1
            
            if latest.position and latest.position <= 3:
                top_3 += 1
            elif latest.position is None:
                not_ranked += 1
        
        if improved > declined:
            insights.append({
                'type': 'success',
                'title': 'Ranking Improvements',
                'message': f'{improved} keywords improved in rankings.',
                'priority': 'low',
            })
        elif declined > improved:
            insights.append({
                'type': 'warning',
                'title': 'Ranking Declines',
                'message': f'{declined} keywords declined in rankings.',
                'priority': 'medium',
            })
        
        if top_3 > 0:
            insights.append({
                'type': 'success',
                'title': 'Top 3 Rankings',
                'message': f'You rank in the top 3 for {top_3} keywords.',
                'priority': 'low',
            })
        
        if not_ranked > keywords.count() / 2:
            insights.append({
                'type': 'warning',
                'title': 'SEO Opportunity',
                'message': f'{not_ranked} keywords not ranking in top 100. Consider SEO improvements.',
                'priority': 'high',
            })
        
        return insights


def ai_analyze_changes_sync(changes: list, competitor: Competitor) -> dict:
    """
    Synchronous wrapper for AI analysis.
    Use in Celery tasks.
    """
    import asyncio
    
    analyzer = AIAnalyzer()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(analyzer.analyze_changes_batch(changes, competitor))


def generate_executive_summary_sync(tenant_id: str, days: int = 7) -> dict:
    """
    Synchronous wrapper for executive summary generation.
    """
    import asyncio
    
    analyzer = AIAnalyzer()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(analyzer.generate_executive_summary(tenant_id, days))







