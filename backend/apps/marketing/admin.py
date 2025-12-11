"""
Django admin configuration for marketing analysis.
"""
from django.contrib import admin

from .models import (
    Competitor,
    CompetitorChange,
    CompetitorSnapshot,
    Keyword,
    KeywordRanking,
    MarketingConfig,
    MarketingReport,
    ReportTemplate,
)


@admin.register(MarketingConfig)
class MarketingConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'report_frequency', 'report_enabled', 'last_report_at', 'next_report_at']
    list_filter = ['report_frequency', 'report_enabled']
    search_fields = ['tenant__name', 'report_email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'tenant', 'is_active', 'last_scraped_at']
    list_filter = ['is_active', 'track_homepage', 'track_blog', 'track_pricing', 'track_features']
    search_fields = ['name', 'domain', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at', 'last_scraped_at']
    
    fieldsets = [
        (None, {
            'fields': ['tenant', 'name', 'domain', 'website_url']
        }),
        ('Tracking Settings', {
            'fields': ['track_homepage', 'track_blog', 'track_pricing', 'track_features', 'custom_pages']
        }),
        ('Status', {
            'fields': ['is_active', 'last_scraped_at', 'notes']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(CompetitorSnapshot)
class CompetitorSnapshotAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'page_type', 'title', 'http_status', 'created_at']
    list_filter = ['page_type', 'http_status', 'created_at']
    search_fields = ['competitor__name', 'title', 'page_url']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(CompetitorChange)
class CompetitorChangeAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'change_type', 'title', 'importance_score', 'is_reviewed', 'created_at']
    list_filter = ['change_type', 'is_reviewed', 'importance_score', 'created_at']
    search_fields = ['competitor__name', 'title', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_reviewed']
    
    def mark_as_reviewed(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_reviewed=True, reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f'{queryset.count()} changes marked as reviewed.')
    mark_as_reviewed.short_description = 'Mark selected changes as reviewed'


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'your_domain', 'tenant', 'is_active', 'last_checked_at']
    list_filter = ['is_active', 'track_competitors']
    search_fields = ['keyword', 'your_domain', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at', 'last_checked_at']


@admin.register(KeywordRanking)
class KeywordRankingAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'domain', 'position', 'position_change', 'created_at']
    list_filter = ['search_engine', 'created_at']
    search_fields = ['keyword__keyword', 'domain']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(MarketingReport)
class MarketingReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'tenant', 'report_type', 'status', 'period_start', 'period_end', 'sent_at']
    list_filter = ['report_type', 'status', 'created_at']
    search_fields = ['title', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_default', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']






