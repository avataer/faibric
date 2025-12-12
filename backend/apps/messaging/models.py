import uuid
from django.db import models
from django.utils import timezone


class MessageChannel(models.TextChoices):
    """Supported message channels."""
    EMAIL = 'email', 'Email'
    SMS = 'sms', 'SMS'
    PUSH = 'push', 'Push Notification'
    IN_APP = 'in_app', 'In-App Notification'
    WEBHOOK = 'webhook', 'Webhook'


class MessagingConfig(models.Model):
    """
    Messaging provider configuration for a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='messaging_config'
    )
    
    # Email configuration
    email_enabled = models.BooleanField(default=True)
    email_provider = models.CharField(max_length=20, default='smtp', choices=[
        ('smtp', 'SMTP'),
        ('sendgrid', 'SendGrid'),
        ('ses', 'Amazon SES'),
        ('mailgun', 'Mailgun'),
    ])
    
    # SMTP settings
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_use_tls = models.BooleanField(default=True)
    
    # SendGrid
    sendgrid_api_key = models.CharField(max_length=200, blank=True)
    
    # Default from address
    default_from_email = models.EmailField(default='noreply@faibric.com')
    default_from_name = models.CharField(max_length=100, default='Faibric')
    
    # SMS configuration
    sms_enabled = models.BooleanField(default=False)
    sms_provider = models.CharField(max_length=20, default='twilio', choices=[
        ('twilio', 'Twilio'),
        ('nexmo', 'Vonage (Nexmo)'),
        ('messagebird', 'MessageBird'),
    ])
    
    # Twilio
    twilio_account_sid = models.CharField(max_length=100, blank=True)
    twilio_auth_token = models.CharField(max_length=100, blank=True)
    twilio_phone_number = models.CharField(max_length=20, blank=True)
    
    # Push notifications
    push_enabled = models.BooleanField(default=False)
    push_provider = models.CharField(max_length=20, default='firebase', choices=[
        ('firebase', 'Firebase Cloud Messaging'),
        ('onesignal', 'OneSignal'),
    ])
    
    # Firebase
    firebase_server_key = models.TextField(blank=True)
    firebase_project_id = models.CharField(max_length=100, blank=True)
    
    # In-app notifications (always enabled)
    in_app_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Messaging config for {self.tenant.name}"


class MessageTemplate(models.Model):
    """
    Reusable message templates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='message_templates'
    )
    
    # Template identity
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    
    # Channel (which channel this template is for)
    channel = models.CharField(max_length=20, choices=MessageChannel.choices)
    
    # Template content
    subject = models.CharField(max_length=500, blank=True)  # For email
    body = models.TextField()  # Main content (supports variables)
    body_html = models.TextField(blank=True)  # HTML version for email
    
    # Variables documentation
    variables = models.JSONField(default=list, blank=True)  # ["name", "order_id", ...]
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['tenant', 'slug', 'channel']]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.channel})"
    
    def render(self, context: dict) -> dict:
        """Render template with context variables."""
        subject = self.subject
        body = self.body
        body_html = self.body_html
        
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"  # {{variable}}
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
            body_html = body_html.replace(placeholder, str(value))
        
        return {
            'subject': subject,
            'body': body,
            'body_html': body_html,
        }


class Message(models.Model):
    """
    A sent or scheduled message.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        QUEUED = 'queued', 'Queued'
        SENDING = 'sending', 'Sending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'
        BOUNCED = 'bounced', 'Bounced'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # Channel
    channel = models.CharField(max_length=20, choices=MessageChannel.choices)
    
    # Recipient
    recipient = models.CharField(max_length=255)  # Email, phone, user_id
    recipient_name = models.CharField(max_length=200, blank=True)
    
    # Template used (optional)
    template = models.ForeignKey(
        MessageTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages'
    )
    
    # Content
    subject = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    body_html = models.TextField(blank=True)
    
    # Context data used
    context = models.JSONField(default=dict, blank=True)
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    
    # Provider response
    provider_message_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'channel', 'status']),
            models.Index(fields=['tenant', 'recipient']),
            models.Index(fields=['scheduled_at', 'status']),
        ]
    
    def __str__(self):
        return f"{self.channel} to {self.recipient} ({self.status})"


class InAppNotification(models.Model):
    """
    In-app notifications for end users.
    """
    class NotificationType(models.TextChoices):
        INFO = 'info', 'Info'
        SUCCESS = 'success', 'Success'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Target user (from app's user system)
    user_id = models.CharField(max_length=255)  # AppUser ID or external ID
    
    # Notification content
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    
    # Action (optional link/button)
    action_url = models.URLField(blank=True)
    action_label = models.CharField(max_length=100, blank=True)
    
    # Metadata
    data = models.JSONField(default=dict, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'user_id', 'is_read']),
            models.Index(fields=['tenant', 'user_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.user_id})"
    
    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class PushToken(models.Model):
    """
    Push notification tokens for devices.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='push_tokens'
    )
    
    # User association
    user_id = models.CharField(max_length=255)
    
    # Device info
    token = models.TextField()  # FCM token
    device_type = models.CharField(max_length=20, choices=[
        ('web', 'Web'),
        ('android', 'Android'),
        ('ios', 'iOS'),
    ])
    device_name = models.CharField(max_length=200, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['tenant', 'token']]
        indexes = [
            models.Index(fields=['tenant', 'user_id', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.device_type} token for {self.user_id}"









