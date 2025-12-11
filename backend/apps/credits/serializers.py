"""
Serializers for credits API.
"""
from rest_framework import serializers

from .models import (
    SubscriptionTier,
    CreditBalance,
    LLMRequest,
    CreditTransaction,
    UsageReport,
)


class SubscriptionTierSerializer(serializers.ModelSerializer):
    """Serializer for subscription tiers."""
    
    class Meta:
        model = SubscriptionTier
        fields = [
            'id',
            'name',
            'slug',
            'price_monthly',
            'price_yearly',
            'currency',
            'monthly_credits',
            'credit_overage_price',
            'max_projects',
            'max_team_members',
            'max_storage_gb',
            'max_api_calls_daily',
            'features',
            'is_popular',
            'stripe_price_id_monthly',
        ]


class CreditBalanceSerializer(serializers.ModelSerializer):
    """Serializer for credit balance."""
    
    tier_name = serializers.CharField(source='subscription_tier.name', read_only=True)
    total_available = serializers.SerializerMethodField()
    
    class Meta:
        model = CreditBalance
        fields = [
            'id',
            'subscription_tier',
            'tier_name',
            'credits_remaining',
            'credits_used_this_period',
            'tokens_used_this_period',
            'purchased_credits',
            'total_available',
            'period_start',
            'period_end',
            'total_credits_used',
            'total_tokens_generated',
            'total_requests',
        ]
    
    def get_total_available(self, obj):
        return obj.credits_remaining + obj.purchased_credits


class LLMRequestSerializer(serializers.ModelSerializer):
    """Serializer for LLM requests."""
    
    class Meta:
        model = LLMRequest
        fields = [
            'id',
            'request_type',
            'model',
            'prompt',
            'response',
            'input_tokens',
            'output_tokens',
            'total_tokens',
            'credits_charged',
            'response_time_ms',
            'user_rating',
            'was_accepted',
            'was_modified',
            'was_error',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class LLMRequestLogSerializer(serializers.Serializer):
    """Serializer for logging LLM requests."""
    
    request_type = serializers.ChoiceField(
        choices=['generate', 'modify', 'chat', 'analyze', 'explain', 'debug', 'other']
    )
    model = serializers.CharField()
    prompt = serializers.CharField()
    response = serializers.CharField()
    input_tokens = serializers.IntegerField()
    output_tokens = serializers.IntegerField()
    response_time_ms = serializers.IntegerField(required=False)
    project_id = serializers.UUIDField(required=False)
    session_id = serializers.CharField(required=False, allow_blank=True)
    system_prompt = serializers.CharField(required=False, allow_blank=True)
    was_error = serializers.BooleanField(default=False)
    error_message = serializers.CharField(required=False, allow_blank=True)


class RateLLMRequestSerializer(serializers.Serializer):
    """Serializer for rating LLM requests."""
    
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    was_accepted = serializers.BooleanField(required=False)
    was_modified = serializers.BooleanField(required=False)


class CreditTransactionSerializer(serializers.ModelSerializer):
    """Serializer for credit transactions."""
    
    class Meta:
        model = CreditTransaction
        fields = [
            'id',
            'transaction_type',
            'credits',
            'amount_paid',
            'currency',
            'description',
            'balance_after',
            'created_at',
        ]


class PurchaseCreditsSerializer(serializers.Serializer):
    """Serializer for purchasing credits."""
    
    amount = serializers.IntegerField(min_value=10)
    payment_method_id = serializers.CharField(required=False)


class UsageReportSerializer(serializers.ModelSerializer):
    """Serializer for usage reports."""
    
    class Meta:
        model = UsageReport
        fields = [
            'id',
            'period_type',
            'period_start',
            'period_end',
            'total_requests',
            'total_credits_used',
            'total_tokens',
            'total_input_tokens',
            'total_output_tokens',
            'usage_by_model',
            'usage_by_type',
            'estimated_cost',
            'average_rating',
            'acceptance_rate',
            'created_at',
        ]


class UsageSummarySerializer(serializers.Serializer):
    """Serializer for usage summary."""
    
    tier = serializers.CharField()
    credits_remaining = serializers.IntegerField()
    credits_used = serializers.IntegerField()
    purchased_credits = serializers.IntegerField()
    total_available = serializers.IntegerField()
    tokens_used = serializers.IntegerField()
    period_start = serializers.CharField()
    period_end = serializers.CharField()
    total_requests = serializers.IntegerField()






