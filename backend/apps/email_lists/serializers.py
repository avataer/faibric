from rest_framework import serializers
from .models import EmailList, Subscriber, EmailConfig


class EmailConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailConfig
        fields = [
            'id', 'mailchimp_enabled', 'sendgrid_enabled', 'convertkit_enabled',
            'default_from_email', 'default_from_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailConfigUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailConfig
        fields = [
            'mailchimp_enabled', 'mailchimp_api_key', 'mailchimp_server_prefix',
            'sendgrid_enabled', 'sendgrid_api_key',
            'convertkit_enabled', 'convertkit_api_key', 'convertkit_api_secret',
            'default_from_email', 'default_from_name'
        ]
        extra_kwargs = {
            'mailchimp_api_key': {'write_only': True},
            'sendgrid_api_key': {'write_only': True},
            'convertkit_api_key': {'write_only': True},
            'convertkit_api_secret': {'write_only': True},
        }


class EmailListSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailList
        fields = [
            'id', 'name', 'slug', 'description',
            'double_optin', 'welcome_email_enabled',
            'welcome_email_subject', 'welcome_email_body',
            'subscriber_count', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'subscriber_count', 'created_at', 'updated_at']


class EmailListCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailList
        fields = [
            'name', 'slug', 'description',
            'double_optin', 'welcome_email_enabled',
            'welcome_email_subject', 'welcome_email_body',
            'mailchimp_list_id', 'sendgrid_list_id', 'convertkit_form_id'
        ]


class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'custom_fields', 'status', 'source',
            'created_at', 'confirmed_at', 'unsubscribed_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'confirmed_at', 'unsubscribed_at']


class PublicSubscribeSerializer(serializers.Serializer):
    """
    Serializer for public subscription endpoint.
    Used by customer's apps to subscribe users.
    """
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100, required=False, default='')
    last_name = serializers.CharField(max_length=100, required=False, default='')
    list_slug = serializers.CharField(max_length=100)
    source = serializers.CharField(max_length=100, required=False, default='')
    custom_fields = serializers.DictField(required=False, default=dict)


class UnsubscribeSerializer(serializers.Serializer):
    """Serializer for unsubscribe endpoint."""
    token = serializers.CharField()
    reason = serializers.CharField(max_length=500, required=False, default='')


class ConfirmSubscriptionSerializer(serializers.Serializer):
    """Serializer for confirmation endpoint."""
    token = serializers.CharField()

