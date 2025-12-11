"""
Onboarding Flow Models.

Tracks the entire journey from landing page to project creation.
"""
import uuid
import secrets
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class LandingSession(models.Model):
    """
    Tracks a visitor session from landing to conversion.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Session identification
    session_token = models.CharField(max_length=64, unique=True, db_index=True)
    
    # The initial request they made
    initial_request = models.TextField(help_text="What the user typed in the main input")
    
    # Status tracking
    STATUS_CHOICES = [
        ('request_submitted', 'Request Submitted'),
        ('email_requested', 'Email Requested'),
        ('email_provided', 'Email Provided'),
        ('email_changed', 'Email Changed'),
        ('magic_link_sent', 'Magic Link Sent'),
        ('magic_link_clicked', 'Magic Link Clicked'),
        ('account_created', 'Account Created'),
        ('project_created', 'Project Created'),
        ('building', 'Building'),
        ('deployed', 'Deployed'),
        ('abandoned', 'Abandoned'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='request_submitted')
    
    # Email info
    email = models.EmailField(blank=True, db_index=True)
    email_verified = models.BooleanField(default=False)
    
    # Magic link
    magic_token = models.CharField(max_length=64, blank=True, db_index=True)
    magic_token_expires_at = models.DateTimeField(null=True, blank=True)
    magic_link_sent_at = models.DateTimeField(null=True, blank=True)
    magic_link_clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Email change tracking
    email_change_count = models.IntegerField(default=0)
    previous_emails = models.JSONField(default=list)
    
    # Conversion tracking
    converted_to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='onboarding_sessions'
    )
    converted_to_tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    converted_to_project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Attribution
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    utm_content = models.CharField(max_length=100, blank=True)
    utm_term = models.CharField(max_length=100, blank=True)
    referrer = models.URLField(blank=True)
    landing_page = models.URLField(blank=True)
    
    # Device info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=20, blank=True)  # mobile, tablet, desktop
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    
    # Session duration tracking
    total_time_seconds = models.IntegerField(
        default=0,
        help_text="Total time spent in session (seconds)"
    )
    active_time_seconds = models.IntegerField(
        default=0,
        help_text="Time actively engaged (not idle)"
    )
    
    # Input tracking summary
    total_inputs = models.IntegerField(default=0)
    total_characters_typed = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['email', 'created_at']),
            models.Index(fields=['utm_source', 'utm_campaign']),
        ]
    
    def __str__(self):
        return f"{self.email or 'Anonymous'} - {self.status}"
    
    def generate_magic_token(self):
        """Generate a new magic link token."""
        self.magic_token = secrets.token_urlsafe(32)
        self.magic_token_expires_at = timezone.now() + timedelta(hours=24)
        self.save(update_fields=['magic_token', 'magic_token_expires_at'])
        return self.magic_token
    
    def is_magic_token_valid(self, token: str) -> bool:
        """Check if magic token is valid."""
        if not self.magic_token or self.magic_token != token:
            return False
        if not self.magic_token_expires_at:
            return False
        return timezone.now() < self.magic_token_expires_at
    
    @property
    def is_converted(self) -> bool:
        return self.converted_to_user is not None
    
    @property
    def duration_minutes(self) -> float:
        """Calculate session duration in minutes."""
        if self.last_activity_at and self.created_at:
            delta = self.last_activity_at - self.created_at
            return round(delta.total_seconds() / 60, 1)
        elif self.total_time_seconds:
            return round(self.total_time_seconds / 60, 1)
        return 0
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity_at = timezone.now()
        if self.created_at:
            self.total_time_seconds = int((self.last_activity_at - self.created_at).total_seconds())
        self.save(update_fields=['last_activity_at', 'total_time_seconds', 'updated_at'])


class SessionEvent(models.Model):
    """
    Logs every event in a landing session for detailed tracking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session = models.ForeignKey(
        LandingSession,
        on_delete=models.CASCADE,
        related_name='events'
    )
    
    # Event info
    EVENT_TYPE_CHOICES = [
        ('page_view', 'Page View'),
        ('request_submitted', 'Request Submitted'),
        ('request_modified', 'Request Modified'),  # When they edit their request
        ('input_typed', 'Input Typed'),  # Track typing in input field
        ('email_form_shown', 'Email Form Shown'),
        ('email_entered', 'Email Entered'),
        ('email_changed', 'Email Changed'),
        ('magic_link_sent', 'Magic Link Sent'),
        ('magic_link_resent', 'Magic Link Resent'),
        ('magic_link_clicked', 'Magic Link Clicked'),
        ('magic_link_expired', 'Magic Link Expired'),
        ('account_created', 'Account Created'),
        ('project_created', 'Project Created'),
        ('build_started', 'Build Started'),
        ('build_progress', 'Build Progress'),
        ('build_completed', 'Build Completed'),
        ('deploy_started', 'Deploy Started'),
        ('deploy_completed', 'Deploy Completed'),
        ('chat_message', 'Chat Message'),  # Any follow-up message
        ('feature_request', 'Feature Request'),  # Feature additions
        ('error', 'Error'),
        ('session_timeout', 'Session Timeout'),
        ('page_leave', 'Page Leave'),  # When they leave/close
        ('page_return', 'Page Return'),  # When they come back
    ]
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    
    # Event data
    event_data = models.JSONField(default=dict, blank=True)
    
    # The actual input/text they typed (for learning)
    user_input = models.TextField(blank=True, help_text="What the user typed/entered")
    
    # For email changes
    old_email = models.EmailField(blank=True)
    new_email = models.EmailField(blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    
    # Page/context where this happened
    page_url = models.URLField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['session', 'event_type']),
            models.Index(fields=['event_type', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.session_id} - {self.event_type}"


class UserInput(models.Model):
    """
    Logs ALL user inputs across the platform for learning and analysis.
    This is the central repository for everything users type.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to session if from onboarding
    session = models.ForeignKey(
        LandingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_inputs'
    )
    
    # Link to user if logged in
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='all_inputs'
    )
    
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # What type of input
    INPUT_TYPE_CHOICES = [
        ('initial_request', 'Initial Request (Landing)'),
        ('request_edit', 'Request Edit'),
        ('follow_up', 'Follow-up Message'),
        ('feature_add', 'Feature Addition'),
        ('code_request', 'Code Generation Request'),
        ('code_edit', 'Code Edit Request'),
        ('chat_message', 'Chat Message'),
        ('feedback', 'Feedback'),
        ('bug_report', 'Bug Report'),
        ('other', 'Other'),
    ]
    input_type = models.CharField(max_length=30, choices=INPUT_TYPE_CHOICES)
    
    # The actual input
    input_text = models.TextField(help_text="Exactly what the user typed")
    
    # Context
    context = models.TextField(blank=True, help_text="What was on screen when they typed this")
    previous_input = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The input this was a follow-up to"
    )
    
    # What we responded with
    ai_response = models.TextField(blank=True)
    
    # Timing
    time_to_type_seconds = models.IntegerField(
        null=True, blank=True,
        help_text="How long they spent typing this"
    )
    
    # Quality/outcome
    was_successful = models.BooleanField(null=True, blank=True)
    user_satisfaction = models.IntegerField(null=True, blank=True, help_text="1-5 rating")
    
    # Device/browser
    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    
    # Attribution
    utm_source = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['input_type', 'timestamp']),
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.input_type}: {self.input_text[:50]}..."


class DailyReport(models.Model):
    """
    Daily compiled report for Faibric Admin.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    date = models.DateField(unique=True)
    
    # Landing/Onboarding metrics
    total_visitors = models.IntegerField(default=0)
    total_requests = models.IntegerField(default=0)
    emails_collected = models.IntegerField(default=0)
    email_changes = models.IntegerField(default=0)
    magic_links_sent = models.IntegerField(default=0)
    magic_links_clicked = models.IntegerField(default=0)
    accounts_created = models.IntegerField(default=0)
    projects_created = models.IntegerField(default=0)
    
    # Funnel conversion rates
    request_to_email_rate = models.FloatField(null=True, blank=True)
    email_to_click_rate = models.FloatField(null=True, blank=True)
    click_to_account_rate = models.FloatField(null=True, blank=True)
    overall_conversion_rate = models.FloatField(null=True, blank=True)
    
    # Usage metrics (from insights)
    total_llm_requests = models.IntegerField(default=0)
    total_tokens_used = models.IntegerField(default=0)
    average_rating = models.FloatField(null=True, blank=True)
    issues_flagged = models.IntegerField(default=0)
    issues_fixed = models.IntegerField(default=0)
    
    # Customer health
    at_risk_customers = models.IntegerField(default=0)
    healthy_customers = models.IntegerField(default=0)
    
    # Google Ads metrics
    ad_impressions = models.IntegerField(default=0)
    ad_clicks = models.IntegerField(default=0)
    ad_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ad_conversions = models.IntegerField(default=0)
    ad_ctr = models.FloatField(null=True, blank=True)
    ad_cpc = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ad_cpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Attribution breakdown
    conversions_by_source = models.JSONField(default=dict)
    conversions_by_campaign = models.JSONField(default=dict)
    
    # Top requests (what people are asking for)
    top_requests = models.JSONField(default=list)
    
    # Issues summary
    common_issues = models.JSONField(default=list)
    
    # Detailed event log (for the day)
    all_sessions = models.JSONField(default=list)
    
    # Email sent
    report_sent = models.BooleanField(default=False)
    report_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Daily Report: {self.date}"


class AdminNotification(models.Model):
    """
    Notifications for Faibric Admin.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    NOTIFICATION_TYPE_CHOICES = [
        ('daily_report', 'Daily Report'),
        ('alert', 'Alert'),
        ('at_risk_customer', 'At-Risk Customer'),
        ('high_volume', 'High Volume'),
        ('quality_issue', 'Quality Issue'),
    ]
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    
    # Related objects
    daily_report = models.ForeignKey(
        DailyReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type}: {self.title}"

