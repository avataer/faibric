from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CheckoutConfigViewSet, ProductViewSet, CouponViewSet, OrderViewSet,
    PublicCheckoutView, StripeWebhookView
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'coupons', CouponViewSet, basename='coupon')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    
    # Config
    path('config/', CheckoutConfigViewSet.as_view({'get': 'config'}), name='checkout-config'),
    path('config/update/', CheckoutConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='checkout-config-update'),
    
    # Stripe webhook
    path('webhooks/stripe/<uuid:tenant_id>/', StripeWebhookView.as_view(), name='stripe-webhook'),
    
    # Public API (for customer's apps)
    path('public/config/', PublicCheckoutView.as_view(), {'action': 'config'}, name='public-checkout-config'),
    path('public/products/', PublicCheckoutView.as_view(), {'action': 'products'}, name='public-products'),
    path('public/products/<uuid:id>/', PublicCheckoutView.as_view(), {'action': 'product'}, name='public-product'),
    path('public/cart/', PublicCheckoutView.as_view(), {'action': 'cart'}, name='public-cart'),
    path('public/cart/total/', PublicCheckoutView.as_view(), {'action': 'cart-total'}, name='public-cart-total'),
    path('public/cart/add/', PublicCheckoutView.as_view(), {'action': 'cart-add'}, name='public-cart-add'),
    path('public/cart/update/', PublicCheckoutView.as_view(), {'action': 'cart-update'}, name='public-cart-update'),
    path('public/cart/remove/', PublicCheckoutView.as_view(), {'action': 'cart-remove'}, name='public-cart-remove'),
    path('public/cart/clear/', PublicCheckoutView.as_view(), {'action': 'cart-clear'}, name='public-cart-clear'),
    path('public/checkout/', PublicCheckoutView.as_view(), {'action': 'checkout'}, name='public-checkout'),
    path('public/paypal/capture/', PublicCheckoutView.as_view(), {'action': 'paypal-capture'}, name='public-paypal-capture'),
    path('public/coupon/validate/', PublicCheckoutView.as_view(), {'action': 'validate-coupon'}, name='public-validate-coupon'),
    path('public/orders/', PublicCheckoutView.as_view(), {'action': 'orders'}, name='public-orders'),
    path('public/orders/<uuid:id>/', PublicCheckoutView.as_view(), {'action': 'order'}, name='public-order'),
]









