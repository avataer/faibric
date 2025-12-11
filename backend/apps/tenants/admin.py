from django.contrib import admin
from .models import Tenant, TenantMembership, TenantInvitation, AuditLog


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'owner', 'plan', 'is_active', 'created_at']
    list_filter = ['plan', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'owner__username', 'owner__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['owner']
    
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'slug', 'owner')
        }),
        ('Billing', {
            'fields': ('plan', 'stripe_customer_id')
        }),
        ('Settings', {
            'fields': ('settings', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'role', 'is_active', 'invited_at', 'accepted_at']
    list_filter = ['role', 'is_active', 'invited_at']
    search_fields = ['user__username', 'user__email', 'tenant__name']
    readonly_fields = ['id', 'invited_at']
    raw_id_fields = ['user', 'tenant', 'invited_by']


@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'tenant', 'role', 'invited_by', 'created_at', 'expires_at', 'is_accepted']
    list_filter = ['role', 'created_at']
    search_fields = ['email', 'tenant__name']
    readonly_fields = ['id', 'token', 'created_at']
    raw_id_fields = ['tenant', 'invited_by']
    
    def is_accepted(self, obj):
        return obj.is_accepted
    is_accepted.boolean = True


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'tenant', 'action', 'resource_type', 'resource_id', 'ip_address']
    list_filter = ['action', 'resource_type', 'created_at']
    search_fields = ['user__username', 'resource_type', 'resource_id', 'description']
    readonly_fields = ['id', 'created_at', 'tenant', 'user', 'action', 'resource_type', 
                      'resource_id', 'ip_address', 'user_agent', 'old_values', 'new_values', 'description']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

