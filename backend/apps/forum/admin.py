from django.contrib import admin
from .models import (
    ForumConfig, Category, Board, Thread, Post,
    PostReaction, Report, UserBan
)


@admin.register(ForumConfig)
class ForumConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'forum_name', 'is_enabled', 'updated_at']
    list_filter = ['is_enabled']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'order', 'is_active']
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'tenant', 'thread_count', 'post_count', 'is_active']
    list_filter = ['is_active', 'is_private']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ['title', 'board', 'author_name', 'reply_count', 'is_pinned', 'is_locked', 'created_at']
    list_filter = ['is_pinned', 'is_locked', 'is_deleted', 'created_at']
    search_fields = ['title', 'author_name']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['content_preview', 'thread', 'author_name', 'upvotes', 'downvotes', 'created_at']
    list_filter = ['is_deleted', 'is_hidden', 'created_at']
    search_fields = ['content', 'author_name']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['reason', 'reporter_name', 'status', 'created_at']
    list_filter = ['reason', 'status', 'created_at']


@admin.register(UserBan)
class UserBanAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'tenant', 'reason', 'is_permanent', 'is_active', 'created_at']
    list_filter = ['is_permanent', 'is_active']
    search_fields = ['user_name', 'user_id']






