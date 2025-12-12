"""
Serializers for recommendations API.
"""
from rest_framework import serializers

from .models import (
    ItemCatalog,
    UserProfile,
    UserEvent,
    RecommendationModel,
    RecommendationRequest,
    ABExperiment,
)


class ItemCatalogSerializer(serializers.ModelSerializer):
    """Serializer for catalog items."""
    
    average_rating = serializers.FloatField(read_only=True)
    
    class Meta:
        model = ItemCatalog
        fields = [
            'id',
            'external_id',
            'item_type',
            'name',
            'description',
            'category',
            'subcategory',
            'attributes',
            'tags',
            'price',
            'currency',
            'image_url',
            'url',
            'view_count',
            'purchase_count',
            'average_rating',
            'rating_count',
            'is_active',
            'is_in_stock',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'view_count', 'purchase_count', 'rating_count', 'created_at', 'updated_at']


class ItemCatalogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating catalog items."""
    
    class Meta:
        model = ItemCatalog
        fields = [
            'external_id',
            'item_type',
            'name',
            'description',
            'category',
            'subcategory',
            'attributes',
            'tags',
            'price',
            'currency',
            'image_url',
            'url',
            'is_in_stock',
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profiles."""
    
    class Meta:
        model = UserProfile
        fields = [
            'id',
            'external_user_id',
            'preferences',
            'favorite_categories',
            'total_views',
            'total_purchases',
            'total_ratings',
            'last_active_at',
            'created_at',
        ]
        read_only_fields = ['id', 'total_views', 'total_purchases', 'total_ratings', 'created_at']


class UserEventSerializer(serializers.ModelSerializer):
    """Serializer for user events."""
    
    item_name = serializers.CharField(source='item.name', read_only=True)
    external_user_id = serializers.CharField(source='user.external_user_id', read_only=True)
    
    class Meta:
        model = UserEvent
        fields = [
            'id',
            'external_user_id',
            'item',
            'item_name',
            'event_type',
            'value',
            'metadata',
            'session_id',
            'source',
            'timestamp',
        ]
        read_only_fields = ['id', 'timestamp']


class TrackEventSerializer(serializers.Serializer):
    """Serializer for tracking events."""
    
    user_id = serializers.CharField(help_text="External user ID")
    item_id = serializers.CharField(help_text="External item ID")
    event_type = serializers.ChoiceField(
        choices=['view', 'click', 'add_to_cart', 'purchase', 'rating', 'review', 'share', 'favorite', 'search']
    )
    value = serializers.FloatField(required=False, allow_null=True)
    metadata = serializers.DictField(required=False, default=dict)
    session_id = serializers.CharField(required=False, allow_blank=True)
    source = serializers.CharField(required=False, allow_blank=True)
    
    # Optional item info for auto-creation
    item_name = serializers.CharField(required=False, allow_blank=True)
    item_category = serializers.CharField(required=False, allow_blank=True)
    item_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class BatchTrackEventSerializer(serializers.Serializer):
    """Serializer for batch event tracking."""
    
    events = TrackEventSerializer(many=True)


class RecommendationRequestSerializer(serializers.Serializer):
    """Serializer for recommendation requests."""
    
    strategy = serializers.ChoiceField(
        choices=[
            'personalized', 'similar_items', 'also_bought',
            'trending', 'popular', 'new_arrivals', 'top_rated',
            'best_sellers', 'for_you'
        ],
        default='personalized'
    )
    user_id = serializers.CharField(required=False, allow_blank=True)
    item_id = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=100)


class RecommendationItemSerializer(serializers.Serializer):
    """Serializer for recommendation result items."""
    
    item_id = serializers.CharField()
    external_id = serializers.CharField()
    name = serializers.CharField()
    score = serializers.FloatField()
    reason = serializers.CharField(required=False)
    category = serializers.CharField(required=False)


class RecommendationResponseSerializer(serializers.Serializer):
    """Serializer for recommendation response."""
    
    strategy = serializers.CharField()
    count = serializers.IntegerField()
    items = RecommendationItemSerializer(many=True)
    response_time_ms = serializers.IntegerField()
    request_id = serializers.CharField(required=False)


class RecommendationModelSerializer(serializers.ModelSerializer):
    """Serializer for recommendation models."""
    
    class Meta:
        model = RecommendationModel
        fields = [
            'id',
            'name',
            'model_type',
            'parameters',
            'training_started_at',
            'training_completed_at',
            'training_events_count',
            'training_users_count',
            'training_items_count',
            'metrics',
            'status',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ABExperimentSerializer(serializers.ModelSerializer):
    """Serializer for A/B experiments."""
    
    class Meta:
        model = ABExperiment
        fields = [
            'id',
            'name',
            'description',
            'variants',
            'traffic_percentage',
            'start_date',
            'end_date',
            'status',
            'results',
            'winning_variant',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'results', 'winning_variant', 'created_at', 'updated_at']


class CatalogBulkUploadSerializer(serializers.Serializer):
    """Serializer for bulk catalog upload."""
    
    items = ItemCatalogCreateSerializer(many=True)









