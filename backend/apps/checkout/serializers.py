from rest_framework import serializers
from .models import (
    CheckoutConfig, Product, Cart, CartItem,
    Order, OrderItem, Payment, Coupon
)


class CheckoutConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckoutConfig
        fields = [
            'id', 'stripe_enabled', 'stripe_publishable_key',
            'paypal_enabled', 'paypal_sandbox',
            'currency', 'tax_rate',
            'shipping_enabled', 'free_shipping_threshold',
            'send_order_confirmation', 'send_shipping_notification',
            'success_url', 'cancel_url',
            'is_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CheckoutConfigUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckoutConfig
        fields = [
            'stripe_enabled', 'stripe_publishable_key', 'stripe_secret_key', 'stripe_webhook_secret',
            'paypal_enabled', 'paypal_client_id', 'paypal_secret', 'paypal_sandbox',
            'currency', 'tax_rate',
            'shipping_enabled', 'free_shipping_threshold',
            'send_order_confirmation', 'send_shipping_notification',
            'success_url', 'cancel_url',
            'is_enabled'
        ]
        extra_kwargs = {
            'stripe_secret_key': {'write_only': True},
            'stripe_webhook_secret': {'write_only': True},
            'paypal_secret': {'write_only': True},
        }


class ProductSerializer(serializers.ModelSerializer):
    is_on_sale = serializers.BooleanField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'sku',
            'price', 'compare_at_price', 'is_on_sale',
            'track_inventory', 'inventory_quantity', 'in_stock',
            'is_digital', 'image_url', 'images',
            'metadata', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'sku',
            'price', 'compare_at_price',
            'track_inventory', 'inventory_quantity', 'allow_backorder',
            'is_digital', 'download_url', 'download_limit',
            'image_url', 'images', 'metadata', 'is_active'
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'quantity', 'unit_price',
            'options', 'line_total', 'created_at'
        ]
        read_only_fields = ['id', 'unit_price', 'created_at']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = [
            'id', 'customer_id', 'session_id',
            'items', 'item_count', 'subtotal',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    options = serializers.JSONField(required=False, default=dict)


class UpdateCartItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=0)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'product_sku', 'product_image',
            'quantity', 'unit_price', 'line_total', 'options',
            'download_url', 'download_count'
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_id', 'customer_email', 'customer_name',
            'status', 'subtotal', 'tax_amount', 'shipping_amount', 'discount_amount',
            'total_amount', 'currency',
            'shipping_name', 'shipping_address_line1', 'shipping_address_line2',
            'shipping_city', 'shipping_state', 'shipping_postal_code', 'shipping_country',
            'billing_same_as_shipping',
            'payment_method', 'payment_status', 'coupon_code',
            'items', 'notes',
            'created_at', 'paid_at', 'shipped_at', 'delivered_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'status', 'payment_status',
            'created_at', 'paid_at', 'shipped_at', 'delivered_at'
        ]


class CreateOrderSerializer(serializers.Serializer):
    customer_email = serializers.EmailField()
    customer_name = serializers.CharField(max_length=255, required=False, default='')
    customer_phone = serializers.CharField(max_length=50, required=False, default='')
    shipping_address = serializers.JSONField(required=False)
    billing_address = serializers.JSONField(required=False)
    coupon_code = serializers.CharField(max_length=50, required=False, default='')
    notes = serializers.CharField(required=False, default='')
    payment_method = serializers.ChoiceField(choices=['stripe', 'paypal'])


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'provider', 'amount', 'currency',
            'status', 'card_brand', 'card_last_four',
            'refunded_amount', 'error_message',
            'created_at', 'updated_at'
        ]


class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description',
            'discount_type', 'discount_value',
            'minimum_order_amount', 'maximum_discount',
            'usage_limit', 'usage_count', 'per_customer_limit',
            'valid_from', 'valid_until',
            'is_active', 'is_valid', 'created_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at']


class CartTotalSerializer(serializers.Serializer):
    subtotal = serializers.FloatField()
    tax_amount = serializers.FloatField()
    shipping_amount = serializers.FloatField()
    discount_amount = serializers.FloatField()
    total = serializers.FloatField()
    currency = serializers.CharField()
    item_count = serializers.IntegerField()


class CheckoutSessionSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=['stripe', 'paypal'])
    success_url = serializers.URLField(required=False)
    cancel_url = serializers.URLField(required=False)






