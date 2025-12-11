import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class BillingProfile(models.Model):
    """
    Billing profile for a tenant - stores payment method and billing info.
    Customer enters this information ONCE.
    """
    PAYMENT_PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='billing_profile'
    )
    
    # Billing contact info (entered once)
    billing_name = models.CharField(max_length=200, blank=True)
    billing_email = models.EmailField(blank=True)
    billing_address_line1 = models.CharField(max_length=200, blank=True)
    billing_address_line2 = models.CharField(max_length=200, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_postal_code = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=2, default='US', help_text='ISO 3166-1 alpha-2')
    
    # Primary payment provider
    payment_provider = models.CharField(
        max_length=20,
        choices=PAYMENT_PROVIDER_CHOICES,
        default='stripe'
    )
    
    # Stripe integration
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    stripe_payment_method_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    
    # PayPal integration
    paypal_customer_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    paypal_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Card info (last 4 digits for display only - full card never stored)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)  # visa, mastercard, etc.
    card_exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    card_exp_year = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    has_valid_payment_method = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Billing for {self.tenant.name}"
    
    @property
    def display_card(self):
        """Display card info like '**** **** **** 4242'"""
        if self.card_last_four:
            return f"•••• •••• •••• {self.card_last_four}"
        return None


class Subscription(models.Model):
    """
    Subscription plan for a tenant.
    """
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('starter', 'Starter - $29/mo'),
        ('pro', 'Professional - $79/mo'),
        ('enterprise', 'Enterprise - $199/mo'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('trialing', 'Trialing'),
        ('paused', 'Paused'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Pricing
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Limits based on plan
    max_apps = models.PositiveIntegerField(default=3)
    max_ai_tokens_per_month = models.PositiveIntegerField(default=50000)
    max_storage_gb = models.PositiveIntegerField(default=1)
    
    # Trial info
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Billing cycle
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.plan}"
    
    @property
    def is_active(self):
        return self.status in ['active', 'trialing']


class UsageRecord(models.Model):
    """
    Track usage for billing purposes.
    Records AI tokens, storage, bandwidth, etc.
    """
    USAGE_TYPE_CHOICES = [
        ('ai_tokens', 'AI Tokens'),
        ('storage_bytes', 'Storage (bytes)'),
        ('bandwidth_bytes', 'Bandwidth (bytes)'),
        ('api_calls', 'API Calls'),
        ('deployments', 'Deployments'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    
    usage_type = models.CharField(max_length=50, choices=USAGE_TYPE_CHOICES)
    quantity = models.BigIntegerField(default=0)
    
    # For associating with specific resources
    resource_type = models.CharField(max_length=50, blank=True)  # e.g., 'project'
    resource_id = models.CharField(max_length=100, blank=True)
    
    # Description for invoice line items
    description = models.CharField(max_length=200, blank=True)
    
    # Billing period this usage belongs to
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Pricing at time of usage
    unit_price = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0.000000'))
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Whether this has been invoiced
    invoiced = models.BooleanField(default=False)
    invoice = models.ForeignKey(
        'Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_records'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'usage_type', 'period_start']),
            models.Index(fields=['tenant', 'invoiced']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.usage_type}: {self.quantity}"


class Invoice(models.Model):
    """
    Monthly invoice for a tenant.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('void', 'Void'),
        ('uncollectible', 'Uncollectible'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    
    # Invoice number (human-readable)
    number = models.CharField(max_length=50, unique=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Currency
    currency = models.CharField(max_length=3, default='USD')
    
    # Billing period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Due date
    due_date = models.DateTimeField()
    
    # External references
    stripe_invoice_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_invoice_id = models.CharField(max_length=100, blank=True, null=True)
    
    # PDF storage
    pdf_url = models.URLField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"Invoice {self.number} - {self.tenant.name}"


class InvoiceLineItem(models.Model):
    """
    Individual line item on an invoice.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Type of charge
    charge_type = models.CharField(max_length=50, default='usage')  # subscription, usage, one_time
    
    class Meta:
        ordering = ['charge_type', 'description']
    
    def __str__(self):
        return f"{self.description}: ${self.amount}"


class PaymentMethod(models.Model):
    """
    Stored payment methods for a billing profile.
    Allows multiple cards, one default.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing_profile = models.ForeignKey(
        BillingProfile,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    # Provider info
    provider = models.CharField(max_length=20)  # stripe, paypal
    provider_payment_method_id = models.CharField(max_length=100)
    
    # Card display info
    card_brand = models.CharField(max_length=20, blank=True)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    card_exp_year = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # Status
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.card_brand} •••• {self.card_last_four}"

