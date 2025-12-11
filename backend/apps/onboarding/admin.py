"""
Django admin for Onboarding.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import LandingSession, SessionEvent, DailyReport, AdminNotification


class SessionEventInline(admin.TabularInline):
    model = SessionEvent
    extra = 0
    readonly_fields = ['event_type', 'event_data', 'old_email', 'new_email', 'error_message', 'timestamp']
    ordering = ['timestamp']


@admin.register(LandingSession)
class LandingSessionAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'status', 'initial_request_preview', 'email_changes_display',
        'utm_source', 'utm_campaign', 'is_converted_display', 'created_at'
    ]
    list_filter = ['status', 'email_verified', 'utm_source', 'device_type', 'created_at']
    search_fields = ['email', 'initial_request', 'session_token']
    readonly_fields = [
        'session_token', 'magic_token', 'magic_token_expires_at',
        'created_at', 'updated_at', 'completed_at'
    ]
    date_hierarchy = 'created_at'
    inlines = [SessionEventInline]
    
    fieldsets = [
        (None, {
            'fields': ['session_token', 'status', 'initial_request']
        }),
        ('Email', {
            'fields': ['email', 'email_verified', 'email_change_count', 'previous_emails']
        }),
        ('Magic Link', {
            'fields': ['magic_token', 'magic_token_expires_at', 'magic_link_sent_at', 'magic_link_clicked_at'],
            'classes': ['collapse']
        }),
        ('Conversion', {
            'fields': ['converted_to_user', 'converted_to_tenant', 'converted_to_project']
        }),
        ('Attribution', {
            'fields': ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'referrer']
        }),
        ('Device', {
            'fields': ['ip_address', 'device_type', 'browser', 'os'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at', 'completed_at']
        }),
    ]
    
    def initial_request_preview(self, obj):
        return obj.initial_request[:50] + '...' if len(obj.initial_request) > 50 else obj.initial_request
    initial_request_preview.short_description = 'Request'
    
    def email_changes_display(self, obj):
        if obj.email_change_count > 0:
            return format_html(
                '<span style="color: orange;">⚠️ {}</span>',
                obj.email_change_count
            )
        return '0'
    email_changes_display.short_description = 'Email Changes'
    
    def is_converted_display(self, obj):
        if obj.is_converted:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: gray;">No</span>')
    is_converted_display.short_description = 'Converted'


@admin.register(SessionEvent)
class SessionEventAdmin(admin.ModelAdmin):
    list_display = ['session', 'event_type', 'timestamp']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['session__email']
    readonly_fields = ['timestamp']


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_visitors', 'emails_collected', 'accounts_created',
        'overall_conversion_display', 'ad_spend', 'report_sent'
    ]
    list_filter = ['report_sent', 'date']
    date_hierarchy = 'date'
    readonly_fields = ['created_at']
    
    fieldsets = [
        ('Period', {
            'fields': ['date']
        }),
        ('Conversion Funnel', {
            'fields': [
                'total_visitors', 'total_requests', 'emails_collected',
                'email_changes', 'magic_links_sent', 'magic_links_clicked',
                'accounts_created', 'projects_created'
            ]
        }),
        ('Conversion Rates', {
            'fields': [
                'request_to_email_rate', 'email_to_click_rate',
                'click_to_account_rate', 'overall_conversion_rate'
            ]
        }),
        ('Usage Metrics', {
            'fields': [
                'total_llm_requests', 'total_tokens_used', 'average_rating',
                'issues_flagged', 'issues_fixed', 'at_risk_customers', 'healthy_customers'
            ]
        }),
        ('Google Ads', {
            'fields': [
                'ad_impressions', 'ad_clicks', 'ad_spend', 'ad_conversions',
                'ad_ctr', 'ad_cpc', 'ad_cpa'
            ]
        }),
        ('Attribution', {
            'fields': ['conversions_by_source', 'conversions_by_campaign'],
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ['report_sent', 'report_sent_at', 'created_at']
        }),
    ]
    
    def overall_conversion_display(self, obj):
        if obj.overall_conversion_rate:
            pct = obj.overall_conversion_rate * 100
            color = 'green' if pct > 5 else ('orange' if pct > 2 else 'red')
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, pct
            )
        return '-'
    overall_conversion_display.short_description = 'Conversion %'
    
    actions = ['generate_report', 'send_report_email']
    
    def generate_report(self, request, queryset):
        from .services import DailyReportService
        for report in queryset:
            DailyReportService.generate_report(report.date)
        self.message_user(request, f"Regenerated {queryset.count()} reports")
    
    def send_report_email(self, request, queryset):
        from .services import DailyReportService
        sent = 0
        for report in queryset:
            if DailyReportService.send_daily_report_email(report):
                sent += 1
        self.message_user(request, f"Sent {sent} report emails")


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'is_read', 'email_sent', 'created_at']
    list_filter = ['notification_type', 'is_read', 'email_sent', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at']
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)







