import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class AnalyticsConfig(models.Model):
    """
    Analytics configuration for a tenant.
    Stores API keys for external analytics services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='analytics_config'
    )
    
    # Mixpanel integration
    mixpanel_enabled = models.BooleanField(default=False)
    mixpanel_token = models.CharField(max_length=100, blank=True)
    mixpanel_api_secret = models.CharField(max_length=100, blank=True)
    
    # Google Analytics integration
    ga_enabled = models.BooleanField(default=False)
    ga_measurement_id = models.CharField(max_length=50, blank=True)  # G-XXXXXXXX
    ga_api_secret = models.CharField(max_length=100, blank=True)
    
    # Custom webhook (send events to customer's own endpoint)
    webhook_enabled = models.BooleanField(default=False)
    webhook_url = models.URLField(blank=True)
    webhook_secret = models.CharField(max_length=100, blank=True)
    
    # Internal analytics (always enabled)
    internal_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics config for {self.tenant.name}"


class Event(models.Model):
    """
    Analytics event - tracks user actions.
    Stored internally and forwarded to configured services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='analytics_events'
    )
    
    # Event identification
    event_name = models.CharField(max_length=100, db_index=True)
    
    # User identification (anonymous or identified)
    distinct_id = models.CharField(max_length=200, db_index=True)  # User ID or anonymous ID
    anonymous_id = models.CharField(max_length=200, blank=True)
    user_id = models.CharField(max_length=200, blank=True)  # Identified user
    
    # Event properties
    properties = models.JSONField(default=dict, blank=True)
    
    # Context (device, location, etc.)
    context = models.JSONField(default=dict, blank=True)
    
    # Source info
    source = models.CharField(max_length=50, default='web')  # web, ios, android, api
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Processing status
    forwarded_to_mixpanel = models.BooleanField(default=False)
    forwarded_to_ga = models.BooleanField(default=False)
    forwarded_to_webhook = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'event_name', 'timestamp']),
            models.Index(fields=['tenant', 'distinct_id', 'timestamp']),
            models.Index(fields=['tenant', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.event_name} - {self.distinct_id}"


class Funnel(models.Model):
    """
    Funnel definition for conversion tracking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='funnels'
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Funnel is a template if tenant is null
    is_template = models.BooleanField(default=False)
    template_name = models.CharField(max_length=100, blank=True)  # signup, purchase, etc.
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Time window for funnel completion (in hours)
    conversion_window_hours = models.PositiveIntegerField(default=168)  # 7 days
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = [['tenant', 'name']]
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name if self.tenant else 'Template'})"


class FunnelStep(models.Model):
    """
    Individual step in a funnel.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    funnel = models.ForeignKey(Funnel, on_delete=models.CASCADE, related_name='steps')
    
    # Step order
    order = models.PositiveIntegerField()
    
    # Step definition
    name = models.CharField(max_length=200)
    event_name = models.CharField(max_length=100)  # Event that completes this step
    
    # Optional filter on event properties
    property_filters = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['funnel', 'order']
        unique_together = [['funnel', 'order']]
    
    def __str__(self):
        return f"{self.funnel.name} - Step {self.order}: {self.name}"


class FunnelConversion(models.Model):
    """
    Track individual user journeys through funnels.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    funnel = models.ForeignKey(Funnel, on_delete=models.CASCADE, related_name='conversions')
    
    # User tracking
    distinct_id = models.CharField(max_length=200)
    
    # Progress
    current_step = models.PositiveIntegerField(default=0)
    completed_steps = models.JSONField(default=list)  # List of {step_order, timestamp}
    
    # Status
    is_completed = models.BooleanField(default=False)
    is_dropped = models.BooleanField(default=False)
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['funnel', 'distinct_id']),
            models.Index(fields=['funnel', 'is_completed']),
        ]
    
    def __str__(self):
        status = "Completed" if self.is_completed else f"Step {self.current_step}"
        return f"{self.funnel.name} - {self.distinct_id} - {status}"


class UserProfile(models.Model):
    """
    Profile data for tracked users (for customer's end-users, not Faibric users).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='tracked_users'
    )
    
    # User identification
    distinct_id = models.CharField(max_length=200)
    
    # Profile properties (name, email, etc.)
    properties = models.JSONField(default=dict)
    
    # First and last seen
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Event counts
    total_events = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = [['tenant', 'distinct_id']]
        indexes = [
            models.Index(fields=['tenant', 'distinct_id']),
            models.Index(fields=['tenant', 'last_seen']),
        ]
    
    def __str__(self):
        return f"{self.distinct_id} ({self.tenant.name})"


class APIUsageLog(models.Model):
    """
    Track AI API usage for cost analysis.
    Every API call is logged with tokens and cost.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to session/user
    session_token = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    user_id = models.IntegerField(blank=True, null=True, db_index=True)
    
    # API call details
    model = models.CharField(max_length=100)
    task_type = models.CharField(max_length=50, db_index=True)  # generate_new, modify, summarize, etc.
    
    # Token usage
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    
    # Cost in USD
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Success tracking
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Extra metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_token', 'created_at']),
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['model', 'created_at']),
            models.Index(fields=['task_type', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.model} - {self.task_type} - ${self.cost}"


class UserSummary(models.Model):
    """
    AI-generated summary of user activity and preferences.
    Updated periodically by cheap AI model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to session
    session_token = models.CharField(max_length=100, unique=True, db_index=True)
    
    # User info extracted from chats
    user_type = models.CharField(max_length=100, blank=True)  # e.g., "stocks trader", "hairdresser"
    user_needs = models.TextField(blank=True)  # What they want
    preferences = models.JSONField(default=dict, blank=True)  # Extracted preferences
    
    # Experience summary
    total_builds = models.IntegerField(default=0)
    successful_builds = models.IntegerField(default=0)
    total_modifications = models.IntegerField(default=0)
    
    # AI-generated summary of their journey
    journey_summary = models.TextField(blank=True)
    satisfaction_score = models.FloatField(null=True, blank=True)  # 0-100
    
    # All messages from this user (for context)
    all_messages = models.JSONField(default=list)
    
    # Cost tracking
    total_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.session_token} - {self.user_type}"

