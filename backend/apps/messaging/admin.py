from django.contrib import admin
from .models import (
    MessagingConfig, MessageTemplate, Message,
    InAppNotification, PushToken
)


@admin.register(MessagingConfig)
class MessagingConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled']
    list_filter = ['email_enabled', 'sms_enabled', 'push_enabled']


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'channel', 'is_active', 'created_at']
    list_filter = ['channel', 'is_active']
    search_fields = ['name', 'slug', 'tenant__name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'channel', 'subject_preview', 'status', 'created_at', 'sent_at']
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['recipient', 'subject']
    readonly_fields = ['provider_message_id', 'provider_response', 'created_at', 'sent_at']
    
    def subject_preview(self, obj):
        if obj.subject:
            return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
        return '-'
    subject_preview.short_description = 'Subject'


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user_id', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'user_id', 'tenant__name']


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'device_type', 'is_active', 'last_used_at']
    list_filter = ['device_type', 'is_active']
    search_fields = ['user_id', 'tenant__name']






