"""
Faibric Platform Admin Models.
Analytics, funnels, and platform-level metrics.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class PlatformMetrics(models.Model):
    """
    Daily platform-wide metrics for Faibric admin.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    date = models.DateField(unique=True)
    
    # User metrics
    total_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    churned_users = models.IntegerField(default=0)
    
    # Tenant metrics
    total_tenants = models.IntegerField(default=0)
    new_tenants = models.IntegerField(default=0)
    active_tenants = models.IntegerField(default=0)
    
    # Subscription metrics
    free_tier_count = models.IntegerField(default=0)
    starter_tier_count = models.IntegerField(default=0)
    pro_tier_count = models.IntegerField(default=0)
    
    # Revenue
    daily_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mrr = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Monthly Recurring Revenue")
    arr = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Annual Recurring Revenue")
    
    # Usage metrics
    total_llm_requests = models.IntegerField(default=0)
    total_tokens_used = models.IntegerField(default=0)
    total_credits_consumed = models.IntegerField(default=0)
    
    # Cost metrics (Faibric's cost)
    total_llm_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    
    # Project metrics
    total_projects = models.IntegerField(default=0)
    new_projects = models.IntegerField(default=0)
    deployed_projects = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Platform Metrics"
    
    def __str__(self):
        return f"Metrics for {self.date}"


class FunnelStep(models.Model):
    """
    Funnel steps for tracking conversions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    funnel_name = models.CharField(max_length=100)
    step_name = models.CharField(max_length=100)
    step_order = models.IntegerField()
    
    # Event to track
    event_name = models.CharField(max_length=100)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['funnel_name', 'step_order']
        unique_together = [['funnel_name', 'step_order']]
    
    def __str__(self):
        return f"{self.funnel_name} - Step {self.step_order}: {self.step_name}"


class FunnelEvent(models.Model):
    """
    Track funnel events for users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    funnel_step = models.ForeignKey(FunnelStep, on_delete=models.CASCADE)
    
    # Session tracking
    session_id = models.CharField(max_length=100, blank=True)
    
    # Attribution
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    utm_content = models.CharField(max_length=100, blank=True)
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['funnel_step', 'timestamp']),
            models.Index(fields=['utm_source', 'utm_campaign']),
        ]
    
    def __str__(self):
        return f"{self.funnel_step.step_name} at {self.timestamp}"


class FunnelConversion(models.Model):
    """
    Aggregated funnel conversion data.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    funnel_name = models.CharField(max_length=100)
    date = models.DateField()
    
    # By step
    step_counts = models.JSONField(default=dict, help_text="Step name to count")
    
    # Conversion rates
    step_to_step_rates = models.JSONField(default=dict, help_text="Step to next step conversion rates")
    
    # Overall
    total_started = models.IntegerField(default=0)
    total_completed = models.IntegerField(default=0)
    overall_conversion_rate = models.FloatField(default=0)
    
    # By source
    by_source = models.JSONField(default=dict, blank=True)
    by_campaign = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = [['funnel_name', 'date']]
    
    def __str__(self):
        return f"{self.funnel_name} - {self.date}"


class AdCampaign(models.Model):
    """
    Track ad campaigns (Google Ads).
    Can be for Faibric or for customers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Owner (null = Faibric's own campaign)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ad_campaigns'
    )
    
    # Campaign details
    name = models.CharField(max_length=200)
    
    PLATFORM_CHOICES = [
        ('google_ads', 'Google Ads'),
        ('facebook', 'Facebook/Meta'),
        ('linkedin', 'LinkedIn'),
        ('twitter', 'Twitter/X'),
    ]
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='google_ads')
    
    # External IDs
    external_campaign_id = models.CharField(max_length=100, blank=True)
    external_ad_account_id = models.CharField(max_length=100, blank=True)
    
    # Budget
    daily_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Targeting
    target_url = models.URLField(blank=True)
    target_keywords = models.JSONField(default=list, blank=True)
    target_audiences = models.JSONField(default=list, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('ended', 'Ended'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Dates
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Performance metrics (synced from Google Ads)
    total_impressions = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    total_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_conversions = models.IntegerField(default=0)
    
    ctr = models.FloatField(default=0, help_text="Click-through rate")
    cpc = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Cost per click")
    cpa = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Cost per acquisition")
    
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        owner = self.tenant.name if self.tenant else "Faibric"
        return f"{owner}: {self.name}"


class AdCampaignDaily(models.Model):
    """
    Daily metrics for ad campaigns.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    campaign = models.ForeignKey(AdCampaign, on_delete=models.CASCADE, related_name='daily_metrics')
    date = models.DateField()
    
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    spend = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    conversions = models.IntegerField(default=0)
    
    # Calculated metrics
    ctr = models.FloatField(default=0)
    cpc = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    cpa = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = [['campaign', 'date']]
    
    def __str__(self):
        return f"{self.campaign.name} - {self.date}"


class SystemHealth(models.Model):
    """
    System health metrics for monitoring.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    timestamp = models.DateTimeField(default=timezone.now)
    
    # API metrics
    api_requests_1h = models.IntegerField(default=0)
    api_errors_1h = models.IntegerField(default=0)
    api_avg_response_ms = models.IntegerField(default=0)
    
    # Database
    db_connections = models.IntegerField(default=0)
    db_query_avg_ms = models.IntegerField(default=0)
    
    # Queue (Celery)
    queue_pending = models.IntegerField(default=0)
    queue_failed = models.IntegerField(default=0)
    
    # Storage
    storage_used_gb = models.FloatField(default=0)
    storage_limit_gb = models.FloatField(default=0)
    
    # LLM
    llm_requests_1h = models.IntegerField(default=0)
    llm_errors_1h = models.IntegerField(default=0)
    llm_avg_response_ms = models.IntegerField(default=0)
    
    # Status
    STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('degraded', 'Degraded'),
        ('down', 'Down'),
    ]
    overall_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='healthy')
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "System Health"
    
    def __str__(self):
        return f"Health at {self.timestamp}: {self.overall_status}"









