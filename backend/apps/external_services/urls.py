"""
URL patterns for external services status and testing.
"""
from django.urls import path

from .views import ServiceStatusView, TestServicesView, TestLLMView

urlpatterns = [
    path('status/', ServiceStatusView.as_view(), name='service-status'),
    path('test/', TestServicesView.as_view(), name='test-services'),
    path('test/llm/', TestLLMView.as_view(), name='test-llm'),
]






