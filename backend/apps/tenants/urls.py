from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantViewSet, TenantMembershipViewSet, InvitationViewSet,
    WhitelabelConfigView, VerifyDomainView,
    SSOConfigView, SSOLoginView, SSOCallbackView
)

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'memberships', TenantMembershipViewSet, basename='membership')
router.register(r'invitations', InvitationViewSet, basename='invitation')

urlpatterns = [
    path('', include(router.urls)),
    path('whitelabel/', WhitelabelConfigView.as_view(), name='whitelabel-config'),
    path('whitelabel/verify-domain/', VerifyDomainView.as_view(), name='whitelabel-verify-domain'),
    path('sso/config/', SSOConfigView.as_view(), name='sso-config'),
    path('sso/login/<slug:tenant_slug>/', SSOLoginView.as_view(), name='sso-login'),
    path('sso/callback/<slug:tenant_slug>/', SSOCallbackView.as_view(), name='sso-callback'),
]

