from rest_framework import serializers
from .models import ChatWidget, ChatSession, ChatMessage, LLMConfig, LLMProvider


class LLMConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMConfig
        fields = [
            'id', 'use_own_keys', 'default_provider',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LLMConfigUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMConfig
        fields = [
            'use_own_keys', 'default_provider',
            'openai_api_key', 'anthropic_api_key',
            'gemini_api_key', 'grok_api_key'
        ]
        extra_kwargs = {
            'openai_api_key': {'write_only': True},
            'anthropic_api_key': {'write_only': True},
            'gemini_api_key': {'write_only': True},
            'grok_api_key': {'write_only': True},
        }


class ChatWidgetSerializer(serializers.ModelSerializer):
    embed_code = serializers.SerializerMethodField()
    session_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatWidget
        fields = [
            'id', 'name', 'description',
            'theme', 'primary_color', 'position',
            'welcome_message', 'placeholder_text',
            'llm_provider', 'model_name', 'system_prompt',
            'knowledge_base',
            'collect_email', 'show_powered_by', 'enable_file_upload',
            'max_messages_per_session', 'max_sessions_per_day',
            'is_active', 'embed_code', 'session_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'embed_code', 'session_count', 'created_at', 'updated_at']
    
    def get_embed_code(self, obj):
        from .services import WidgetService
        return WidgetService.get_widget_embed_code(obj)
    
    def get_session_count(self, obj):
        return obj.sessions.count()


class ChatWidgetCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatWidget
        fields = [
            'name', 'description',
            'theme', 'primary_color', 'position',
            'welcome_message', 'placeholder_text',
            'llm_provider', 'model_name', 'system_prompt',
            'knowledge_base',
            'collect_email', 'show_powered_by', 'enable_file_upload',
            'max_messages_per_session', 'max_sessions_per_day',
        ]


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'model_used', 'helpful', 'created_at']
        read_only_fields = ['id', 'model_used', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'visitor_id', 'user_email', 'user_name',
            'page_url', 'is_active', 'escalated',
            'messages', 'message_count',
            'started_at', 'last_message_at', 'ended_at'
        ]
        read_only_fields = ['id', 'started_at', 'last_message_at', 'ended_at']


class ChatSessionListSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(read_only=True)
    widget_name = serializers.CharField(source='widget.name', read_only=True)
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'visitor_id', 'user_email', 'user_name',
            'widget_name', 'page_url', 'is_active', 'escalated',
            'message_count', 'started_at', 'last_message_at'
        ]


# Public API serializers (for widget clients)

class PublicWidgetConfigSerializer(serializers.ModelSerializer):
    """Public config for widget clients."""
    class Meta:
        model = ChatWidget
        fields = [
            'id', 'theme', 'primary_color', 'position',
            'welcome_message', 'placeholder_text',
            'collect_email', 'show_powered_by', 'enable_file_upload'
        ]


class StartSessionSerializer(serializers.Serializer):
    """Start a new chat session."""
    visitor_id = serializers.CharField(max_length=100)
    page_url = serializers.URLField(required=False, allow_blank=True)
    user_email = serializers.EmailField(required=False, allow_blank=True)
    user_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    metadata = serializers.DictField(required=False, default=dict)


class SendMessageSerializer(serializers.Serializer):
    """Send a message in a session."""
    session_id = serializers.UUIDField()
    message = serializers.CharField(max_length=4000)


class RateMessageSerializer(serializers.Serializer):
    """Rate a message."""
    message_id = serializers.UUIDField()
    helpful = serializers.BooleanField()


class EscalateSerializer(serializers.Serializer):
    """Escalate session to human support."""
    session_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=500, required=False, default='')









