from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Tenant, TenantMembership, TenantInvitation, AuditLog

User = get_user_model()


class TenantSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'owner', 'owner_username',
            'plan', 'settings', 'is_active', 'member_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class TenantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['name', 'slug']
    
    def validate_slug(self, value):
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError("This slug is already taken.")
        return value


class TenantMembershipSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = TenantMembership
        fields = [
            'id', 'tenant', 'tenant_name', 'user', 'user_username', 
            'user_email', 'role', 'permissions', 'is_active',
            'invited_at', 'accepted_at'
        ]
        read_only_fields = ['id', 'tenant', 'user', 'invited_at', 'accepted_at']


class TenantInvitationSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    invited_by_username = serializers.CharField(source='invited_by.username', read_only=True)
    
    class Meta:
        model = TenantInvitation
        fields = [
            'id', 'tenant', 'tenant_name', 'email', 'role',
            'invited_by', 'invited_by_username', 'created_at', 
            'expires_at', 'is_expired', 'is_accepted'
        ]
        read_only_fields = ['id', 'tenant', 'token', 'invited_by', 'created_at', 'expires_at']


class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=TenantMembership.ROLE_CHOICES, default='member')


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()


class AuditLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_username', 'action', 'resource_type',
            'resource_id', 'ip_address', 'description', 'created_at'
        ]


class UserTenantSerializer(serializers.Serializer):
    """Serializer for listing user's tenants"""
    tenant = TenantSerializer()
    role = serializers.CharField()

