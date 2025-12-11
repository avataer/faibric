"""
Django admin for Customer Insights.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CustomerInput,
    QualityReview,
    AdminFix,
    CustomerPattern,
    InsightReport,
    CustomerHealth,
)


@admin.register(CustomerInput)
class CustomerInputAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'tenant', 'input_type', 'quality_status', 
        'user_rating', 'was_error', 'needs_attention_display', 'created_at'
    ]
    list_filter = ['input_type', 'quality_status', 'was_error', 'created_at', 'model_used']
    search_fields = ['user__email', 'tenant__name', 'user_input']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = [
        (None, {
            'fields': ['tenant', 'user', 'input_type', 'project']
        }),
        ('Input & Response', {
            'fields': ['user_input', 'context', 'llm_response'],
            'classes': ['wide']
        }),
        ('Model Info', {
            'fields': ['model_used', 'tokens_input', 'tokens_output', 'response_time_ms']
        }),
        ('Quality', {
            'fields': ['quality_status', 'was_error', 'response_too_short', 
                      'user_rating', 'user_accepted', 'user_feedback']
        }),
        ('Tracking', {
            'fields': ['session_id', 'ip_address', 'user_agent'],
            'classes': ['collapse']
        }),
    ]
    
    def needs_attention_display(self, obj):
        if obj.needs_attention:
            return format_html('<span style="color: red;">⚠️ Yes</span>')
        return format_html('<span style="color: green;">✓ No</span>')
    needs_attention_display.short_description = 'Needs Attention'
    
    actions = ['mark_needs_review', 'mark_good']
    
    def mark_needs_review(self, request, queryset):
        queryset.update(quality_status='needs_review')
    mark_needs_review.short_description = "Mark as Needs Review"
    
    def mark_good(self, request, queryset):
        queryset.update(quality_status='good')
    mark_good.short_description = "Mark as Good Quality"


@admin.register(QualityReview)
class QualityReviewAdmin(admin.ModelAdmin):
    list_display = ['customer_input', 'reviewer', 'outcome', 'issue_category', 'quality_score', 'created_at']
    list_filter = ['outcome', 'issue_category', 'created_at']
    search_fields = ['admin_notes', 'customer_input__user__email']
    readonly_fields = ['created_at']


@admin.register(AdminFix)
class AdminFixAdmin(admin.ModelAdmin):
    list_display = [
        'customer_input', 'admin', 'fix_method', 
        'customer_notified', 'customer_viewed', 'customer_accepted_fix', 'created_at'
    ]
    list_filter = ['fix_method', 'customer_notified', 'customer_viewed', 'customer_accepted_fix']
    search_fields = ['fix_notes', 'customer_input__user__email']
    readonly_fields = ['created_at', 'updated_at', 'notification_sent_at', 'customer_viewed_at']
    
    actions = ['send_notifications']
    
    def send_notifications(self, request, queryset):
        from .services import AdminFixService
        sent = 0
        for fix in queryset.filter(customer_notified=False):
            if AdminFixService.notify_customer(str(fix.id)):
                sent += 1
        self.message_user(request, f"Sent {sent} notifications")
    send_notifications.short_description = "Send customer notifications"


@admin.register(CustomerPattern)
class CustomerPatternAdmin(admin.ModelAdmin):
    list_display = ['name', 'pattern_type', 'occurrence_count', 'impact_level', 'is_resolved']
    list_filter = ['pattern_type', 'impact_level', 'is_resolved']
    search_fields = ['name', 'description']


@admin.register(InsightReport)
class InsightReportAdmin(admin.ModelAdmin):
    list_display = [
        'report_type', 'period_start', 'total_inputs', 'total_users',
        'average_rating', 'acceptance_rate', 'error_rate', 'fixed_count'
    ]
    list_filter = ['report_type', 'period_start']
    date_hierarchy = 'period_start'


@admin.register(CustomerHealth)
class CustomerHealthAdmin(admin.ModelAdmin):
    list_display = [
        'tenant', 'health_score', 'satisfaction_score', 
        'is_at_risk', 'unresolved_issues', 'last_activity_at'
    ]
    list_filter = ['is_at_risk', 'health_score']
    search_fields = ['tenant__name']
    readonly_fields = ['updated_at']
    
    def health_score_display(self, obj):
        color = 'green' if obj.health_score >= 70 else ('orange' if obj.health_score >= 40 else 'red')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.health_score
        )
    health_score_display.short_description = 'Health Score'







