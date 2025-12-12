from rest_framework import serializers
from .models import (
    CabinetConfig, EndUser, SupportTicket,
    TicketMessage, Notification, Activity
)


class CabinetConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = CabinetConfig
        fields = [
            'id', 'cabinet_name', 'logo_url', 'primary_color',
            'orders_enabled', 'subscriptions_enabled', 'files_enabled',
            'support_enabled', 'notifications_enabled',
            'allow_registration', 'require_email_verification',
            'is_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EndUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = EndUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'display_name',
            'full_name', 'avatar_url', 'phone',
            'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country',
            'timezone', 'language', 'preferences',
            'is_verified', 'created_at', 'last_login_at'
        ]
        read_only_fields = ['id', 'email', 'is_verified', 'created_at', 'last_login_at']


class EndUserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EndUser
        fields = [
            'first_name', 'last_name', 'display_name', 'avatar_url', 'phone',
            'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'timezone', 'language', 'preferences'
        ]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=100, required=False, default='')
    last_name = serializers.CharField(max_length=100, required=False, default='')


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)


class TicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketMessage
        fields = [
            'id', 'is_staff_reply', 'sender_name',
            'content', 'attachments', 'created_at'
        ]


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_number', 'subject', 'category',
            'status', 'priority', 'related_order_id',
            'messages', 'created_at', 'updated_at', 'resolved_at'
        ]
        read_only_fields = [
            'id', 'ticket_number', 'status',
            'created_at', 'updated_at', 'resolved_at'
        ]


class SupportTicketListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_number', 'subject', 'category',
            'status', 'priority', 'created_at', 'updated_at'
        ]


class CreateTicketSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()
    category = serializers.CharField(max_length=50, required=False, default='')
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        default='medium'
    )
    related_order_id = serializers.CharField(max_length=100, required=False, default='')


class ReplyToTicketSerializer(serializers.Serializer):
    message = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'action_url', 'action_text', 'metadata',
            'is_read', 'read_at', 'created_at'
        ]


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            'id', 'activity_type', 'title', 'description',
            'entity_type', 'entity_id', 'icon',
            'metadata', 'created_at'
        ]


class DashboardSerializer(serializers.Serializer):
    user = EndUserSerializer()
    stats = serializers.DictField()









