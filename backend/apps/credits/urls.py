"""
URL patterns for credits API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SubscriptionTierViewSet,
    CreditBalanceViewSet,
    LLMRequestViewSet,
    CreditTransactionViewSet,
    UsageReportViewSet,
    AdminStatsViewSet,
)

router = DefaultRouter()
router.register(r'tiers', SubscriptionTierViewSet, basename='subscription-tiers')
router.register(r'balance', CreditBalanceViewSet, basename='credit-balance')
router.register(r'requests', LLMRequestViewSet, basename='llm-requests')
router.register(r'transactions', CreditTransactionViewSet, basename='credit-transactions')
router.register(r'reports', UsageReportViewSet, basename='usage-reports')
router.register(r'admin/stats', AdminStatsViewSet, basename='admin-stats')

urlpatterns = [
    path('', include(router.urls)),
]

