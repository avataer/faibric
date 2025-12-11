"""
Credits and Usage Tracking System.

This system tracks:
1. LLM requests (each "change request" = 1 credit + tokens generated)
2. Monthly credit allowances based on subscription tier
3. Credit purchases and top-ups
4. Detailed usage analytics
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class SubscriptionTier(models.Model):
    """
    Subscription tiers for Faibric.
    FREE, STARTER ($19.99), PRO ($99.99)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    
    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Credits included per month
    monthly_credits = models.IntegerField(default=0, help_text="Credits included per month")
    monthly_tokens = models.IntegerField(default=0, help_text="Token limit per month (0 = based on credits)")
    
    # Overage pricing
    credit_overage_price = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.10,
        help_text="Price per additional credit"
    )
    
    # Feature limits
    max_projects = models.IntegerField(default=1)
    max_team_members = models.IntegerField(default=1)
    max_storage_gb = models.IntegerField(default=1)
    max_api_calls_daily = models.IntegerField(default=100)
    
    # Features included
    features = models.JSONField(default=list, blank=True)
    
    # Stripe
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)
    
    # Display
    is_popular = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'price_monthly']
    
    def __str__(self):
        return f"{self.name} (${self.price_monthly}/mo)"


class CreditBalance(models.Model):
    """
    Credit balance for a tenant.
    Tracks current credits and usage.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='credit_balance'
    )
    
    # Current subscription
    subscription_tier = models.ForeignKey(
        SubscriptionTier,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    # Credit balances
    credits_remaining = models.IntegerField(default=0, help_text="Credits left this period")
    credits_used_this_period = models.IntegerField(default=0)
    tokens_used_this_period = models.IntegerField(default=0)
    
    # Purchased credits (don't expire)
    purchased_credits = models.IntegerField(default=0, help_text="Extra purchased credits")
    
    # Period tracking
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Lifetime stats
    total_credits_used = models.IntegerField(default=0)
    total_tokens_generated = models.IntegerField(default=0)
    total_requests = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.tenant.name} - {self.credits_remaining} credits"
    
    def has_credits(self, amount: int = 1) -> bool:
        """Check if tenant has enough credits."""
        return (self.credits_remaining + self.purchased_credits) >= amount
    
    def use_credit(self, amount: int = 1, tokens: int = 0) -> bool:
        """
        Use credits. Returns True if successful.
        First uses subscription credits, then purchased credits.
        """
        if not self.has_credits(amount):
            return False
        
        # Use subscription credits first
        if self.credits_remaining >= amount:
            self.credits_remaining -= amount
        else:
            # Use remaining subscription credits + purchased
            remaining_from_sub = self.credits_remaining
            self.credits_remaining = 0
            self.purchased_credits -= (amount - remaining_from_sub)
        
        self.credits_used_this_period += amount
        self.tokens_used_this_period += tokens
        self.total_credits_used += amount
        self.total_tokens_generated += tokens
        self.total_requests += 1
        self.save()
        
        return True
    
    def add_purchased_credits(self, amount: int):
        """Add purchased credits."""
        self.purchased_credits += amount
        self.save()
    
    def reset_period(self):
        """Reset for new billing period."""
        if self.subscription_tier:
            self.credits_remaining = self.subscription_tier.monthly_credits
        else:
            self.credits_remaining = 0
        
        self.credits_used_this_period = 0
        self.tokens_used_this_period = 0
        
        # Set new period
        self.period_start = timezone.now()
        # Approximate month
        from datetime import timedelta
        self.period_end = self.period_start + timedelta(days=30)
        
        self.save()


class LLMRequest(models.Model):
    """
    Log of all LLM requests for learning and analytics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='llm_requests'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Request details
    REQUEST_TYPE_CHOICES = [
        ('generate', 'Code Generation'),
        ('modify', 'Code Modification'),
        ('chat', 'AI Chat'),
        ('analyze', 'Code Analysis'),
        ('explain', 'Code Explanation'),
        ('debug', 'Debugging'),
        ('other', 'Other'),
    ]
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    
    # Model used
    MODEL_CHOICES = [
        # Primary - Code Generation
        ('claude-opus-4.5', 'Claude Opus 4.5'),
        # Secondary - Chat
        ('claude-sonnet-4', 'Claude Sonnet 4'),
        # Fast tasks
        ('claude-haiku-3.5', 'Claude Haiku 3.5'),
        # Embeddings
        ('text-embedding-3-small', 'OpenAI Embeddings'),
        # Legacy (for old records)
        ('gpt-4', 'GPT-4'),
        ('claude-3-opus', 'Claude 3 Opus'),
    ]
    model = models.CharField(max_length=50, choices=MODEL_CHOICES)
    
    # The actual request and response (for learning)
    prompt = models.TextField(help_text="User's request/prompt")
    system_prompt = models.TextField(blank=True)
    response = models.TextField(help_text="LLM's response")
    
    # Token usage
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    
    # Cost tracking (Faibric's cost)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Credits charged
    credits_charged = models.IntegerField(default=1)
    
    # Context
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    session_id = models.CharField(max_length=100, blank=True)
    
    # Performance
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # Quality (for learning)
    user_rating = models.IntegerField(null=True, blank=True, help_text="1-5 rating")
    was_accepted = models.BooleanField(null=True, blank=True)
    was_modified = models.BooleanField(null=True, blank=True)
    
    # Error tracking
    was_error = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    # Metadata for ML
    request_metadata = models.JSONField(default=dict, blank=True)
    response_metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['model', 'created_at']),
            models.Index(fields=['request_type', 'created_at']),
            models.Index(fields=['user_rating']),
        ]
    
    def __str__(self):
        return f"{self.request_type} - {self.model} ({self.total_tokens} tokens)"


class CreditTransaction(models.Model):
    """
    Credit transactions (purchases, usage, refunds).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='credit_transactions'
    )
    
    TRANSACTION_TYPE_CHOICES = [
        ('subscription', 'Monthly Subscription'),
        ('purchase', 'Credit Purchase'),
        ('usage', 'Credit Usage'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus Credits'),
        ('adjustment', 'Admin Adjustment'),
    ]
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    
    # Amount (positive = add, negative = subtract)
    credits = models.IntegerField()
    
    # For purchases
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    stripe_payment_id = models.CharField(max_length=100, blank=True)
    
    # Reference
    description = models.TextField(blank=True)
    llm_request = models.ForeignKey(
        LLMRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Balance after transaction
    balance_after = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        sign = '+' if self.credits > 0 else ''
        return f"{self.transaction_type}: {sign}{self.credits} credits"


class UsageReport(models.Model):
    """
    Daily/monthly usage reports for analytics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='usage_reports'
    )
    
    # Period
    PERIOD_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPE_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Usage stats
    total_requests = models.IntegerField(default=0)
    total_credits_used = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    total_input_tokens = models.IntegerField(default=0)
    total_output_tokens = models.IntegerField(default=0)
    
    # Breakdown by model
    usage_by_model = models.JSONField(default=dict, blank=True)
    
    # Breakdown by request type
    usage_by_type = models.JSONField(default=dict, blank=True)
    
    # Cost
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Quality metrics
    average_rating = models.FloatField(null=True, blank=True)
    acceptance_rate = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-period_start']
        unique_together = [['tenant', 'period_type', 'period_start']]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.period_type} {self.period_start}"

