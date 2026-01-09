"""
Component-Based Library System

Building blocks, NOT whole projects.

Each project is decomposed into components:
- Navigation (header, sidebar, navbar)
- Hero (landing hero, minimal hero)
- Footer (simple, complex, newsletter)
- Card (product, profile, stats)
- Table (data table, sortable)
- Chart (line, bar, pie)
- Form (contact, login, signup)
- Modal (confirm, info, form)
- List (items, feed, timeline)
- Pricing (table, cards)
- Stats (bar, grid, cards)
- CTA (call to action)
- Feature (grid, list)

Generation Flow:
1. Decompose request into required components
2. For EACH component:
   - Search library for existing block
   - If found → Reuse
   - If not found → Generate with Opus 4.5 → Save to library
3. Compose app from blocks
4. If customer modifies → Version the block WITH NOTES
"""

import re
import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Cache for column existence check
_has_is_approved = None

def _check_has_is_approved_column():
    """Check if is_approved column exists in LibraryItem table."""
    global _has_is_approved
    if _has_is_approved is None:
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'code_library_libraryitem' 
                    AND column_name = 'is_approved'
                """)
                _has_is_approved = cursor.fetchone() is not None
        except Exception:
            _has_is_approved = False
    return _has_is_approved


class ComponentType(Enum):
    """Standard building block types."""
    NAVIGATION = "navigation"      # Header, sidebar, navbar
    HERO = "hero"                  # Landing hero sections
    FOOTER = "footer"              # Page footers
    CARD = "card"                  # Card components
    TABLE = "table"                # Data tables
    CHART = "chart"                # Chart wrappers
    FORM = "form"                  # Forms
    MODAL = "modal"                # Modal dialogs
    LIST = "list"                  # List displays
    PRICING = "pricing"            # Pricing sections
    STATS = "stats"                # Statistics displays
    CTA = "cta"                    # Call to action
    FEATURE = "feature"            # Feature showcases
    TESTIMONIAL = "testimonial"    # Testimonials
    GALLERY = "gallery"            # Image galleries
    DATA_FETCHER = "data_fetcher"  # API data fetching
    AUTH = "auth"                  # Authentication
    LAYOUT = "layout"              # Page layouts
    BUTTON = "button"              # Buttons
    INPUT = "input"                # Form inputs


@dataclass
class ComponentRequirement:
    """A required component for a project."""
    component_type: ComponentType
    variant: str  # e.g., "sidebar", "minimal", "dark"
    description: str  # What it should do
    priority: int  # 1=must have, 2=nice to have


@dataclass
class LibraryComponent:
    """A component from the library."""
    id: str
    component_type: ComponentType
    variant: str
    code: str
    version: str
    version_notes: str
    quality_score: float
    usage_count: int


@dataclass
class ComponentMatch:
    """Result of searching for a component."""
    found: bool
    component: Optional[LibraryComponent]
    score: float
    reason: str  # Why this was/wasn't matched


class ProjectDecomposer:
    """
    Decomposes a project request into required building blocks.
    
    CRITICAL: Layout and Navigation are "PERMANENT" components.
    They are NEVER dropped during the component limit phase.
    """
    
    # Components that MUST NEVER be dropped (structural)
    PERMANENT_COMPONENTS = {ComponentType.LAYOUT, ComponentType.NAVIGATION}
    
    # Maximum content components (excluding permanent ones)
    MAX_CONTENT_COMPONENTS = 5
    
    # Mapping of keywords to required components
    COMPONENT_TRIGGERS = {
        ComponentType.NAVIGATION: [
            'dashboard', 'admin', 'app', 'website', 'portal', 'platform',
            'navigation', 'menu', 'sidebar', 'header', 'navbar', 'management',
            'tracker', 'tool', 'system', 'builder', 'monitor', 'marketplace',
            'clinic', 'hospital', 'healthcare', 'fitness', 'supply', 'chain',
            'logistics', 'finance', 'banking', 'trading', 'crm', 'erp'
        ],
        ComponentType.HERO: [
            'landing', 'homepage', 'marketing', 'product page', 'hero',
            'welcome', 'intro', 'banner'
        ],
        ComponentType.FOOTER: [
            'website', 'landing', 'page', 'footer', 'contact info'
        ],
        ComponentType.CARD: [
            'cards', 'grid', 'gallery', 'products', 'items', 'profile',
            'portfolio', 'showcase', 'card', 'kanban', 'board', 'column',
            'project', 'task', 'property', 'listing', 'patient', 'shipment',
            'workout', 'exercise', 'recipe', 'job', 'crypto', 'stock'
        ],
        ComponentType.TABLE: [
            'table', 'data', 'list', 'records', 'spreadsheet', 'grid view',
            'admin', 'dashboard', 'analytics', 'inventory', 'patients',
            'shipments', 'transactions', 'orders', 'appointments'
        ],
        ComponentType.CHART: [
            'chart', 'graph', 'analytics', 'metrics', 'statistics',
            'visualization', 'dashboard', 'trends', 'data viz', 'progress',
            'performance', 'tracking', 'history'
        ],
        ComponentType.FORM: [
            'form', 'contact', 'signup', 'login', 'register', 'submit',
            'input', 'feedback', 'survey', 'application', 'booking',
            'appointment', 'checkout', 'add', 'create', 'new'
        ],
        ComponentType.MODAL: [
            'modal', 'popup', 'dialog', 'overlay', 'confirmation', 'buy',
            'purchase', 'confirm', 'details', 'preview'
        ],
        ComponentType.LIST: [
            'list', 'feed', 'timeline', 'activity', 'notifications',
            'items', 'todo', 'tasks', 'messages', 'alerts', 'updates',
            'shipments', 'workouts', 'prescriptions', 'history'
        ],
        ComponentType.PRICING: [
            'pricing', 'plans', 'subscription', 'tiers', 'packages'
        ],
        ComponentType.STATS: [
            'stats', 'metrics', 'kpi', 'overview', 'summary', 'dashboard',
            'numbers', 'analytics', 'totals', 'counts', 'revenue'
        ],
        ComponentType.CTA: [
            'cta', 'call to action', 'signup', 'get started', 'try now'
        ],
        ComponentType.FEATURE: [
            'features', 'benefits', 'services', 'capabilities', 'what we do'
        ],
        ComponentType.TESTIMONIAL: [
            'testimonials', 'reviews', 'quotes', 'feedback', 'customers say'
        ],
        ComponentType.GALLERY: [
            'gallery', 'images', 'photos', 'portfolio', 'showcase', 'artwork'
        ],
        ComponentType.DATA_FETCHER: [
            'api', 'fetch', 'real-time', 'live', 'data', 'stock', 'crypto',
            'weather', 'prices', 'external', 'tracker', 'monitor', 'trading'
        ],
        ComponentType.AUTH: [
            'login', 'signup', 'auth', 'register', 'password', 'user account'
        ],
    }
    
    # INDUSTRY VERTICAL TEMPLATES (Fix #4: Semantic Keyword Enrichment)
    INDUSTRY_TEMPLATES = {
        'healthcare': [
            (ComponentType.LAYOUT, 'app', 0),  # Priority 0 = permanent
            (ComponentType.NAVIGATION, 'sidebar', 0),
            (ComponentType.TABLE, 'data', 1),
            (ComponentType.CARD, 'patient', 1),
            (ComponentType.FORM, 'appointment', 2),
            (ComponentType.LIST, 'prescriptions', 2),
        ],
        'logistics': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'sidebar', 0),
            (ComponentType.TABLE, 'shipments', 1),
            (ComponentType.CHART, 'line', 1),
            (ComponentType.LIST, 'alerts', 2),
            (ComponentType.STATS, 'cards', 1),
        ],
        'fintech': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'sidebar', 0),
            (ComponentType.CHART, 'line', 1),
            (ComponentType.TABLE, 'transactions', 1),
            (ComponentType.STATS, 'cards', 1),
            (ComponentType.DATA_FETCHER, 'default', 1),
        ],
        'fitness': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'header', 0),
            (ComponentType.CARD, 'workout', 1),
            (ComponentType.CHART, 'line', 1),
            (ComponentType.LIST, 'activity', 2),
            (ComponentType.FORM, 'log', 2),
        ],
        'real_estate': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'header', 0),
            (ComponentType.CARD, 'property', 1),
            (ComponentType.FORM, 'contact', 2),
            (ComponentType.LIST, 'listings', 1),
            (ComponentType.GALLERY, 'grid', 2),
        ],
    }
    
    # Standard project templates (Priority 0 = PERMANENT, never dropped)
    PROJECT_TEMPLATES = {
        'dashboard': [
            (ComponentType.LAYOUT, 'app', 0),  # PERMANENT
            (ComponentType.NAVIGATION, 'sidebar', 0),  # PERMANENT
            (ComponentType.STATS, 'cards', 1),
            (ComponentType.CHART, 'line', 1),
            (ComponentType.TABLE, 'data', 2),
        ],
        'landing': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'header', 0),
            (ComponentType.HERO, 'full', 1),
            (ComponentType.FEATURE, 'grid', 1),
            (ComponentType.CTA, 'centered', 2),
            (ComponentType.FOOTER, 'full', 2),
        ],
        'ecommerce': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'header', 0),
            (ComponentType.CARD, 'product', 1),
            (ComponentType.PRICING, 'simple', 2),
            (ComponentType.FOOTER, 'full', 2),
        ],
        'portfolio': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'minimal', 0),
            (ComponentType.HERO, 'personal', 1),
            (ComponentType.GALLERY, 'grid', 1),
            (ComponentType.FOOTER, 'simple', 2),
        ],
        'task_management': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'header', 0),
            (ComponentType.CARD, 'kanban', 1),
            (ComponentType.LIST, 'tasks', 1),
            (ComponentType.FORM, 'default', 2),
            (ComponentType.MODAL, 'default', 2),
        ],
        'crm': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'sidebar', 0),
            (ComponentType.CARD, 'contact', 1),
            (ComponentType.TABLE, 'data', 1),
            (ComponentType.FORM, 'default', 2),
            (ComponentType.STATS, 'cards', 2),
        ],
        'tracker': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'sidebar', 0),
            (ComponentType.DATA_FETCHER, 'default', 1),
            (ComponentType.CHART, 'line', 1),
            (ComponentType.TABLE, 'data', 1),
            (ComponentType.STATS, 'cards', 2),
        ],
        # NEW: Blog/Content template
        'blog': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'header', 0),
            (ComponentType.CARD, 'article', 1),
            (ComponentType.LIST, 'feed', 1),
            (ComponentType.FORM, 'comment', 2),
            (ComponentType.FOOTER, 'simple', 2),
        ],
        # NEW: Personal/Static portfolio (different from investment portfolio)
        'personal_portfolio': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'minimal', 0),
            (ComponentType.HERO, 'personal', 1),
            (ComponentType.GALLERY, 'grid', 1),
            (ComponentType.CARD, 'project', 1),
            (ComponentType.FORM, 'contact', 2),
            (ComponentType.FOOTER, 'simple', 2),
        ],
        # NEW: Form-focused apps
        'form_app': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'header', 0),
            (ComponentType.FORM, 'multi_step', 1),
            (ComponentType.MODAL, 'confirmation', 2),
        ],
        # NEW: Documentation/Help site
        'docs': [
            (ComponentType.LAYOUT, 'app', 0),
            (ComponentType.NAVIGATION, 'sidebar', 0),
            (ComponentType.LIST, 'toc', 1),
            (ComponentType.CARD, 'article', 1),
        ],
    }
    
    def decompose(self, prompt: str) -> List[ComponentRequirement]:
        """
        Decompose a project request into required building blocks.
        
        CRITICAL: Layout and Navigation are PERMANENT - never dropped.
        
        Returns a list of ComponentRequirement objects.
        """
        prompt_lower = prompt.lower()
        requirements = []
        seen_types = set()
        
        # First, check industry vertical templates
        industry_template = self._match_industry(prompt_lower)
        if industry_template:
            print(f"[DECOMPOSER] Matched industry template")
            for comp_type, variant, priority in industry_template:
                if comp_type not in seen_types:
                    requirements.append(ComponentRequirement(
                        component_type=comp_type,
                        variant=variant,
                        description=f"{comp_type.value} component for: {prompt[:100]}",
                        priority=priority
                    ))
                    seen_types.add(comp_type)
        
        # Then check standard project templates
        if not requirements:
            template = self._match_template(prompt_lower)
            if template:
                for comp_type, variant, priority in template:
                    if comp_type not in seen_types:
                        requirements.append(ComponentRequirement(
                            component_type=comp_type,
                            variant=variant,
                            description=f"{comp_type.value} component for: {prompt[:100]}",
                            priority=priority
                        ))
                        seen_types.add(comp_type)
        
        # Then add any additional triggered components
        for comp_type, triggers in self.COMPONENT_TRIGGERS.items():
            if comp_type in seen_types:
                continue
                
            for trigger in triggers:
                if trigger in prompt_lower:
                    variant = self._infer_variant(comp_type, prompt_lower)
                    requirements.append(ComponentRequirement(
                        component_type=comp_type,
                        variant=variant,
                        description=f"{comp_type.value} for: {prompt[:100]}",
                        priority=2
                    ))
                    seen_types.add(comp_type)
                    break
        
        # ALWAYS include layout and navigation (PERMANENT components)
        if ComponentType.LAYOUT not in seen_types:
            requirements.insert(0, ComponentRequirement(
                component_type=ComponentType.LAYOUT,
                variant='app',
                description=f"Main layout wrapper for: {prompt[:100]}",
                priority=0  # PERMANENT
            ))
            seen_types.add(ComponentType.LAYOUT)
        
        if ComponentType.NAVIGATION not in seen_types and len(requirements) >= 2:
            nav_variant = 'sidebar' if 'dashboard' in prompt_lower or 'admin' in prompt_lower else 'header'
            requirements.insert(1, ComponentRequirement(
                component_type=ComponentType.NAVIGATION,
                variant=nav_variant,
                description=f"Navigation for: {prompt[:100]}",
                priority=0  # PERMANENT
            ))
            seen_types.add(ComponentType.NAVIGATION)
        
        print(f"[DECOMPOSER] Decomposed into {len(requirements)} components: {[r.component_type.value for r in requirements]}")
        
        return requirements
    
    def _match_industry(self, prompt: str) -> Optional[List[Tuple]]:
        """Match prompt to an industry vertical template."""
        
        # EXCLUSIONS: These should NOT match industry templates
        # Personal portfolio is a STATIC site, not a fintech app
        if 'personal portfolio' in prompt or 'my portfolio' in prompt:
            return None  # Let it match standard portfolio template instead
        
        # Healthcare
        if any(kw in prompt for kw in ['healthcare', 'patient', 'clinic', 'hospital', 'medical', 'prescription', 'appointment']):
            return self.INDUSTRY_TEMPLATES['healthcare']
        # Logistics / Supply Chain
        elif any(kw in prompt for kw in ['supply chain', 'logistics', 'shipment', 'warehouse', 'inventory', 'shipping', 'port', 'freight']):
            return self.INDUSTRY_TEMPLATES['logistics']
        # Fintech / Finance - but NOT personal portfolios
        elif any(kw in prompt for kw in ['stock', 'crypto', 'trading', 'finance', 'banking', 'investment', 'market']):
            return self.INDUSTRY_TEMPLATES['fintech']
        # Investment portfolio (financial) vs personal portfolio (work samples)
        elif 'portfolio' in prompt and any(kw in prompt for kw in ['invest', 'fund', 'asset', 'return', 'dividend']):
            return self.INDUSTRY_TEMPLATES['fintech']
        # Fitness
        elif any(kw in prompt for kw in ['fitness', 'workout', 'exercise', 'gym', 'training', 'health tracker']):
            return self.INDUSTRY_TEMPLATES['fitness']
        # Real Estate
        elif any(kw in prompt for kw in ['real estate', 'property', 'listing', 'housing', 'apartment', 'rental', 'home']):
            return self.INDUSTRY_TEMPLATES['real_estate']
        return None
    
    def _match_template(self, prompt: str) -> Optional[List[Tuple]]:
        """Match prompt to a project template."""
        
        # Tracker types (crypto, stock, etc.)
        if any(kw in prompt for kw in ['tracker', 'monitor', 'real-time', 'live prices', 'tracking']):
            return self.PROJECT_TEMPLATES['tracker']
        
        # Blog/Content sites (BEFORE portfolio check)
        elif any(kw in prompt for kw in ['blog', 'articles', 'posts', 'content', 'news site', 'magazine']):
            return self.PROJECT_TEMPLATES['blog']
        
        # Documentation/Help sites
        elif any(kw in prompt for kw in ['documentation', 'docs', 'help center', 'knowledge base', 'wiki']):
            return self.PROJECT_TEMPLATES['docs']
        
        # Personal portfolio (work samples, NOT investment)
        elif any(kw in prompt for kw in ['personal portfolio', 'my portfolio', 'developer portfolio', 'designer portfolio', 'work samples']):
            return self.PROJECT_TEMPLATES['personal_portfolio']
        
        # Form-focused apps
        elif any(kw in prompt for kw in ['survey', 'questionnaire', 'application form', 'multi-step form', 'wizard']):
            return self.PROJECT_TEMPLATES['form_app']
        
        # Task management (more specific)
        elif any(kw in prompt for kw in ['task', 'kanban', 'todo', 'project management', 'task management']):
            return self.PROJECT_TEMPLATES['task_management']
        
        # CRM
        elif 'crm' in prompt or 'customer relationship' in prompt or 'contact management' in prompt:
            return self.PROJECT_TEMPLATES['crm']
        
        # Dashboard
        elif 'dashboard' in prompt or 'admin' in prompt or 'analytics' in prompt:
            return self.PROJECT_TEMPLATES['dashboard']
        
        # Landing page
        elif 'landing' in prompt or 'marketing' in prompt or 'homepage' in prompt:
            return self.PROJECT_TEMPLATES['landing']
        
        # E-commerce
        elif 'ecommerce' in prompt or 'shop' in prompt or 'store' in prompt or 'catalog' in prompt:
            return self.PROJECT_TEMPLATES['ecommerce']
        
        # Generic portfolio (fallback)
        elif 'portfolio' in prompt:
            return self.PROJECT_TEMPLATES['portfolio']
        
        return None
    
    def _infer_variant(self, comp_type: ComponentType, prompt: str) -> str:
        """Infer the best variant based on context."""
        if comp_type == ComponentType.NAVIGATION:
            if 'sidebar' in prompt:
                return 'sidebar'
            elif 'minimal' in prompt:
                return 'minimal'
            else:
                return 'header'
        elif comp_type == ComponentType.HERO:
            if 'minimal' in prompt:
                return 'minimal'
            elif 'video' in prompt:
                return 'video'
            else:
                return 'full'
        elif comp_type == ComponentType.CHART:
            if 'bar' in prompt:
                return 'bar'
            elif 'pie' in prompt:
                return 'pie'
            else:
                return 'line'
        # Default variant
        return 'default'


class ComponentLibrary:
    """
    Manages the component library - searching and saving building blocks.
    """
    
    def __init__(self):
        from apps.code_library.models import LibraryItem
        self.model = LibraryItem
    
    def search(self, requirement: ComponentRequirement) -> ComponentMatch:
        """
        Search for a component matching the requirement.
        
        Returns ComponentMatch with:
        - found: True if a good match exists
        - component: The matching component (if found)
        - score: Match quality (0-100)
        - reason: Why this was/wasn't a good match
        """
        # Search by component_type + variant
        # Build filter - handle missing is_approved column
        filters = {'is_active': True, 'item_type': 'component'}
        if _check_has_is_approved_column():
            filters['is_approved'] = True
        
        items = self.model.objects.filter(**filters).order_by('-quality_score', '-usage_count')
        
        best_match = None
        best_score = 0
        best_reason = "No matching components found"
        
        for item in items:
            score = 0
            reasons = []
            
            # Check component type match (from tags/keywords)
            item_type = self._extract_component_type(item)
            if item_type == requirement.component_type.value:
                score += 50
                reasons.append(f"Type match: {item_type}")
            
            # Check variant match
            item_variant = self._extract_variant(item)
            if item_variant and item_variant == requirement.variant:
                score += 30
                reasons.append(f"Variant match: {item_variant}")
            elif item_variant:
                score += 10  # Partial credit for having a variant
                reasons.append(f"Different variant: {item_variant}")
            
            # Quality bonus
            score += item.quality_score * 10
            
            # Usage bonus (proven to work)
            score += min(item.usage_count, 10)
            
            if score > best_score:
                best_score = score
                best_match = item
                best_reason = "; ".join(reasons)
        
        # Threshold for "good enough" match
        # Lowered from 40 to 20 to enable more component reuse
        MATCH_THRESHOLD = 20
        
        if best_score >= MATCH_THRESHOLD and best_match:
            return ComponentMatch(
                found=True,
                component=self._to_library_component(best_match),
                score=best_score,
                reason=best_reason
            )
        
        return ComponentMatch(
            found=False,
            component=None,
            score=best_score,
            reason=best_reason or "No matching components"
        )
    
    def save_component(
        self,
        code: str,
        component_type: ComponentType,
        variant: str,
        description: str,
        version: str = "1.0.0",
        version_notes: str = "Initial version",
        parent_id: str = None
    ) -> str:
        """
        Save a new component to the library.

        CRITICAL: Check for duplicates first!
        PHASE 1: Validate component is browser-ready before saving.
        Returns the component ID.
        """
        import re
        from .jsx_validator import validate_jsx

        # PHASE 1: Validate component before saving
        is_valid, error = validate_jsx(code)
        if not is_valid:
            print(f"[LIBRARY] [WARN] Component validation failed: {error}")
            # Still save but mark for review
            version_notes = f"[NEEDS FIX] {error}\n\n{version_notes}"

        # Check for TypeScript that would require transformation
        has_complex_ts = bool(re.search(r'<\w+\s*extends\s+\w+>', code)) or \
                         bool(re.search(r':\s*\w+\[\]', code)) or \
                         bool(re.search(r'as\s+\w+', code))
        if has_complex_ts:
            print(f"[LIBRARY] [WARN] Component has TypeScript that may need transformation")

        name = f"{component_type.value.title()} - {variant.title()}"
        slug = f"{component_type.value}-{variant}-{version}".lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        
        # DUPLICATE CHECK: Don't save if we already have this component type+variant
        existing = self.model.objects.filter(
            item_type='component',
            is_active=True,
            name=name  # Match by name (type + variant)
        ).first()
        
        if existing:
            print(f"[LIBRARY] Component '{name}' already exists (id={existing.id}), skipping save")
            return str(existing.id)
        
        # Create rich documentation
        doc = f"""
## {name}

**Type:** {component_type.value}
**Variant:** {variant}
**Version:** {version}

### Version Notes
{version_notes}

### Usage
Import and use this component in your app:
```jsx
import {component_type.value.title()}{variant.title()} from './components/{component_type.value}';

// In your render:
<{component_type.value.title()}{variant.title()} />
```

### Customization
This component can be customized by passing props or modifying styles.
"""
        
        # Build creation kwargs - handle missing columns
        create_kwargs = {
            'name': name,
            'slug': slug,
            'description': description,
            'usage_example': f'<{component_type.value.title()}{variant.title()} />',
            'documentation': doc,
            'item_type': 'component',  # COMPONENT, not template
            'language': 'jsx',  # PHASE 1: Browser-ready, no transformation needed
            'code': code,
            'keywords': [component_type.value, variant, 'building-block'],
            'tags': [component_type.value, variant],
            'embedding_model': '',
            'dependencies': [],
            'source': 'generated',
            'source_url': '',
            'quality_score': 0.7,  # Default quality
            'is_active': True,
            'is_public': True,
            'is_deprecated': False,
            'deprecation_note': '',
            'needs_review': True,
            'created_by': 'ai'
        }
        
        # Add is_approved only if column exists
        if _check_has_is_approved_column():
            create_kwargs['is_approved'] = True
        
        item = self.model.objects.create(**create_kwargs)
        
        print(f"[LIBRARY] [OK] Saved component: {name} v{version} ({item.id})")
        
        return str(item.id)
    
    def create_version(
        self,
        parent_id: str,
        new_code: str,
        version_notes: str  # REQUIRED - why is this version needed?
    ) -> str:
        """
        Create a new version of an existing component.
        
        version_notes MUST explain why this version is needed,
        to prevent library bloat.
        """
        if not version_notes or len(version_notes) < 20:
            raise ValueError(
                "version_notes is REQUIRED and must explain why this "
                "version is needed (at least 20 characters)"
            )
        
        parent = self.model.objects.get(id=parent_id)
        
        # Parse current version
        current = parent.version if hasattr(parent, 'version') else "1.0.0"
        parts = current.split('.')
        new_version = f"{parts[0]}.{int(parts[1]) + 1}.0"
        
        # Extract type and variant from parent
        comp_type = self._extract_component_type(parent)
        variant = self._extract_variant(parent)
        
        # Mark parent as having a newer version
        parent.deprecation_note = f"Newer version available: {new_version}"
        parent.save()
        
        # Create new version
        return self.save_component(
            code=new_code,
            component_type=ComponentType(comp_type),
            variant=variant,
            description=f"Updated version of {parent.name}. {version_notes}",
            version=new_version,
            version_notes=version_notes,
            parent_id=parent_id
        )
    
    def _extract_component_type(self, item) -> str:
        """Extract component type from item."""
        keywords = item.keywords if isinstance(item.keywords, list) else []
        for kw in keywords:
            try:
                ComponentType(kw)
                return kw
            except ValueError:
                continue
        
        # Infer from name
        name_lower = item.name.lower()
        for ct in ComponentType:
            if ct.value in name_lower:
                return ct.value
        
        return 'unknown'
    
    def _extract_variant(self, item) -> str:
        """Extract variant from item."""
        keywords = item.keywords if isinstance(item.keywords, list) else []
        tags = item.tags if isinstance(item.tags, list) else []
        
        all_terms = keywords + tags
        component_types = [ct.value for ct in ComponentType]
        
        for term in all_terms:
            if term not in component_types and term != 'building-block':
                return term
        
        return 'default'
    
    def _to_library_component(self, item) -> LibraryComponent:
        """Convert DB item to LibraryComponent."""
        return LibraryComponent(
            id=str(item.id),
            component_type=ComponentType(self._extract_component_type(item)),
            variant=self._extract_variant(item),
            code=item.code,
            version=getattr(item, 'version', '1.0.0'),
            version_notes=item.deprecation_note or 'Original version',
            quality_score=item.quality_score,
            usage_count=item.usage_count
        )


class ComponentComposer:
    """
    Composes a complete app from building blocks.
    """
    
    def _strip_exports_and_imports(self, code: str) -> str:
        """
        Remove export default statements and React imports from component code.
        This allows combining multiple components into a single file.
        """
        import re
        
        # Remove export default statements
        code = re.sub(r'export\s+default\s+\w+\s*;?\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'export\s+default\s+function', 'function', code)
        code = re.sub(r'export\s+default\s+const', 'const', code)
        
        # Remove import React statements (we'll add one at the top)
        code = re.sub(r'import\s+React[^;]*;?\s*\n?', '', code)
        code = re.sub(r'import\s*\{[^}]*\}\s*from\s*[\'"]react[\'"];?\s*\n?', '', code)
        
        return code.strip()
    
    def compose(
        self,
        components: Dict[str, str],  # {component_name: code}
        app_description: str
    ) -> str:
        """
        Compose multiple components into a single App.tsx.
        
        CRITICAL: Each component may have its own exports/imports.
        We must strip those and combine properly.
        """
        # Build imports - collect unique hooks from all components
        all_hooks = set()
        for code in components.values():
            if 'useState' in code:
                all_hooks.add('useState')
            if 'useEffect' in code:
                all_hooks.add('useEffect')
            if 'useRef' in code:
                all_hooks.add('useRef')
            if 'useCallback' in code:
                all_hooks.add('useCallback')
            if 'useMemo' in code:
                all_hooks.add('useMemo')
        
        if all_hooks:
            imports = [f"import React, {{ {', '.join(sorted(all_hooks))} }} from 'react';"]
        else:
            imports = ["import React from 'react';"]
        
        # Build component definitions - strip exports from each
        definitions = []
        usage = []
        
        for name, code in components.items():
            # Clean the component code
            clean_code = self._strip_exports_and_imports(code)
            if not clean_code:
                continue
            
            # Extract component function name
            clean_name = name.replace('-', '').replace('_', '').title().replace(' ', '')
            
            definitions.append(f"// {name} component")
            definitions.append(clean_code)
            definitions.append("")
            
            usage.append(f"      <{clean_name} />")
        
        # Build final app with SINGLE export default
        app = f"""
{chr(10).join(imports)}

{chr(10).join(definitions)}

function App() {{
  return (
    <div className="app">
{chr(10).join(usage)}
    </div>
  );
}}

export default App;
"""
        return app

