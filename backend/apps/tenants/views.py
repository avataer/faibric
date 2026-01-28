from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Tenant, TenantMembership, TenantInvitation, AuditLog, WhitelabelConfig, SSOConfiguration
from .serializers import (
    TenantSerializer, TenantCreateSerializer, TenantMembershipSerializer,
    TenantInvitationSerializer, InviteUserSerializer, AcceptInvitationSerializer,
    AuditLogSerializer, UserTenantSerializer, WhitelabelConfigSerializer,
    SSOConfigurationSerializer
)
from .sso_service import SSOService, SSOError
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


class WhitelabelConfigView(APIView):
    """
    API endpoint for managing tenant whitelabel configuration.
    GET: Returns current tenant whitelabel config (creates one if it does not exist)
    PUT: Updates whitelabel config
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get the whitelabel config for the current user's tenant"""
        membership = request.user.tenant_memberships.filter(is_active=True).first()
        if not membership:
            return Response(
                {'error': 'No active tenant membership found'},
                status=status.HTTP_404_NOT_FOUND
            )
        tenant = membership.tenant
        config, created = WhitelabelConfig.objects.get_or_create(tenant=tenant)
        serializer = WhitelabelConfigSerializer(config)
        return Response(serializer.data)

    def put(self, request):
        """Update the whitelabel config for the current user's tenant"""
        membership = request.user.tenant_memberships.filter(
            is_active=True,
            role__in=['owner', 'admin']
        ).first()
        if not membership:
            return Response(
                {'error': 'You must be a tenant admin or owner to modify whitelabel config'},
                status=status.HTTP_403_FORBIDDEN
            )
        tenant = membership.tenant
        config, created = WhitelabelConfig.objects.get_or_create(tenant=tenant)
        serializer = WhitelabelConfigSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyDomainView(APIView):
    """
    API endpoint for verifying custom domain DNS configuration.
    POST: Verifies custom domain by checking DNS CNAME record
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Verify the custom domain for the current user's tenant"""
        membership = request.user.tenant_memberships.filter(is_active=True).first()
        if not membership:
            return Response(
                {'error': 'No active tenant membership found'},
                status=status.HTTP_404_NOT_FOUND
            )
        tenant = membership.tenant
        config = get_object_or_404(WhitelabelConfig, tenant=tenant)

        if not config.custom_domain:
            return Response(
                {'error': 'No custom domain configured'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Simple domain verification - check if CNAME exists
        try:
            import dns.resolver
            answers = dns.resolver.resolve(config.custom_domain, 'CNAME')
            config.domain_verified = True
            config.save()
            return Response({
                'verified': True,
                'domain': config.custom_domain
            })
        except Exception:
            config.domain_verified = False
            config.save()
            return Response(
                {'verified': False, 'error': 'DNS verification failed'},
                status=status.HTTP_400_BAD_REQUEST
            )


class SSOConfigView(APIView):
    """
    API endpoint for managing tenant SSO configuration.
    GET: Returns current tenant SSO config (creates one if it does not exist)
    PUT: Updates SSO config
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get the SSO config for the current user's tenant"""
        membership = request.user.tenant_memberships.filter(
            is_active=True,
            role__in=['owner', 'admin']
        ).first()
        if not membership:
            return Response(
                {'error': 'You must be a tenant admin or owner to view SSO config'},
                status=status.HTTP_403_FORBIDDEN
            )
        tenant = membership.tenant
        config, created = SSOConfiguration.objects.get_or_create(tenant=tenant)
        serializer = SSOConfigurationSerializer(config)
        return Response(serializer.data)

    def put(self, request):
        """Update the SSO config for the current user's tenant"""
        membership = request.user.tenant_memberships.filter(
            is_active=True,
            role__in=['owner', 'admin']
        ).first()
        if not membership:
            return Response(
                {'error': 'You must be a tenant admin or owner to modify SSO config'},
                status=status.HTTP_403_FORBIDDEN
            )
        tenant = membership.tenant
        config, created = SSOConfiguration.objects.get_or_create(tenant=tenant)
        serializer = SSOConfigurationSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SSOLoginView(APIView):
    """
    API endpoint to initiate SSO login.
    GET: Redirects to the configured identity provider.
    """
    permission_classes = []  # Public endpoint

    def get(self, request, tenant_slug):
        """Initiate SSO login for the specified tenant"""
        tenant = get_object_or_404(Tenant, slug=tenant_slug)

        # Build callback URL
        callback_url = request.build_absolute_uri(f'/api/tenants/sso/callback/{tenant_slug}/')

        try:
            sso_service = SSOService(tenant)
            redirect_url = sso_service.initiate_login(callback_url)
            return Response({'redirect_url': redirect_url})
        except SSOError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SSOCallbackView(APIView):
    """
    API endpoint to handle SSO callback from identity provider.
    POST: Handles SAML or OIDC callback and returns authentication token.
    """
    permission_classes = []  # Public endpoint

    def post(self, request, tenant_slug):
        """Handle SSO callback for the specified tenant"""
        from rest_framework_simplejwt.tokens import RefreshToken

        tenant = get_object_or_404(Tenant, slug=tenant_slug)

        try:
            sso_service = SSOService(tenant)
            config = tenant.sso_config

            # Build callback URL for validation
            callback_url = request.build_absolute_uri(f'/api/tenants/sso/callback/{tenant_slug}/')

            if config.sso_type == 'saml':
                # Handle SAML response
                saml_response = request.data.get('SAMLResponse')
                relay_state = request.data.get('RelayState')

                if not saml_response:
                    return Response(
                        {'error': 'SAMLResponse not provided'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                user, was_created = sso_service.handle_saml_callback(saml_response, relay_state)

            elif config.sso_type == 'oidc':
                # Handle OIDC callback
                code = request.data.get('code')
                state = request.data.get('state')

                if not code:
                    return Response(
                        {'error': 'Authorization code not provided'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                user, was_created = sso_service.handle_oidc_callback(code, callback_url, state)

            else:
                return Response(
                    {'error': 'Unknown SSO type'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate JWT tokens for the user
            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'tenant': {
                    'id': str(tenant.id),
                    'name': tenant.name,
                    'slug': tenant.slug,
                },
                'was_created': was_created,
            })

        except SSOError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

