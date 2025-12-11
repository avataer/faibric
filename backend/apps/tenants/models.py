import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Tenant(models.Model):
    """
    Tenant represents a customer organization.
    All data in the system is scoped to a tenant for security isolation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Organization/Company name")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly identifier")
    
    # Owner is the primary admin of this tenant
    owner = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='owned_tenants',
        help_text="Primary owner/admin of this tenant"
    )
    
    # Billing info (will be expanded in Phase 2)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    plan = models.CharField(
        max_length=50, 
        default='free',
        choices=[
            ('free', 'Free'),
            ('starter', 'Starter'),
            ('pro', 'Professional'),
            ('enterprise', 'Enterprise'),
        ]
    )
    
    # Settings
    settings = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.slug})"


class TenantMembership(models.Model):
    """
    Links users to tenants with specific roles.
    A user can belong to multiple tenants.
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    
    # Permissions (can be customized per member)
    permissions = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sent_invitations'
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = [['tenant', 'user']]
        ordering = ['tenant', '-role', 'user']
        indexes = [
            models.Index(fields=['tenant', 'user']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} @ {self.tenant.name} ({self.role})"
    
    def accept_invitation(self):
        """Mark invitation as accepted"""
        self.accepted_at = timezone.now()
        self.save(update_fields=['accepted_at'])


class AuditLog(models.Model):
    """
    Security audit log for tracking important actions.
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('permission_change', 'Permission Change'),
        ('settings_change', 'Settings Change'),
        ('export', 'Data Export'),
        ('api_access', 'API Access'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='audit_logs',
        null=True,  # System-level events may not have a tenant
        blank=True
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs'
    )
    
    # Action details
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100, help_text="Model/resource name")
    resource_id = models.CharField(max_length=100, blank=True, help_text="ID of affected resource")
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Change details
    old_values = models.JSONField(null=True, blank=True, help_text="Previous state")
    new_values = models.JSONField(null=True, blank=True, help_text="New state")
    description = models.TextField(blank=True, help_text="Human-readable description")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"{user_str} {self.action} {self.resource_type} at {self.created_at}"


class TenantInvitation(models.Model):
    """
    Pending invitations to join a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=TenantMembership.ROLE_CHOICES, default='member')
    
    # Invitation token (for email link)
    token = models.CharField(max_length=100, unique=True)
    
    # Status
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_tenant_invitations')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['token']),
        ]
    
    def __str__(self):
        return f"Invitation for {self.email} to {self.tenant.name}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_accepted(self):
        return self.accepted_at is not None

