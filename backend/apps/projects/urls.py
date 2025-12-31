from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, PublicBuilderView

router = DefaultRouter()
router.register(r'', ProjectViewSet, basename='project')

urlpatterns = [
    # Public builder API - no authentication required
    path('builder/modify/', PublicBuilderView.as_view(), name='public-builder'),
    
    # Regular project APIs (require authentication)
    path('', include(router.urls)),
]

