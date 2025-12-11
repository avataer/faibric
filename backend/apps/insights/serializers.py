"""
Serializers for Customer Insights API.
"""
from rest_framework import serializers

from .models import (
    CustomerInput,
    QualityReview,
    AdminFix,
    CustomerPattern,
    InsightReport,
    CustomerHealth,
)


class CustomerInputSerializer(serializers.ModelSerializer):
    """Serializer for customer inputs."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    needs_attention = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CustomerInput
        fields = [
            'id',
            'tenant',
            'tenant_name',
            'user',
            'user_email',
            'input_type',
            'user_input',
            'context',
            'llm_response',
            'model_used',
            'tokens_input',
            'tokens_output',
            'response_time_ms',
            'project',
            'project_name',
            'quality_status',
            'was_error',
            'response_too_short',
            'user_rating',
            'user_accepted',
            'user_feedback',
            'needs_attention',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CustomerInputListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for input lists."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    needs_attention = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CustomerInput
        fields = [
            'id',
            'user_email',
            'input_type',
            'user_input',
            'quality_status',
            'user_rating',
            'was_error',
            'needs_attention',
            'created_at',
        ]


class LogInputSerializer(serializers.Serializer):
    """Serializer for logging a new input."""
    
    input_type = serializers.ChoiceField(
        choices=['code_generation', 'code_modification', 'code_fix', 
                 'code_explanation', 'chat', 'project_creation', 
                 'feature_request', 'other']
    )
    user_input = serializers.CharField()
    llm_response = serializers.CharField()
    model_used = serializers.CharField()
    context = serializers.CharField(required=False, allow_blank=True)
    tokens_input = serializers.IntegerField(default=0)
    tokens_output = serializers.IntegerField(default=0)
    response_time_ms = serializers.IntegerField(required=False)
    project_id = serializers.UUIDField(required=False)
    session_id = serializers.CharField(required=False, allow_blank=True)
    was_error = serializers.BooleanField(default=False)


class RecordFeedbackSerializer(serializers.Serializer):
    """Serializer for recording feedback."""
    
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    accepted = serializers.BooleanField(required=False)
    feedback = serializers.CharField(required=False, allow_blank=True)


class QualityReviewSerializer(serializers.ModelSerializer):
    """Serializer for quality reviews."""
    
    reviewer_email = serializers.EmailField(source='reviewer.email', read_only=True)
    
    class Meta:
        model = QualityReview
        fields = [
            'id',
            'customer_input',
            'reviewer',
            'reviewer_email',
            'outcome',
            'admin_notes',
            'quality_score',
            'issue_category',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CreateReviewSerializer(serializers.Serializer):
    """Serializer for creating a review."""
    
    outcome = serializers.ChoiceField(
        choices=['approved', 'needs_fix', 'fixed', 'wont_fix', 'learning']
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    quality_score = serializers.IntegerField(min_value=1, max_value=10, required=False)
    issue_category = serializers.ChoiceField(
        choices=['incorrect_code', 'incomplete', 'wrong_language', 'poor_quality',
                 'misunderstood', 'hallucination', 'outdated', 'security', 'other'],
        required=False
    )


class AdminFixSerializer(serializers.ModelSerializer):
    """Serializer for admin fixes."""
    
    admin_email = serializers.EmailField(source='admin.email', read_only=True)
    user_email = serializers.EmailField(source='customer_input.user.email', read_only=True)
    
    class Meta:
        model = AdminFix
        fields = [
            'id',
            'customer_input',
            'admin',
            'admin_email',
            'user_email',
            'improved_response',
            'fix_notes',
            'fix_method',
            'improved_prompt',
            'customer_notified',
            'notification_sent_at',
            'customer_viewed',
            'customer_accepted_fix',
            'customer_feedback',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'customer_notified', 'notification_sent_at']


class CreateManualFixSerializer(serializers.Serializer):
    """Serializer for creating a manual fix."""
    
    improved_response = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)


class CreateRegenerateFixSerializer(serializers.Serializer):
    """Serializer for creating a regenerated fix."""
    
    improved_prompt = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class CustomerHealthSerializer(serializers.ModelSerializer):
    """Serializer for customer health."""
    
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = CustomerHealth
        fields = [
            'id',
            'tenant',
            'tenant_name',
            'health_score',
            'satisfaction_score',
            'engagement_score',
            'success_rate',
            'is_at_risk',
            'risk_reasons',
            'last_activity_at',
            'total_inputs',
            'total_accepted',
            'total_rejected',
            'average_rating',
            'unresolved_issues',
            'updated_at',
        ]


class InsightReportSerializer(serializers.ModelSerializer):
    """Serializer for insight reports."""
    
    class Meta:
        model = InsightReport
        fields = [
            'id',
            'report_type',
            'period_start',
            'period_end',
            'total_inputs',
            'total_users',
            'total_tenants',
            'average_rating',
            'acceptance_rate',
            'error_rate',
            'needs_review_count',
            'fixed_count',
            'by_input_type',
            'by_quality_status',
            'by_model',
            'top_issues',
            'customers_needing_attention',
            'created_at',
        ]


class DashboardSerializer(serializers.Serializer):
    """Serializer for dashboard data."""
    
    summary = serializers.DictField()
    at_risk_customers = serializers.ListField()
    recent_fixes = serializers.ListField()
    trends = serializers.DictField()






