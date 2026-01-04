"""
Admin configuration for Project Services.
"""
from django.contrib import admin
from .models import (
    ProjectDatabase, ProjectAuth, ProjectDomain,
    ProjectPayments, ProjectStorage, ProjectVersion,
    ProjectAnalytics, AnalyticsEvent
)


@admin.register(ProjectDatabase)
class ProjectDatabaseAdmin(admin.ModelAdmin):
    list_display = ['project', 'status', 'supabase_url', 'created_at']
    list_filter = ['status']
    search_fields = ['project__name']
    readonly_fields = ['supabase_service_key']  # Hide sensitive key


@admin.register(ProjectAuth)
class ProjectAuthAdmin(admin.ModelAdmin):
    list_display = ['project', 'status', 'email_password', 'google_oauth', 'github_oauth']
    list_filter = ['status', 'email_password', 'google_oauth']
    search_fields = ['project__name']


@admin.register(ProjectDomain)
class ProjectDomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'project', 'is_verified', 'ssl_status', 'is_primary']
    list_filter = ['is_verified', 'ssl_status']
    search_fields = ['domain', 'project__name']


@admin.register(ProjectPayments)
class ProjectPaymentsAdmin(admin.ModelAdmin):
    list_display = ['project', 'stripe_account_status', 'stripe_account_id']
    list_filter = ['stripe_account_status']
    search_fields = ['project__name', 'stripe_account_id']


@admin.register(ProjectStorage)
class ProjectStorageAdmin(admin.ModelAdmin):
    list_display = ['project', 'provider', 'status', 'storage_used_bytes', 'storage_limit_bytes']
    list_filter = ['provider', 'status']
    search_fields = ['project__name']


@admin.register(ProjectVersion)
class ProjectVersionAdmin(admin.ModelAdmin):
    list_display = ['project', 'version_number', 'is_deployed', 'change_description', 'created_at']
    list_filter = ['is_deployed']
    search_fields = ['project__name', 'change_description']
    ordering = ['-created_at']


@admin.register(ProjectAnalytics)
class ProjectAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['project', 'is_enabled', 'total_pageviews', 'total_visitors', 'updated_at']
    list_filter = ['is_enabled']
    search_fields = ['project__name']


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ['project', 'event_type', 'path', 'visitor_id', 'created_at']
    list_filter = ['event_type']
    search_fields = ['path', 'visitor_id']
    date_hierarchy = 'created_at'



