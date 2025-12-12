import uuid
from django.db import models
from django.utils import timezone


class AdminBuilderConfig(models.Model):
    """
    Admin builder configuration for a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='admin_builder_config'
    )
    
    # Branding
    admin_name = models.CharField(max_length=100, default='Admin Panel')
    logo_url = models.URLField(blank=True)
    favicon_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, default='#3B82F6')
    secondary_color = models.CharField(max_length=7, default='#10B981')
    
    # Theme
    theme = models.CharField(max_length=20, default='light', choices=[
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System')
    ])
    
    # Features
    allow_custom_css = models.BooleanField(default=True)
    allow_custom_js = models.BooleanField(default=False)
    
    # Custom code
    custom_css = models.TextField(blank=True)
    custom_head_html = models.TextField(blank=True)
    
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Admin config for {self.tenant.name}"


class AdminPage(models.Model):
    """
    A page in the admin panel.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='admin_pages'
    )
    
    # Page info
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    
    # Parent for nested navigation
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    
    # Layout
    layout = models.JSONField(default=dict, blank=True)
    # Format: { "rows": [{ "columns": [{ "width": 6, "widgets": ["widget_id"] }] }] }
    
    # Page type
    page_type = models.CharField(max_length=20, default='custom', choices=[
        ('dashboard', 'Dashboard'),
        ('list', 'List View'),
        ('form', 'Form'),
        ('detail', 'Detail View'),
        ('custom', 'Custom')
    ])
    
    # Data source for list/detail pages
    data_source = models.ForeignKey(
        'DataSource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pages'
    )
    
    # Navigation
    show_in_nav = models.BooleanField(default=True)
    nav_order = models.PositiveIntegerField(default=0)
    
    # Permissions
    requires_auth = models.BooleanField(default=True)
    allowed_roles = models.JSONField(default=list, blank=True)
    
    # Status
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['nav_order', 'name']
        unique_together = [['tenant', 'slug']]
    
    def __str__(self):
        return self.name
    
    def publish(self):
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=['is_published', 'published_at'])


class Widget(models.Model):
    """
    A widget instance on a page.
    """
    WIDGET_TYPES = [
        ('chart_bar', 'Bar Chart'),
        ('chart_line', 'Line Chart'),
        ('chart_pie', 'Pie Chart'),
        ('chart_area', 'Area Chart'),
        ('stat_card', 'Stat Card'),
        ('table', 'Data Table'),
        ('form', 'Form'),
        ('text', 'Text/HTML'),
        ('image', 'Image'),
        ('button', 'Button'),
        ('card', 'Card'),
        ('list', 'List'),
        ('calendar', 'Calendar'),
        ('map', 'Map'),
        ('video', 'Video'),
        ('iframe', 'IFrame'),
        ('divider', 'Divider'),
        ('spacer', 'Spacer'),
        ('tabs', 'Tabs'),
        ('accordion', 'Accordion'),
        ('modal', 'Modal Trigger'),
        ('custom', 'Custom Component'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(
        AdminPage,
        on_delete=models.CASCADE,
        related_name='widgets'
    )
    
    # Widget info
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=30, choices=WIDGET_TYPES)
    
    # Configuration
    config = models.JSONField(default=dict, blank=True)
    # Config depends on widget type, e.g.:
    # chart: { "data_source": "...", "x_axis": "date", "y_axis": "value" }
    # table: { "columns": [...], "pagination": true }
    # form: { "fields": [...], "submit_action": "..." }
    
    # Styling
    style = models.JSONField(default=dict, blank=True)
    # { "width": "100%", "padding": "16px", "backgroundColor": "#fff" }
    
    # Data binding
    data_source = models.ForeignKey(
        'DataSource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='widgets'
    )
    data_query = models.JSONField(default=dict, blank=True)
    # { "filters": [...], "sort": {...}, "limit": 10 }
    
    # Visibility
    is_visible = models.BooleanField(default=True)
    visibility_conditions = models.JSONField(default=list, blank=True)
    # [{ "field": "user.role", "operator": "equals", "value": "admin" }]
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.widget_type})"


class DataSource(models.Model):
    """
    Data source for widgets (API, database, static).
    """
    SOURCE_TYPES = [
        ('api', 'External API'),
        ('database', 'Database Collection'),
        ('static', 'Static Data'),
        ('checkout_orders', 'Checkout Orders'),
        ('checkout_products', 'Checkout Products'),
        ('cabinet_users', 'Cabinet Users'),
        ('cabinet_tickets', 'Support Tickets'),
        ('storage_files', 'Storage Files'),
        ('analytics_events', 'Analytics Events'),
        ('custom', 'Custom Query'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='data_sources'
    )
    
    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES)
    
    # Configuration based on source type
    config = models.JSONField(default=dict, blank=True)
    # api: { "url": "...", "method": "GET", "headers": {...} }
    # database: { "collection": "users" }
    # static: { "data": [...] }
    
    # Caching
    cache_enabled = models.BooleanField(default=True)
    cache_ttl_seconds = models.PositiveIntegerField(default=300)
    
    # Transformation
    transform = models.TextField(blank=True)
    # JavaScript function to transform data
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.source_type})"


class AdminTemplate(models.Model):
    """
    Pre-built admin panel template.
    """
    CATEGORIES = [
        ('dashboard', 'Dashboard'),
        ('ecommerce', 'E-Commerce'),
        ('crm', 'CRM'),
        ('cms', 'Content Management'),
        ('analytics', 'Analytics'),
        ('project', 'Project Management'),
        ('hr', 'HR Management'),
        ('finance', 'Finance'),
        ('support', 'Support/Helpdesk'),
        ('social', 'Social Media'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template info
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORIES)
    
    # Preview
    thumbnail_url = models.URLField(blank=True)
    preview_url = models.URLField(blank=True)
    
    # Template data
    pages = models.JSONField(default=list)
    # List of page definitions with widgets
    
    data_sources = models.JSONField(default=list)
    # List of data source definitions
    
    # Theme
    theme = models.JSONField(default=dict, blank=True)
    # { "primaryColor": "#...", "fontFamily": "..." }
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    features = models.JSONField(default=list, blank=True)
    
    # Status
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name


class ExportedAdmin(models.Model):
    """
    Exported admin panel as deployable code.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='exported_admins'
    )
    
    # Export info
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20, default='1.0.0')
    
    # Generated code
    code = models.JSONField(default=dict)
    # { "files": { "App.tsx": "...", "pages/Dashboard.tsx": "..." } }
    
    # Build info
    framework = models.CharField(max_length=20, default='react')
    build_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('building', 'Building'),
        ('success', 'Success'),
        ('failed', 'Failed')
    ])
    build_log = models.TextField(blank=True)
    
    # Download
    download_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} v{self.version}"









