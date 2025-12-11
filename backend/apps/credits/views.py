"""
API views for credits and usage.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tenants.models import Tenant, TenantMembership

from .models import (
    SubscriptionTier,
    CreditBalance,
    LLMRequest,
    CreditTransaction,
    UsageReport,
)
from .serializers import (
    SubscriptionTierSerializer,
    CreditBalanceSerializer,
    LLMRequestSerializer,
    LLMRequestLogSerializer,
    RateLLMRequestSerializer,
    CreditTransactionSerializer,
    PurchaseCreditsSerializer,
    UsageReportSerializer,
    UsageSummarySerializer,
)
from .services import (
    CreditService,
    LLMLoggingService,
    UsageReportService,
)


class TenantMixin:
    def get_tenant(self):
        tenant_id = self.request.headers.get('X-Tenant-ID')
        if tenant_id:
            return Tenant.objects.filter(id=tenant_id).first()
        
        membership = TenantMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).first()
        return membership.tenant if membership else None


class SubscriptionTierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API viewset for subscription tiers (public).
    """
    serializer_class = SubscriptionTierSerializer
    queryset = SubscriptionTier.objects.filter(is_active=True).order_by('display_order')
    permission_classes = [IsAuthenticated]


class CreditBalanceViewSet(TenantMixin, viewsets.ViewSet):
    """
    API viewset for credit balance and usage.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get current credit balance."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        service = CreditService(str(tenant.id))
        balance = service.get_or_create_balance()
        
        serializer = CreditBalanceSerializer(balance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get usage summary."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        service = CreditService(str(tenant.id))
        summary = service.get_usage_summary()
        
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def check(self, request):
        """Check if credits available."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        amount = int(request.query_params.get('amount', 1))
        
        service = CreditService(str(tenant.id))
        result = service.check_credits(amount)
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def purchase(self, request):
        """Purchase additional credits."""
        serializer = PurchaseCreditsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        # Calculate price (e.g., $0.10 per credit)
        from decimal import Decimal
        amount = serializer.validated_data['amount']
        price = Decimal(str(amount * 0.10))
        
        # TODO: Process Stripe payment here
        
        service = CreditService(str(tenant.id))
        transaction = service.purchase_credits(amount, price)
        
        return Response({
            'success': True,
            'credits_purchased': amount,
            'transaction_id': str(transaction.id),
        })


class LLMRequestViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for LLM requests (logging and viewing).
    """
    serializer_class = LLMRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return LLMRequest.objects.none()
        
        qs = LLMRequest.objects.filter(tenant=tenant)
        
        # Filters
        model = self.request.query_params.get('model')
        if model:
            qs = qs.filter(model=model)
        
        request_type = self.request.query_params.get('type')
        if request_type:
            qs = qs.filter(request_type=request_type)
        
        return qs.order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def log(self, request):
        """Log an LLM request."""
        serializer = LLMRequestLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        logging_service = LLMLoggingService(
            str(tenant.id),
            str(request.user.id) if request.user else None
        )
        
        llm_request = logging_service.log_request(**serializer.validated_data)
        
        return Response({
            'success': True,
            'request_id': str(llm_request.id),
            'credits_charged': llm_request.credits_charged,
            'tokens_used': llm_request.total_tokens,
        })
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Rate an LLM request."""
        serializer = RateLLMRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        logging_service = LLMLoggingService(str(tenant.id))
        success = logging_service.rate_request(
            pk,
            rating=serializer.validated_data.get('rating'),
            was_accepted=serializer.validated_data.get('was_accepted'),
            was_modified=serializer.validated_data.get('was_modified'),
        )
        
        return Response({'success': success})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get LLM usage stats."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        from django.db.models import Count, Sum, Avg
        
        qs = LLMRequest.objects.filter(tenant=tenant)
        
        stats = {
            'total_requests': qs.count(),
            'total_tokens': qs.aggregate(Sum('total_tokens'))['total_tokens__sum'] or 0,
            'average_rating': qs.filter(user_rating__isnull=False).aggregate(Avg('user_rating'))['user_rating__avg'],
            'by_model': list(qs.values('model').annotate(
                count=Count('id'),
                tokens=Sum('total_tokens')
            )),
            'by_type': list(qs.values('request_type').annotate(
                count=Count('id'),
                tokens=Sum('total_tokens')
            )),
        }
        
        return Response(stats)


class CreditTransactionViewSet(TenantMixin, viewsets.ReadOnlyModelViewSet):
    """
    API viewset for credit transactions.
    """
    serializer_class = CreditTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return CreditTransaction.objects.none()
        
        return CreditTransaction.objects.filter(tenant=tenant).order_by('-created_at')


class UsageReportViewSet(TenantMixin, viewsets.ReadOnlyModelViewSet):
    """
    API viewset for usage reports.
    """
    serializer_class = UsageReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return UsageReport.objects.none()
        
        period_type = self.request.query_params.get('period', 'daily')
        
        return UsageReport.objects.filter(
            tenant=tenant,
            period_type=period_type
        ).order_by('-period_start')
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate usage report for a date."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        service = UsageReportService(str(tenant.id))
        report = service.generate_daily_report()
        
        serializer = UsageReportSerializer(report)
        return Response(serializer.data)


class AdminStatsViewSet(viewsets.ViewSet):
    """
    Faibric Admin stats (platform-wide).
    Staff only.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get platform-wide credit and LLM stats."""
        if not request.user.is_staff:
            return Response({'error': 'Staff only'}, status=403)
        
        from django.db.models import Count, Sum, Avg
        from django.utils import timezone
        from datetime import timedelta
        
        # Time range
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # LLM stats
        llm_qs = LLMRequest.objects.filter(created_at__gte=month_start)
        
        total_requests = llm_qs.count()
        total_tokens = llm_qs.aggregate(Sum('total_tokens'))['total_tokens__sum'] or 0
        total_cost = llm_qs.aggregate(Sum('estimated_cost'))['estimated_cost__sum'] or 0
        
        by_model = {}
        for entry in llm_qs.values('model').annotate(count=Count('id')):
            model_name = entry['model'].split('/')[-1] if entry['model'] else 'unknown'
            by_model[model_name] = entry['count']
        
        # Credit stats
        total_credits_used = CreditTransaction.objects.filter(
            created_at__gte=month_start,
            transaction_type='usage'
        ).aggregate(Sum('credits'))['credits__sum'] or 0
        
        # Subscription stats
        active_subscriptions = CreditBalance.objects.exclude(
            subscription_tier__slug='free'
        ).count()
        
        return Response({
            'total_requests': total_requests,
            'total_tokens': f"{total_tokens:,}",
            'total_cost': f"{total_cost:.2f}",
            'total_credits_used': abs(total_credits_used),
            'active_subscriptions': active_subscriptions,
            'by_model': by_model,
        })

