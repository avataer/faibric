from rest_framework import permissions
from .middleware import set_current_tenant


class TenantPermission(permissions.BasePermission):
    """
    Permission class that ensures users can only access resources in their tenant.
    Also sets the tenant context since JWT auth happens after middleware.
    """
    
    message = "You do not have permission to access this tenant's resources."
    
    def has_permission(self, request, view):
        """Check if user has access to any tenant"""
        # Allow unauthenticated access to safe methods if view allows it
        if not request.user or not request.user.is_authenticated:
            return request.method in permissions.SAFE_METHODS and getattr(view, 'allow_anonymous', False)
        
        # If tenant not set by middleware (JWT auth happens after middleware),
        # try to set it now
        if not hasattr(request, 'tenant') or request.tenant is None:
            self._set_tenant_from_user(request)
        
        # User must have a tenant
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            # Check if this is a tenant creation endpoint
            if getattr(view, 'allow_no_tenant', False):
                return True
            return False
        
        return True
    
    def _set_tenant_from_user(self, request):
        """Set tenant context from authenticated user"""
        from .models import TenantMembership
        
        user = request.user
        
        # Check for explicit tenant header
        tenant_id = request.headers.get('X-Tenant-ID')
        
        if tenant_id:
            try:
                membership = TenantMembership.objects.select_related('tenant').get(
                    user=user,
                    tenant_id=tenant_id,
                    is_active=True
                )
                request.tenant = membership.tenant
                request.tenant_membership = membership
                set_current_tenant(membership.tenant)
            except TenantMembership.DoesNotExist:
                pass
        else:
            # Get user's default/primary tenant
            membership = TenantMembership.objects.select_related('tenant').filter(
                user=user,
                is_active=True
            ).order_by('-role').first()
            
            if membership:
                request.tenant = membership.tenant
                request.tenant_membership = membership
                set_current_tenant(membership.tenant)
    
    def has_object_permission(self, request, view, obj):
        """Check if user has access to this specific object"""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False
        
        # Check if object has tenant_id field
        if hasattr(obj, 'tenant_id'):
            return str(obj.tenant_id) == str(tenant.id)
        
        # Check if object has tenant field
        if hasattr(obj, 'tenant'):
            return obj.tenant == tenant
        
        # For objects without tenant field (legacy), check user ownership
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id
        
        return True


class TenantAdminPermission(TenantPermission):
    """
    Permission that requires admin or owner role in the tenant.
    """
    
    message = "You must be a tenant admin to perform this action."
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        membership = getattr(request, 'tenant_membership', None)
        if not membership:
            return False
        
        return membership.role in ['owner', 'admin']


class TenantOwnerPermission(TenantPermission):
    """
    Permission that requires owner role in the tenant.
    """
    
    message = "You must be the tenant owner to perform this action."
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        membership = getattr(request, 'tenant_membership', None)
        if not membership:
            return False
        
        return membership.role == 'owner'


class IsTenantMember(permissions.BasePermission):
    """
    Check if user is a member of a specific tenant (by URL parameter).
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get tenant_id from URL kwargs
        tenant_id = view.kwargs.get('tenant_id') or view.kwargs.get('pk')
        if not tenant_id:
            return True
        
        from apps.tenants.models import TenantMembership
        return TenantMembership.objects.filter(
            user=request.user,
            tenant_id=tenant_id,
            is_active=True
        ).exists()

