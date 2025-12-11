"""
URL patterns for recommendations API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ItemCatalogViewSet,
    UserProfileViewSet,
    EventTrackingViewSet,
    RecommendationViewSet,
    RecommendationModelViewSet,
    ABExperimentViewSet,
)

router = DefaultRouter()
router.register(r'catalog', ItemCatalogViewSet, basename='catalog')
router.register(r'users', UserProfileViewSet, basename='recommendation-users')
router.register(r'events', EventTrackingViewSet, basename='events')
router.register(r'recommend', RecommendationViewSet, basename='recommendations')
router.register(r'models', RecommendationModelViewSet, basename='recommendation-models')
router.register(r'experiments', ABExperimentViewSet, basename='ab-experiments')

urlpatterns = [
    path('', include(router.urls)),
]






