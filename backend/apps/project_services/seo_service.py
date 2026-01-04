"""
SEO Optimization Service
Generate meta tags, sitemaps, and optimize for search engines.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
import re


@dataclass
class SEOMetadata:
    title: str
    description: str
    keywords: List[str]
    og_image: Optional[str] = None
    canonical_url: Optional[str] = None


class SEOService:
    """
    Generates SEO metadata and optimization for projects.
    """
    
    def generate_meta_tags(self, metadata: SEOMetadata, url: str) -> str:
        """
        Generate HTML meta tags for SEO.
        """
        keywords_str = ', '.join(metadata.keywords) if metadata.keywords else ''
        og_image = metadata.og_image or f"{url}/og-image.png"
        canonical = metadata.canonical_url or url
        
        return f'''
<!-- Primary Meta Tags -->
<title>{self._escape(metadata.title)}</title>
<meta name="title" content="{self._escape(metadata.title)}">
<meta name="description" content="{self._escape(metadata.description)}">
<meta name="keywords" content="{self._escape(keywords_str)}">
<link rel="canonical" href="{canonical}">

<!-- Open Graph / Facebook -->
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{self._escape(metadata.title)}">
<meta property="og:description" content="{self._escape(metadata.description)}">
<meta property="og:image" content="{og_image}">

<!-- Twitter -->
<meta property="twitter:card" content="summary_large_image">
<meta property="twitter:url" content="{url}">
<meta property="twitter:title" content="{self._escape(metadata.title)}">
<meta property="twitter:description" content="{self._escape(metadata.description)}">
<meta property="twitter:image" content="{og_image}">

<!-- Additional SEO -->
<meta name="robots" content="index, follow">
<meta name="language" content="English">
<meta name="author" content="Faibric">
'''
    
    def generate_sitemap(self, pages: List[Dict], base_url: str) -> str:
        """
        Generate XML sitemap.
        
        pages: [{'path': '/', 'priority': 1.0, 'changefreq': 'daily'}, ...]
        """
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for page in pages:
            path = page.get('path', '/')
            priority = page.get('priority', 0.5)
            changefreq = page.get('changefreq', 'weekly')
            
            xml += f'''  <url>
    <loc>{base_url.rstrip("/")}{path}</loc>
    <priority>{priority}</priority>
    <changefreq>{changefreq}</changefreq>
  </url>
'''
        
        xml += '</urlset>'
        return xml
    
    def generate_robots_txt(self, base_url: str, disallow: List[str] = None) -> str:
        """
        Generate robots.txt file.
        """
        disallow = disallow or []
        
        txt = f'''User-agent: *
Allow: /

'''
        for path in disallow:
            txt += f'Disallow: {path}\n'
        
        txt += f'\nSitemap: {base_url.rstrip("/")}/sitemap.xml\n'
        return txt
    
    def extract_seo_from_prompt(self, prompt: str, project_name: str) -> SEOMetadata:
        """
        Extract SEO metadata from user prompt.
        """
        # Clean prompt
        clean_prompt = prompt.strip()
        
        # Generate title
        title = project_name or self._extract_title(clean_prompt)
        
        # Generate description
        description = self._generate_description(clean_prompt)
        
        # Extract keywords
        keywords = self._extract_keywords(clean_prompt)
        
        return SEOMetadata(
            title=title,
            description=description,
            keywords=keywords
        )
    
    def _extract_title(self, prompt: str) -> str:
        """Extract a title from the prompt."""
        # Remove common prefixes
        for prefix in ['build a', 'create a', 'make a', 'develop a', 'design a']:
            if prompt.lower().startswith(prefix):
                prompt = prompt[len(prefix):].strip()
                break
        
        # Take first meaningful phrase
        words = prompt.split()[:6]
        title = ' '.join(words).title()
        
        return title
    
    def _generate_description(self, prompt: str) -> str:
        """Generate a meta description from the prompt."""
        # Limit to 160 characters
        description = prompt[:157].strip()
        if len(prompt) > 157:
            description += '...'
        
        return description
    
    def _extract_keywords(self, prompt: str) -> List[str]:
        """Extract relevant keywords from the prompt."""
        # Remove common words
        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'build', 'create', 'make', 'develop', 'design', 'that', 'this',
            'it', 'i', 'we', 'you', 'they', 'my', 'your', 'our'
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', prompt.lower())
        
        # Filter
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:10]  # Limit to 10 keywords
    
    def _escape(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))
    
    def generate_structured_data(self, metadata: SEOMetadata, url: str, type: str = 'WebApplication') -> str:
        """
        Generate JSON-LD structured data for rich snippets.
        """
        return f'''
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "{type}",
  "name": "{self._escape(metadata.title)}",
  "description": "{self._escape(metadata.description)}",
  "url": "{url}",
  "applicationCategory": "WebApplication",
  "operatingSystem": "Web Browser",
  "offers": {{
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  }}
}}
</script>
'''
    
    def generate_seo_head(self, prompt: str, project_name: str, url: str) -> str:
        """
        Generate complete SEO head section.
        """
        metadata = self.extract_seo_from_prompt(prompt, project_name)
        
        head = self.generate_meta_tags(metadata, url)
        head += self.generate_structured_data(metadata, url)
        
        return head


# Singleton
seo_service = SEOService()



