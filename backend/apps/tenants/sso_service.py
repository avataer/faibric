"""
SSO Service for handling SAML 2.0 and OpenID Connect authentication flows.
"""
import base64
import hashlib
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import SSOConfiguration, Tenant, TenantMembership

User = get_user_model()


class SSOError(Exception):
    """Base exception for SSO-related errors."""
    pass


class SAMLError(SSOError):
    """SAML-specific errors."""
    pass


class OIDCError(SSOError):
    """OIDC-specific errors."""
    pass


class SSOService:
    """
    Service class for handling SSO authentication flows.
    Supports SAML 2.0 and OpenID Connect providers.
    """

    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        try:
            self.config = tenant.sso_config
        except SSOConfiguration.DoesNotExist:
            raise SSOError("SSO is not configured for this tenant")

        if not self.config.is_enabled:
            raise SSOError("SSO is not enabled for this tenant")

    def initiate_login(self, callback_url: str) -> str:
        """
        Initiate SSO login based on configured provider type.
        Returns the redirect URL to the identity provider.
        """
        if self.config.sso_type == 'saml':
            return self.initiate_saml_login(callback_url)
        elif self.config.sso_type == 'oidc':
            return self.initiate_oidc_login(callback_url)
        else:
            raise SSOError(f"Unknown SSO type: {self.config.sso_type}")

    def initiate_saml_login(self, callback_url: str) -> str:
        """
        Initiate SAML authentication flow.
        Returns the redirect URL to the SAML IdP.
        """
        if not self.config.idp_sso_url:
            raise SAMLError("SAML IdP SSO URL is not configured")

        # Generate SAML AuthnRequest
        request_id = f"_id{secrets.token_hex(16)}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Build the SAML AuthnRequest XML
        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    AssertionConsumerServiceURL="{callback_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{callback_url}</saml:Issuer>
    <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" AllowCreate="true"/>
</samlp:AuthnRequest>"""

        # Encode the request
        encoded_request = base64.b64encode(saml_request.encode()).decode()

        # Build the redirect URL
        params = {
            'SAMLRequest': encoded_request,
            'RelayState': callback_url,
        }
        redirect_url = f"{self.config.idp_sso_url}?{urllib.parse.urlencode(params)}"

        return redirect_url

    def handle_saml_callback(self, saml_response: str, relay_state: str = None) -> Tuple[User, bool]:
        """
        Handle SAML authentication response.
        Validates the SAML response and provisions/updates the user.
        Returns tuple of (user, was_created).
        """
        if not self.config.idp_certificate:
            raise SAMLError("SAML IdP certificate is not configured")

        try:
            # Decode the SAML response
            decoded_response = base64.b64decode(saml_response).decode()

            # Parse user attributes from SAML response
            # Note: In production, use a proper SAML library like python3-saml
            user_attrs = self._parse_saml_response(decoded_response)

            if not user_attrs.get('email'):
                raise SAMLError("Email not found in SAML response")

            # Validate domain restriction if configured
            if self.config.domain_restriction:
                email_domain = user_attrs['email'].split('@')[-1]
                if email_domain != self.config.domain_restriction:
                    raise SAMLError(f"Email domain {email_domain} is not allowed")

            return self.provision_or_update_user(user_attrs)

        except Exception as e:
            if isinstance(e, SAMLError):
                raise
            raise SAMLError(f"Failed to process SAML response: {str(e)}")

    def _parse_saml_response(self, xml_response: str) -> Dict[str, Any]:
        """
        Parse user attributes from SAML response.
        Note: This is a simplified parser. Use python3-saml in production.
        """
        import re

        attrs = {}

        # Extract NameID (email)
        nameid_match = re.search(r'<saml:NameID[^>]*>([^<]+)</saml:NameID>', xml_response)
        if nameid_match:
            attrs['email'] = nameid_match.group(1).strip()

        # Extract common attributes
        attr_patterns = {
            'email': r'Name="email"[^>]*>.*?<saml:AttributeValue[^>]*>([^<]+)',
            'first_name': r'Name="firstName"[^>]*>.*?<saml:AttributeValue[^>]*>([^<]+)',
            'last_name': r'Name="lastName"[^>]*>.*?<saml:AttributeValue[^>]*>([^<]+)',
            'username': r'Name="username"[^>]*>.*?<saml:AttributeValue[^>]*>([^<]+)',
        }

        for attr_name, pattern in attr_patterns.items():
            match = re.search(pattern, xml_response, re.DOTALL)
            if match:
                attrs[attr_name] = match.group(1).strip()

        return attrs

    def initiate_oidc_login(self, callback_url: str) -> str:
        """
        Initiate OpenID Connect authentication flow.
        Returns the redirect URL to the OIDC provider.
        """
        if not self.config.oidc_issuer:
            raise OIDCError("OIDC issuer URL is not configured")
        if not self.config.oidc_client_id:
            raise OIDCError("OIDC client ID is not configured")

        # Generate state and nonce for security
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        # Build authorization URL
        # Standard OIDC discovery endpoint
        auth_endpoint = f"{self.config.oidc_issuer.rstrip('/')}/authorize"

        params = {
            'client_id': self.config.oidc_client_id,
            'response_type': 'code',
            'scope': 'openid email profile',
            'redirect_uri': callback_url,
            'state': state,
            'nonce': nonce,
        }

        redirect_url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"

        return redirect_url

    def handle_oidc_callback(self, code: str, callback_url: str, state: str = None) -> Tuple[User, bool]:
        """
        Handle OIDC authentication callback.
        Exchanges authorization code for tokens and provisions/updates user.
        Returns tuple of (user, was_created).
        """
        if not self.config.oidc_client_secret:
            raise OIDCError("OIDC client secret is not configured")

        try:
            import requests

            # Exchange code for tokens
            token_endpoint = f"{self.config.oidc_issuer.rstrip('/')}/token"

            token_response = requests.post(
                token_endpoint,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': callback_url,
                    'client_id': self.config.oidc_client_id,
                    'client_secret': self.config.oidc_client_secret,
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30,
            )

            if not token_response.ok:
                raise OIDCError(f"Token exchange failed: {token_response.text}")

            tokens = token_response.json()
            access_token = tokens.get('access_token')

            if not access_token:
                raise OIDCError("No access token in response")

            # Get user info
            userinfo_endpoint = f"{self.config.oidc_issuer.rstrip('/')}/userinfo"

            userinfo_response = requests.get(
                userinfo_endpoint,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=30,
            )

            if not userinfo_response.ok:
                raise OIDCError(f"Failed to get user info: {userinfo_response.text}")

            userinfo = userinfo_response.json()

            # Map OIDC claims to user attributes
            user_attrs = {
                'email': userinfo.get('email'),
                'first_name': userinfo.get('given_name', ''),
                'last_name': userinfo.get('family_name', ''),
                'username': userinfo.get('preferred_username', userinfo.get('email', '').split('@')[0]),
            }

            if not user_attrs['email']:
                raise OIDCError("Email not found in user info")

            # Validate domain restriction if configured
            if self.config.domain_restriction:
                email_domain = user_attrs['email'].split('@')[-1]
                if email_domain != self.config.domain_restriction:
                    raise OIDCError(f"Email domain {email_domain} is not allowed")

            return self.provision_or_update_user(user_attrs)

        except requests.RequestException as e:
            raise OIDCError(f"OIDC request failed: {str(e)}")
        except Exception as e:
            if isinstance(e, OIDCError):
                raise
            raise OIDCError(f"Failed to process OIDC callback: {str(e)}")

    def provision_or_update_user(self, user_attrs: Dict[str, Any]) -> Tuple[User, bool]:
        """
        Create or update a user based on SSO attributes.
        Also creates tenant membership if needed.
        Returns tuple of (user, was_created).
        """
        email = user_attrs['email']
        was_created = False

        # Try to find existing user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            if not self.config.auto_provision_users:
                raise SSOError("User not found and auto-provisioning is disabled")

            # Create new user
            username = user_attrs.get('username', email.split('@')[0])

            # Ensure unique username
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=user_attrs.get('first_name', ''),
                last_name=user_attrs.get('last_name', ''),
            )
            was_created = True

        # Update user info if needed
        if not was_created:
            updated = False
            if user_attrs.get('first_name') and user.first_name != user_attrs['first_name']:
                user.first_name = user_attrs['first_name']
                updated = True
            if user_attrs.get('last_name') and user.last_name != user_attrs['last_name']:
                user.last_name = user_attrs['last_name']
                updated = True
            if updated:
                user.save()

        # Ensure tenant membership
        membership, membership_created = TenantMembership.objects.get_or_create(
            tenant=self.tenant,
            user=user,
            defaults={
                'role': self.config.default_role,
                'is_active': True,
            }
        )

        # Activate membership if it was inactive
        if not membership_created and not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=['is_active'])

        return user, was_created
