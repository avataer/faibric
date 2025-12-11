"""
API views for Faibric Platform Admin.
Requires superuser/staff access.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Count, Sum

from apps.tenants.models import Tenant, TenantMembership

from .models import (
    PlatformMetrics,
    FunnelStep,
    FunnelEvent,
    FunnelConversion,
    AdCampaign,
    AdCampaignDaily,
    SystemHealth,
)
from .services import (
    PlatformMetricsService,
    FunnelService,
    GoogleAdsService,
    SystemHealthService,
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


class PlatformDashboardView(APIView):
    """
    Faibric admin dashboard - requires staff access.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        
        service = PlatformMetricsService()
        data = service.get_dashboard_data(days=days)
        
        return Response(data)


class PlatformMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Platform metrics - requires staff access.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = PlatformMetrics.objects.all().order_by('-date')
    
    def list(self, request):
        days = int(request.query_params.get('days', 30))
        metrics = self.queryset[:days]
        
        return Response([
            {
                'date': m.date.isoformat(),
                'users': {
                    'total': m.total_users,
                    'new': m.new_users,
                    'active': m.active_users,
                },
                'tenants': {
                    'total': m.total_tenants,
                    'new': m.new_tenants,
                },
                'subscriptions': {
                    'free': m.free_tier_count,
                    'starter': m.starter_tier_count,
                    'pro': m.pro_tier_count,
                },
                'revenue': {
                    'daily': float(m.daily_revenue),
                    'mrr': float(m.mrr),
                    'arr': float(m.arr),
                },
                'usage': {
                    'llm_requests': m.total_llm_requests,
                    'tokens': m.total_tokens_used,
                    'credits': m.total_credits_consumed,
                    'cost': float(m.total_llm_cost),
                },
                'projects': {
                    'total': m.total_projects,
                    'new': m.new_projects,
                },
            }
            for m in metrics
        ])
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate metrics for yesterday."""
        service = PlatformMetricsService()
        metrics = service.generate_daily_metrics()
        
        return Response({
            'success': True,
            'date': metrics.date.isoformat(),
        })


class FunnelViewSet(viewsets.ViewSet):
    """
    Funnel analytics - can be for Faibric (staff) or customer (tenant).
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List all funnels."""
        funnels = FunnelStep.objects.values('funnel_name').distinct()
        
        return Response([
            {'name': f['funnel_name']}
            for f in funnels
        ])
    
    @action(detail=False, methods=['get'])
    def report(self, request):
        """Get funnel report."""
        funnel_name = request.query_params.get('funnel')
        if not funnel_name:
            return Response({'error': 'funnel parameter required'}, status=400)
        
        days = int(request.query_params.get('days', 30))
        
        service = FunnelService()
        report = service.get_funnel_report(funnel_name, days=days)
        
        return Response(report)
    
    @action(detail=False, methods=['post'])
    def track(self, request):
        """Track a funnel event."""
        funnel_name = request.data.get('funnel')
        step = request.data.get('step')
        
        if not funnel_name or step is None:
            return Response({'error': 'funnel and step required'}, status=400)
        
        service = FunnelService()
        event = service.track_event(
            funnel_name=funnel_name,
            step_order=step,
            user_id=str(request.user.id) if request.user.is_authenticated else None,
            session_id=request.data.get('session_id'),
            utm_source=request.data.get('utm_source'),
            utm_medium=request.data.get('utm_medium'),
            utm_campaign=request.data.get('utm_campaign'),
            metadata=request.data.get('metadata'),
        )
        
        return Response({
            'success': event is not None,
            'event_id': str(event.id) if event else None,
        })


class AdCampaignViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    Ad campaign management.
    - For staff: Faibric's own campaigns
    - For customers: Their campaigns
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            # Staff can see Faibric campaigns
            return AdCampaign.objects.filter(tenant__isnull=True)
        else:
            # Customers see their own
            tenant = self.get_tenant()
            if not tenant:
                return AdCampaign.objects.none()
            return AdCampaign.objects.filter(tenant=tenant)
    
    def list(self, request):
        campaigns = self.get_queryset().order_by('-created_at')
        
        return Response([
            {
                'id': str(c.id),
                'name': c.name,
                'platform': c.platform,
                'status': c.status,
                'daily_budget': float(c.daily_budget) if c.daily_budget else None,
                'total_spend': float(c.total_spend),
                'total_impressions': c.total_impressions,
                'total_clicks': c.total_clicks,
                'total_conversions': c.total_conversions,
                'ctr': c.ctr,
                'cpc': float(c.cpc),
                'cpa': float(c.cpa),
                'start_date': c.start_date.isoformat() if c.start_date else None,
                'end_date': c.end_date.isoformat() if c.end_date else None,
            }
            for c in campaigns
        ])
    
    def create(self, request):
        tenant = None if request.user.is_staff else self.get_tenant()
        
        service = GoogleAdsService(str(tenant.id) if tenant else None)
        campaign = service.create_campaign(
            name=request.data.get('name'),
            daily_budget=request.data.get('daily_budget'),
            target_url=request.data.get('target_url'),
            keywords=request.data.get('keywords'),
            start_date=request.data.get('start_date'),
        )
        
        return Response({
            'success': True,
            'campaign_id': str(campaign.id),
        })
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        tenant = None if request.user.is_staff else self.get_tenant()
        
        service = GoogleAdsService(str(tenant.id) if tenant else None)
        success = service.pause_campaign(pk)
        
        return Response({'success': success})
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        tenant = None if request.user.is_staff else self.get_tenant()
        
        service = GoogleAdsService(str(tenant.id) if tenant else None)
        success = service.resume_campaign(pk)
        
        return Response({'success': success})
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        tenant = None if request.user.is_staff else self.get_tenant()
        days = int(request.query_params.get('days', 30))
        
        service = GoogleAdsService(str(tenant.id) if tenant else None)
        data = service.get_campaign_performance(campaign_id=pk, days=days)
        
        return Response(data[0] if data else {})
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sync campaign metrics from Google Ads."""
        try:
            campaign = AdCampaign.objects.get(id=pk)
        except AdCampaign.DoesNotExist:
            return Response({'error': 'Campaign not found'}, status=404)
        
        tenant = None if request.user.is_staff else self.get_tenant()
        service = GoogleAdsService(str(tenant.id) if tenant else None)
        
        success = service.sync_campaign_metrics(campaign)
        
        return Response({'success': success})


class SystemHealthView(APIView):
    """
    System health monitoring - staff only.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        service = SystemHealthService()
        return Response(service.get_current_status())
    
    def post(self, request):
        service = SystemHealthService()
        health = service.record_health_check()
        
        return Response({
            'success': True,
            'status': health.overall_status,
        })


class TenantListView(APIView):
    """
    List all tenants - staff only.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        from apps.credits.models import CreditBalance
        
        tenants = Tenant.objects.filter(is_active=True).order_by('-created_at')
        
        return Response([
            {
                'id': str(t.id),
                'name': t.name,
                'slug': t.slug,
                'created_at': t.created_at.isoformat(),
                'owner': t.owner.email if t.owner else None,
                'member_count': t.memberships.filter(is_active=True).count(),
                'credit_balance': getattr(
                    CreditBalance.objects.filter(tenant=t).first(),
                    'credits_remaining', 0
                ),
            }
            for t in tenants
        ])







