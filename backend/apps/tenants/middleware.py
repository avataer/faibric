import threading
from django.utils.deprecation import MiddlewareMixin

# Thread-local storage for current tenant
_thread_locals = threading.local()


def get_current_tenant():
    """Get the current tenant from thread-local storage"""
    return getattr(_thread_locals, 'tenant', None)


def get_current_user():
    """Get the current user from thread-local storage"""
    return getattr(_thread_locals, 'user', None)


def set_current_tenant(tenant):
    """Set the current tenant in thread-local storage"""
    _thread_locals.tenant = tenant


def set_current_user(user):
    """Set the current user in thread-local storage"""
    _thread_locals.user = user


def clear_tenant_context():
    """Clear tenant context (call at end of request)"""
    _thread_locals.tenant = None
    _thread_locals.user = None


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware that sets the current tenant based on the authenticated user.
    
    This middleware:
    1. Identifies the current tenant from the user's memberships
    2. Stores it in thread-local storage for access throughout the request
    3. Can also accept X-Tenant-ID header for users with multiple tenants
    """
    
    def process_request(self, request):
        # Clear any previous tenant context
        clear_tenant_context()
        
        # Skip if user is not authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        user = request.user
        set_current_user(user)
        
        # Check for explicit tenant header (for multi-tenant users)
        tenant_id = request.headers.get('X-Tenant-ID')
        
        if tenant_id:
            # Validate user has access to this tenant
            from apps.tenants.models import TenantMembership
            try:
                membership = TenantMembership.objects.select_related('tenant').get(
                    user=user,
                    tenant_id=tenant_id,
                    is_active=True
                )
                set_current_tenant(membership.tenant)
                request.tenant = membership.tenant
                request.tenant_membership = membership
            except TenantMembership.DoesNotExist:
                # User doesn't have access to this tenant
                pass
        else:
            # Get user's default/primary tenant
            from apps.tenants.models import TenantMembership
            membership = TenantMembership.objects.select_related('tenant').filter(
                user=user,
                is_active=True
            ).order_by('-role').first()  # Prefer owner/admin roles
            
            if membership:
                set_current_tenant(membership.tenant)
                request.tenant = membership.tenant
                request.tenant_membership = membership
            else:
                # User has no tenant - they need to create one or be invited
                request.tenant = None
                request.tenant_membership = None
        
        return None
    
    def process_response(self, request, response):
        # Clean up thread-local storage
        clear_tenant_context()
        return response


class TenantAuditMiddleware(MiddlewareMixin):
    """
    Middleware that logs important actions for security auditing.
    """
    
    # Actions to audit
    AUDITED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Paths to exclude from auditing
    EXCLUDED_PATHS = [
        '/api/health/',
        '/api/auth/token/refresh/',
    ]
    
    def process_response(self, request, response):
        # Only audit certain methods
        if request.method not in self.AUDITED_METHODS:
            return response
        
        # Skip excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return response
        
        # Skip if no authenticated user
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        
        # Only audit successful modifications
        if response.status_code not in [200, 201, 204]:
            return response
        
        # Log the action (async to not slow down response)
        try:
            self._create_audit_log(request, response)
        except Exception:
            # Don't fail the request if audit logging fails
            pass
        
        return response
    
    def _create_audit_log(self, request, response):
        """Create an audit log entry"""
        from apps.tenants.models import AuditLog
        
        # Determine action type
        action_map = {
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        action = action_map.get(request.method, 'api_access')
        
        # Extract resource info from path
        path_parts = request.path.strip('/').split('/')
        resource_type = path_parts[1] if len(path_parts) > 1 else 'unknown'
        resource_id = path_parts[2] if len(path_parts) > 2 else ''
        
        # Get IP address
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        if not ip:
            ip = request.META.get('REMOTE_ADDR', '')
        
        AuditLog.objects.create(
            tenant=getattr(request, 'tenant', None),
            user=request.user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip or None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            description=f"{request.method} {request.path}"
        )

