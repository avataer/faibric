import uuid
import secrets
from django.db import models
from django.utils import timezone


class EmailList(models.Model):
    """
    An email list/newsletter for a tenant.
    Customers can create multiple lists (newsletter, updates, marketing, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='email_lists'
    )
    
    # List identification
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    
    # Settings
    double_optin = models.BooleanField(default=True, help_text="Require email confirmation")
    welcome_email_enabled = models.BooleanField(default=True)
    welcome_email_subject = models.CharField(max_length=200, default="Welcome!")
    welcome_email_body = models.TextField(blank=True)
    
    # External sync
    mailchimp_list_id = models.CharField(max_length=50, blank=True)
    sendgrid_list_id = models.CharField(max_length=50, blank=True)
    convertkit_form_id = models.CharField(max_length=50, blank=True)
    
    # Stats
    subscriber_count = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['tenant', 'slug']]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"
    
    def update_subscriber_count(self):
        """Update cached subscriber count."""
        self.subscriber_count = self.subscribers.filter(
            status='subscribed'
        ).count()
        self.save(update_fields=['subscriber_count'])


class Subscriber(models.Model):
    """
    A subscriber to an email list.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('subscribed', 'Subscribed'),
        ('unsubscribed', 'Unsubscribed'),
        ('bounced', 'Bounced'),
        ('complained', 'Complained'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email_list = models.ForeignKey(EmailList, on_delete=models.CASCADE, related_name='subscribers')
    
    # Contact info
    email = models.EmailField()
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    
    # Custom fields
    custom_fields = models.JSONField(default=dict, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Confirmation token (for double opt-in)
    confirmation_token = models.CharField(max_length=100, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Unsubscribe token
    unsubscribe_token = models.CharField(max_length=100, unique=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    unsubscribe_reason = models.TextField(blank=True)
    
    # Source tracking
    source = models.CharField(max_length=100, blank=True)  # Where they signed up
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['email_list', 'email']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email_list', 'status']),
            models.Index(fields=['email_list', 'email']),
            models.Index(fields=['unsubscribe_token']),
            models.Index(fields=['confirmation_token']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.email_list.name})"
    
    def save(self, *args, **kwargs):
        if not self.unsubscribe_token:
            self.unsubscribe_token = secrets.token_urlsafe(32)
        if not self.confirmation_token and self.status == 'pending':
            self.confirmation_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
    
    def confirm(self):
        """Confirm subscription."""
        self.status = 'subscribed'
        self.confirmed_at = timezone.now()
        self.confirmation_token = ''
        self.save()
        self.email_list.update_subscriber_count()
    
    def unsubscribe(self, reason=''):
        """Unsubscribe from list."""
        self.status = 'unsubscribed'
        self.unsubscribed_at = timezone.now()
        self.unsubscribe_reason = reason
        self.save()
        self.email_list.update_subscriber_count()


class EmailConfig(models.Model):
    """
    Email provider configuration for a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='email_config'
    )
    
    # Mailchimp
    mailchimp_enabled = models.BooleanField(default=False)
    mailchimp_api_key = models.CharField(max_length=100, blank=True)
    mailchimp_server_prefix = models.CharField(max_length=10, blank=True)  # e.g., 'us1'
    
    # SendGrid
    sendgrid_enabled = models.BooleanField(default=False)
    sendgrid_api_key = models.CharField(max_length=100, blank=True)
    
    # ConvertKit
    convertkit_enabled = models.BooleanField(default=False)
    convertkit_api_key = models.CharField(max_length=100, blank=True)
    convertkit_api_secret = models.CharField(max_length=100, blank=True)
    
    # Default from address
    default_from_email = models.EmailField(blank=True)
    default_from_name = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Email config for {self.tenant.name}"

