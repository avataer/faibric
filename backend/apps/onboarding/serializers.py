"""
Serializers for Onboarding API.
"""
from rest_framework import serializers

from .models import LandingSession, SessionEvent, DailyReport, AdminNotification


class SubmitRequestSerializer(serializers.Serializer):
    """Serializer for initial request submission."""
    
    request = serializers.CharField(max_length=5000)
    utm_source = serializers.CharField(required=False, allow_blank=True)
    utm_medium = serializers.CharField(required=False, allow_blank=True)
    utm_campaign = serializers.CharField(required=False, allow_blank=True)
    utm_content = serializers.CharField(required=False, allow_blank=True)
    utm_term = serializers.CharField(required=False, allow_blank=True)
    referrer = serializers.URLField(required=False, allow_blank=True)
    landing_page = serializers.URLField(required=False, allow_blank=True)


class ProvideEmailSerializer(serializers.Serializer):
    """Serializer for email submission."""
    
    session_token = serializers.CharField()
    email = serializers.EmailField()


class VerifyTokenSerializer(serializers.Serializer):
    """Serializer for magic link verification."""
    
    token = serializers.CharField()


class SessionEventSerializer(serializers.ModelSerializer):
    """Serializer for session events."""
    
    class Meta:
        model = SessionEvent
        fields = [
            'id',
            'event_type',
            'event_data',
            'old_email',
            'new_email',
            'error_message',
            'timestamp',
        ]


class LandingSessionSerializer(serializers.ModelSerializer):
    """Serializer for landing sessions."""
    
    events = SessionEventSerializer(many=True, read_only=True)
    is_converted = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = LandingSession
        fields = [
            'id',
            'session_token',
            'initial_request',
            'status',
            'email',
            'email_verified',
            'email_change_count',
            'previous_emails',
            'utm_source',
            'utm_medium',
            'utm_campaign',
            'is_converted',
            'device_type',
            'browser',
            'events',
            'created_at',
            'completed_at',
        ]


class LandingSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for session lists."""
    
    is_converted = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = LandingSession
        fields = [
            'id',
            'email',
            'status',
            'initial_request',
            'email_change_count',
            'utm_source',
            'utm_campaign',
            'is_converted',
            'created_at',
        ]


class DailyReportSerializer(serializers.ModelSerializer):
    """Serializer for daily reports."""
    
    class Meta:
        model = DailyReport
        fields = [
            'id',
            'date',
            'total_visitors',
            'total_requests',
            'emails_collected',
            'email_changes',
            'magic_links_sent',
            'magic_links_clicked',
            'accounts_created',
            'projects_created',
            'request_to_email_rate',
            'email_to_click_rate',
            'click_to_account_rate',
            'overall_conversion_rate',
            'total_llm_requests',
            'total_tokens_used',
            'average_rating',
            'issues_flagged',
            'issues_fixed',
            'at_risk_customers',
            'healthy_customers',
            'ad_impressions',
            'ad_clicks',
            'ad_spend',
            'ad_conversions',
            'ad_ctr',
            'ad_cpc',
            'ad_cpa',
            'conversions_by_source',
            'conversions_by_campaign',
            'top_requests',
            'report_sent',
            'created_at',
        ]


class DailyReportDetailSerializer(DailyReportSerializer):
    """Detailed serializer including all sessions."""
    
    class Meta(DailyReportSerializer.Meta):
        fields = DailyReportSerializer.Meta.fields + ['all_sessions']


class AdminNotificationSerializer(serializers.ModelSerializer):
    """Serializer for admin notifications."""
    
    class Meta:
        model = AdminNotification
        fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'data',
            'is_read',
            'email_sent',
            'created_at',
        ]






