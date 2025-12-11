from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.tenants.permissions import TenantPermission, TenantAdminPermission
from .models import BillingProfile, Subscription, Invoice, UsageRecord
from .serializers import (
    BillingProfileSerializer, BillingProfileUpdateSerializer,
    SubscriptionSerializer, InvoiceSerializer, UsageRecordSerializer,
    UsageSummarySerializer, PaymentMethodSerializer, SetupIntentSerializer,
    AttachPaymentMethodSerializer, ChangePlanSerializer
)
from .services import stripe_service, paypal_service, UsageTrackingService


class BillingViewSet(viewsets.ViewSet):
    """
    ViewSet for managing billing profile and payment methods.
    Customer enters billing info ONCE and it handles everything.
    """
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_billing_profile(self, request):
        """Get billing profile for current tenant."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        return BillingProfile.objects.filter(tenant=tenant).first()
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current billing profile."""
        profile = self._get_billing_profile(request)
        if not profile:
            return Response({'error': 'Billing profile not found'}, status=404)
        
        serializer = BillingProfileSerializer(profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """
        Update billing info - customer enters this ONCE.
        Includes name, email, address.
        """
        profile = self._get_billing_profile(request)
        if not profile:
            return Response({'error': 'Billing profile not found'}, status=404)
        
        serializer = BillingProfileUpdateSerializer(
            profile, 
            data=request.data, 
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Update Stripe customer if exists
        if profile.stripe_customer_id and stripe_service.is_enabled:
            try:
                import stripe
                stripe.Customer.modify(
                    profile.stripe_customer_id,
                    email=profile.billing_email,
                    name=profile.billing_name,
                )
            except Exception:
                pass  # Non-critical
        
        return Response(BillingProfileSerializer(profile).data)
    
    @action(detail=False, methods=['post'])
    def setup_payment(self, request):
        """
        Start payment method setup flow.
        Returns a Stripe SetupIntent client_secret for use with Stripe Elements.
        """
        profile = self._get_billing_profile(request)
        if not profile:
            return Response({'error': 'Billing profile not found'}, status=404)
        
        result = stripe_service.create_setup_intent(profile)
        if not result:
            return Response(
                {'error': 'Failed to create setup intent. Is Stripe configured?'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return Response(SetupIntentSerializer(result).data)
    
    @action(detail=False, methods=['post'])
    def attach_payment_method(self, request):
        """
        Attach a payment method after customer completes Stripe Elements form.
        This is called after the customer enters their card ONCE.
        """
        profile = self._get_billing_profile(request)
        if not profile:
            return Response({'error': 'Billing profile not found'}, status=404)
        
        serializer = AttachPaymentMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        success = stripe_service.attach_payment_method(
            profile,
            serializer.validated_data['payment_method_id']
        )
        
        if not success:
            return Response(
                {'error': 'Failed to attach payment method'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(BillingProfileSerializer(profile).data)
    
    @action(detail=False, methods=['get'])
    def payment_methods(self, request):
        """List all payment methods."""
        profile = self._get_billing_profile(request)
        if not profile:
            return Response({'error': 'Billing profile not found'}, status=404)
        
        methods = stripe_service.get_payment_methods(profile)
        return Response(methods)


class SubscriptionViewSet(viewsets.ViewSet):
    """
    ViewSet for managing subscriptions.
    """
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def _get_subscription(self, request):
        """Get subscription for current tenant."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        return Subscription.objects.filter(tenant=tenant).first()
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current subscription."""
        subscription = self._get_subscription(request)
        if not subscription:
            return Response({'error': 'Subscription not found'}, status=404)
        
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_plan(self, request):
        """Change subscription plan."""
        subscription = self._get_subscription(request)
        if not subscription:
            return Response({'error': 'Subscription not found'}, status=404)
        
        serializer = ChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_plan = serializer.validated_data['plan']
        
        # Plan pricing and limits
        PLAN_CONFIG = {
            'free': {'price': 0, 'apps': 3, 'tokens': 50000, 'storage': 1},
            'starter': {'price': 29, 'apps': 10, 'tokens': 200000, 'storage': 10},
            'pro': {'price': 79, 'apps': 50, 'tokens': 1000000, 'storage': 50},
            'enterprise': {'price': 199, 'apps': 999, 'tokens': 10000000, 'storage': 500},
        }
        
        config = PLAN_CONFIG.get(new_plan)
        if not config:
            return Response({'error': 'Invalid plan'}, status=400)
        
        # Update subscription
        subscription.plan = new_plan
        subscription.monthly_price = config['price']
        subscription.max_apps = config['apps']
        subscription.max_ai_tokens_per_month = config['tokens']
        subscription.max_storage_gb = config['storage']
        subscription.save()
        
        # Also update tenant plan
        subscription.tenant.plan = new_plan
        subscription.tenant.save(update_fields=['plan'])
        
        return Response(SubscriptionSerializer(subscription).data)
    
    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """Cancel subscription (reverts to free)."""
        subscription = self._get_subscription(request)
        if not subscription:
            return Response({'error': 'Subscription not found'}, status=404)
        
        # Cancel Stripe subscription if exists
        profile = BillingProfile.objects.filter(tenant=subscription.tenant).first()
        if profile and profile.stripe_subscription_id:
            stripe_service.cancel_subscription(profile)
        
        # Revert to free plan
        subscription.plan = 'free'
        subscription.status = 'canceled'
        subscription.save()
        
        return Response(SubscriptionSerializer(subscription).data)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing invoices.
    """
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Invoice.objects.none()
        return Invoice.objects.filter(tenant=tenant)


class UsageViewSet(viewsets.ViewSet):
    """
    ViewSet for viewing usage and costs.
    """
    permission_classes = [IsAuthenticated, TenantPermission]
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current month's usage summary."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        usage = UsageTrackingService.get_current_usage(tenant)
        return Response(usage)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get usage history."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        records = UsageRecord.objects.filter(tenant=tenant)[:100]
        serializer = UsageRecordSerializer(records, many=True)
        return Response(serializer.data)

