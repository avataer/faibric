"""
Extended Analytics Models for Faibric Admin Dashboard.
Covers: Health scores, alerts, cohorts, reports, AI insights.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

User = get_user_model()


# =============================================================================
# CUSTOMER HEALTH & ENGAGEMENT
# =============================================================================

class CustomerHealthScore(models.Model):
    """
    Health score for each user/session, calculated daily.
    Score 0-100: green (70+), yellow (40-69), red (<40)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session_token = models.CharField(max_length=100, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    
    # Component scores (0-100 each)
    build_success_rate = models.FloatField(default=0)  # % successful builds
    engagement_score = models.FloatField(default=0)    # Time spent, modifications
    return_rate = models.FloatField(default=0)         # Came back within 7 days?
    feature_adoption = models.FloatField(default=0)    # Used advanced features?
    satisfaction_score = models.FloatField(default=0)  # Feedback, no errors
    
    # Calculated overall score
    overall_score = models.FloatField(default=0)
    
    # Health status
    HEALTH_CHOICES = [
        ('healthy', 'Healthy'),
        ('at_risk', 'At Risk'),
        ('churning', 'Churning'),
    ]
    health_status = models.CharField(max_length=20, choices=HEALTH_CHOICES, default='healthy')
    
    # Trend
    TREND_CHOICES = [
        ('improving', 'Improving'),
        ('stable', 'Stable'),
        ('declining', 'Declining'),
    ]
    trend = models.CharField(max_length=20, choices=TREND_CHOICES, default='stable')
    previous_score = models.FloatField(null=True, blank=True)
    
    # Churn prediction
    churn_probability = models.FloatField(default=0)  # 0-1 probability
    
    # Metadata
    total_builds = models.IntegerField(default=0)
    successful_builds = models.IntegerField(default=0)
    total_modifications = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=1)
    total_time_minutes = models.FloatField(default=0)
    last_active_at = models.DateTimeField(null=True, blank=True)
    
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-overall_score']
        indexes = [
            models.Index(fields=['health_status', 'overall_score']),
            models.Index(fields=['session_token']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.email or self.session_token[:16]} - {self.overall_score:.0f}"
    
    def calculate_score(self):
        """Calculate overall health score from components."""
        weights = {
            'build_success_rate': 0.30,
            'engagement_score': 0.25,
            'return_rate': 0.20,
            'feature_adoption': 0.15,
            'satisfaction_score': 0.10,
        }
        
        self.previous_score = self.overall_score
        self.overall_score = (
            self.build_success_rate * weights['build_success_rate'] +
            self.engagement_score * weights['engagement_score'] +
            self.return_rate * weights['return_rate'] +
            self.feature_adoption * weights['feature_adoption'] +
            self.satisfaction_score * weights['satisfaction_score']
        )
        
        # Determine health status
        if self.overall_score >= 70:
            self.health_status = 'healthy'
        elif self.overall_score >= 40:
            self.health_status = 'at_risk'
        else:
            self.health_status = 'churning'
        
        # Determine trend
        if self.previous_score:
            diff = self.overall_score - self.previous_score
            if diff > 5:
                self.trend = 'improving'
            elif diff < -5:
                self.trend = 'declining'
            else:
                self.trend = 'stable'
        
        # Simple churn probability based on score
        self.churn_probability = max(0, min(1, (100 - self.overall_score) / 100))
        
        self.save()


class UserSegment(models.Model):
    """
    User segmentation for grouping and analysis.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Segment criteria (JSON)
    criteria = models.JSONField(default=dict)
    # Example: {"source": "twitter", "device": "mobile", "builds": ">3"}
    
    # Cached count
    user_count = models.IntegerField(default=0)
    
    # Color for UI
    color = models.CharField(max_length=20, default='#3b82f6')
    
    is_auto = models.BooleanField(default=False)  # Auto-generated vs manual
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


# =============================================================================
# COHORT ANALYSIS
# =============================================================================

class Cohort(models.Model):
    """
    Weekly/Monthly cohort for retention analysis.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    
    # Period identifier (e.g., "2024-W01", "2024-01")
    period_key = models.CharField(max_length=20, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Cohort size
    initial_users = models.IntegerField(default=0)
    
    # Retention data: {0: 100, 1: 80, 2: 60, ...} (% retained in period N)
    retention_data = models.JSONField(default=dict)
    
    # Conversion data
    converted_to_deploy = models.IntegerField(default=0)
    conversion_rate = models.FloatField(default=0)
    
    # Revenue (if applicable)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-period_start']
    
    def __str__(self):
        return f"{self.period_type} Cohort: {self.period_key}"


# =============================================================================
# ALERTS & NOTIFICATIONS
# =============================================================================

class AlertRule(models.Model):
    """
    Configurable alert rules for anomaly detection.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # What to monitor
    METRIC_CHOICES = [
        ('error_rate', 'Error Rate'),
        ('daily_cost', 'Daily Cost'),
        ('build_queue', 'Build Queue Depth'),
        ('build_time', 'Average Build Time'),
        ('api_latency', 'API Latency'),
        ('user_churn', 'User Churn Rate'),
        ('conversion_rate', 'Conversion Rate'),
        ('custom', 'Custom Metric'),
    ]
    metric = models.CharField(max_length=50, choices=METRIC_CHOICES)
    
    # Condition
    CONDITION_CHOICES = [
        ('gt', 'Greater Than'),
        ('lt', 'Less Than'),
        ('eq', 'Equals'),
        ('change_gt', 'Change Greater Than'),
        ('change_lt', 'Change Less Than'),
    ]
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    threshold = models.FloatField()
    
    # Time window (minutes)
    time_window_minutes = models.IntegerField(default=5)
    
    # Notification settings
    notify_email = models.BooleanField(default=True)
    notify_slack = models.BooleanField(default=False)
    slack_webhook = models.URLField(blank=True)
    
    # Cooldown (don't alert again within N minutes)
    cooldown_minutes = models.IntegerField(default=30)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Stats
    trigger_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name}: {self.metric} {self.condition} {self.threshold}"
    
    def can_trigger(self):
        """Check if alert can trigger (not in cooldown)."""
        if not self.last_triggered_at:
            return True
        cooldown_end = self.last_triggered_at + timedelta(minutes=self.cooldown_minutes)
        return timezone.now() > cooldown_end


class Alert(models.Model):
    """
    Triggered alert instance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='alerts')
    
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning')
    
    # Alert details
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Current value that triggered the alert
    current_value = models.FloatField()
    threshold_value = models.FloatField()
    
    # AI explanation (optional)
    ai_explanation = models.TextField(blank=True)
    
    # Status
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Notification status
    email_sent = models.BooleanField(default=False)
    slack_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.severity}] {self.title}"


# =============================================================================
# SCHEDULED REPORTS
# =============================================================================

class ScheduledReport(models.Model):
    """
    Scheduled report configuration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100)
    
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    
    # What to include
    include_overview = models.BooleanField(default=True)
    include_costs = models.BooleanField(default=True)
    include_users = models.BooleanField(default=True)
    include_funnel = models.BooleanField(default=True)
    include_components = models.BooleanField(default=True)
    include_ai_summary = models.BooleanField(default=True)
    
    # Recipients
    email_recipients = models.JSONField(default=list)  # List of emails
    
    # Schedule
    send_hour = models.IntegerField(default=9)  # Hour of day (0-23)
    send_day = models.IntegerField(default=1)   # Day of week (1-7) or month (1-31)
    
    last_sent_at = models.DateTimeField(null=True, blank=True)
    next_send_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"


class GeneratedReport(models.Model):
    """
    Generated report instance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    scheduled_report = models.ForeignKey(
        ScheduledReport, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    # Report type
    REPORT_TYPE_CHOICES = [
        ('daily', 'Daily Summary'),
        ('weekly', 'Weekly Summary'),
        ('monthly', 'Monthly Summary'),
        ('custom', 'Custom Report'),
    ]
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    
    # Period covered
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Content
    title = models.CharField(max_length=200)
    html_content = models.TextField()
    plain_text_content = models.TextField(blank=True)
    
    # AI-generated summary
    ai_summary = models.TextField(blank=True)
    ai_insights = models.JSONField(default=list)  # List of insight strings
    ai_recommendations = models.JSONField(default=list)
    
    # Data snapshot
    data_snapshot = models.JSONField(default=dict)
    
    # Delivery
    sent_to = models.JSONField(default=list)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.period_start} - {self.period_end})"


# =============================================================================
# AI ANALYTICS
# =============================================================================

class PromptAnalytics(models.Model):
    """
    Analytics for AI prompts and responses.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session_token = models.CharField(max_length=100, db_index=True)
    
    # The prompt
    user_prompt = models.TextField()
    prompt_length = models.IntegerField(default=0)
    
    # Classification
    detected_type = models.CharField(max_length=50, blank=True)  # website, tool, etc.
    detected_industry = models.CharField(max_length=50, blank=True)  # restaurant, finance
    detected_features = models.JSONField(default=list)  # List of requested features
    
    # Keywords extracted
    keywords = models.JSONField(default=list)
    
    # Generation result
    was_successful = models.BooleanField(default=True)
    error_type = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # Performance
    generation_time_seconds = models.FloatField(default=0)
    tokens_used = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Quality
    code_length = models.IntegerField(default=0)
    component_count = models.IntegerField(default=0)
    
    # Library usage
    used_library = models.BooleanField(default=False)
    library_components_used = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Prompt Analytics"
    
    def __str__(self):
        return f"{self.detected_type}: {self.user_prompt[:50]}..."


class AIInsight(models.Model):
    """
    AI-generated insights about the platform.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    INSIGHT_TYPE_CHOICES = [
        ('pattern', 'Pattern Detected'),
        ('anomaly', 'Anomaly'),
        ('recommendation', 'Recommendation'),
        ('prediction', 'Prediction'),
        ('summary', 'Summary'),
    ]
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPE_CHOICES)
    
    # Content
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Supporting data
    data = models.JSONField(default=dict)
    
    # Confidence
    confidence = models.FloatField(default=0.8)  # 0-1
    
    # Action
    suggested_action = models.TextField(blank=True)
    action_taken = models.BooleanField(default=False)
    
    # Validity
    valid_until = models.DateTimeField(null=True, blank=True)
    is_dismissed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.insight_type}] {self.title}"


# =============================================================================
# REAL-TIME ACTIVITY
# =============================================================================

class ActivityFeed(models.Model):
    """
    Real-time activity feed for live monitoring.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    ACTIVITY_TYPE_CHOICES = [
        ('new_user', 'New User'),
        ('build_started', 'Build Started'),
        ('build_completed', 'Build Completed'),
        ('build_failed', 'Build Failed'),
        ('deployed', 'Deployed'),
        ('modification', 'Modification'),
        ('error', 'Error'),
        ('alert', 'Alert Triggered'),
        ('system', 'System Event'),
    ]
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    
    # Actor
    session_token = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    
    # Content
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Related objects
    related_data = models.JSONField(default=dict)
    
    # Severity for coloring
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"[{self.activity_type}] {self.title}"


# =============================================================================
# OPERATIONAL METRICS
# =============================================================================

class SystemMetric(models.Model):
    """
    System health metrics over time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    METRIC_TYPE_CHOICES = [
        ('api_latency', 'API Latency (ms)'),
        ('build_queue', 'Build Queue Depth'),
        ('build_time', 'Average Build Time (s)'),
        ('error_rate', 'Error Rate (%)'),
        ('active_users', 'Active Users'),
        ('memory_usage', 'Memory Usage (%)'),
        ('github_rate_limit', 'GitHub Rate Limit Remaining'),
        ('anthropic_latency', 'Anthropic API Latency (ms)'),
    ]
    metric_type = models.CharField(max_length=30, choices=METRIC_TYPE_CHOICES)
    
    value = models.FloatField()
    
    # For aggregations
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    avg_value = models.FloatField(null=True, blank=True)
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['metric_type', '-recorded_at']),
        ]
    
    def __str__(self):
        return f"{self.metric_type}: {self.value}"


class BuildQueueItem(models.Model):
    """
    Track items in build queue for monitoring.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session_token = models.CharField(max_length=100, db_index=True)
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    
    # Timing
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Duration
    wait_time_seconds = models.FloatField(null=True, blank=True)
    build_time_seconds = models.FloatField(null=True, blank=True)
    
    # Retry info
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-queued_at']
    
    def __str__(self):
        return f"{self.session_token[:16]} - {self.status}"


# =============================================================================
# FUNNEL ANALYTICS
# =============================================================================

class FunnelSnapshot(models.Model):
    """
    Daily snapshot of conversion funnel.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    date = models.DateField(unique=True)
    
    # Funnel stages (counts)
    visitors = models.IntegerField(default=0)
    requests_submitted = models.IntegerField(default=0)
    emails_provided = models.IntegerField(default=0)
    emails_verified = models.IntegerField(default=0)
    builds_started = models.IntegerField(default=0)
    builds_completed = models.IntegerField(default=0)
    deployed = models.IntegerField(default=0)
    
    # Conversion rates (calculated)
    request_rate = models.FloatField(default=0)      # requests / visitors
    email_rate = models.FloatField(default=0)        # emails / requests
    verify_rate = models.FloatField(default=0)       # verified / emails
    build_rate = models.FloatField(default=0)        # builds / verified
    complete_rate = models.FloatField(default=0)     # completed / builds
    deploy_rate = models.FloatField(default=0)       # deployed / completed
    overall_rate = models.FloatField(default=0)      # deployed / visitors
    
    # By source breakdown
    by_source = models.JSONField(default=dict)
    # {"organic": {visitors: 100, deployed: 10}, "twitter": {...}}
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Funnel {self.date}: {self.overall_rate:.1%}"
    
    def calculate_rates(self):
        """Calculate conversion rates."""
        if self.visitors > 0:
            self.request_rate = self.requests_submitted / self.visitors
            self.overall_rate = self.deployed / self.visitors
        if self.requests_submitted > 0:
            self.email_rate = self.emails_provided / self.requests_submitted
        if self.emails_provided > 0:
            self.verify_rate = self.emails_verified / self.emails_provided
        if self.emails_verified > 0:
            self.build_rate = self.builds_started / self.emails_verified
        if self.builds_started > 0:
            self.complete_rate = self.builds_completed / self.builds_started
        if self.builds_completed > 0:
            self.deploy_rate = self.deployed / self.builds_completed
        self.save()


# =============================================================================
# COMPONENT LIBRARY EXTENDED ANALYTICS
# =============================================================================

class ComponentGapAnalysis(models.Model):
    """
    AI-detected gaps in the component library.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Gap identification
    gap_type = models.CharField(max_length=100)  # e.g., "restaurant_menu"
    gap_description = models.TextField()
    
    # Demand signals
    request_count = models.IntegerField(default=0)  # How many users requested this
    example_prompts = models.JSONField(default=list)  # Sample prompts
    
    # Priority
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    priority_score = models.FloatField(default=0)  # Calculated score
    
    # Status
    is_addressed = models.BooleanField(default=False)
    addressed_by_component = models.ForeignKey(
        'code_library.LibraryItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    detected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority_score', '-request_count']
    
    def __str__(self):
        return f"[{self.priority}] {self.gap_type}"


# =============================================================================
# ADMIN CONFIGURATION
# =============================================================================

class AdminConfig(models.Model):
    """
    Singleton configuration for admin dashboard.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Notification email
    admin_email = models.EmailField(default='amptiness@icloud.com')
    
    # Alert settings
    enable_email_alerts = models.BooleanField(default=True)
    enable_slack_alerts = models.BooleanField(default=False)
    slack_webhook_url = models.URLField(blank=True)
    
    # Daily report settings
    send_daily_report = models.BooleanField(default=True)
    daily_report_hour = models.IntegerField(default=9)  # 9 AM
    
    # Cost thresholds
    daily_cost_warning = models.DecimalField(max_digits=10, decimal_places=2, default=50)
    daily_cost_critical = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    
    # Error thresholds
    error_rate_warning = models.FloatField(default=0.1)  # 10%
    error_rate_critical = models.FloatField(default=0.25)  # 25%
    
    # Queue thresholds
    queue_depth_warning = models.IntegerField(default=10)
    queue_depth_critical = models.IntegerField(default=25)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Admin Configuration"
        verbose_name_plural = "Admin Configuration"
    
    def __str__(self):
        return "Admin Configuration"
    
    @classmethod
    def get_config(cls):
        """Get or create the singleton config."""
        config, _ = cls.objects.get_or_create(pk='00000000-0000-0000-0000-000000000001')
        return config
