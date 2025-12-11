from django.contrib import admin
from .models import EmailList, Subscriber, EmailConfig


@admin.register(EmailConfig)
class EmailConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'mailchimp_enabled', 'sendgrid_enabled', 'convertkit_enabled']
    list_filter = ['mailchimp_enabled', 'sendgrid_enabled', 'convertkit_enabled']


@admin.register(EmailList)
class EmailListAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'subscriber_count', 'double_optin', 'is_active']
    list_filter = ['is_active', 'double_optin']
    search_fields = ['name', 'tenant__name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'email_list', 'status', 'source', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['unsubscribe_token', 'confirmation_token']

