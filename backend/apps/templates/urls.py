from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TemplateViewSet

router = DefaultRouter()
router.register(r'', TemplateViewSet, basename='template')

urlpatterns = [
    path('', include(router.urls)),
]

