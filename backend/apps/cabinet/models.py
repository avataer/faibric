import uuid
import secrets
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class CabinetConfig(models.Model):
    """
    Cabinet configuration for a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='cabinet_config'
    )
    
    # Branding
    cabinet_name = models.CharField(max_length=100, default='My Account')
    logo_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, default='#3B82F6')
    
    # Features
    orders_enabled = models.BooleanField(default=True)
    subscriptions_enabled = models.BooleanField(default=True)
    files_enabled = models.BooleanField(default=True)
    support_enabled = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)
    
    # Auth settings
    allow_registration = models.BooleanField(default=True)
    require_email_verification = models.BooleanField(default=True)
    password_min_length = models.PositiveIntegerField(default=8)
    
    # Session
    session_timeout_hours = models.PositiveIntegerField(default=24)
    
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cabinet config for {self.tenant.name}"


class EndUser(models.Model):
    """
    End-user of customer's app (the customer's client).
    Separate from Faibric's User model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='end_users'
    )
    
    # Auth
    email = models.EmailField()
    password_hash = models.CharField(max_length=255)
    
    # Profile
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    display_name = models.CharField(max_length=200, blank=True)
    avatar_url = models.URLField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    
    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='US')
    
    # Preferences
    preferences = models.JSONField(default=dict, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = [['tenant', 'email']]
        indexes = [
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['tenant', 'is_active']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or self.email.split('@')[0]
    
    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)


class EndUserSession(models.Model):
    """
    Session for end-user authentication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        EndUser,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    token = models.CharField(max_length=64, unique=True)
    
    # Device info
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Validity
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['token', 'is_active']),
        ]
    
    def __str__(self):
        return f"Session for {self.user.email}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @classmethod
    def create_session(cls, user, hours=24, user_agent='', ip_address=None):
        token = secrets.token_urlsafe(48)
        expires_at = timezone.now() + timezone.timedelta(hours=hours)
        
        session = cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
        return session


class EmailVerification(models.Model):
    """
    Email verification token.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        EndUser,
        on_delete=models.CASCADE,
        related_name='email_verifications'
    )
    
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def create_verification(cls, user, hours=24):
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timezone.timedelta(hours=hours)
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )


class PasswordReset(models.Model):
    """
    Password reset token.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        EndUser,
        on_delete=models.CASCADE,
        related_name='password_resets'
    )
    
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def create_reset(cls, user, hours=1):
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timezone.timedelta(hours=hours)
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )


class SupportTicket(models.Model):
    """
    Support ticket from end-user.
    """
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        WAITING = 'waiting', 'Waiting for Customer'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    user = models.ForeignKey(
        EndUser,
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    
    # Ticket info
    ticket_number = models.CharField(max_length=20, unique=True)
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=50, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    
    # Related entities
    related_order_id = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'user', 'status']),
            models.Index(fields=['ticket_number']),
        ]
    
    def __str__(self):
        return f"Ticket {self.ticket_number}: {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            import random
            self.ticket_number = f"TKT-{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)


class TicketMessage(models.Model):
    """
    Message in a support ticket.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # Sender
    is_staff_reply = models.BooleanField(default=False)
    sender_name = models.CharField(max_length=200)
    sender_email = models.EmailField(blank=True)
    
    # Content
    content = models.TextField()
    
    # Attachments
    attachments = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender_name}"


class Notification(models.Model):
    """
    Notification for end-user.
    """
    class NotificationType(models.TextChoices):
        ORDER = 'order', 'Order Update'
        SUPPORT = 'support', 'Support Response'
        SYSTEM = 'system', 'System Message'
        PROMOTION = 'promotion', 'Promotion'
        REMINDER = 'reminder', 'Reminder'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        EndUser,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Link to related entity
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type}: {self.title}"
    
    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class Activity(models.Model):
    """
    Activity log for end-user's cabinet.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        EndUser,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    
    activity_type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Related entity
    entity_type = models.CharField(max_length=50, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    
    # Icon
    icon = models.CharField(max_length=50, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Activities'
    
    def __str__(self):
        return f"{self.activity_type}: {self.title}"







