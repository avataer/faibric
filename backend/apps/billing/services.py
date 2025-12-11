"""
Payment provider services for Stripe and PayPal integration.
"""
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class StripeService:
    """
    Stripe payment integration service.
    Handles customers, payment methods, subscriptions, and invoices.
    """
    
    def __init__(self):
        import stripe
        self.stripe = stripe
        self.stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        self._enabled = bool(self.stripe.api_key)
    
    @property
    def is_enabled(self):
        return self._enabled
    
    def create_customer(self, tenant, billing_profile) -> Optional[str]:
        """Create a Stripe customer for a tenant."""
        if not self.is_enabled:
            logger.warning("Stripe not configured")
            return None
        
        try:
            customer = self.stripe.Customer.create(
                email=billing_profile.billing_email or tenant.owner.email,
                name=billing_profile.billing_name or tenant.name,
                metadata={
                    'tenant_id': str(tenant.id),
                    'tenant_name': tenant.name,
                },
                address={
                    'line1': billing_profile.billing_address_line1,
                    'line2': billing_profile.billing_address_line2,
                    'city': billing_profile.billing_city,
                    'state': billing_profile.billing_state,
                    'postal_code': billing_profile.billing_postal_code,
                    'country': billing_profile.billing_country,
                } if billing_profile.billing_address_line1 else None
            )
            
            billing_profile.stripe_customer_id = customer.id
            billing_profile.save(update_fields=['stripe_customer_id'])
            
            logger.info(f"Created Stripe customer {customer.id} for tenant {tenant.id}")
            return customer.id
            
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            return None
    
    def create_setup_intent(self, billing_profile) -> Optional[Dict[str, Any]]:
        """
        Create a SetupIntent for collecting payment method.
        Returns client_secret for frontend to use with Stripe Elements.
        """
        if not self.is_enabled:
            return None
        
        try:
            # Ensure customer exists
            if not billing_profile.stripe_customer_id:
                self.create_customer(billing_profile.tenant, billing_profile)
            
            setup_intent = self.stripe.SetupIntent.create(
                customer=billing_profile.stripe_customer_id,
                payment_method_types=['card'],
                metadata={
                    'tenant_id': str(billing_profile.tenant_id),
                }
            )
            
            return {
                'client_secret': setup_intent.client_secret,
                'setup_intent_id': setup_intent.id,
            }
            
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error creating setup intent: {e}")
            return None
    
    def attach_payment_method(self, billing_profile, payment_method_id: str) -> bool:
        """Attach a payment method to a customer and set as default."""
        if not self.is_enabled:
            return False
        
        try:
            # Attach to customer
            payment_method = self.stripe.PaymentMethod.attach(
                payment_method_id,
                customer=billing_profile.stripe_customer_id,
            )
            
            # Set as default
            self.stripe.Customer.modify(
                billing_profile.stripe_customer_id,
                invoice_settings={'default_payment_method': payment_method_id},
            )
            
            # Update billing profile with card info
            card = payment_method.card
            billing_profile.stripe_payment_method_id = payment_method_id
            billing_profile.card_last_four = card.last4
            billing_profile.card_brand = card.brand
            billing_profile.card_exp_month = card.exp_month
            billing_profile.card_exp_year = card.exp_year
            billing_profile.has_valid_payment_method = True
            billing_profile.save()
            
            logger.info(f"Attached payment method to tenant {billing_profile.tenant_id}")
            return True
            
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error attaching payment method: {e}")
            return False
    
    def create_subscription(self, billing_profile, price_id: str) -> Optional[Dict[str, Any]]:
        """Create a subscription for a customer."""
        if not self.is_enabled:
            return None
        
        try:
            subscription = self.stripe.Subscription.create(
                customer=billing_profile.stripe_customer_id,
                items=[{'price': price_id}],
                default_payment_method=billing_profile.stripe_payment_method_id,
                metadata={
                    'tenant_id': str(billing_profile.tenant_id),
                }
            )
            
            billing_profile.stripe_subscription_id = subscription.id
            billing_profile.save(update_fields=['stripe_subscription_id'])
            
            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'current_period_end': subscription.current_period_end,
            }
            
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {e}")
            return None
    
    def cancel_subscription(self, billing_profile, at_period_end: bool = True) -> bool:
        """Cancel a subscription."""
        if not self.is_enabled or not billing_profile.stripe_subscription_id:
            return False
        
        try:
            if at_period_end:
                self.stripe.Subscription.modify(
                    billing_profile.stripe_subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                self.stripe.Subscription.delete(billing_profile.stripe_subscription_id)
            
            return True
            
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {e}")
            return False
    
    def create_invoice(self, billing_profile, line_items: list) -> Optional[Dict[str, Any]]:
        """Create an invoice with line items."""
        if not self.is_enabled:
            return None
        
        try:
            # Add invoice items
            for item in line_items:
                self.stripe.InvoiceItem.create(
                    customer=billing_profile.stripe_customer_id,
                    amount=int(item['amount'] * 100),  # Convert to cents
                    currency='usd',
                    description=item['description'],
                )
            
            # Create invoice
            invoice = self.stripe.Invoice.create(
                customer=billing_profile.stripe_customer_id,
                auto_advance=True,  # Auto-finalize
                collection_method='charge_automatically',
            )
            
            return {
                'invoice_id': invoice.id,
                'amount_due': invoice.amount_due / 100,
                'status': invoice.status,
            }
            
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error creating invoice: {e}")
            return None
    
    def get_payment_methods(self, billing_profile) -> list:
        """Get all payment methods for a customer."""
        if not self.is_enabled or not billing_profile.stripe_customer_id:
            return []
        
        try:
            methods = self.stripe.PaymentMethod.list(
                customer=billing_profile.stripe_customer_id,
                type='card',
            )
            
            return [
                {
                    'id': pm.id,
                    'brand': pm.card.brand,
                    'last4': pm.card.last4,
                    'exp_month': pm.card.exp_month,
                    'exp_year': pm.card.exp_year,
                }
                for pm in methods.data
            ]
            
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error listing payment methods: {e}")
            return []


class PayPalService:
    """
    PayPal payment integration service.
    Used as a backup payment method.
    """
    
    def __init__(self):
        self.client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
        self.secret = getattr(settings, 'PAYPAL_SECRET', '')
        self._enabled = bool(self.client_id and self.secret)
        self._access_token = None
        self._token_expires = None
    
    @property
    def is_enabled(self):
        return self._enabled
    
    def _get_access_token(self) -> Optional[str]:
        """Get PayPal OAuth access token."""
        if not self.is_enabled:
            return None
        
        # Check if we have a valid cached token
        if self._access_token and self._token_expires and timezone.now() < self._token_expires:
            return self._access_token
        
        import requests
        from datetime import timedelta
        
        try:
            url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
            # Use production URL for live: https://api-m.paypal.com/v1/oauth2/token
            
            response = requests.post(
                url,
                auth=(self.client_id, self.secret),
                data={'grant_type': 'client_credentials'},
                headers={'Accept': 'application/json'},
            )
            response.raise_for_status()
            
            data = response.json()
            self._access_token = data['access_token']
            self._token_expires = timezone.now() + timedelta(seconds=data['expires_in'] - 60)
            
            return self._access_token
            
        except Exception as e:
            logger.error(f"PayPal auth error: {e}")
            return None
    
    def create_order(self, billing_profile, amount: Decimal, description: str) -> Optional[Dict[str, Any]]:
        """Create a PayPal order for one-time payment."""
        if not self.is_enabled:
            return None
        
        import requests
        
        token = self._get_access_token()
        if not token:
            return None
        
        try:
            url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"
            
            response = requests.post(
                url,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                },
                json={
                    'intent': 'CAPTURE',
                    'purchase_units': [{
                        'amount': {
                            'currency_code': 'USD',
                            'value': str(amount),
                        },
                        'description': description,
                        'custom_id': str(billing_profile.tenant_id),
                    }],
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                'order_id': data['id'],
                'status': data['status'],
                'approve_url': next(
                    (link['href'] for link in data['links'] if link['rel'] == 'approve'),
                    None
                ),
            }
            
        except Exception as e:
            logger.error(f"PayPal create order error: {e}")
            return None
    
    def capture_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Capture a PayPal order after user approval."""
        if not self.is_enabled:
            return None
        
        import requests
        
        token = self._get_access_token()
        if not token:
            return None
        
        try:
            url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
            
            response = requests.post(
                url,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                },
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                'order_id': data['id'],
                'status': data['status'],
                'payer_email': data.get('payer', {}).get('email_address'),
            }
            
        except Exception as e:
            logger.error(f"PayPal capture order error: {e}")
            return None


class UsageTrackingService:
    """
    Service for tracking and recording usage for billing.
    """
    
    # Pricing per unit (can be moved to settings or database)
    PRICING = {
        'ai_tokens': Decimal('0.00001'),  # $0.01 per 1000 tokens
        'storage_bytes': Decimal('0.000000001'),  # ~$1 per GB
        'bandwidth_bytes': Decimal('0.0000000001'),  # ~$0.10 per GB
        'api_calls': Decimal('0.0001'),  # $0.10 per 1000 calls
        'deployments': Decimal('0.00'),  # Included in plan
    }
    
    @classmethod
    def record_usage(cls, tenant, usage_type: str, quantity: int, 
                     resource_type: str = '', resource_id: str = '',
                     description: str = '') -> 'UsageRecord':
        """Record a usage event."""
        from .models import UsageRecord
        
        now = timezone.now()
        
        # Calculate price
        unit_price = cls.PRICING.get(usage_type, Decimal('0'))
        total_price = unit_price * quantity
        
        record = UsageRecord.objects.create(
            tenant=tenant,
            usage_type=usage_type,
            quantity=quantity,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description or f"{usage_type}: {quantity}",
            period_start=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            period_end=now,
            unit_price=unit_price,
            total_price=total_price,
        )
        
        return record
    
    @classmethod
    def get_current_usage(cls, tenant) -> Dict[str, Any]:
        """Get current month's usage summary."""
        from .models import UsageRecord
        from django.db.models import Sum
        
        now = timezone.now()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage = UsageRecord.objects.filter(
            tenant=tenant,
            period_start__gte=period_start,
            invoiced=False,
        ).values('usage_type').annotate(
            total_quantity=Sum('quantity'),
            total_price=Sum('total_price'),
        )
        
        return {
            item['usage_type']: {
                'quantity': item['total_quantity'],
                'price': float(item['total_price']),
            }
            for item in usage
        }
    
    @classmethod
    def record_ai_tokens(cls, tenant, input_tokens: int, output_tokens: int, 
                         project_id: str = ''):
        """Convenience method for recording AI token usage."""
        total_tokens = input_tokens + output_tokens
        return cls.record_usage(
            tenant=tenant,
            usage_type='ai_tokens',
            quantity=total_tokens,
            resource_type='project',
            resource_id=project_id,
            description=f"AI generation: {input_tokens} input + {output_tokens} output tokens"
        )


# Singleton instances
stripe_service = StripeService()
paypal_service = PayPalService()
usage_service = UsageTrackingService()

