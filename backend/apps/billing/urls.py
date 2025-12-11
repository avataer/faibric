from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BillingViewSet, SubscriptionViewSet, InvoiceViewSet, UsageViewSet
from .webhooks import stripe_webhook, paypal_webhook

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
    
    # Billing profile endpoints
    path('profile/', BillingViewSet.as_view({'get': 'profile'}), name='billing-profile'),
    path('profile/update/', BillingViewSet.as_view({'put': 'update_profile', 'patch': 'update_profile'}), name='billing-profile-update'),
    path('setup-payment/', BillingViewSet.as_view({'post': 'setup_payment'}), name='billing-setup-payment'),
    path('attach-payment-method/', BillingViewSet.as_view({'post': 'attach_payment_method'}), name='billing-attach-payment'),
    path('payment-methods/', BillingViewSet.as_view({'get': 'payment_methods'}), name='billing-payment-methods'),
    
    # Subscription endpoints
    path('subscription/', SubscriptionViewSet.as_view({'get': 'current'}), name='subscription-current'),
    path('subscription/change-plan/', SubscriptionViewSet.as_view({'post': 'change_plan'}), name='subscription-change-plan'),
    path('subscription/cancel/', SubscriptionViewSet.as_view({'post': 'cancel'}), name='subscription-cancel'),
    
    # Usage endpoints
    path('usage/', UsageViewSet.as_view({'get': 'current'}), name='usage-current'),
    path('usage/history/', UsageViewSet.as_view({'get': 'history'}), name='usage-history'),
    
    # Webhooks (no auth required)
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
    path('webhooks/paypal/', paypal_webhook, name='paypal-webhook'),
]

