from django.contrib import admin
from .models import (
    CheckoutConfig, Product, Cart, CartItem,
    Order, OrderItem, Payment, Coupon
)


@admin.register(CheckoutConfig)
class CheckoutConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'stripe_enabled', 'paypal_enabled', 'currency', 'is_enabled']
    list_filter = ['stripe_enabled', 'paypal_enabled', 'is_enabled']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'price', 'sku', 'in_stock', 'is_active']
    list_filter = ['is_active', 'is_digital', 'track_inventory']
    search_fields = ['name', 'sku', 'description']


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['unit_price', 'line_total']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'tenant', 'customer_id', 'item_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'converted_to_order']
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['unit_price', 'line_total']


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['provider', 'amount', 'status', 'created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'tenant', 'customer_email', 'status', 'total_amount', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'payment_method']
    search_fields = ['order_number', 'customer_email', 'customer_name']
    inlines = [OrderItemInline, PaymentInline]
    readonly_fields = ['order_number', 'paid_at', 'shipped_at', 'delivered_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'provider', 'amount', 'status', 'created_at']
    list_filter = ['provider', 'status']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'tenant', 'discount_type', 'discount_value', 'usage_count', 'is_valid', 'is_active']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code', 'description']






