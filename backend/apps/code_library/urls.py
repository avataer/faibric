"""
URL patterns for code library API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LibraryCategoryViewSet,
    LibraryItemViewSet,
    ConstraintViewSet,
    CodeGenerationViewSet,
)

router = DefaultRouter()
router.register(r'categories', LibraryCategoryViewSet, basename='library-categories')
router.register(r'items', LibraryItemViewSet, basename='library-items')
router.register(r'constraints', ConstraintViewSet, basename='constraints')
router.register(r'generate', CodeGenerationViewSet, basename='code-generation')

urlpatterns = [
    path('', include(router.urls)),
]






