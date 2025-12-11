"""
Customer Insights & Quality Assurance System.

Tracks all customer inputs, identifies quality issues,
and enables Faibric admin to provide fixes.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class CustomerInput(models.Model):
    """
    Logs EVERY input from customers for analysis and quality assurance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Customer info
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='customer_inputs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='customer_inputs'
    )
    
    # Input classification
    INPUT_TYPE_CHOICES = [
        ('code_generation', 'Code Generation'),
        ('code_modification', 'Code Modification'),
        ('code_fix', 'Code Fix/Debug'),
        ('code_explanation', 'Code Explanation'),
        ('chat', 'AI Chat'),
        ('project_creation', 'Project Creation'),
        ('feature_request', 'Feature Request'),
        ('other', 'Other'),
    ]
    input_type = models.CharField(max_length=30, choices=INPUT_TYPE_CHOICES)
    
    # The actual input
    user_input = models.TextField(help_text="What the customer asked for")
    context = models.TextField(blank=True, help_text="Additional context provided")
    
    # What we generated
    llm_response = models.TextField(help_text="What Faibric returned")
    
    # Model used
    model_used = models.CharField(max_length=50)
    tokens_input = models.IntegerField(default=0)
    tokens_output = models.IntegerField(default=0)
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # Project context
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Quality indicators (auto-detected + user feedback)
    QUALITY_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('good', 'Good Quality'),
        ('needs_review', 'Needs Review'),
        ('flagged', 'Flagged for Improvement'),
        ('fixed', 'Fixed by Admin'),
    ]
    quality_status = models.CharField(
        max_length=20,
        choices=QUALITY_STATUS_CHOICES,
        default='pending'
    )
    
    # Auto-detection flags
    was_error = models.BooleanField(default=False)
    response_too_short = models.BooleanField(default=False)
    user_rating = models.IntegerField(null=True, blank=True, help_text="1-5 rating from user")
    user_accepted = models.BooleanField(null=True, blank=True)
    user_feedback = models.TextField(blank=True)
    
    # Tracking
    session_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['quality_status', 'created_at']),
            models.Index(fields=['input_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.input_type} ({self.quality_status})"
    
    @property
    def needs_attention(self) -> bool:
        """Check if this input needs admin attention."""
        if self.was_error:
            return True
        if self.user_rating and self.user_rating <= 2:
            return True
        if self.user_accepted is False:
            return True
        if self.quality_status in ['needs_review', 'flagged']:
            return True
        return False


class QualityReview(models.Model):
    """
    Admin review of a customer input.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    customer_input = models.ForeignKey(
        CustomerInput,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='quality_reviews'
    )
    
    # Review outcome
    REVIEW_OUTCOME_CHOICES = [
        ('approved', 'Approved - Quality OK'),
        ('needs_fix', 'Needs Fix'),
        ('fixed', 'Fixed'),
        ('wont_fix', "Won't Fix"),
        ('learning', 'Added to Learning'),
    ]
    outcome = models.CharField(max_length=20, choices=REVIEW_OUTCOME_CHOICES)
    
    # Review notes
    admin_notes = models.TextField(blank=True)
    
    # Quality score (admin assessment)
    quality_score = models.IntegerField(
        null=True, blank=True,
        help_text="1-10 quality assessment"
    )
    
    # Issue categorization
    ISSUE_CATEGORY_CHOICES = [
        ('incorrect_code', 'Incorrect Code'),
        ('incomplete', 'Incomplete Response'),
        ('wrong_language', 'Wrong Language/Framework'),
        ('poor_quality', 'Poor Code Quality'),
        ('misunderstood', 'Misunderstood Request'),
        ('hallucination', 'Hallucination'),
        ('outdated', 'Outdated Approach'),
        ('security', 'Security Issue'),
        ('other', 'Other'),
    ]
    issue_category = models.CharField(
        max_length=30,
        choices=ISSUE_CATEGORY_CHOICES,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review of {self.customer_input_id} - {self.outcome}"


class AdminFix(models.Model):
    """
    Admin-provided fix for a customer issue.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    customer_input = models.ForeignKey(
        CustomerInput,
        on_delete=models.CASCADE,
        related_name='admin_fixes'
    )
    
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_fixes'
    )
    
    # The fix
    improved_response = models.TextField(help_text="Admin's improved response")
    fix_notes = models.TextField(blank=True, help_text="Notes about what was fixed")
    
    # How the fix was created
    FIX_METHOD_CHOICES = [
        ('manual', 'Manual Edit'),
        ('regenerated', 'Regenerated with Claude Opus 4.5'),
        ('hybrid', 'AI + Manual Edit'),
    ]
    fix_method = models.CharField(max_length=20, choices=FIX_METHOD_CHOICES)
    
    # If regenerated, what prompt was used
    improved_prompt = models.TextField(
        blank=True,
        help_text="Improved prompt used for regeneration"
    )
    
    # Customer notification
    customer_notified = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    notification_email_id = models.CharField(max_length=100, blank=True)
    
    # Customer response to fix
    customer_viewed = models.BooleanField(default=False)
    customer_viewed_at = models.DateTimeField(null=True, blank=True)
    customer_accepted_fix = models.BooleanField(null=True, blank=True)
    customer_feedback = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Fix for {self.customer_input_id} by {self.admin}"


class CustomerPattern(models.Model):
    """
    Detected patterns in customer requests for insights.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Pattern identification
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    PATTERN_TYPE_CHOICES = [
        ('common_request', 'Common Request Type'),
        ('common_error', 'Common Error'),
        ('common_complaint', 'Common Complaint'),
        ('feature_gap', 'Feature Gap'),
        ('framework_trend', 'Framework/Tech Trend'),
        ('quality_issue', 'Quality Issue Pattern'),
    ]
    pattern_type = models.CharField(max_length=30, choices=PATTERN_TYPE_CHOICES)
    
    # Pattern data
    keywords = models.JSONField(default=list)
    example_inputs = models.JSONField(default=list)
    occurrence_count = models.IntegerField(default=0)
    
    # Impact assessment
    impact_level = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='medium'
    )
    
    # Action taken
    action_taken = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    
    first_detected_at = models.DateTimeField()
    last_detected_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-occurrence_count']
    
    def __str__(self):
        return f"{self.name} ({self.occurrence_count} occurrences)"


class InsightReport(models.Model):
    """
    Periodic insight reports for Faibric admin.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    REPORT_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Metrics
    total_inputs = models.IntegerField(default=0)
    total_users = models.IntegerField(default=0)
    total_tenants = models.IntegerField(default=0)
    
    # Quality metrics
    average_rating = models.FloatField(null=True, blank=True)
    acceptance_rate = models.FloatField(null=True, blank=True)
    error_rate = models.FloatField(null=True, blank=True)
    needs_review_count = models.IntegerField(default=0)
    fixed_count = models.IntegerField(default=0)
    
    # Breakdowns
    by_input_type = models.JSONField(default=dict)
    by_quality_status = models.JSONField(default=dict)
    by_model = models.JSONField(default=dict)
    
    # Top issues
    top_issues = models.JSONField(default=list)
    top_patterns = models.JSONField(default=list)
    
    # Customers needing attention
    customers_needing_attention = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-period_start']
        unique_together = [['report_type', 'period_start']]
    
    def __str__(self):
        return f"{self.report_type} Report: {self.period_start}"


class CustomerHealth(models.Model):
    """
    Track customer health score for proactive support.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='health_score'
    )
    
    # Health metrics
    health_score = models.IntegerField(
        default=100,
        help_text="0-100 health score"
    )
    
    # Component scores
    satisfaction_score = models.IntegerField(default=100)
    engagement_score = models.IntegerField(default=100)
    success_rate = models.FloatField(default=1.0)
    
    # Flags
    is_at_risk = models.BooleanField(default=False)
    risk_reasons = models.JSONField(default=list)
    
    # Activity
    last_activity_at = models.DateTimeField(null=True, blank=True)
    total_inputs = models.IntegerField(default=0)
    total_accepted = models.IntegerField(default=0)
    total_rejected = models.IntegerField(default=0)
    average_rating = models.FloatField(null=True, blank=True)
    
    # Issues
    unresolved_issues = models.IntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['health_score']
        verbose_name_plural = "Customer Health Scores"
    
    def __str__(self):
        return f"{self.tenant.name} - Health: {self.health_score}"
    
    def calculate_health(self):
        """Recalculate health score."""
        scores = []
        
        # Satisfaction (based on ratings)
        if self.average_rating:
            self.satisfaction_score = int((self.average_rating / 5) * 100)
            scores.append(self.satisfaction_score)
        
        # Success rate (accepted vs rejected)
        if self.total_inputs > 0:
            self.success_rate = self.total_accepted / self.total_inputs
            scores.append(int(self.success_rate * 100))
        
        # Engagement (based on activity)
        # ...
        
        # Calculate overall health
        if scores:
            self.health_score = int(sum(scores) / len(scores))
        
        # Determine if at risk
        self.is_at_risk = self.health_score < 50 or self.unresolved_issues > 3
        
        if self.is_at_risk:
            reasons = []
            if self.health_score < 50:
                reasons.append("Low health score")
            if self.unresolved_issues > 3:
                reasons.append(f"{self.unresolved_issues} unresolved issues")
            if self.average_rating and self.average_rating < 3:
                reasons.append("Low satisfaction rating")
            self.risk_reasons = reasons
        
        self.save()







