from django.contrib import admin
from .models import BillingProfile, Subscription, Invoice, InvoiceLineItem, UsageRecord, PaymentMethod


@admin.register(BillingProfile)
class BillingProfileAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'billing_email', 'payment_provider', 'card_brand', 'card_last_four', 'has_valid_payment_method']
    list_filter = ['payment_provider', 'has_valid_payment_method']
    search_fields = ['tenant__name', 'billing_email', 'billing_name']
    readonly_fields = ['id', 'stripe_customer_id', 'paypal_customer_id', 'created_at', 'updated_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'plan', 'status', 'monthly_price', 'max_apps', 'current_period_end']
    list_filter = ['plan', 'status']
    search_fields = ['tenant__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    readonly_fields = ['id']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['number', 'tenant', 'status', 'total', 'amount_due', 'due_date', 'paid_at']
    list_filter = ['status', 'created_at']
    search_fields = ['number', 'tenant__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [InvoiceLineItemInline]


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'usage_type', 'quantity', 'total_price', 'invoiced', 'created_at']
    list_filter = ['usage_type', 'invoiced', 'created_at']
    search_fields = ['tenant__name', 'description']
    readonly_fields = ['id', 'created_at']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['billing_profile', 'provider', 'card_brand', 'card_last_four', 'is_default']
    list_filter = ['provider', 'is_default']
    readonly_fields = ['id', 'created_at']

