"""
Django admin for Platform Admin models.
"""
from django.contrib import admin

from .models import (
    PlatformMetrics,
    FunnelStep,
    FunnelEvent,
    FunnelConversion,
    AdCampaign,
    AdCampaignDaily,
    SystemHealth,
)


@admin.register(PlatformMetrics)
class PlatformMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_users', 'new_users', 'active_users', 'mrr', 'total_llm_requests']
    list_filter = ['date']
    date_hierarchy = 'date'


@admin.register(FunnelStep)
class FunnelStepAdmin(admin.ModelAdmin):
    list_display = ['funnel_name', 'step_order', 'step_name', 'event_name', 'is_active']
    list_filter = ['funnel_name', 'is_active']
    ordering = ['funnel_name', 'step_order']


@admin.register(FunnelEvent)
class FunnelEventAdmin(admin.ModelAdmin):
    list_display = ['funnel_step', 'user', 'utm_source', 'utm_campaign', 'timestamp']
    list_filter = ['funnel_step__funnel_name', 'utm_source', 'timestamp']
    date_hierarchy = 'timestamp'


@admin.register(FunnelConversion)
class FunnelConversionAdmin(admin.ModelAdmin):
    list_display = ['funnel_name', 'date', 'total_started', 'total_completed', 'overall_conversion_rate']
    list_filter = ['funnel_name']
    date_hierarchy = 'date'


@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'platform', 'status', 'daily_budget', 'total_spend', 'total_clicks']
    list_filter = ['platform', 'status']
    search_fields = ['name']


@admin.register(AdCampaignDaily)
class AdCampaignDailyAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'date', 'impressions', 'clicks', 'spend', 'conversions']
    list_filter = ['campaign']
    date_hierarchy = 'date'


@admin.register(SystemHealth)
class SystemHealthAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'overall_status', 'api_requests_1h', 'api_errors_1h', 'llm_requests_1h']
    list_filter = ['overall_status']







