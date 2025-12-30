"""
Project Services Models - Database, Auth, Storage, Payments, Domains
"""
import uuid
from django.db import models
from django.conf import settings


class ProjectDatabase(models.Model):
    """
    Supabase database instance for a project.
    Auto-provisioned when project needs data persistence.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='database'
    )
    
    # Supabase connection info
    supabase_url = models.URLField(blank=True)
    supabase_anon_key = models.CharField(max_length=500, blank=True)
    supabase_service_key = models.CharField(max_length=500, blank=True)  # Encrypted
    
    # Database schema
    tables = models.JSONField(default=list, help_text="List of table definitions")
    
    # Status
    status = models.CharField(max_length=50, default='pending', choices=[
        ('pending', 'Pending'),
        ('provisioning', 'Provisioning'),
        ('active', 'Active'),
        ('error', 'Error'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Project Database'
        verbose_name_plural = 'Project Databases'
    
    def __str__(self):
        return f"DB: {self.project.name}"


class ProjectAuth(models.Model):
    """
    Authentication configuration for a project.
    Supports multiple auth providers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='auth'
    )
    
    # Auth providers enabled
    email_password = models.BooleanField(default=True)
    magic_link = models.BooleanField(default=True)
    google_oauth = models.BooleanField(default=False)
    github_oauth = models.BooleanField(default=False)
    
    # OAuth credentials (encrypted)
    google_client_id = models.CharField(max_length=500, blank=True)
    google_client_secret = models.CharField(max_length=500, blank=True)
    github_client_id = models.CharField(max_length=500, blank=True)
    github_client_secret = models.CharField(max_length=500, blank=True)
    
    # Settings
    require_email_verification = models.BooleanField(default=True)
    allow_signup = models.BooleanField(default=True)
    session_duration_hours = models.IntegerField(default=24 * 7)  # 1 week
    
    # Status
    status = models.CharField(max_length=50, default='pending', choices=[
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('error', 'Error'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Project Auth'
        verbose_name_plural = 'Project Auth Configs'
    
    def __str__(self):
        return f"Auth: {self.project.name}"


class ProjectDomain(models.Model):
    """
    Custom domain configuration for a project.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='custom_domains'
    )
    
    # Domain info
    domain = models.CharField(max_length=255, unique=True, db_index=True)
    is_primary = models.BooleanField(default=False)
    
    # Verification
    verification_token = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    
    # SSL
    ssl_status = models.CharField(max_length=50, default='pending', choices=[
        ('pending', 'Pending'),
        ('provisioning', 'Provisioning'),
        ('active', 'Active'),
        ('error', 'Error'),
    ])
    
    # DNS records required
    dns_records = models.JSONField(default=list, help_text="DNS records to configure")
    
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Project Domain'
        verbose_name_plural = 'Project Domains'
        ordering = ['-is_primary', 'domain']
    
    def __str__(self):
        return f"{self.domain} -> {self.project.name}"


class ProjectPayments(models.Model):
    """
    Stripe payment configuration for a project.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Stripe Connect account
    stripe_account_id = models.CharField(max_length=100, blank=True)
    stripe_account_status = models.CharField(max_length=50, default='pending', choices=[
        ('pending', 'Pending'),
        ('connected', 'Connected'),
        ('error', 'Error'),
    ])
    
    # Products and prices
    products = models.JSONField(default=list, help_text="Stripe product definitions")
    
    # Webhooks
    webhook_secret = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Project Payments'
        verbose_name_plural = 'Project Payment Configs'
    
    def __str__(self):
        return f"Payments: {self.project.name}"


class ProjectStorage(models.Model):
    """
    File storage configuration for a project.
    Uses Supabase Storage or Cloudflare R2.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='storage'
    )
    
    # Storage provider
    provider = models.CharField(max_length=50, default='supabase', choices=[
        ('supabase', 'Supabase Storage'),
        ('cloudflare', 'Cloudflare R2'),
        ('s3', 'AWS S3'),
    ])
    
    # Buckets
    buckets = models.JSONField(default=list, help_text="Storage bucket definitions")
    
    # Usage
    storage_used_bytes = models.BigIntegerField(default=0)
    storage_limit_bytes = models.BigIntegerField(default=500 * 1024 * 1024)  # 500MB default
    
    # Status
    status = models.CharField(max_length=50, default='pending', choices=[
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('error', 'Error'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Project Storage'
        verbose_name_plural = 'Project Storage Configs'
    
    def __str__(self):
        return f"Storage: {self.project.name}"


class ProjectVersion(models.Model):
    """
    Version history for a project. Enables rollback.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='service_versions'  # Avoid conflict with projects.ProjectVersion
    )
    
    # Version info
    version_number = models.IntegerField()
    commit_hash = models.CharField(max_length=40, blank=True)
    
    # Snapshot
    code_snapshot = models.TextField(help_text="Full App.tsx code at this version")
    config_snapshot = models.JSONField(default=dict, help_text="Configuration at this version")
    
    # Metadata
    change_description = models.TextField(blank=True)
    created_by = models.CharField(max_length=100, default='system')
    
    # Status
    is_deployed = models.BooleanField(default=False)
    deployment_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Project Version'
        verbose_name_plural = 'Project Versions'
        ordering = ['-version_number']
        unique_together = ['project', 'version_number']
    
    def __str__(self):
        return f"{self.project.name} v{self.version_number}"


class ProjectAnalytics(models.Model):
    """
    Analytics data for a project.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # Tracking enabled
    is_enabled = models.BooleanField(default=True)
    
    # Aggregate stats (updated periodically)
    total_pageviews = models.BigIntegerField(default=0)
    total_visitors = models.BigIntegerField(default=0)
    total_sessions = models.BigIntegerField(default=0)
    
    # Last 30 days
    pageviews_30d = models.IntegerField(default=0)
    visitors_30d = models.IntegerField(default=0)
    
    # Top pages (JSON: [{path: "/", views: 100}, ...])
    top_pages = models.JSONField(default=list)
    
    # Traffic sources
    traffic_sources = models.JSONField(default=dict)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Project Analytics'
        verbose_name_plural = 'Project Analytics'
    
    def __str__(self):
        return f"Analytics: {self.project.name}"


class AnalyticsEvent(models.Model):
    """
    Individual analytics events.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='analytics_events'
    )
    
    # Event info
    event_type = models.CharField(max_length=50, db_index=True)  # pageview, click, form_submit
    path = models.CharField(max_length=500)
    
    # Visitor info
    visitor_id = models.CharField(max_length=100, db_index=True)
    session_id = models.CharField(max_length=100)
    
    # Metadata
    referrer = models.URLField(blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    country = models.CharField(max_length=2, blank=True)
    
    # Custom data
    event_data = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = 'Analytics Event'
        verbose_name_plural = 'Analytics Events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'event_type', 'created_at']),
            models.Index(fields=['project', 'path', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type}: {self.path}"

