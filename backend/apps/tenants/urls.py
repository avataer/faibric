from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet, TenantMembershipViewSet, InvitationViewSet

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'memberships', TenantMembershipViewSet, basename='membership')
router.register(r'invitations', InvitationViewSet, basename='invitation')

urlpatterns = [
    path('', include(router.urls)),
]

