from rest_framework import serializers
from .models import (
    MessagingConfig, MessageTemplate, Message,
    InAppNotification, PushToken, MessageChannel
)


class MessagingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingConfig
        fields = [
            'id', 'email_enabled', 'email_provider',
            'sms_enabled', 'sms_provider',
            'push_enabled', 'push_provider',
            'in_app_enabled',
            'default_from_email', 'default_from_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MessagingConfigUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingConfig
        fields = [
            'email_enabled', 'email_provider',
            'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_use_tls',
            'sendgrid_api_key',
            'default_from_email', 'default_from_name',
            'sms_enabled', 'sms_provider',
            'twilio_account_sid', 'twilio_auth_token', 'twilio_phone_number',
            'push_enabled', 'push_provider',
            'firebase_server_key', 'firebase_project_id',
            'in_app_enabled',
        ]
        extra_kwargs = {
            'smtp_password': {'write_only': True},
            'sendgrid_api_key': {'write_only': True},
            'twilio_auth_token': {'write_only': True},
            'firebase_server_key': {'write_only': True},
        }


class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = [
            'id', 'name', 'slug', 'description', 'channel',
            'subject', 'body', 'body_html', 'variables',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id', 'channel', 'recipient', 'recipient_name',
            'subject', 'body', 'status', 'error_message',
            'created_at', 'sent_at', 'delivered_at'
        ]
        read_only_fields = ['id', 'status', 'error_message', 'created_at', 'sent_at', 'delivered_at']


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = [
            'id', 'notification_type', 'title', 'body',
            'action_url', 'action_label', 'data',
            'is_read', 'read_at', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'is_read', 'read_at', 'created_at']


class PushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushToken
        fields = [
            'id', 'user_id', 'device_type', 'device_name',
            'is_active', 'last_used_at', 'created_at'
        ]
        read_only_fields = ['id', 'last_used_at', 'created_at']


# ============= API Request Serializers =============

class SendMessageSerializer(serializers.Serializer):
    """Send a message across channels."""
    recipient = serializers.CharField(max_length=255)
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=MessageChannel.choices),
        min_length=1
    )
    template_slug = serializers.CharField(max_length=100, required=False, allow_blank=True)
    subject = serializers.CharField(max_length=500, required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True)
    body_html = serializers.CharField(required=False, allow_blank=True)
    context = serializers.DictField(required=False, default=dict)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    
    def validate(self, data):
        if not data.get('template_slug') and not data.get('body'):
            raise serializers.ValidationError(
                "Either template_slug or body is required"
            )
        return data


class SendEmailSerializer(serializers.Serializer):
    """Send a single email."""
    to_email = serializers.EmailField()
    subject = serializers.CharField(max_length=500)
    body = serializers.CharField()
    body_html = serializers.CharField(required=False, allow_blank=True)
    from_email = serializers.EmailField(required=False, allow_blank=True)
    from_name = serializers.CharField(max_length=100, required=False, allow_blank=True)


class SendSMSSerializer(serializers.Serializer):
    """Send a single SMS."""
    to_number = serializers.CharField(max_length=20)
    body = serializers.CharField(max_length=1600)
    from_number = serializers.CharField(max_length=20, required=False, allow_blank=True)


class SendPushSerializer(serializers.Serializer):
    """Send a push notification."""
    user_id = serializers.CharField(max_length=255)
    title = serializers.CharField(max_length=200)
    body = serializers.CharField(max_length=1000)
    data = serializers.DictField(required=False, default=dict)


class SendInAppSerializer(serializers.Serializer):
    """Create an in-app notification."""
    user_id = serializers.CharField(max_length=255)
    title = serializers.CharField(max_length=200)
    body = serializers.CharField(max_length=2000)
    notification_type = serializers.ChoiceField(
        choices=InAppNotification.NotificationType.choices,
        default='info'
    )
    action_url = serializers.URLField(required=False, allow_blank=True)
    action_label = serializers.CharField(max_length=100, required=False, allow_blank=True)
    data = serializers.DictField(required=False, default=dict)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class RegisterPushTokenSerializer(serializers.Serializer):
    """Register a push token."""
    user_id = serializers.CharField(max_length=255)
    token = serializers.CharField()
    device_type = serializers.ChoiceField(choices=['web', 'android', 'ios'])
    device_name = serializers.CharField(max_length=200, required=False, allow_blank=True)


# ============= Public API Serializers (for customer's apps) =============

class PublicNotificationListSerializer(serializers.Serializer):
    """Get notifications for a user."""
    unread_only = serializers.BooleanField(default=False)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)


class MarkNotificationReadSerializer(serializers.Serializer):
    """Mark notification as read."""
    notification_id = serializers.UUIDField()


class PublicPushTokenSerializer(serializers.Serializer):
    """Register push token from customer's app."""
    token = serializers.CharField()
    device_type = serializers.ChoiceField(choices=['web', 'android', 'ios'])
    device_name = serializers.CharField(max_length=200, required=False, allow_blank=True)









