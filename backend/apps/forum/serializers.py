from rest_framework import serializers
from .models import (
    ForumConfig, Category, Board, Thread, Post,
    PostReaction, Report, UserBan
)


class ForumConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForumConfig
        fields = [
            'id', 'forum_name', 'forum_description',
            'allow_anonymous_viewing', 'require_approval_for_posts',
            'allow_attachments', 'max_attachment_size_mb',
            'enable_profanity_filter', 'auto_close_threads_days',
            'posts_per_day_limit', 'threads_per_day_limit',
            'is_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    board_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'order',
            'board_count', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_board_count(self, obj):
        return obj.boards.filter(is_active=True).count()


class BoardSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Board
        fields = [
            'id', 'category', 'category_name', 'name', 'slug',
            'description', 'icon', 'order',
            'is_private', 'requires_login',
            'thread_count', 'post_count',
            'last_post_at', 'last_post_by',
            'is_active', 'created_at'
        ]
        read_only_fields = [
            'id', 'thread_count', 'post_count',
            'last_post_at', 'last_post_by', 'created_at'
        ]


class BoardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = [
            'category', 'name', 'slug', 'description', 'icon',
            'order', 'is_private', 'requires_login'
        ]


class PostSerializer(serializers.ModelSerializer):
    score = serializers.IntegerField(read_only=True)
    user_reaction = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'thread', 'parent',
            'author_id', 'author_name', 'author_avatar',
            'content', 'content_html', 'is_first_post',
            'upvotes', 'downvotes', 'score', 'user_reaction',
            'is_edited', 'edited_at', 'edit_count',
            'is_approved', 'is_hidden',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_first_post', 'upvotes', 'downvotes',
            'is_edited', 'edited_at', 'edit_count',
            'is_approved', 'is_hidden', 'created_at', 'updated_at'
        ]
    
    def get_user_reaction(self, obj):
        request = self.context.get('request')
        user_id = request.headers.get('X-User-Id') if request else None
        if not user_id:
            return None
        
        reaction = obj.reactions.filter(user_id=user_id).first()
        return reaction.reaction_type if reaction else None


class PostCreateSerializer(serializers.Serializer):
    content = serializers.CharField()
    parent_id = serializers.UUIDField(required=False, allow_null=True)


class ThreadListSerializer(serializers.ModelSerializer):
    board_name = serializers.CharField(source='board.name', read_only=True)
    
    class Meta:
        model = Thread
        fields = [
            'id', 'board', 'board_name', 'title', 'slug',
            'author_id', 'author_name', 'author_avatar',
            'content_preview',
            'is_pinned', 'is_locked', 'is_featured',
            'view_count', 'reply_count',
            'last_post_at', 'last_post_by',
            'created_at'
        ]


class ThreadDetailSerializer(serializers.ModelSerializer):
    board_name = serializers.CharField(source='board.name', read_only=True)
    posts = PostSerializer(many=True, read_only=True)
    
    class Meta:
        model = Thread
        fields = [
            'id', 'board', 'board_name', 'title', 'slug',
            'author_id', 'author_name', 'author_avatar',
            'is_pinned', 'is_locked', 'is_featured',
            'view_count', 'reply_count',
            'last_post_at', 'last_post_by',
            'is_approved',
            'created_at', 'updated_at',
            'posts'
        ]


class ThreadCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=300)
    content = serializers.CharField()
    author_id = serializers.CharField(max_length=255)
    author_name = serializers.CharField(max_length=200)
    author_avatar = serializers.URLField(required=False, allow_blank=True)


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'id', 'thread', 'post',
            'reporter_id', 'reporter_name',
            'reason', 'description',
            'status', 'resolved_by', 'resolved_at', 'resolution_notes',
            'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'resolved_by', 'resolved_at',
            'resolution_notes', 'created_at'
        ]


class ReportCreateSerializer(serializers.Serializer):
    thread_id = serializers.UUIDField(required=False, allow_null=True)
    post_id = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.ChoiceField(choices=[
        'spam', 'harassment', 'inappropriate', 'misinformation', 'other'
    ])
    description = serializers.CharField(max_length=1000, required=False, default='')
    
    def validate(self, data):
        if not data.get('thread_id') and not data.get('post_id'):
            raise serializers.ValidationError(
                "Either thread_id or post_id is required"
            )
        return data


class UserBanSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserBan
        fields = [
            'id', 'user_id', 'user_name', 'reason',
            'is_permanent', 'expires_at', 'banned_by',
            'is_active', 'is_expired', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ReactSerializer(serializers.Serializer):
    reaction_type = serializers.ChoiceField(choices=['upvote', 'downvote'])







