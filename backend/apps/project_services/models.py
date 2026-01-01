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


class ProjectDesign(models.Model):
    """
    Design tokens and custom CSS for a project.
    Used by the live design editor.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='design'
    )
    
    # Design tokens (CSS variables)
    tokens = models.JSONField(default=dict, help_text="CSS variable overrides")
    
    # Custom CSS
    custom_css = models.TextField(blank=True, help_text="Additional custom CSS")
    
    # Font settings
    primary_font = models.CharField(max_length=100, blank=True)
    heading_font = models.CharField(max_length=100, blank=True)
    
    # Theme
    is_dark_mode = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Project Design'
        verbose_name_plural = 'Project Designs'
    
    def __str__(self):
        return f"Design: {self.project.name}"


class ProjectFeedback(models.Model):
    """
    User feedback for a project. Used by self-improvement system.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    
    # Feedback type
    feedback_type = models.CharField(max_length=50, choices=[
        ('general', 'General'),
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('quality', 'Quality Issue'),
    ], default='general')
    
    # Rating (1-5)
    rating = models.IntegerField(default=3)
    
    # Feedback message
    message = models.TextField()
    
    # Component reference (if feedback is about a specific component)
    component_id = models.UUIDField(null=True, blank=True)
    
    # Additional data
    metadata = models.JSONField(default=dict)
    
    # Status
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Project Feedback'
        verbose_name_plural = 'Project Feedback'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Feedback: {self.project.name} - {self.feedback_type}"


class ImprovementTask(models.Model):
    """
    Task for the self-improvement system.
    Created automatically based on feedback, quality issues, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Task type
    task_type = models.CharField(max_length=50, choices=[
        ('review_component', 'Review Component'),
        ('fix_bug', 'Fix Bug'),
        ('improve_quality', 'Improve Quality'),
        ('update_keywords', 'Update Keywords'),
        ('check_compatibility', 'Check Compatibility'),
    ])
    
    # Component reference
    component_id = models.UUIDField(null=True, blank=True)
    
    # Priority
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    
    # Description
    description = models.TextField()
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')
    
    # Result
    result = models.JSONField(default=dict, blank=True)
    
    # Additional data
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Improvement Task'
        verbose_name_plural = 'Improvement Tasks'
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f"{self.task_type}: {self.description[:50]}"

