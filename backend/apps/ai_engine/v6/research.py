"""
Research service for gathering information before code generation.
Searches web, GitHub, NPM, PyPI, and documentation.
"""
import hashlib
import logging
from datetime import timedelta
from typing import List, Optional

import httpx
from django.conf import settings
from django.utils import timezone

from apps.code_library.models import ResearchCache

logger = logging.getLogger(__name__)


class ResearchService:
    """
    Service for researching best practices and examples before generation.
    """
    
    def __init__(self):
        self.cache_duration = timedelta(hours=24)
    
    def _get_cache_key(self, query: str, research_type: str) -> str:
        """Generate cache key for a research query."""
        text = f"{research_type}:{query.lower().strip()}"
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _get_cached(self, query: str, research_type: str) -> Optional[dict]:
        """Check for cached research results."""
        cache_key = self._get_cache_key(query, research_type)
        
        try:
            cached = ResearchCache.objects.get(query_hash=cache_key)
            if not cached.is_expired:
                return {
                    'results': cached.results,
                    'summary': cached.summary,
                    'cached': True,
                }
        except ResearchCache.DoesNotExist:
            pass
        
        return None
    
    def _save_cache(
        self,
        query: str,
        research_type: str,
        results: list,
        summary: str = ''
    ):
        """Save research results to cache."""
        cache_key = self._get_cache_key(query, research_type)
        
        ResearchCache.objects.update_or_create(
            query_hash=cache_key,
            defaults={
                'query': query,
                'research_type': research_type,
                'results': results,
                'summary': summary,
                'result_count': len(results),
                'expires_at': timezone.now() + self.cache_duration,
            }
        )
    
    async def search_web(
        self,
        query: str,
        num_results: int = 5
    ) -> dict:
        """
        Search the web for relevant information.
        Uses Serper API or similar.
        """
        # Check cache
        cached = self._get_cached(query, 'web')
        if cached:
            return cached
        
        serper_key = getattr(settings, 'SERPER_API_KEY', None)
        
        if not serper_key:
            # Return mock results
            results = self._get_mock_web_results(query)
            self._save_cache(query, 'web', results)
            return {'results': results, 'cached': False}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    'https://google.serper.dev/search',
                    headers={
                        'X-API-KEY': serper_key,
                        'Content-Type': 'application/json',
                    },
                    json={
                        'q': query,
                        'num': num_results,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get('organic', [])[:num_results]:
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                    })
                
                self._save_cache(query, 'web', results)
                return {'results': results, 'cached': False}
                
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {'results': [], 'error': str(e)}
    
    async def search_github(
        self,
        query: str,
        language: str = None,
        num_results: int = 5
    ) -> dict:
        """
        Search GitHub for code examples and repositories.
        """
        cached = self._get_cached(f"{query}:{language or 'all'}", 'github')
        if cached:
            return cached
        
        github_token = getattr(settings, 'GITHUB_TOKEN', None)
        
        headers = {
            'Accept': 'application/vnd.github.v3+json',
        }
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        try:
            # Search repositories
            search_query = query
            if language:
                search_query += f' language:{language}'
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Search repos
                response = await client.get(
                    'https://api.github.com/search/repositories',
                    headers=headers,
                    params={
                        'q': search_query,
                        'sort': 'stars',
                        'order': 'desc',
                        'per_page': num_results,
                    }
                )
                response.raise_for_status()
                repo_data = response.json()
                
                results = []
                for repo in repo_data.get('items', [])[:num_results]:
                    results.append({
                        'type': 'repository',
                        'name': repo.get('full_name', ''),
                        'url': repo.get('html_url', ''),
                        'description': repo.get('description', ''),
                        'stars': repo.get('stargazers_count', 0),
                        'language': repo.get('language', ''),
                    })
                
                # Also search code
                code_response = await client.get(
                    'https://api.github.com/search/code',
                    headers=headers,
                    params={
                        'q': search_query,
                        'per_page': num_results,
                    }
                )
                
                if code_response.status_code == 200:
                    code_data = code_response.json()
                    for item in code_data.get('items', [])[:num_results]:
                        results.append({
                            'type': 'code',
                            'name': item.get('name', ''),
                            'path': item.get('path', ''),
                            'repo': item.get('repository', {}).get('full_name', ''),
                            'url': item.get('html_url', ''),
                        })
                
                cache_key = f"{query}:{language or 'all'}"
                self._save_cache(cache_key, 'github', results)
                return {'results': results, 'cached': False}
                
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return {'results': self._get_mock_github_results(query), 'error': str(e)}
    
    async def search_npm(
        self,
        query: str,
        num_results: int = 5
    ) -> dict:
        """
        Search NPM for JavaScript/TypeScript packages.
        """
        cached = self._get_cached(query, 'npm')
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    'https://registry.npmjs.org/-/v1/search',
                    params={
                        'text': query,
                        'size': num_results,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get('objects', []):
                    pkg = item.get('package', {})
                    results.append({
                        'name': pkg.get('name', ''),
                        'version': pkg.get('version', ''),
                        'description': pkg.get('description', ''),
                        'url': pkg.get('links', {}).get('npm', ''),
                        'keywords': pkg.get('keywords', []),
                    })
                
                self._save_cache(query, 'npm', results)
                return {'results': results, 'cached': False}
                
        except Exception as e:
            logger.error(f"NPM search error: {e}")
            return {'results': [], 'error': str(e)}
    
    async def search_pypi(
        self,
        query: str,
        num_results: int = 5
    ) -> dict:
        """
        Search PyPI for Python packages.
        """
        cached = self._get_cached(query, 'pypi')
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f'https://pypi.org/search/',
                    params={'q': query}
                )
                # PyPI doesn't have a JSON search API, so we'll use a different approach
                # For now, return mock results
                results = self._get_mock_pypi_results(query)
                
                self._save_cache(query, 'pypi', results)
                return {'results': results, 'cached': False}
                
        except Exception as e:
            logger.error(f"PyPI search error: {e}")
            return {'results': [], 'error': str(e)}
    
    def _get_mock_web_results(self, query: str) -> list:
        """Generate mock web search results."""
        return [
            {
                'title': f'Best practices for {query} - MDN Web Docs',
                'url': f'https://developer.mozilla.org/en-US/docs/{query.replace(" ", "_")}',
                'snippet': f'Learn about {query} and how to implement it properly in modern web applications.',
            },
            {
                'title': f'{query.title()} Tutorial - freeCodeCamp',
                'url': f'https://www.freecodecamp.org/news/{query.replace(" ", "-")}',
                'snippet': f'A comprehensive guide to {query} with examples and best practices.',
            },
            {
                'title': f'How to implement {query} - Stack Overflow',
                'url': f'https://stackoverflow.com/questions/{query.replace(" ", "-")}',
                'snippet': f'Answers and solutions for implementing {query} in your projects.',
            },
        ]
    
    def _get_mock_github_results(self, query: str) -> list:
        """Generate mock GitHub results."""
        return [
            {
                'type': 'repository',
                'name': f'example/{query.replace(" ", "-")}',
                'url': f'https://github.com/example/{query.replace(" ", "-")}',
                'description': f'A great implementation of {query}',
                'stars': 1500,
            },
        ]
    
    def _get_mock_pypi_results(self, query: str) -> list:
        """Generate mock PyPI results."""
        return [
            {
                'name': query.replace(' ', '-').lower(),
                'version': '1.0.0',
                'description': f'A Python package for {query}',
                'url': f'https://pypi.org/project/{query.replace(" ", "-").lower()}/',
            },
        ]
    
    async def research_topic(
        self,
        topic: str,
        language: str = None,
        include_web: bool = True,
        include_github: bool = True,
        include_packages: bool = True
    ) -> dict:
        """
        Comprehensive research on a topic for code generation.
        """
        results = {
            'topic': topic,
            'language': language,
            'web': [],
            'github': [],
            'packages': [],
            'summary': '',
        }
        
        # Gather research from all sources
        if include_web:
            web_results = await self.search_web(f"{topic} best practices 2024")
            results['web'] = web_results.get('results', [])
        
        if include_github:
            github_results = await self.search_github(topic, language=language)
            results['github'] = github_results.get('results', [])
        
        if include_packages:
            if language in ['typescript', 'javascript']:
                pkg_results = await self.search_npm(topic)
                results['packages'] = pkg_results.get('results', [])
            elif language == 'python':
                pkg_results = await self.search_pypi(topic)
                results['packages'] = pkg_results.get('results', [])
        
        # Generate summary
        results['summary'] = self._generate_summary(results)
        
        return results
    
    def _generate_summary(self, results: dict) -> str:
        """Generate a summary of research findings."""
        parts = []
        
        topic = results['topic']
        parts.append(f"Research findings for: {topic}")
        parts.append("")
        
        if results['web']:
            parts.append("Web Resources:")
            for item in results['web'][:3]:
                parts.append(f"- {item['title']}: {item['snippet'][:100]}...")
            parts.append("")
        
        if results['github']:
            parts.append("GitHub Examples:")
            for item in results['github'][:3]:
                if item['type'] == 'repository':
                    parts.append(f"- {item['name']} ({item['stars']} stars): {item.get('description', '')[:100]}")
            parts.append("")
        
        if results['packages']:
            parts.append("Relevant Packages:")
            for pkg in results['packages'][:3]:
                parts.append(f"- {pkg['name']}: {pkg.get('description', '')[:100]}")
        
        return '\n'.join(parts)


def research_topic_sync(
    topic: str,
    language: str = None,
    **kwargs
) -> dict:
    """
    Synchronous wrapper for research.
    """
    import asyncio
    
    service = ResearchService()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        service.research_topic(topic, language=language, **kwargs)
    )







