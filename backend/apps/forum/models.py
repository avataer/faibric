import uuid
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class ForumConfig(models.Model):
    """
    Forum configuration for a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='forum_config'
    )
    
    # Forum settings
    forum_name = models.CharField(max_length=200, default='Community Forum')
    forum_description = models.TextField(blank=True)
    
    # Features
    allow_anonymous_viewing = models.BooleanField(default=True)
    require_approval_for_posts = models.BooleanField(default=False)
    allow_attachments = models.BooleanField(default=True)
    max_attachment_size_mb = models.PositiveIntegerField(default=10)
    
    # Moderation
    enable_profanity_filter = models.BooleanField(default=False)
    auto_close_threads_days = models.PositiveIntegerField(
        default=0, 
        help_text="0 = never auto-close"
    )
    
    # Rate limiting
    posts_per_day_limit = models.PositiveIntegerField(default=50)
    threads_per_day_limit = models.PositiveIntegerField(default=10)
    
    # Status
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Forum config for {self.tenant.name}"


class Category(models.Model):
    """
    Forum category (group of boards).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='forum_categories'
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    
    # Display order
    order = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = [['tenant', 'slug']]
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Board(models.Model):
    """
    A discussion board within a category.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='forum_boards'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='boards',
        null=True,
        blank=True
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # Emoji or icon class
    
    # Display order
    order = models.PositiveIntegerField(default=0)
    
    # Permissions
    is_private = models.BooleanField(default=False)
    requires_login = models.BooleanField(default=False)
    
    # Stats (cached)
    thread_count = models.PositiveIntegerField(default=0)
    post_count = models.PositiveIntegerField(default=0)
    
    # Last activity
    last_post_at = models.DateTimeField(null=True, blank=True)
    last_post_by = models.CharField(max_length=200, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = [['tenant', 'slug']]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def update_stats(self):
        """Update cached stats."""
        self.thread_count = self.threads.filter(is_deleted=False).count()
        self.post_count = Post.objects.filter(
            thread__board=self,
            is_deleted=False
        ).count()
        
        last_post = Post.objects.filter(
            thread__board=self,
            is_deleted=False
        ).order_by('-created_at').first()
        
        if last_post:
            self.last_post_at = last_post.created_at
            self.last_post_by = last_post.author_name
        
        self.save(update_fields=[
            'thread_count', 'post_count', 
            'last_post_at', 'last_post_by'
        ])


class Thread(models.Model):
    """
    A discussion thread.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name='threads'
    )
    
    # Thread info
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300)
    
    # Author (from customer's app users)
    author_id = models.CharField(max_length=255)
    author_name = models.CharField(max_length=200)
    author_avatar = models.URLField(blank=True)
    
    # First post content (for preview)
    content_preview = models.TextField(blank=True)
    
    # Thread state
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    # Stats
    view_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)
    
    # Last activity
    last_post_at = models.DateTimeField(auto_now_add=True)
    last_post_by = models.CharField(max_length=200, blank=True)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=255, blank=True)
    delete_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-last_post_at']
        indexes = [
            models.Index(fields=['board', 'is_deleted', '-is_pinned', '-last_post_at']),
            models.Index(fields=['author_id']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:300]
        super().save(*args, **kwargs)
    
    def update_stats(self):
        """Update thread stats."""
        self.reply_count = self.posts.filter(is_deleted=False).count() - 1  # Exclude first post
        if self.reply_count < 0:
            self.reply_count = 0
        
        last_post = self.posts.filter(is_deleted=False).order_by('-created_at').first()
        if last_post:
            self.last_post_at = last_post.created_at
            self.last_post_by = last_post.author_name
        
        self.save(update_fields=['reply_count', 'last_post_at', 'last_post_by'])


class Post(models.Model):
    """
    A post/reply in a thread.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    
    # Reply to another post (for nested replies)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    # Author
    author_id = models.CharField(max_length=255)
    author_name = models.CharField(max_length=200)
    author_avatar = models.URLField(blank=True)
    
    # Content
    content = models.TextField()
    content_html = models.TextField(blank=True)  # Rendered HTML
    
    # Is first post in thread?
    is_first_post = models.BooleanField(default=False)
    
    # Reactions/votes
    upvotes = models.PositiveIntegerField(default=0)
    downvotes = models.PositiveIntegerField(default=0)
    
    # Edit history
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    edit_count = models.PositiveIntegerField(default=0)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=255, blank=True)
    delete_reason = models.TextField(blank=True)
    
    # Report tracking
    report_count = models.PositiveIntegerField(default=0)
    is_hidden = models.BooleanField(default=False)  # Hidden due to reports
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['thread', 'is_deleted', 'created_at']),
            models.Index(fields=['author_id']),
        ]
    
    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"Post by {self.author_name}: {preview}"
    
    @property
    def score(self):
        return self.upvotes - self.downvotes


class PostReaction(models.Model):
    """
    Reactions (upvote/downvote) on posts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    
    user_id = models.CharField(max_length=255)
    reaction_type = models.CharField(max_length=20, choices=[
        ('upvote', 'Upvote'),
        ('downvote', 'Downvote'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['post', 'user_id']]
    
    def __str__(self):
        return f"{self.user_id} {self.reaction_type} on {self.post.id}"


class Report(models.Model):
    """
    Reports on posts or threads.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='forum_reports'
    )
    
    # What's being reported
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    
    # Reporter
    reporter_id = models.CharField(max_length=255)
    reporter_name = models.CharField(max_length=200)
    
    # Report details
    reason = models.CharField(max_length=50, choices=[
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('inappropriate', 'Inappropriate Content'),
        ('misinformation', 'Misinformation'),
        ('other', 'Other'),
    ])
    description = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ], default='pending')
    
    # Resolution
    resolved_by = models.CharField(max_length=255, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        target = f"thread {self.thread_id}" if self.thread else f"post {self.post_id}"
        return f"Report on {target} by {self.reporter_name}"


class UserBan(models.Model):
    """
    Banned users from the forum.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='forum_bans'
    )
    
    user_id = models.CharField(max_length=255)
    user_name = models.CharField(max_length=200)
    
    reason = models.TextField()
    
    # Ban duration
    is_permanent = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Who banned
    banned_by = models.CharField(max_length=255)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['tenant', 'user_id']]
    
    def __str__(self):
        return f"Ban: {self.user_name}"
    
    @property
    def is_expired(self):
        if self.is_permanent:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return True
        return False






