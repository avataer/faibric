"""
Web scrapers for competitor analysis.
Uses httpx for async HTTP requests and BeautifulSoup for HTML parsing.
"""
import hashlib
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from django.utils import timezone

from .models import Competitor, CompetitorSnapshot, CompetitorChange

logger = logging.getLogger(__name__)


class CompetitorScraper:
    """
    Scraper for competitor websites.
    """
    
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    def __init__(self, competitor: Competitor):
        self.competitor = competitor
        self.base_url = competitor.website_url
        self.domain = competitor.domain
    
    def _get_page_url(self, page_type: str) -> Optional[str]:
        """Get URL for a specific page type."""
        if page_type == 'homepage':
            return self.base_url
        
        # Common URL patterns
        patterns = {
            'blog': ['/blog', '/blog/', '/news', '/articles'],
            'pricing': ['/pricing', '/pricing/', '/plans', '/plans/'],
            'features': ['/features', '/features/', '/product', '/product/'],
        }
        
        if page_type in patterns:
            # Return first pattern as default
            return urljoin(self.base_url, patterns[page_type][0])
        
        return None
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content for change detection."""
        # Normalize whitespace
        normalized = ' '.join(content.split())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def _extract_headings(self, soup: BeautifulSoup) -> list:
        """Extract all headings from the page."""
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(tag):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({
                        'level': tag,
                        'text': text
                    })
        return headings
    
    def _extract_features(self, soup: BeautifulSoup) -> list:
        """Extract mentioned features from the page."""
        features = []
        
        # Look for feature-like content patterns
        feature_patterns = [
            soup.find_all(class_=re.compile(r'feature', re.I)),
            soup.find_all('li', class_=re.compile(r'benefit|feature|advantage', re.I)),
        ]
        
        for pattern_results in feature_patterns:
            for element in pattern_results:
                text = element.get_text(strip=True)
                if text and len(text) < 500:  # Reasonable feature description length
                    features.append(text)
        
        return features[:50]  # Limit to 50 features
    
    def _extract_pricing(self, soup: BeautifulSoup) -> dict:
        """Extract pricing information from the page."""
        pricing = {
            'plans': [],
            'currency': 'USD',
            'has_free_tier': False,
        }
        
        # Look for price patterns
        price_pattern = re.compile(r'\$[\d,]+(?:\.\d{2})?(?:\s*\/\s*\w+)?')
        
        # Find pricing cards/sections
        pricing_sections = soup.find_all(class_=re.compile(r'pricing|plan|tier', re.I))
        
        for section in pricing_sections[:10]:  # Limit to 10 sections
            text = section.get_text()
            prices = price_pattern.findall(text)
            
            # Extract plan name (usually in heading)
            heading = section.find(['h2', 'h3', 'h4'])
            plan_name = heading.get_text(strip=True) if heading else "Unknown Plan"
            
            if prices:
                pricing['plans'].append({
                    'name': plan_name,
                    'prices': prices[:5],
                })
        
        # Check for free tier
        if re.search(r'\bfree\b', soup.get_text(), re.I):
            pricing['has_free_tier'] = True
        
        return pricing
    
    def _extract_blog_posts(self, soup: BeautifulSoup, base_url: str) -> list:
        """Extract blog post listings."""
        posts = []
        
        # Common blog post patterns
        article_patterns = [
            soup.find_all('article'),
            soup.find_all(class_=re.compile(r'post|article|blog-item|entry', re.I)),
        ]
        
        seen_urls = set()
        
        for pattern_results in article_patterns:
            for article in pattern_results[:20]:  # Limit to 20 posts
                # Find title and link
                title_elem = article.find(['h1', 'h2', 'h3', 'a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Find link
                link = article.find('a', href=True)
                url = urljoin(base_url, link['href']) if link else None
                
                if url and url not in seen_urls and title:
                    seen_urls.add(url)
                    
                    # Find date if available
                    date_elem = article.find('time') or article.find(class_=re.compile(r'date|time|posted', re.I))
                    date_text = date_elem.get_text(strip=True) if date_elem else None
                    
                    posts.append({
                        'title': title[:200],
                        'url': url,
                        'date': date_text,
                    })
        
        return posts
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content from the page."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        # Limit length
        return text[:50000]  # 50KB limit
    
    async def scrape_page(
        self,
        page_type: str,
        page_url: Optional[str] = None
    ) -> Optional[CompetitorSnapshot]:
        """
        Scrape a single page and create a snapshot.
        """
        url = page_url or self._get_page_url(page_type)
        if not url:
            logger.warning(f"No URL for page type {page_type}")
            return None
        
        try:
            async with httpx.AsyncClient(
                headers=self.DEFAULT_HEADERS,
                follow_redirects=True,
                timeout=30.0
            ) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
                    return CompetitorSnapshot.objects.create(
                        competitor=self.competitor,
                        page_type=page_type,
                        page_url=url,
                        http_status=response.status_code,
                        content_hash='',
                    )
                
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract content
                title = soup.title.string if soup.title else ''
                meta_desc = ''
                meta_tag = soup.find('meta', attrs={'name': 'description'})
                if meta_tag:
                    meta_desc = meta_tag.get('content', '')
                
                headings = self._extract_headings(soup)
                text_content = self._extract_text_content(soup)
                content_hash = self._compute_content_hash(text_content)
                
                # Page-type specific extraction
                features = []
                pricing = {}
                blog_posts = []
                
                if page_type == 'features' or page_type == 'homepage':
                    features = self._extract_features(soup)
                elif page_type == 'pricing':
                    pricing = self._extract_pricing(soup)
                elif page_type == 'blog':
                    blog_posts = self._extract_blog_posts(soup, url)
                
                # Create snapshot
                snapshot = await CompetitorSnapshot.objects.acreate(
                    competitor=self.competitor,
                    page_type=page_type,
                    page_url=url,
                    title=title[:500] if title else '',
                    meta_description=meta_desc[:2000] if meta_desc else '',
                    headings=headings,
                    content_text=text_content,
                    content_hash=content_hash,
                    features_mentioned=features,
                    pricing_info=pricing,
                    blog_posts=blog_posts,
                    http_status=response.status_code,
                )
                
                return snapshot
                
        except httpx.TimeoutException:
            logger.error(f"Timeout scraping {url}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    async def scrape_all_pages(self) -> dict:
        """
        Scrape all configured pages for this competitor.
        """
        results = {
            'success': True,
            'snapshots': [],
            'errors': [],
        }
        
        pages_to_scrape = []
        
        if self.competitor.track_homepage:
            pages_to_scrape.append(('homepage', None))
        if self.competitor.track_blog:
            pages_to_scrape.append(('blog', None))
        if self.competitor.track_pricing:
            pages_to_scrape.append(('pricing', None))
        if self.competitor.track_features:
            pages_to_scrape.append(('features', None))
        
        # Add custom pages
        for custom_url in self.competitor.custom_pages:
            pages_to_scrape.append(('custom', custom_url))
        
        for page_type, page_url in pages_to_scrape:
            try:
                snapshot = await self.scrape_page(page_type, page_url)
                if snapshot:
                    results['snapshots'].append(snapshot)
                else:
                    results['errors'].append(f"Failed to scrape {page_type}")
            except Exception as e:
                results['errors'].append(f"Error scraping {page_type}: {str(e)}")
        
        # Update last scraped time
        self.competitor.last_scraped_at = timezone.now()
        await self.competitor.asave(update_fields=['last_scraped_at'])
        
        if results['errors']:
            results['success'] = False
        
        return results


class ChangeDetector:
    """
    Detects changes between competitor snapshots.
    """
    
    def __init__(self, competitor: Competitor):
        self.competitor = competitor
    
    def _get_previous_snapshot(
        self,
        page_type: str,
        exclude_id=None
    ) -> Optional[CompetitorSnapshot]:
        """Get the most recent previous snapshot for comparison."""
        qs = CompetitorSnapshot.objects.filter(
            competitor=self.competitor,
            page_type=page_type,
        ).order_by('-created_at')
        
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        
        return qs.first()
    
    def detect_content_change(
        self,
        old_snapshot: CompetitorSnapshot,
        new_snapshot: CompetitorSnapshot
    ) -> Optional[dict]:
        """Detect if content has changed between snapshots."""
        if old_snapshot.content_hash == new_snapshot.content_hash:
            return None
        
        return {
            'change_type': 'content_update',
            'page_type': new_snapshot.page_type,
            'page_url': new_snapshot.page_url,
            'title': f"Content updated on {new_snapshot.page_type} page",
            'description': f"Title changed from '{old_snapshot.title}' to '{new_snapshot.title}'" if old_snapshot.title != new_snapshot.title else "Page content was updated",
        }
    
    def detect_new_features(
        self,
        old_snapshot: CompetitorSnapshot,
        new_snapshot: CompetitorSnapshot
    ) -> list:
        """Detect new features mentioned."""
        changes = []
        
        old_features = set(old_snapshot.features_mentioned or [])
        new_features = set(new_snapshot.features_mentioned or [])
        
        added_features = new_features - old_features
        
        for feature in added_features:
            changes.append({
                'change_type': 'new_feature',
                'page_type': new_snapshot.page_type,
                'page_url': new_snapshot.page_url,
                'title': f"New feature mentioned: {feature[:100]}",
                'description': feature,
            })
        
        return changes
    
    def detect_pricing_changes(
        self,
        old_snapshot: CompetitorSnapshot,
        new_snapshot: CompetitorSnapshot
    ) -> list:
        """Detect pricing changes."""
        changes = []
        
        old_pricing = old_snapshot.pricing_info or {}
        new_pricing = new_snapshot.pricing_info or {}
        
        # Compare plans
        old_plans = {p.get('name', ''): p for p in old_pricing.get('plans', [])}
        new_plans = {p.get('name', ''): p for p in new_pricing.get('plans', [])}
        
        # New plans
        for name, plan in new_plans.items():
            if name not in old_plans:
                changes.append({
                    'change_type': 'pricing_change',
                    'page_type': new_snapshot.page_type,
                    'page_url': new_snapshot.page_url,
                    'title': f"New pricing plan: {name}",
                    'description': f"Prices: {', '.join(plan.get('prices', []))}",
                })
            elif old_plans[name].get('prices') != plan.get('prices'):
                changes.append({
                    'change_type': 'pricing_change',
                    'page_type': new_snapshot.page_type,
                    'page_url': new_snapshot.page_url,
                    'title': f"Pricing changed for: {name}",
                    'description': f"Old: {old_plans[name].get('prices')}, New: {plan.get('prices')}",
                })
        
        return changes
    
    def detect_new_blog_posts(
        self,
        old_snapshot: CompetitorSnapshot,
        new_snapshot: CompetitorSnapshot
    ) -> list:
        """Detect new blog posts."""
        changes = []
        
        old_posts = {p.get('url', ''): p for p in (old_snapshot.blog_posts or [])}
        new_posts = new_snapshot.blog_posts or []
        
        for post in new_posts:
            url = post.get('url', '')
            if url and url not in old_posts:
                changes.append({
                    'change_type': 'new_blog_post',
                    'page_type': 'blog',
                    'page_url': url,
                    'title': f"New blog post: {post.get('title', 'Untitled')}",
                    'description': f"Published: {post.get('date', 'Unknown date')}",
                })
        
        return changes
    
    def detect_changes(self, new_snapshot: CompetitorSnapshot) -> list:
        """
        Detect all changes from the previous snapshot.
        Returns a list of detected changes.
        """
        changes = []
        
        old_snapshot = self._get_previous_snapshot(
            new_snapshot.page_type,
            exclude_id=new_snapshot.id
        )
        
        if not old_snapshot:
            # First snapshot, no changes to detect
            return changes
        
        # Content change detection
        content_change = self.detect_content_change(old_snapshot, new_snapshot)
        if content_change:
            changes.append(content_change)
        
        # Feature-specific detections
        if new_snapshot.page_type in ['features', 'homepage']:
            changes.extend(self.detect_new_features(old_snapshot, new_snapshot))
        
        if new_snapshot.page_type == 'pricing':
            changes.extend(self.detect_pricing_changes(old_snapshot, new_snapshot))
        
        if new_snapshot.page_type == 'blog':
            changes.extend(self.detect_new_blog_posts(old_snapshot, new_snapshot))
        
        # Create CompetitorChange records
        for change_data in changes:
            CompetitorChange.objects.create(
                competitor=self.competitor,
                change_type=change_data['change_type'],
                page_type=change_data['page_type'],
                page_url=change_data['page_url'],
                title=change_data['title'],
                description=change_data.get('description', ''),
                old_snapshot=old_snapshot,
                new_snapshot=new_snapshot,
            )
        
        return changes


def scrape_competitor_sync(competitor: Competitor) -> dict:
    """
    Synchronous wrapper for scraping a competitor.
    Use this in Celery tasks.
    """
    import asyncio
    
    scraper = CompetitorScraper(competitor)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    results = loop.run_until_complete(scraper.scrape_all_pages())
    
    # Detect changes for each snapshot
    detector = ChangeDetector(competitor)
    all_changes = []
    
    for snapshot in results.get('snapshots', []):
        changes = detector.detect_changes(snapshot)
        all_changes.extend(changes)
    
    results['changes'] = all_changes
    return results


async def scrape_all_active_competitors(tenant_id: str) -> dict:
    """
    Scrape all active competitors for a tenant.
    """
    from apps.tenants.models import Tenant
    
    tenant = await Tenant.objects.aget(id=tenant_id)
    competitors = [c async for c in tenant.competitors.filter(is_active=True)]
    
    results = {
        'tenant': str(tenant_id),
        'competitors_scraped': 0,
        'total_snapshots': 0,
        'total_changes': 0,
        'errors': [],
    }
    
    for competitor in competitors:
        scraper = CompetitorScraper(competitor)
        scrape_results = await scraper.scrape_all_pages()
        
        results['competitors_scraped'] += 1
        results['total_snapshots'] += len(scrape_results.get('snapshots', []))
        results['errors'].extend(scrape_results.get('errors', []))
        
        # Detect changes
        detector = ChangeDetector(competitor)
        for snapshot in scrape_results.get('snapshots', []):
            changes = detector.detect_changes(snapshot)
            results['total_changes'] += len(changes)
    
    return results







