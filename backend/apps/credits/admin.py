"""
Django admin for credits.
"""
from django.contrib import admin

from .models import (
    SubscriptionTier,
    CreditBalance,
    LLMRequest,
    CreditTransaction,
    UsageReport,
)


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_monthly', 'monthly_credits', 'is_popular', 'is_active', 'display_order']
    list_filter = ['is_active', 'is_popular']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(CreditBalance)
class CreditBalanceAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'subscription_tier', 'credits_remaining', 'purchased_credits', 'total_requests', 'period_end']
    list_filter = ['subscription_tier']
    search_fields = ['tenant__name']
    readonly_fields = ['total_credits_used', 'total_tokens_generated', 'total_requests']


@admin.register(LLMRequest)
class LLMRequestAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'request_type', 'model', 'total_tokens', 'credits_charged', 'user_rating', 'created_at']
    list_filter = ['request_type', 'model', 'was_error', 'created_at']
    search_fields = ['tenant__name', 'prompt']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'transaction_type', 'credits', 'amount_paid', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['tenant__name', 'description']
    readonly_fields = ['created_at']


@admin.register(UsageReport)
class UsageReportAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'period_type', 'period_start', 'total_requests', 'total_tokens', 'estimated_cost']
    list_filter = ['period_type', 'period_start']
    search_fields = ['tenant__name']









