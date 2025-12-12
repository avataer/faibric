from django.contrib import admin
from .models import (
    CabinetConfig, EndUser, EndUserSession,
    EmailVerification, PasswordReset,
    SupportTicket, TicketMessage, Notification, Activity
)


@admin.register(CabinetConfig)
class CabinetConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'cabinet_name', 'is_enabled']
    list_filter = ['is_enabled']


@admin.register(EndUser)
class EndUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'tenant', 'full_name', 'is_active', 'is_verified', 'created_at']
    list_filter = ['is_active', 'is_verified', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['password_hash', 'created_at', 'last_login_at']


@admin.register(EndUserSession)
class EndUserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_active', 'expires_at', 'created_at']
    list_filter = ['is_active']
    readonly_fields = ['token']


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ['created_at']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'tenant', 'user', 'subject', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['ticket_number', 'subject', 'user__email']
    inlines = [TicketMessageInline]
    readonly_fields = ['ticket_number']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['title', 'message', 'user__email']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'title', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['title', 'description', 'user__email']









