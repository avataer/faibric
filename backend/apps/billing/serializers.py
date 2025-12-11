from rest_framework import serializers
from .models import BillingProfile, Subscription, Invoice, InvoiceLineItem, UsageRecord, PaymentMethod


class BillingProfileSerializer(serializers.ModelSerializer):
    display_card = serializers.ReadOnlyField()
    
    class Meta:
        model = BillingProfile
        fields = [
            'id', 'billing_name', 'billing_email',
            'billing_address_line1', 'billing_address_line2',
            'billing_city', 'billing_state', 'billing_postal_code', 'billing_country',
            'payment_provider', 'card_last_four', 'card_brand',
            'card_exp_month', 'card_exp_year', 'display_card',
            'has_valid_payment_method', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'card_last_four', 'card_brand', 'card_exp_month', 'card_exp_year',
            'display_card', 'has_valid_payment_method', 'created_at', 'updated_at'
        ]


class BillingProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating billing info (entered once by customer)."""
    
    class Meta:
        model = BillingProfile
        fields = [
            'billing_name', 'billing_email',
            'billing_address_line1', 'billing_address_line2',
            'billing_city', 'billing_state', 'billing_postal_code', 'billing_country',
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'status', 'monthly_price',
            'max_apps', 'max_ai_tokens_per_month', 'max_storage_gb',
            'trial_ends_at', 'current_period_start', 'current_period_end',
            'is_active', 'created_at', 'canceled_at'
        ]
        read_only_fields = [
            'id', 'status', 'monthly_price', 'max_apps', 
            'max_ai_tokens_per_month', 'max_storage_gb',
            'trial_ends_at', 'current_period_start', 'current_period_end',
            'is_active', 'created_at', 'canceled_at'
        ]


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'amount', 'charge_type']


class InvoiceSerializer(serializers.ModelSerializer):
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'status', 'subtotal', 'tax', 'total',
            'amount_paid', 'amount_due', 'currency',
            'period_start', 'period_end', 'due_date',
            'pdf_url', 'created_at', 'paid_at', 'line_items'
        ]


class UsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageRecord
        fields = [
            'id', 'usage_type', 'quantity', 'description',
            'period_start', 'period_end', 'total_price',
            'invoiced', 'created_at'
        ]


class UsageSummarySerializer(serializers.Serializer):
    """Summary of current month's usage."""
    ai_tokens = serializers.DictField(required=False)
    storage_bytes = serializers.DictField(required=False)
    bandwidth_bytes = serializers.DictField(required=False)
    api_calls = serializers.DictField(required=False)


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'provider', 'card_brand', 'card_last_four',
            'card_exp_month', 'card_exp_year', 'is_default', 'created_at'
        ]


class SetupIntentSerializer(serializers.Serializer):
    """Response for payment method setup."""
    client_secret = serializers.CharField()
    setup_intent_id = serializers.CharField()


class AttachPaymentMethodSerializer(serializers.Serializer):
    """Request to attach a payment method."""
    payment_method_id = serializers.CharField()


class ChangePlanSerializer(serializers.Serializer):
    """Request to change subscription plan."""
    plan = serializers.ChoiceField(choices=['free', 'starter', 'pro', 'enterprise'])

