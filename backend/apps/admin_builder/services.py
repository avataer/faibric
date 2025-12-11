"""
Admin builder services.
"""
import logging
from typing import List, Dict, Optional
from django.db import transaction

from .models import (
    AdminBuilderConfig, AdminPage, Widget, DataSource,
    AdminTemplate, ExportedAdmin
)
from .templates_library import get_all_templates, get_template

logger = logging.getLogger(__name__)


class AdminBuilderService:
    """Service for admin panel building."""
    
    def __init__(self, tenant: 'Tenant'):
        self.tenant = tenant
        self._config = None
    
    @property
    def config(self) -> AdminBuilderConfig:
        if self._config is None:
            self._config, _ = AdminBuilderConfig.objects.get_or_create(
                tenant=self.tenant
            )
        return self._config
    
    # ============= PAGES =============
    
    def get_pages(self, published_only: bool = False) -> List[AdminPage]:
        """Get all pages."""
        qs = AdminPage.objects.filter(tenant=self.tenant)
        if published_only:
            qs = qs.filter(is_published=True)
        return list(qs.prefetch_related('widgets'))
    
    def get_page(self, page_id: str) -> Optional[AdminPage]:
        """Get a page by ID."""
        try:
            return AdminPage.objects.prefetch_related('widgets').get(
                id=page_id,
                tenant=self.tenant
            )
        except AdminPage.DoesNotExist:
            return None
    
    def get_page_by_slug(self, slug: str) -> Optional[AdminPage]:
        """Get a page by slug."""
        try:
            return AdminPage.objects.prefetch_related('widgets').get(
                slug=slug,
                tenant=self.tenant
            )
        except AdminPage.DoesNotExist:
            return None
    
    @transaction.atomic
    def create_page(self, data: dict) -> AdminPage:
        """Create a new page."""
        page = AdminPage.objects.create(
            tenant=self.tenant,
            **data
        )
        return page
    
    @transaction.atomic
    def update_page(self, page: AdminPage, data: dict) -> AdminPage:
        """Update a page."""
        for field, value in data.items():
            setattr(page, field, value)
        page.save()
        return page
    
    def delete_page(self, page: AdminPage) -> bool:
        """Delete a page."""
        page.delete()
        return True
    
    # ============= WIDGETS =============
    
    def get_widgets(self, page: AdminPage) -> List[Widget]:
        """Get widgets for a page."""
        return list(page.widgets.all())
    
    @transaction.atomic
    def create_widget(self, page: AdminPage, data: dict) -> Widget:
        """Create a widget on a page."""
        widget = Widget.objects.create(
            page=page,
            **data
        )
        return widget
    
    @transaction.atomic
    def update_widget(self, widget: Widget, data: dict) -> Widget:
        """Update a widget."""
        for field, value in data.items():
            setattr(widget, field, value)
        widget.save()
        return widget
    
    def delete_widget(self, widget: Widget) -> bool:
        """Delete a widget."""
        widget.delete()
        return True
    
    # ============= DATA SOURCES =============
    
    def get_data_sources(self) -> List[DataSource]:
        """Get all data sources."""
        return list(DataSource.objects.filter(tenant=self.tenant))
    
    def get_data_source(self, ds_id: str) -> Optional[DataSource]:
        """Get a data source by ID."""
        try:
            return DataSource.objects.get(id=ds_id, tenant=self.tenant)
        except DataSource.DoesNotExist:
            return None
    
    @transaction.atomic
    def create_data_source(self, data: dict) -> DataSource:
        """Create a data source."""
        return DataSource.objects.create(
            tenant=self.tenant,
            **data
        )
    
    @transaction.atomic
    def update_data_source(self, ds: DataSource, data: dict) -> DataSource:
        """Update a data source."""
        for field, value in data.items():
            setattr(ds, field, value)
        ds.save()
        return ds
    
    def delete_data_source(self, ds: DataSource) -> bool:
        """Delete a data source."""
        ds.delete()
        return True
    
    def fetch_data_source(self, ds: DataSource, query: dict = None) -> Dict:
        """Fetch data from a data source."""
        from apps.checkout.models import Order, Product
        from apps.cabinet.models import EndUser, SupportTicket
        from apps.storage.models import File
        from apps.analytics.models import Event
        
        source_type = ds.source_type
        data = []
        
        if source_type == 'checkout_orders':
            orders = Order.objects.filter(tenant=self.tenant)
            data = list(orders.values('id', 'order_number', 'customer_email', 'status', 'total_amount', 'created_at'))
        
        elif source_type == 'checkout_products':
            products = Product.objects.filter(tenant=self.tenant)
            data = list(products.values('id', 'name', 'price', 'sku', 'is_active', 'inventory_quantity'))
        
        elif source_type == 'cabinet_users':
            users = EndUser.objects.filter(tenant=self.tenant)
            data = list(users.values('id', 'email', 'first_name', 'last_name', 'is_active', 'created_at'))
        
        elif source_type == 'cabinet_tickets':
            tickets = SupportTicket.objects.filter(tenant=self.tenant)
            data = list(tickets.values('id', 'ticket_number', 'subject', 'status', 'priority', 'created_at'))
        
        elif source_type == 'storage_files':
            files = File.objects.filter(tenant=self.tenant, is_deleted=False)
            data = list(files.values('id', 'original_name', 'content_type', 'file_size', 'created_at'))
        
        elif source_type == 'analytics_events':
            events = Event.objects.filter(tenant=self.tenant)[:1000]
            data = list(events.values('id', 'event_name', 'properties', 'timestamp'))
        
        elif source_type == 'static':
            data = ds.config.get('data', [])
        
        elif source_type == 'api':
            import requests
            try:
                config = ds.config
                response = requests.request(
                    method=config.get('method', 'GET'),
                    url=config.get('url'),
                    headers=config.get('headers', {}),
                    timeout=10
                )
                data = response.json()
            except Exception as e:
                logger.error(f"API data source fetch failed: {e}")
                data = []
        
        return {'data': data, 'count': len(data)}
    
    # ============= TEMPLATES =============
    
    def get_templates(self, category: str = None) -> List[Dict]:
        """Get available templates."""
        templates = get_all_templates()
        if category:
            templates = [t for t in templates if t['category'] == category]
        return templates
    
    def get_template(self, slug: str) -> Optional[Dict]:
        """Get a specific template."""
        return get_template(slug)
    
    @transaction.atomic
    def apply_template(self, template_slug: str) -> List[AdminPage]:
        """Apply a template to create pages."""
        template = get_template(template_slug)
        if not template:
            raise ValueError(f"Template '{template_slug}' not found")
        
        created_pages = []
        
        # Create data sources first
        ds_map = {}
        for ds_def in template.get('data_sources', []):
            ds = DataSource.objects.create(
                tenant=self.tenant,
                name=ds_def['name'],
                source_type=ds_def['source_type'],
                config=ds_def.get('config', {})
            )
            ds_map[ds_def['name']] = ds
        
        # Create pages
        for page_def in template.get('pages', []):
            page = AdminPage.objects.create(
                tenant=self.tenant,
                name=page_def['name'],
                slug=page_def['slug'],
                title=page_def['title'],
                icon=page_def.get('icon', ''),
                page_type=page_def.get('page_type', 'custom'),
                nav_order=page_def.get('nav_order', 0),
                layout=page_def.get('layout', {}),
                data_source=ds_map.get(page_def.get('data_source'))
            )
            
            # Create widgets
            for widget_def in page_def.get('widgets', []):
                Widget.objects.create(
                    page=page,
                    name=widget_def['name'],
                    widget_type=widget_def['widget_type'],
                    config=widget_def.get('config', {}),
                    style=widget_def.get('style', {})
                )
            
            created_pages.append(page)
        
        # Apply theme to config
        theme = template.get('theme', {})
        if theme:
            self.config.primary_color = theme.get('primaryColor', self.config.primary_color)
            self.config.secondary_color = theme.get('secondaryColor', self.config.secondary_color)
            self.config.save()
        
        return created_pages
    
    # ============= EXPORT =============
    
    @transaction.atomic
    def export_to_react(self, name: str = None) -> ExportedAdmin:
        """Export the admin panel to React code."""
        pages = self.get_pages(published_only=True)
        
        code = {
            'files': {},
            'package_json': self._generate_package_json(),
        }
        
        # Generate App.tsx
        code['files']['App.tsx'] = self._generate_app_tsx(pages)
        
        # Generate pages
        for page in pages:
            filename = f"pages/{page.slug.replace('-', '_').title()}.tsx"
            code['files'][filename] = self._generate_page_tsx(page)
        
        # Generate layout
        code['files']['Layout.tsx'] = self._generate_layout_tsx(pages)
        
        export = ExportedAdmin.objects.create(
            tenant=self.tenant,
            name=name or f"{self.config.admin_name} Export",
            code=code,
            build_status='success'
        )
        
        return export
    
    def _generate_package_json(self) -> str:
        return '''{
  "name": "admin-panel",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.0.0",
    "recharts": "^2.10.0"
  }
}'''
    
    def _generate_app_tsx(self, pages: List[AdminPage]) -> str:
        routes = '\n'.join([
            f'        <Route path="/{p.slug}" element={{<{p.slug.replace("-", "_").title()} />}} />'
            for p in pages
        ])
        
        imports = '\n'.join([
            f"import {p.slug.replace('-', '_').title()} from './pages/{p.slug.replace('-', '_').title()}';"
            for p in pages
        ])
        
        return f'''import React from 'react';
import {{ BrowserRouter, Routes, Route }} from 'react-router-dom';
import Layout from './Layout';
{imports}

function App() {{
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
{routes}
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}}

export default App;
'''
    
    def _generate_layout_tsx(self, pages: List[AdminPage]) -> str:
        nav_items = '\n'.join([
            f'        <NavLink to="/{p.slug}">{p.icon} {p.name}</NavLink>'
            for p in pages if p.show_in_nav
        ])
        
        return f'''import React from 'react';
import {{ NavLink }} from 'react-router-dom';

const Layout = ({{ children }}) => {{
  return (
    <div className="admin-layout">
      <nav className="sidebar">
{nav_items}
      </nav>
      <main className="content">
        {{children}}
      </main>
    </div>
  );
}};

export default Layout;
'''
    
    def _generate_page_tsx(self, page: AdminPage) -> str:
        return f'''import React from 'react';

const {page.slug.replace('-', '_').title()} = () => {{
  return (
    <div className="page">
      <h1>{page.title}</h1>
      {{/* Page content */}}
    </div>
  );
}};

export default {page.slug.replace('-', '_').title()};
'''







