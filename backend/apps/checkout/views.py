from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse

from apps.tenants.permissions import TenantPermission
from .models import (
    CheckoutConfig, Product, Cart, CartItem,
    Order, OrderItem, Payment, Coupon
)
from .serializers import (
    CheckoutConfigSerializer, CheckoutConfigUpdateSerializer,
    ProductSerializer, ProductCreateSerializer,
    CartSerializer, CartItemSerializer, AddToCartSerializer, UpdateCartItemSerializer,
    OrderSerializer, CreateOrderSerializer, PaymentSerializer,
    CouponSerializer, CartTotalSerializer, CheckoutSessionSerializer
)
from .services import CheckoutService


class CheckoutConfigViewSet(viewsets.ViewSet):
    """ViewSet for checkout configuration."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_config(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        config, _ = CheckoutConfig.objects.get_or_create(tenant=tenant)
        return config
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        return Response(CheckoutConfigSerializer(config).data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_config(self, request):
        config = self._get_config(request)
        if not config:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = CheckoutConfigUpdateSerializer(
            config, data=request.data, partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CheckoutConfigSerializer(config).data)


class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet for products."""
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProductCreateSerializer
        return ProductSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Product.objects.none()
        return Product.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class CouponViewSet(viewsets.ModelViewSet):
    """ViewSet for coupons."""
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Coupon.objects.none()
        return Coupon.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate a coupon code."""
        tenant = getattr(request, 'tenant', None)
        code = request.data.get('code')
        subtotal = request.data.get('subtotal', 0)
        
        try:
            coupon = Coupon.objects.get(tenant=tenant, code=code)
            if coupon.is_valid:
                from decimal import Decimal
                discount = coupon.calculate_discount(Decimal(str(subtotal)))
                return Response({
                    'valid': True,
                    'discount': float(discount),
                    'coupon': CouponSerializer(coupon).data
                })
            return Response({'valid': False, 'error': 'Coupon is no longer valid'})
        except Coupon.DoesNotExist:
            return Response({'valid': False, 'error': 'Coupon not found'})


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for orders (admin view)."""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Order.objects.none()
        return Order.objects.filter(tenant=tenant).prefetch_related('items')
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in Order.Status.values:
            return Response({'error': 'Invalid status'}, status=400)
        
        tenant = getattr(request, 'tenant', None)
        service = CheckoutService(tenant)
        order = service.update_order_status(order, new_status)
        
        return Response(OrderSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        order = self.get_object()
        tenant = getattr(request, 'tenant', None)
        amount = request.data.get('amount')
        
        payment = order.payments.filter(status=Payment.Status.SUCCEEDED).first()
        if not payment:
            return Response({'error': 'No successful payment found'}, status=400)
        
        service = CheckoutService(tenant)
        
        try:
            if payment.provider == 'stripe':
                result = service.get_stripe_service().refund_payment(
                    payment,
                    amount=Decimal(str(amount)) if amount else None
                )
            else:
                result = service.get_paypal_service().refund_payment(
                    payment,
                    amount=Decimal(str(amount)) if amount else None
                )
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


# ============= PUBLIC API (for customer's apps) =============

class PublicCheckoutView(APIView):
    """Public endpoint for checkout operations."""
    permission_classes = [AllowAny]
    
    def _get_tenant(self, request):
        from apps.projects.models import Project
        
        app_id = request.headers.get('X-Faibric-App-Id')
        if not app_id:
            return None
        
        try:
            project = Project.objects.select_related('tenant').get(id=app_id)
            return project.tenant
        except Project.DoesNotExist:
            return None
    
    def get(self, request, action=None, **kwargs):
        tenant = self._get_tenant(request)
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        service = CheckoutService(tenant)
        user_id = request.headers.get('X-User-Id')
        session_id = request.headers.get('X-Session-Id')
        
        if action == 'products':
            products = Product.objects.filter(tenant=tenant, is_active=True)
            return Response(ProductSerializer(products, many=True).data)
        
        elif action == 'product':
            product_id = kwargs.get('id')
            try:
                product = Product.objects.get(id=product_id, tenant=tenant, is_active=True)
                return Response(ProductSerializer(product).data)
            except Product.DoesNotExist:
                return Response({'error': 'Product not found'}, status=404)
        
        elif action == 'cart':
            cart = service.get_or_create_cart(
                customer_id=user_id,
                session_id=session_id or 'anon'
            )
            return Response(CartSerializer(cart).data)
        
        elif action == 'cart-total':
            cart = service.get_or_create_cart(
                customer_id=user_id,
                session_id=session_id or 'anon'
            )
            coupon_code = request.query_params.get('coupon')
            totals = service.get_cart_total(cart, coupon_code)
            return Response(totals)
        
        elif action == 'orders':
            if not user_id:
                return Response({'error': 'X-User-Id required'}, status=400)
            orders = service.get_customer_orders(user_id)
            return Response(OrderSerializer(orders, many=True).data)
        
        elif action == 'order':
            order_id = kwargs.get('id')
            order = service.get_order(order_id)
            if not order:
                return Response({'error': 'Order not found'}, status=404)
            # Check ownership
            if order.customer_id != user_id:
                return Response({'error': 'Access denied'}, status=403)
            return Response(OrderSerializer(order).data)
        
        elif action == 'config':
            config = service.config
            return Response({
                'stripe_enabled': config.stripe_enabled,
                'stripe_publishable_key': config.stripe_publishable_key,
                'paypal_enabled': config.paypal_enabled,
                'paypal_sandbox': config.paypal_sandbox,
                'paypal_client_id': config.paypal_client_id,
                'currency': config.currency,
                'tax_rate': float(config.tax_rate),
                'shipping_enabled': config.shipping_enabled,
                'free_shipping_threshold': float(config.free_shipping_threshold) if config.free_shipping_threshold else None
            })
        
        return Response({'error': 'Unknown action'}, status=400)
    
    def post(self, request, action=None, **kwargs):
        tenant = self._get_tenant(request)
        if not tenant:
            return Response({'error': 'Invalid app ID'}, status=400)
        
        service = CheckoutService(tenant)
        user_id = request.headers.get('X-User-Id')
        session_id = request.headers.get('X-Session-Id')
        
        if action == 'cart-add':
            serializer = AddToCartSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            cart = service.get_or_create_cart(
                customer_id=user_id,
                session_id=session_id or 'anon'
            )
            
            try:
                product = Product.objects.get(
                    id=data['product_id'],
                    tenant=tenant,
                    is_active=True
                )
            except Product.DoesNotExist:
                return Response({'error': 'Product not found'}, status=404)
            
            try:
                item = service.add_to_cart(
                    cart, product, data['quantity'], data.get('options')
                )
                return Response(CartItemSerializer(item).data)
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        
        elif action == 'cart-update':
            serializer = UpdateCartItemSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            cart = service.get_or_create_cart(
                customer_id=user_id,
                session_id=session_id or 'anon'
            )
            
            item = service.update_cart_item(cart, str(data['product_id']), data['quantity'])
            if item:
                return Response(CartItemSerializer(item).data)
            return Response({'removed': True})
        
        elif action == 'cart-remove':
            product_id = request.data.get('product_id')
            cart = service.get_or_create_cart(
                customer_id=user_id,
                session_id=session_id or 'anon'
            )
            service.remove_from_cart(cart, product_id)
            return Response({'success': True})
        
        elif action == 'cart-clear':
            cart = service.get_or_create_cart(
                customer_id=user_id,
                session_id=session_id or 'anon'
            )
            service.clear_cart(cart)
            return Response({'success': True})
        
        elif action == 'checkout':
            serializer = CreateOrderSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            cart = service.get_or_create_cart(
                customer_id=user_id,
                session_id=session_id or 'anon'
            )
            
            if not cart.items.exists():
                return Response({'error': 'Cart is empty'}, status=400)
            
            try:
                order = service.create_order_from_cart(
                    cart=cart,
                    customer_email=data['customer_email'],
                    customer_name=data.get('customer_name', ''),
                    shipping_address=data.get('shipping_address'),
                    billing_address=data.get('billing_address'),
                    coupon_code=data.get('coupon_code'),
                    notes=data.get('notes', '')
                )
                
                # Create payment session
                payment_method = data['payment_method']
                success_url = service.config.success_url or request.data.get('success_url', '')
                cancel_url = service.config.cancel_url or request.data.get('cancel_url', '')
                
                if payment_method == 'stripe':
                    stripe_service = service.get_stripe_service()
                    payment_data = stripe_service.create_payment_intent(
                        amount=order.total_amount,
                        currency=order.currency,
                        order=order
                    )
                    return Response({
                        'order': OrderSerializer(order).data,
                        'payment': {
                            'provider': 'stripe',
                            'client_secret': payment_data['client_secret']
                        }
                    })
                
                elif payment_method == 'paypal':
                    paypal_service = service.get_paypal_service()
                    payment_data = paypal_service.create_order(
                        order=order,
                        return_url=success_url + f'?order_id={order.id}',
                        cancel_url=cancel_url
                    )
                    return Response({
                        'order': OrderSerializer(order).data,
                        'payment': {
                            'provider': 'paypal',
                            'order_id': payment_data['order_id'],
                            'approval_url': payment_data['approval_url']
                        }
                    })
                
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
            except Exception as e:
                return Response({'error': str(e)}, status=500)
        
        elif action == 'paypal-capture':
            paypal_order_id = request.data.get('order_id')
            if not paypal_order_id:
                return Response({'error': 'PayPal order_id required'}, status=400)
            
            try:
                paypal_service = service.get_paypal_service()
                result = paypal_service.capture_order(paypal_order_id)
                
                payment = Payment.objects.get(provider_payment_id=paypal_order_id)
                return Response({
                    'success': True,
                    'order': OrderSerializer(payment.order).data
                })
            except Exception as e:
                return Response({'error': str(e)}, status=400)
        
        elif action == 'validate-coupon':
            code = request.data.get('code')
            subtotal = request.data.get('subtotal', 0)
            
            try:
                coupon = Coupon.objects.get(tenant=tenant, code=code)
                if coupon.is_valid:
                    from decimal import Decimal
                    discount = coupon.calculate_discount(Decimal(str(subtotal)))
                    return Response({
                        'valid': True,
                        'discount': float(discount),
                        'discount_type': coupon.discount_type,
                        'description': coupon.description
                    })
                return Response({'valid': False, 'error': 'Coupon expired'})
            except Coupon.DoesNotExist:
                return Response({'valid': False, 'error': 'Invalid coupon'})
        
        return Response({'error': 'Unknown action'}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """Handle Stripe webhooks."""
    permission_classes = [AllowAny]
    
    def post(self, request, tenant_id=None):
        from apps.tenants.models import Tenant
        
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            config = tenant.checkout_config
        except (Tenant.DoesNotExist, CheckoutConfig.DoesNotExist):
            return HttpResponse(status=400)
        
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        service = CheckoutService(tenant)
        try:
            result = service.get_stripe_service().handle_webhook(payload, sig_header)
            return HttpResponse(status=200)
        except Exception as e:
            return HttpResponse(status=400)









