import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class MarketingConfig(models.Model):
    """
    Marketing analysis configuration for a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='marketing_config'
    )
    
    # Report settings
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    report_frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='weekly'
    )
    report_email = models.EmailField(
        blank=True,
        help_text="Email to receive reports (defaults to tenant owner email)"
    )
    report_enabled = models.BooleanField(default=True)
    
    # Additional report recipients
    additional_recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="List of additional email addresses"
    )
    
    # Last report sent
    last_report_at = models.DateTimeField(null=True, blank=True)
    next_report_at = models.DateTimeField(null=True, blank=True)
    
    # Settings
    settings = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Marketing Configuration"
        verbose_name_plural = "Marketing Configurations"
    
    def __str__(self):
        return f"Marketing Config for {self.tenant.name}"


class Competitor(models.Model):
    """
    Competitor website to track.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='competitors'
    )
    
    name = models.CharField(max_length=200, help_text="Competitor name")
    domain = models.CharField(max_length=255, help_text="Domain to track (e.g., competitor.com)")
    website_url = models.URLField(help_text="Full URL of competitor website")
    
    # Tracking settings
    track_homepage = models.BooleanField(default=True)
    track_blog = models.BooleanField(default=True)
    track_pricing = models.BooleanField(default=True)
    track_features = models.BooleanField(default=True)
    
    # Custom pages to track
    custom_pages = models.JSONField(
        default=list,
        blank=True,
        help_text="List of custom page URLs to track"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = [['tenant', 'domain']]
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.domain})"


class CompetitorSnapshot(models.Model):
    """
    Snapshot of competitor page content at a point in time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    competitor = models.ForeignKey(
        Competitor,
        on_delete=models.CASCADE,
        related_name='snapshots'
    )
    
    PAGE_TYPE_CHOICES = [
        ('homepage', 'Homepage'),
        ('blog', 'Blog'),
        ('pricing', 'Pricing'),
        ('features', 'Features'),
        ('custom', 'Custom Page'),
    ]
    
    page_type = models.CharField(max_length=20, choices=PAGE_TYPE_CHOICES)
    page_url = models.URLField()
    
    # Content
    title = models.CharField(max_length=500, blank=True)
    meta_description = models.TextField(blank=True)
    headings = models.JSONField(default=list, blank=True, help_text="List of h1-h6 headings")
    content_text = models.TextField(blank=True, help_text="Extracted text content")
    content_hash = models.CharField(max_length=64, help_text="SHA256 hash for change detection")
    
    # Extracted data
    features_mentioned = models.JSONField(default=list, blank=True)
    pricing_info = models.JSONField(default=dict, blank=True)
    blog_posts = models.JSONField(default=list, blank=True)
    
    # Metadata
    http_status = models.IntegerField(default=200)
    screenshot_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['competitor', 'page_type', '-created_at']),
            models.Index(fields=['content_hash']),
        ]
    
    def __str__(self):
        return f"{self.competitor.name} - {self.page_type} ({self.created_at.date()})"


class CompetitorChange(models.Model):
    """
    Detected change in competitor website.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    competitor = models.ForeignKey(
        Competitor,
        on_delete=models.CASCADE,
        related_name='changes'
    )
    
    CHANGE_TYPE_CHOICES = [
        ('new_feature', 'New Feature'),
        ('pricing_change', 'Pricing Change'),
        ('new_blog_post', 'New Blog Post'),
        ('content_update', 'Content Update'),
        ('new_page', 'New Page'),
        ('layout_change', 'Layout Change'),
    ]
    
    change_type = models.CharField(max_length=30, choices=CHANGE_TYPE_CHOICES)
    page_type = models.CharField(max_length=20, choices=CompetitorSnapshot.PAGE_TYPE_CHOICES)
    page_url = models.URLField()
    
    # Change details
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    
    # Before/after snapshots
    old_snapshot = models.ForeignKey(
        CompetitorSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='changes_as_old'
    )
    new_snapshot = models.ForeignKey(
        CompetitorSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='changes_as_new'
    )
    
    # AI analysis
    ai_summary = models.TextField(blank=True)
    ai_recommendations = models.JSONField(default=list, blank=True)
    importance_score = models.IntegerField(
        default=5,
        help_text="1-10 importance score from AI"
    )
    
    # Status
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_competitor_changes'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['competitor', '-created_at']),
            models.Index(fields=['change_type', '-created_at']),
            models.Index(fields=['importance_score']),
        ]
    
    def __str__(self):
        return f"{self.competitor.name}: {self.change_type} - {self.title[:50]}"


class Keyword(models.Model):
    """
    Keyword to track for SEO ranking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='keywords'
    )
    
    keyword = models.CharField(max_length=200)
    
    # Your site info
    your_domain = models.CharField(
        max_length=255,
        help_text="Your domain to track ranking for"
    )
    
    # Tracking settings
    track_competitors = models.BooleanField(
        default=True,
        help_text="Also track competitor rankings for this keyword"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['keyword']
        unique_together = [['tenant', 'keyword', 'your_domain']]
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
        ]
    
    def __str__(self):
        return self.keyword


class KeywordRanking(models.Model):
    """
    Keyword ranking snapshot.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    keyword = models.ForeignKey(
        Keyword,
        on_delete=models.CASCADE,
        related_name='rankings'
    )
    
    # Ranking data
    domain = models.CharField(max_length=255, help_text="Domain this ranking is for")
    position = models.IntegerField(null=True, blank=True, help_text="Position in search results (null if not in top 100)")
    
    # Search result details
    title = models.CharField(max_length=500, blank=True)
    url = models.URLField(blank=True)
    snippet = models.TextField(blank=True)
    
    # Search engine info
    search_engine = models.CharField(max_length=50, default='google')
    search_location = models.CharField(max_length=100, default='us')
    
    # Previous position for trend
    previous_position = models.IntegerField(null=True, blank=True)
    position_change = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['keyword', '-created_at']),
            models.Index(fields=['domain', '-created_at']),
        ]
    
    def __str__(self):
        pos = self.position if self.position else "Not ranked"
        return f"{self.keyword.keyword}: {self.domain} @ {pos}"


class MarketingReport(models.Model):
    """
    Generated marketing analysis report.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='marketing_reports'
    )
    
    REPORT_TYPE_CHOICES = [
        ('scheduled', 'Scheduled Report'),
        ('manual', 'Manual Report'),
        ('alert', 'Alert Report'),
    ]
    
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default='scheduled'
    )
    
    # Date range
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Report content
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    
    # Sections (as JSON for flexibility)
    competitor_analysis = models.JSONField(default=dict, blank=True)
    keyword_rankings = models.JSONField(default=dict, blank=True)
    changes_detected = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    
    # AI-generated insights
    ai_executive_summary = models.TextField(blank=True)
    ai_key_insights = models.JSONField(default=list, blank=True)
    ai_action_items = models.JSONField(default=list, blank=True)
    
    # Full HTML report
    html_content = models.TextField(blank=True)
    
    # Delivery status
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('generated', 'Generated'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='generating'
    )
    sent_to = models.JSONField(default=list, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Metrics
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.period_start} - {self.period_end})"


class ReportTemplate(models.Model):
    """
    Custom report template.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='report_templates',
        null=True,
        blank=True,
        help_text="Null for system templates"
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Template sections to include
    include_competitor_analysis = models.BooleanField(default=True)
    include_keyword_rankings = models.BooleanField(default=True)
    include_changes = models.BooleanField(default=True)
    include_recommendations = models.BooleanField(default=True)
    include_ai_insights = models.BooleanField(default=True)
    
    # Custom HTML template
    html_template = models.TextField(blank=True)
    
    # Styling
    primary_color = models.CharField(max_length=20, default='#3B82F6')
    logo_url = models.URLField(blank=True)
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        prefix = "System" if self.tenant is None else self.tenant.name
        return f"{prefix}: {self.name}"







