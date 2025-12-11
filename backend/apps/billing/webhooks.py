"""
Webhook handlers for Stripe and PayPal.
"""
import json
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhooks for payment events.
    """
    import stripe
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    if not webhook_secret:
        logger.warning("Stripe webhook secret not configured")
        return HttpResponse(status=400)
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        logger.error("Invalid Stripe webhook payload")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe webhook signature")
        return HttpResponse(status=400)
    
    # Handle events
    event_type = event['type']
    data = event['data']['object']
    
    logger.info(f"Stripe webhook: {event_type}")
    
    try:
        if event_type == 'payment_intent.succeeded':
            _handle_payment_succeeded(data)
        elif event_type == 'payment_intent.payment_failed':
            _handle_payment_failed(data)
        elif event_type == 'invoice.paid':
            _handle_invoice_paid(data)
        elif event_type == 'invoice.payment_failed':
            _handle_invoice_payment_failed(data)
        elif event_type == 'customer.subscription.updated':
            _handle_subscription_updated(data)
        elif event_type == 'customer.subscription.deleted':
            _handle_subscription_deleted(data)
        elif event_type == 'setup_intent.succeeded':
            _handle_setup_intent_succeeded(data)
        
    except Exception as e:
        logger.exception(f"Error handling Stripe webhook {event_type}: {e}")
        # Still return 200 to prevent Stripe from retrying
    
    return HttpResponse(status=200)


def _handle_payment_succeeded(data):
    """Handle successful payment."""
    from .models import BillingProfile
    
    customer_id = data.get('customer')
    if not customer_id:
        return
    
    try:
        profile = BillingProfile.objects.get(stripe_customer_id=customer_id)
        logger.info(f"Payment succeeded for tenant {profile.tenant_id}")
    except BillingProfile.DoesNotExist:
        logger.warning(f"No billing profile for Stripe customer {customer_id}")


def _handle_payment_failed(data):
    """Handle failed payment."""
    from .models import BillingProfile
    
    customer_id = data.get('customer')
    if not customer_id:
        return
    
    try:
        profile = BillingProfile.objects.get(stripe_customer_id=customer_id)
        logger.warning(f"Payment failed for tenant {profile.tenant_id}")
        # TODO: Send notification email
    except BillingProfile.DoesNotExist:
        pass


def _handle_invoice_paid(data):
    """Handle paid invoice."""
    from .models import Invoice, BillingProfile
    from django.utils import timezone
    
    stripe_invoice_id = data.get('id')
    customer_id = data.get('customer')
    
    try:
        profile = BillingProfile.objects.get(stripe_customer_id=customer_id)
        
        # Update or create invoice record
        invoice, created = Invoice.objects.update_or_create(
            stripe_invoice_id=stripe_invoice_id,
            defaults={
                'tenant': profile.tenant,
                'number': data.get('number', stripe_invoice_id),
                'status': 'paid',
                'subtotal': data.get('subtotal', 0) / 100,
                'tax': data.get('tax', 0) / 100 if data.get('tax') else 0,
                'total': data.get('total', 0) / 100,
                'amount_paid': data.get('amount_paid', 0) / 100,
                'amount_due': 0,
                'paid_at': timezone.now(),
            }
        )
        
        logger.info(f"Invoice {invoice.number} marked as paid")
        
    except BillingProfile.DoesNotExist:
        logger.warning(f"No billing profile for Stripe customer {customer_id}")


def _handle_invoice_payment_failed(data):
    """Handle failed invoice payment."""
    from .models import Invoice, BillingProfile
    
    stripe_invoice_id = data.get('id')
    customer_id = data.get('customer')
    
    try:
        profile = BillingProfile.objects.get(stripe_customer_id=customer_id)
        
        Invoice.objects.filter(stripe_invoice_id=stripe_invoice_id).update(
            status='open'  # Keep open for retry
        )
        
        logger.warning(f"Invoice payment failed for tenant {profile.tenant_id}")
        # TODO: Send notification email
        
    except BillingProfile.DoesNotExist:
        pass


def _handle_subscription_updated(data):
    """Handle subscription updates."""
    from .models import Subscription, BillingProfile
    from django.utils import timezone
    from datetime import datetime
    
    customer_id = data.get('customer')
    
    try:
        profile = BillingProfile.objects.get(stripe_customer_id=customer_id)
        subscription = Subscription.objects.get(tenant=profile.tenant)
        
        # Update subscription status
        status_map = {
            'active': 'active',
            'past_due': 'past_due',
            'canceled': 'canceled',
            'trialing': 'trialing',
            'paused': 'paused',
        }
        
        subscription.status = status_map.get(data.get('status'), subscription.status)
        
        # Update period
        if data.get('current_period_start'):
            subscription.current_period_start = datetime.fromtimestamp(
                data['current_period_start'], tz=timezone.utc
            )
        if data.get('current_period_end'):
            subscription.current_period_end = datetime.fromtimestamp(
                data['current_period_end'], tz=timezone.utc
            )
        
        subscription.save()
        logger.info(f"Subscription updated for tenant {profile.tenant_id}")
        
    except (BillingProfile.DoesNotExist, Subscription.DoesNotExist):
        pass


def _handle_subscription_deleted(data):
    """Handle subscription cancellation."""
    from .models import Subscription, BillingProfile
    from django.utils import timezone
    
    customer_id = data.get('customer')
    
    try:
        profile = BillingProfile.objects.get(stripe_customer_id=customer_id)
        subscription = Subscription.objects.get(tenant=profile.tenant)
        
        subscription.status = 'canceled'
        subscription.canceled_at = timezone.now()
        subscription.save()
        
        logger.info(f"Subscription canceled for tenant {profile.tenant_id}")
        
    except (BillingProfile.DoesNotExist, Subscription.DoesNotExist):
        pass


def _handle_setup_intent_succeeded(data):
    """Handle successful payment method setup."""
    logger.info(f"Setup intent succeeded: {data.get('id')}")
    # Payment method attachment is handled via API call


@csrf_exempt
@require_POST
def paypal_webhook(request):
    """
    Handle PayPal webhooks.
    """
    try:
        payload = json.loads(request.body)
        event_type = payload.get('event_type', '')
        
        logger.info(f"PayPal webhook: {event_type}")
        
        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            _handle_paypal_payment_completed(payload)
        elif event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
            _handle_paypal_subscription_activated(payload)
        elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
            _handle_paypal_subscription_cancelled(payload)
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.exception(f"Error handling PayPal webhook: {e}")
        return HttpResponse(status=200)  # Return 200 anyway


def _handle_paypal_payment_completed(payload):
    """Handle PayPal payment completion."""
    resource = payload.get('resource', {})
    custom_id = resource.get('custom_id')  # tenant_id
    
    if custom_id:
        logger.info(f"PayPal payment completed for tenant {custom_id}")


def _handle_paypal_subscription_activated(payload):
    """Handle PayPal subscription activation."""
    logger.info("PayPal subscription activated")


def _handle_paypal_subscription_cancelled(payload):
    """Handle PayPal subscription cancellation."""
    logger.info("PayPal subscription cancelled")

