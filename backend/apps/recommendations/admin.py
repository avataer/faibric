"""
Django admin configuration for recommendations.
"""
from django.contrib import admin

from .models import (
    ItemCatalog,
    UserProfile,
    UserEvent,
    RecommendationModel,
    RecommendationRequest,
    ABExperiment,
)


@admin.register(ItemCatalog)
class ItemCatalogAdmin(admin.ModelAdmin):
    list_display = ['name', 'external_id', 'category', 'item_type', 'price', 'view_count', 'purchase_count', 'is_active']
    list_filter = ['item_type', 'category', 'is_active', 'is_in_stock']
    search_fields = ['name', 'external_id', 'description']
    readonly_fields = ['view_count', 'purchase_count', 'rating_sum', 'rating_count', 'created_at', 'updated_at']
    
    fieldsets = [
        (None, {
            'fields': ['tenant', 'external_id', 'item_type', 'name', 'description']
        }),
        ('Categorization', {
            'fields': ['category', 'subcategory', 'tags', 'attributes']
        }),
        ('Pricing', {
            'fields': ['price', 'currency']
        }),
        ('Media', {
            'fields': ['image_url', 'url']
        }),
        ('Stats', {
            'fields': ['view_count', 'purchase_count', 'rating_sum', 'rating_count'],
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ['is_active', 'is_in_stock']
        }),
    ]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['external_user_id', 'tenant', 'total_views', 'total_purchases', 'last_active_at']
    list_filter = ['tenant', 'last_active_at']
    search_fields = ['external_user_id']
    readonly_fields = ['total_views', 'total_purchases', 'total_ratings', 'created_at', 'updated_at']


@admin.register(UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'item', 'event_type', 'value', 'timestamp']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['user__external_user_id', 'item__name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(RecommendationModel)
class RecommendationModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_type', 'status', 'is_active', 'training_completed_at']
    list_filter = ['model_type', 'status', 'is_active']
    search_fields = ['name']
    readonly_fields = ['training_started_at', 'training_completed_at', 'created_at', 'updated_at']


@admin.register(RecommendationRequest)
class RecommendationRequestAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'user', 'context_item', 'response_time_ms', 'timestamp']
    list_filter = ['strategy', 'timestamp', 'experiment_id']
    search_fields = ['user__external_user_id']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(ABExperiment)
class ABExperimentAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'traffic_percentage', 'start_date', 'end_date']
    list_filter = ['status']
    search_fields = ['name', 'description']
    readonly_fields = ['results', 'winning_variant', 'created_at', 'updated_at']







