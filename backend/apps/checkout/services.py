"""
Checkout services for Stripe and PayPal payments.
"""
import logging
from decimal import Decimal
from typing import Optional, Dict, List
from django.db import transaction
from django.utils import timezone

from .models import (
    CheckoutConfig, Product, Cart, CartItem,
    Order, OrderItem, Payment, Coupon
)

logger = logging.getLogger(__name__)


class StripeCheckoutService:
    """Stripe payment integration."""
    
    def __init__(self, config: CheckoutConfig):
        self.config = config
        
        import stripe
        stripe.api_key = config.stripe_secret_key
        self.stripe = stripe
    
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        order: Order,
        metadata: dict = None
    ) -> Dict:
        """Create a Stripe PaymentIntent."""
        try:
            intent = self.stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency.lower(),
                metadata={
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    **(metadata or {})
                },
                automatic_payment_methods={'enabled': True}
            )
            
            # Create payment record
            Payment.objects.create(
                tenant=order.tenant,
                order=order,
                provider='stripe',
                provider_payment_intent_id=intent.id,
                amount=amount,
                currency=currency,
                status=Payment.Status.PENDING,
                provider_response={'client_secret': intent.client_secret}
            )
            
            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
        except Exception as e:
            logger.error(f"Stripe PaymentIntent creation failed: {e}")
            raise
    
    def create_checkout_session(
        self,
        order: Order,
        line_items: List[Dict],
        success_url: str,
        cancel_url: str
    ) -> str:
        """Create a Stripe Checkout Session."""
        try:
            session = self.stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'order_id': str(order.id),
                    'order_number': order.order_number
                },
                customer_email=order.customer_email
            )
            
            return session.url
        except Exception as e:
            logger.error(f"Stripe Checkout Session creation failed: {e}")
            raise
    
    def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """Handle Stripe webhook events."""
        try:
            event = self.stripe.Webhook.construct_event(
                payload, signature, self.config.stripe_webhook_secret
            )
            
            if event['type'] == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                self._handle_payment_success(payment_intent)
            elif event['type'] == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                self._handle_payment_failure(payment_intent)
            
            return {'status': 'success', 'event_type': event['type']}
        except Exception as e:
            logger.error(f"Stripe webhook handling failed: {e}")
            raise
    
    def _handle_payment_success(self, payment_intent: dict):
        """Handle successful payment."""
        try:
            payment = Payment.objects.get(
                provider_payment_intent_id=payment_intent['id']
            )
            payment.status = Payment.Status.SUCCEEDED
            payment.provider_payment_id = payment_intent.get('latest_charge', '')
            payment.provider_response = payment_intent
            payment.save()
            
            # Update order
            order = payment.order
            order.status = Order.Status.PAID
            order.payment_status = 'paid'
            order.paid_at = timezone.now()
            order.save()
            
            logger.info(f"Payment succeeded for order {order.order_number}")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for intent {payment_intent['id']}")
    
    def _handle_payment_failure(self, payment_intent: dict):
        """Handle failed payment."""
        try:
            payment = Payment.objects.get(
                provider_payment_intent_id=payment_intent['id']
            )
            payment.status = Payment.Status.FAILED
            payment.error_message = payment_intent.get('last_payment_error', {}).get('message', 'Payment failed')
            payment.provider_response = payment_intent
            payment.save()
            
            logger.warning(f"Payment failed for order {payment.order.order_number}")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for intent {payment_intent['id']}")
    
    def refund_payment(self, payment: Payment, amount: Decimal = None) -> Dict:
        """Refund a payment."""
        try:
            refund_amount = amount or payment.amount
            
            refund = self.stripe.Refund.create(
                payment_intent=payment.provider_payment_intent_id,
                amount=int(refund_amount * 100)
            )
            
            payment.refunded_amount += refund_amount
            if payment.refunded_amount >= payment.amount:
                payment.status = Payment.Status.REFUNDED
            else:
                payment.status = Payment.Status.PARTIALLY_REFUNDED
            payment.save()
            
            # Update order if fully refunded
            if payment.status == Payment.Status.REFUNDED:
                payment.order.status = Order.Status.REFUNDED
                payment.order.save()
            
            return {'refund_id': refund.id, 'amount': float(refund_amount)}
        except Exception as e:
            logger.error(f"Stripe refund failed: {e}")
            raise


class PayPalCheckoutService:
    """PayPal payment integration."""
    
    def __init__(self, config: CheckoutConfig):
        self.config = config
        self.base_url = (
            'https://api-m.sandbox.paypal.com'
            if config.paypal_sandbox
            else 'https://api-m.paypal.com'
        )
        self._access_token = None
    
    def _get_access_token(self) -> str:
        """Get PayPal access token."""
        import requests
        from base64 import b64encode
        
        if self._access_token:
            return self._access_token
        
        credentials = b64encode(
            f"{self.config.paypal_client_id}:{self.config.paypal_secret}".encode()
        ).decode()
        
        response = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            headers={
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={'grant_type': 'client_credentials'}
        )
        response.raise_for_status()
        
        self._access_token = response.json()['access_token']
        return self._access_token
    
    def create_order(
        self,
        order: Order,
        return_url: str,
        cancel_url: str
    ) -> Dict:
        """Create a PayPal order."""
        import requests
        
        try:
            access_token = self._get_access_token()
            
            items = []
            for item in order.items.all():
                items.append({
                    'name': item.product_name[:127],
                    'unit_amount': {
                        'currency_code': order.currency,
                        'value': str(item.unit_price)
                    },
                    'quantity': str(item.quantity)
                })
            
            payload = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'reference_id': str(order.id),
                    'custom_id': order.order_number,
                    'amount': {
                        'currency_code': order.currency,
                        'value': str(order.total_amount),
                        'breakdown': {
                            'item_total': {
                                'currency_code': order.currency,
                                'value': str(order.subtotal)
                            },
                            'shipping': {
                                'currency_code': order.currency,
                                'value': str(order.shipping_amount)
                            },
                            'tax_total': {
                                'currency_code': order.currency,
                                'value': str(order.tax_amount)
                            },
                            'discount': {
                                'currency_code': order.currency,
                                'value': str(order.discount_amount)
                            }
                        }
                    },
                    'items': items
                }],
                'application_context': {
                    'return_url': return_url,
                    'cancel_url': cancel_url,
                    'brand_name': 'Faibric Store',
                    'shipping_preference': 'NO_SHIPPING' if all(
                        i.product.is_digital for i in order.items.all() if i.product
                    ) else 'SET_PROVIDED_ADDRESS'
                }
            }
            
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=payload
            )
            response.raise_for_status()
            
            paypal_order = response.json()
            
            # Create payment record
            Payment.objects.create(
                tenant=order.tenant,
                order=order,
                provider='paypal',
                provider_payment_id=paypal_order['id'],
                amount=order.total_amount,
                currency=order.currency,
                status=Payment.Status.PENDING,
                provider_response=paypal_order
            )
            
            # Get approval URL
            approval_url = next(
                (link['href'] for link in paypal_order['links'] if link['rel'] == 'approve'),
                None
            )
            
            return {
                'order_id': paypal_order['id'],
                'approval_url': approval_url
            }
        except Exception as e:
            logger.error(f"PayPal order creation failed: {e}")
            raise
    
    def capture_order(self, paypal_order_id: str) -> Dict:
        """Capture a PayPal order after approval."""
        import requests
        
        try:
            access_token = self._get_access_token()
            
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders/{paypal_order_id}/capture",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
            )
            response.raise_for_status()
            
            capture_data = response.json()
            
            # Update payment
            payment = Payment.objects.get(provider_payment_id=paypal_order_id)
            payment.status = Payment.Status.SUCCEEDED
            payment.provider_response = capture_data
            payment.save()
            
            # Update order
            order = payment.order
            order.status = Order.Status.PAID
            order.payment_status = 'paid'
            order.paid_at = timezone.now()
            order.save()
            
            return {'status': 'captured', 'order_id': paypal_order_id}
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for PayPal order {paypal_order_id}")
            raise
        except Exception as e:
            logger.error(f"PayPal capture failed: {e}")
            raise
    
    def refund_payment(self, payment: Payment, amount: Decimal = None) -> Dict:
        """Refund a PayPal payment."""
        import requests
        
        try:
            access_token = self._get_access_token()
            refund_amount = amount or payment.amount
            
            # Get capture ID from the provider response
            capture_id = payment.provider_response.get('purchase_units', [{}])[0].get(
                'payments', {}
            ).get('captures', [{}])[0].get('id')
            
            if not capture_id:
                raise ValueError("Capture ID not found")
            
            payload = {
                'amount': {
                    'currency_code': payment.currency,
                    'value': str(refund_amount)
                }
            }
            
            response = requests.post(
                f"{self.base_url}/v2/payments/captures/{capture_id}/refund",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=payload
            )
            response.raise_for_status()
            
            refund_data = response.json()
            
            payment.refunded_amount += refund_amount
            if payment.refunded_amount >= payment.amount:
                payment.status = Payment.Status.REFUNDED
            else:
                payment.status = Payment.Status.PARTIALLY_REFUNDED
            payment.save()
            
            if payment.status == Payment.Status.REFUNDED:
                payment.order.status = Order.Status.REFUNDED
                payment.order.save()
            
            return {'refund_id': refund_data['id'], 'amount': float(refund_amount)}
        except Exception as e:
            logger.error(f"PayPal refund failed: {e}")
            raise


class CheckoutService:
    """
    Main checkout service.
    """
    
    def __init__(self, tenant: 'Tenant'):
        self.tenant = tenant
        self._config = None
    
    @property
    def config(self) -> CheckoutConfig:
        if self._config is None:
            self._config, _ = CheckoutConfig.objects.get_or_create(
                tenant=self.tenant
            )
        return self._config
    
    def get_stripe_service(self) -> StripeCheckoutService:
        if not self.config.stripe_enabled:
            raise ValueError("Stripe is not enabled")
        return StripeCheckoutService(self.config)
    
    def get_paypal_service(self) -> PayPalCheckoutService:
        if not self.config.paypal_enabled:
            raise ValueError("PayPal is not enabled")
        return PayPalCheckoutService(self.config)
    
    # ============= CART =============
    
    def get_or_create_cart(
        self,
        customer_id: str = None,
        session_id: str = None
    ) -> Cart:
        """Get or create a cart."""
        if customer_id:
            cart, _ = Cart.objects.get_or_create(
                tenant=self.tenant,
                customer_id=customer_id,
                is_active=True,
                converted_to_order=False
            )
        elif session_id:
            cart, _ = Cart.objects.get_or_create(
                tenant=self.tenant,
                session_id=session_id,
                is_active=True,
                converted_to_order=False
            )
        else:
            raise ValueError("customer_id or session_id required")
        
        return cart
    
    def add_to_cart(
        self,
        cart: Cart,
        product: Product,
        quantity: int = 1,
        options: dict = None
    ) -> CartItem:
        """Add item to cart."""
        if not product.in_stock:
            raise ValueError("Product is out of stock")
        
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                'unit_price': product.price,
                'options': options or {}
            }
        )
        
        if not created:
            item.quantity += quantity
            item.save()
        
        return item
    
    def update_cart_item(
        self,
        cart: Cart,
        product_id: str,
        quantity: int
    ) -> Optional[CartItem]:
        """Update cart item quantity."""
        try:
            item = CartItem.objects.get(cart=cart, product_id=product_id)
            
            if quantity <= 0:
                item.delete()
                return None
            
            item.quantity = quantity
            item.save()
            return item
        except CartItem.DoesNotExist:
            return None
    
    def remove_from_cart(self, cart: Cart, product_id: str) -> bool:
        """Remove item from cart."""
        count, _ = CartItem.objects.filter(
            cart=cart, product_id=product_id
        ).delete()
        return count > 0
    
    def clear_cart(self, cart: Cart):
        """Clear all items from cart."""
        cart.items.all().delete()
    
    def get_cart_total(self, cart: Cart, coupon_code: str = None) -> Dict:
        """Calculate cart totals."""
        subtotal = cart.subtotal
        tax_amount = subtotal * (self.config.tax_rate / 100)
        shipping_amount = Decimal('0')
        discount_amount = Decimal('0')
        
        # Apply shipping
        if self.config.shipping_enabled:
            # Simple flat rate for now
            shipping_amount = Decimal('10.00')
            if self.config.free_shipping_threshold and subtotal >= self.config.free_shipping_threshold:
                shipping_amount = Decimal('0')
        
        # Apply coupon
        if coupon_code:
            try:
                coupon = Coupon.objects.get(
                    tenant=self.tenant,
                    code=coupon_code,
                    is_active=True
                )
                if coupon.is_valid:
                    discount_amount = coupon.calculate_discount(subtotal)
                    if coupon.discount_type == Coupon.DiscountType.FREE_SHIPPING:
                        shipping_amount = Decimal('0')
            except Coupon.DoesNotExist:
                pass
        
        total = subtotal + tax_amount + shipping_amount - discount_amount
        
        return {
            'subtotal': float(subtotal),
            'tax_amount': float(tax_amount),
            'shipping_amount': float(shipping_amount),
            'discount_amount': float(discount_amount),
            'total': float(total),
            'currency': self.config.currency,
            'item_count': cart.item_count
        }
    
    # ============= ORDER =============
    
    @transaction.atomic
    def create_order_from_cart(
        self,
        cart: Cart,
        customer_email: str,
        customer_name: str = '',
        shipping_address: dict = None,
        billing_address: dict = None,
        coupon_code: str = None,
        notes: str = ''
    ) -> Order:
        """Create an order from a cart."""
        if not cart.items.exists():
            raise ValueError("Cart is empty")
        
        totals = self.get_cart_total(cart, coupon_code)
        
        # Create order
        order = Order.objects.create(
            tenant=self.tenant,
            customer_id=cart.customer_id or cart.session_id,
            customer_email=customer_email,
            customer_name=customer_name,
            subtotal=totals['subtotal'],
            tax_amount=totals['tax_amount'],
            shipping_amount=totals['shipping_amount'],
            discount_amount=totals['discount_amount'],
            total_amount=totals['total'],
            currency=totals['currency'],
            coupon_code=coupon_code or '',
            notes=notes,
            cart=cart
        )
        
        # Add shipping address
        if shipping_address:
            order.shipping_name = shipping_address.get('name', customer_name)
            order.shipping_address_line1 = shipping_address.get('address_line1', '')
            order.shipping_address_line2 = shipping_address.get('address_line2', '')
            order.shipping_city = shipping_address.get('city', '')
            order.shipping_state = shipping_address.get('state', '')
            order.shipping_postal_code = shipping_address.get('postal_code', '')
            order.shipping_country = shipping_address.get('country', 'US')
        
        # Add billing address
        if billing_address:
            order.billing_same_as_shipping = False
            order.billing_name = billing_address.get('name', customer_name)
            order.billing_address_line1 = billing_address.get('address_line1', '')
            order.billing_address_line2 = billing_address.get('address_line2', '')
            order.billing_city = billing_address.get('city', '')
            order.billing_state = billing_address.get('state', '')
            order.billing_postal_code = billing_address.get('postal_code', '')
            order.billing_country = billing_address.get('country', 'US')
        
        order.save()
        
        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku,
                product_image=cart_item.product.image_url,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                line_total=cart_item.line_total,
                options=cart_item.options,
                download_url=cart_item.product.download_url if cart_item.product.is_digital else ''
            )
            
            # Update inventory
            if cart_item.product.track_inventory:
                cart_item.product.inventory_quantity -= cart_item.quantity
                cart_item.product.save()
        
        # Mark cart as converted
        cart.converted_to_order = True
        cart.is_active = False
        cart.save()
        
        # Update coupon usage
        if coupon_code:
            try:
                coupon = Coupon.objects.get(tenant=self.tenant, code=coupon_code)
                coupon.usage_count += 1
                coupon.save()
            except Coupon.DoesNotExist:
                pass
        
        return order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID."""
        try:
            return Order.objects.prefetch_related('items').get(
                id=order_id,
                tenant=self.tenant
            )
        except Order.DoesNotExist:
            return None
    
    def get_customer_orders(self, customer_id: str) -> List[Order]:
        """Get orders for a customer."""
        return list(
            Order.objects.filter(
                tenant=self.tenant,
                customer_id=customer_id
            ).prefetch_related('items')
        )
    
    def update_order_status(self, order: Order, status: str) -> Order:
        """Update order status."""
        order.status = status
        
        if status == Order.Status.SHIPPED:
            order.shipped_at = timezone.now()
        elif status == Order.Status.DELIVERED:
            order.delivered_at = timezone.now()
        
        order.save()
        return order






