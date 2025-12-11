from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Tenant, TenantMembership, TenantInvitation, AuditLog
from .serializers import (
    TenantSerializer, TenantCreateSerializer, TenantMembershipSerializer,
    TenantInvitationSerializer, InviteUserSerializer, AcceptInvitationSerializer,
    AuditLogSerializer, UserTenantSerializer
)
from .permissions import TenantPermission, TenantAdminPermission, TenantOwnerPermission
from .utils import create_tenant_for_user, invite_user_to_tenant, accept_invitation, get_user_tenants


class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tenants.
    Users can only see and manage tenants they belong to.
    """
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # Allow creating tenant without existing tenant
    allow_no_tenant = True
    
    def get_queryset(self):
        """Return only tenants the user belongs to"""
        return Tenant.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True
        ).distinct()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TenantCreateSerializer
        return TenantSerializer
    
    def perform_create(self, serializer):
        """Create a new tenant with the current user as owner"""
        tenant = create_tenant_for_user(
            self.request.user,
            name=serializer.validated_data.get('name'),
            slug=serializer.validated_data.get('slug')
        )
        serializer.instance = tenant
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), TenantAdminPermission()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), TenantOwnerPermission()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def my_tenants(self, request):
        """List all tenants the current user belongs to with their roles"""
        tenant_data = get_user_tenants(request.user)
        serializer = UserTenantSerializer(tenant_data, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """List all members of a tenant"""
        tenant = self.get_object()
        memberships = TenantMembership.objects.filter(tenant=tenant, is_active=True)
        serializer = TenantMembershipSerializer(memberships, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """Invite a user to the tenant"""
        tenant = self.get_object()
        
        # Check if user is admin
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True,
            role__in=['owner', 'admin']
        ).first()
        
        if not membership:
            return Response(
                {'error': 'You must be an admin to invite users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if user is already a member
        if TenantMembership.objects.filter(
            tenant=tenant, 
            user__email=serializer.validated_data['email']
        ).exists():
            return Response(
                {'error': 'User is already a member of this tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invitation = invite_user_to_tenant(
            tenant=tenant,
            email=serializer.validated_data['email'],
            role=serializer.validated_data['role'],
            invited_by=request.user
        )
        
        # TODO: Send invitation email
        
        return Response(
            TenantInvitationSerializer(invitation).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def audit_logs(self, request, pk=None):
        """Get audit logs for a tenant"""
        tenant = self.get_object()
        
        # Only admins can view audit logs
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True,
            role__in=['owner', 'admin']
        ).first()
        
        if not membership:
            return Response(
                {'error': 'You must be an admin to view audit logs'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        logs = AuditLog.objects.filter(tenant=tenant)[:100]
        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)


class TenantMembershipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tenant memberships.
    """
    serializer_class = TenantMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return TenantMembership.objects.none()
        return TenantMembership.objects.filter(tenant=tenant)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a membership (remove user from tenant)"""
        membership = self.get_object()
        
        # Can't deactivate owner
        if membership.role == 'owner':
            return Response(
                {'error': 'Cannot remove the tenant owner'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership.is_active = False
        membership.save()
        
        return Response({'status': 'membership deactivated'})
    
    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """Change a member's role"""
        membership = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in dict(TenantMembership.ROLE_CHOICES):
            return Response(
                {'error': 'Invalid role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Can't change owner role
        if membership.role == 'owner':
            return Response(
                {'error': 'Cannot change owner role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Can't promote to owner
        if new_role == 'owner':
            return Response(
                {'error': 'Cannot promote to owner. Transfer ownership instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership.role = new_role
        membership.save()
        
        return Response(TenantMembershipSerializer(membership).data)


class InvitationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing invitations.
    """
    serializer_class = TenantInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Show invitations for current user's email
        return TenantInvitation.objects.filter(
            email=self.request.user.email,
            accepted_at__isnull=True
        )
    
    @action(detail=False, methods=['post'])
    def accept(self, request):
        """Accept an invitation"""
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            membership = accept_invitation(
                token=serializer.validated_data['token'],
                user=request.user
            )
            return Response(
                TenantMembershipSerializer(membership).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

