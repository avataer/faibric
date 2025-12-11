import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ItemCatalog(models.Model):
    """
    Catalog of items that can be recommended.
    Can be products, content, articles, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='catalog_items'
    )
    
    # Item identification
    external_id = models.CharField(max_length=255, help_text="External ID from customer's system")
    
    ITEM_TYPE_CHOICES = [
        ('product', 'Product'),
        ('article', 'Article'),
        ('video', 'Video'),
        ('course', 'Course'),
        ('service', 'Service'),
        ('custom', 'Custom'),
    ]
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='product')
    
    # Item details
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=200, blank=True)
    subcategory = models.CharField(max_length=200, blank=True)
    
    # Attributes for content-based filtering
    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Item attributes like color, size, genre, tags, etc."
    )
    tags = models.JSONField(default=list, blank=True)
    
    # Price info (for products)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Image/media
    image_url = models.URLField(blank=True)
    url = models.URLField(blank=True, help_text="Link to item page")
    
    # Embedding for content-based filtering
    embedding = models.JSONField(null=True, blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)
    
    # Popularity metrics
    view_count = models.IntegerField(default=0)
    purchase_count = models.IntegerField(default=0)
    rating_sum = models.FloatField(default=0)
    rating_count = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_in_stock = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-purchase_count', '-view_count']
        unique_together = [['tenant', 'external_id']]
        indexes = [
            models.Index(fields=['tenant', 'item_type', 'is_active']),
            models.Index(fields=['tenant', 'category']),
            models.Index(fields=['purchase_count']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.external_id})"
    
    @property
    def average_rating(self):
        if self.rating_count == 0:
            return 0
        return self.rating_sum / self.rating_count


class UserProfile(models.Model):
    """
    User profile for recommendations (end-users of customers).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='recommendation_users'
    )
    
    # User identification (from customer's system)
    external_user_id = models.CharField(max_length=255)
    
    # User preferences
    preferences = models.JSONField(default=dict, blank=True)
    favorite_categories = models.JSONField(default=list, blank=True)
    disliked_items = models.JSONField(default=list, blank=True)
    
    # Computed user embedding (from behavior)
    user_embedding = models.JSONField(null=True, blank=True)
    
    # Activity stats
    total_views = models.IntegerField(default=0)
    total_purchases = models.IntegerField(default=0)
    total_ratings = models.IntegerField(default=0)
    
    last_active_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['tenant', 'external_user_id']]
        indexes = [
            models.Index(fields=['tenant', 'external_user_id']),
        ]
    
    def __str__(self):
        return f"User {self.external_user_id}"


class UserEvent(models.Model):
    """
    User events for building recommendation models.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='user_events'
    )
    
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='events'
    )
    item = models.ForeignKey(
        ItemCatalog,
        on_delete=models.CASCADE,
        related_name='events'
    )
    
    EVENT_TYPE_CHOICES = [
        ('view', 'View'),
        ('click', 'Click'),
        ('add_to_cart', 'Add to Cart'),
        ('purchase', 'Purchase'),
        ('rating', 'Rating'),
        ('review', 'Review'),
        ('share', 'Share'),
        ('favorite', 'Favorite'),
        ('search', 'Search'),
    ]
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    
    # Event details
    value = models.FloatField(
        null=True,
        blank=True,
        help_text="Rating value, purchase amount, etc."
    )
    metadata = models.JSONField(default=dict, blank=True)
    
    # Context
    session_id = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=100, blank=True, help_text="Where the event came from")
    
    # Timestamp
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'user', 'event_type']),
            models.Index(fields=['tenant', 'item', 'event_type']),
            models.Index(fields=['tenant', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.external_user_id} {self.event_type} {self.item.name}"


class RecommendationModel(models.Model):
    """
    Trained recommendation model metadata.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='recommendation_models'
    )
    
    name = models.CharField(max_length=100)
    
    MODEL_TYPE_CHOICES = [
        ('collaborative', 'Collaborative Filtering'),
        ('content_based', 'Content-Based'),
        ('hybrid', 'Hybrid'),
        ('popularity', 'Popularity-Based'),
        ('trending', 'Trending'),
    ]
    model_type = models.CharField(max_length=20, choices=MODEL_TYPE_CHOICES)
    
    # Model parameters
    parameters = models.JSONField(default=dict, blank=True)
    
    # Training info
    training_started_at = models.DateTimeField(null=True, blank=True)
    training_completed_at = models.DateTimeField(null=True, blank=True)
    training_events_count = models.IntegerField(default=0)
    training_users_count = models.IntegerField(default=0)
    training_items_count = models.IntegerField(default=0)
    
    # Model data (for simple models)
    model_data = models.JSONField(null=True, blank=True)
    
    # Performance metrics
    metrics = models.JSONField(default=dict, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('training', 'Training'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
        ('deprecated', 'Deprecated'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    is_active = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.model_type})"


class RecommendationRequest(models.Model):
    """
    Log of recommendation requests for analytics and A/B testing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='recommendation_requests'
    )
    
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='recommendation_requests'
    )
    
    # Request details
    STRATEGY_CHOICES = [
        ('similar_items', 'Similar Items'),
        ('also_bought', 'Users Also Bought'),
        ('trending', 'Trending'),
        ('personalized', 'Personalized For You'),
        ('category', 'Category Recommendations'),
        ('search', 'Search-Based'),
    ]
    strategy = models.CharField(max_length=30, choices=STRATEGY_CHOICES)
    
    context_item = models.ForeignKey(
        ItemCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='context_requests'
    )
    
    # Results
    recommended_items = models.JSONField(default=list)
    model_used = models.ForeignKey(
        RecommendationModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Performance
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # A/B Testing
    experiment_id = models.CharField(max_length=100, blank=True)
    variant = models.CharField(max_length=50, blank=True)
    
    # Engagement tracking
    items_clicked = models.JSONField(default=list)
    items_purchased = models.JSONField(default=list)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'strategy', 'timestamp']),
            models.Index(fields=['experiment_id']),
        ]
    
    def __str__(self):
        return f"{self.strategy} request at {self.timestamp}"


class ABExperiment(models.Model):
    """
    A/B testing experiment for recommendation algorithms.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='ab_experiments'
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Experiment configuration
    variants = models.JSONField(
        default=list,
        help_text="List of variant configs with model/strategy/weight"
    )
    
    # Traffic allocation
    traffic_percentage = models.IntegerField(
        default=100,
        help_text="Percentage of requests to include in experiment"
    )
    
    # Duration
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Results
    results = models.JSONField(default=dict, blank=True)
    winning_variant = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.status})"






