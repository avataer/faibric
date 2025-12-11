from django.contrib import admin
from .models import AnalyticsConfig, Event, Funnel, FunnelStep, FunnelConversion, UserProfile


@admin.register(AnalyticsConfig)
class AnalyticsConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'mixpanel_enabled', 'ga_enabled', 'webhook_enabled']
    list_filter = ['mixpanel_enabled', 'ga_enabled', 'webhook_enabled']
    search_fields = ['tenant__name']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'distinct_id', 'tenant', 'timestamp', 'source']
    list_filter = ['event_name', 'source', 'timestamp']
    search_fields = ['event_name', 'distinct_id', 'tenant__name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'timestamp'


class FunnelStepInline(admin.TabularInline):
    model = FunnelStep
    extra = 1
    ordering = ['order']


@admin.register(Funnel)
class FunnelAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'is_active', 'template_name', 'created_at']
    list_filter = ['is_active', 'is_template']
    search_fields = ['name', 'tenant__name']
    inlines = [FunnelStepInline]


@admin.register(FunnelConversion)
class FunnelConversionAdmin(admin.ModelAdmin):
    list_display = ['funnel', 'distinct_id', 'current_step', 'is_completed', 'started_at']
    list_filter = ['is_completed', 'started_at']
    search_fields = ['funnel__name', 'distinct_id']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['distinct_id', 'tenant', 'total_events', 'first_seen', 'last_seen']
    list_filter = ['first_seen', 'last_seen']
    search_fields = ['distinct_id', 'tenant__name']

