import secrets
from datetime import timedelta
from django.utils import timezone
from django.utils.text import slugify

from .middleware import get_current_tenant, get_current_user


def generate_invitation_token():
    """Generate a secure random token for invitations"""
    return secrets.token_urlsafe(32)


def create_tenant_for_user(user, name=None, slug=None):
    """
    Create a new tenant for a user.
    Called when a new user signs up or when creating a new organization.
    """
    from .models import Tenant, TenantMembership
    
    # Generate default name and slug if not provided
    if not name:
        name = f"{user.username}'s Organization"
    
    if not slug:
        base_slug = slugify(name)[:90]
        slug = base_slug
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
    
    # Create tenant
    tenant = Tenant.objects.create(
        name=name,
        slug=slug,
        owner=user
    )
    
    # Create owner membership
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role='owner',
        invited_by=user,
        accepted_at=timezone.now()
    )
    
    return tenant


def invite_user_to_tenant(tenant, email, role='member', invited_by=None):
    """
    Create an invitation for a user to join a tenant.
    """
    from .models import TenantInvitation
    
    invitation = TenantInvitation.objects.create(
        tenant=tenant,
        email=email,
        role=role,
        token=generate_invitation_token(),
        invited_by=invited_by or tenant.owner,
        expires_at=timezone.now() + timedelta(days=7)
    )
    
    return invitation


def accept_invitation(token, user):
    """
    Accept a tenant invitation.
    """
    from .models import TenantInvitation, TenantMembership
    
    try:
        invitation = TenantInvitation.objects.get(token=token)
    except TenantInvitation.DoesNotExist:
        raise ValueError("Invalid invitation token")
    
    if invitation.is_expired:
        raise ValueError("Invitation has expired")
    
    if invitation.is_accepted:
        raise ValueError("Invitation has already been accepted")
    
    # Check if user already has membership
    if TenantMembership.objects.filter(tenant=invitation.tenant, user=user).exists():
        raise ValueError("User is already a member of this tenant")
    
    # Create membership
    membership = TenantMembership.objects.create(
        tenant=invitation.tenant,
        user=user,
        role=invitation.role,
        invited_by=invitation.invited_by,
        accepted_at=timezone.now()
    )
    
    # Mark invitation as accepted
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=['accepted_at'])
    
    return membership


def get_user_tenants(user):
    """
    Get all tenants a user belongs to.
    """
    from .models import TenantMembership
    
    return [
        {
            'tenant': membership.tenant,
            'role': membership.role,
            'membership': membership
        }
        for membership in TenantMembership.objects.select_related('tenant').filter(
            user=user,
            is_active=True
        ).order_by('-role')
    ]


def ensure_user_has_tenant(user):
    """
    Ensure a user has at least one tenant.
    Creates a default tenant if none exists.
    """
    from .models import TenantMembership
    
    if not TenantMembership.objects.filter(user=user, is_active=True).exists():
        return create_tenant_for_user(user)
    
    return TenantMembership.objects.filter(
        user=user, 
        is_active=True
    ).order_by('-role').first().tenant


class TenantQuerySetMixin:
    """
    Mixin for QuerySets that automatically filters by current tenant.
    """
    
    def for_tenant(self, tenant=None):
        """Filter queryset by tenant"""
        if tenant is None:
            tenant = get_current_tenant()
        
        if tenant is None:
            return self.none()
        
        return self.filter(tenant=tenant)
    
    def for_current_tenant(self):
        """Filter queryset by current tenant from middleware"""
        return self.for_tenant(get_current_tenant())


class TenantModelMixin:
    """
    Mixin for models that belong to a tenant.
    Automatically sets tenant on save if not set.
    """
    
    def save(self, *args, **kwargs):
        if not self.tenant_id:
            tenant = get_current_tenant()
            if tenant:
                self.tenant = tenant
        super().save(*args, **kwargs)

