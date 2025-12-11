from django.contrib import admin
from .models import ChatWidget, ChatSession, ChatMessage, LLMConfig


@admin.register(LLMConfig)
class LLMConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'use_own_keys', 'default_provider', 'updated_at']
    list_filter = ['use_own_keys', 'default_provider']


@admin.register(ChatWidget)
class ChatWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'llm_provider', 'is_active', 'created_at']
    list_filter = ['is_active', 'llm_provider', 'theme']
    search_fields = ['name', 'tenant__name']


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['id', 'role', 'content', 'model_used', 'tokens_used', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'widget', 'visitor_id', 'user_email', 'is_active', 'escalated', 'started_at']
    list_filter = ['is_active', 'escalated', 'started_at']
    search_fields = ['visitor_id', 'user_email']
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'content_preview', 'model_used', 'helpful', 'created_at']
    list_filter = ['role', 'helpful', 'created_at']
    search_fields = ['content']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'







