"""
URL configuration for faibric_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for Render.com"""
    return JsonResponse({'status': 'healthy', 'service': 'faibric-api'})


urlpatterns = [
    path('api/health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/tenants/', include('apps.tenants.urls')),  # Multi-tenant management
    path('api/projects/', include('apps.projects.urls')),
    path('api/ai/', include('apps.ai_engine.urls')),
    path('api/templates/', include('apps.templates.urls')),
    path('api/deploy/', include('apps.deployment.urls')),
    path('api/stocks/', include('apps.stocks.urls')),  # Real stock data API
    path('api/gateway/', include('apps.gateway.urls')),  # Universal API Gateway
    path('api/v1/', include('apps.platform.urls')),  # Platform services (DB, Auth, etc.)
    path('api/billing/', include('apps.billing.urls')),  # Billing and payments
    path('api/analytics/', include('apps.analytics.urls')),  # Analytics and funnels
    path('api/email/', include('apps.email_lists.urls')),  # Email lists and subscriptions
    path('api/chat/', include('apps.chat.urls')),  # AI chat widget
    path('api/messaging/', include('apps.messaging.urls')),  # Unified messaging
    path('api/forum/', include('apps.forum.urls')),  # Community forum
    path('api/storage/', include('apps.storage.urls')),  # File storage
    path('api/checkout/', include('apps.checkout.urls')),  # E-commerce checkout
    path('api/cabinet/', include('apps.cabinet.urls')),  # Client cabinets
    path('api/admin-builder/', include('apps.admin_builder.urls')),  # Admin panel builder
    path('api/marketing/', include('apps.marketing.urls')),  # Marketing analysis
    path('api/library/', include('apps.code_library.urls')),  # Code library
    path('api/recommendations/', include('apps.recommendations.urls')),  # Recommendations
    path('api/credits/', include('apps.credits.urls')),  # Credits and usage
    path('api/platform/', include('apps.platform_admin.urls')),  # Faibric admin
    path('api/insights/', include('apps.insights.urls')),  # Customer insights
    path('api/onboarding/', include('apps.onboarding.urls')),  # Landing & onboarding
    path('api/services/', include('apps.external_services.urls')),  # External service status
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

