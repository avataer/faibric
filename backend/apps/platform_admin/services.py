"""
Faibric Platform Admin Services.
Analytics, metrics generation, and Google Ads integration.
"""
import logging
from typing import Dict, List, Optional
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Avg, F
from django.utils import timezone
from django.conf import settings

from .models import (
    PlatformMetrics,
    FunnelStep,
    FunnelEvent,
    FunnelConversion,
    AdCampaign,
    AdCampaignDaily,
    SystemHealth,
)

logger = logging.getLogger(__name__)


class PlatformMetricsService:
    """
    Service for generating platform-wide metrics.
    """
    
    def generate_daily_metrics(self, target_date: date = None) -> PlatformMetrics:
        """Generate daily platform metrics."""
        from django.contrib.auth import get_user_model
        from apps.tenants.models import Tenant
        from apps.credits.models import LLMRequest, CreditBalance, SubscriptionTier
        from apps.projects.models import Project
        
        User = get_user_model()
        
        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        next_date = target_date + timedelta(days=1)
        
        # User metrics
        total_users = User.objects.filter(is_active=True).count()
        new_users = User.objects.filter(
            date_joined__date=target_date
        ).count()
        active_users = User.objects.filter(
            last_login__date=target_date
        ).count()
        
        # Tenant metrics
        total_tenants = Tenant.objects.filter(is_active=True).count()
        new_tenants = Tenant.objects.filter(
            created_at__date=target_date
        ).count()
        
        # Subscription breakdown
        tier_counts = CreditBalance.objects.values(
            'subscription_tier__slug'
        ).annotate(count=Count('id'))
        
        tier_map = {tc['subscription_tier__slug']: tc['count'] for tc in tier_counts}
        
        # Usage metrics
        llm_requests = LLMRequest.objects.filter(
            created_at__date=target_date
        )
        total_llm_requests = llm_requests.count()
        total_tokens = llm_requests.aggregate(Sum('total_tokens'))['total_tokens__sum'] or 0
        total_credits = llm_requests.aggregate(Sum('credits_charged'))['credits_charged__sum'] or 0
        total_cost = llm_requests.aggregate(Sum('estimated_cost'))['estimated_cost__sum'] or Decimal('0')
        
        # Project metrics
        total_projects = Project.objects.count()
        new_projects = Project.objects.filter(created_at__date=target_date).count()
        
        # Calculate MRR
        starter_price = SubscriptionTier.objects.filter(slug='starter').values_list('price_monthly', flat=True).first() or 0
        pro_price = SubscriptionTier.objects.filter(slug='pro').values_list('price_monthly', flat=True).first() or 0
        
        mrr = (tier_map.get('starter', 0) * float(starter_price)) + (tier_map.get('pro', 0) * float(pro_price))
        
        metrics, _ = PlatformMetrics.objects.update_or_create(
            date=target_date,
            defaults={
                'total_users': total_users,
                'new_users': new_users,
                'active_users': active_users,
                'total_tenants': total_tenants,
                'new_tenants': new_tenants,
                'free_tier_count': tier_map.get('free', 0),
                'starter_tier_count': tier_map.get('starter', 0),
                'pro_tier_count': tier_map.get('pro', 0),
                'mrr': Decimal(str(mrr)),
                'arr': Decimal(str(mrr * 12)),
                'total_llm_requests': total_llm_requests,
                'total_tokens_used': total_tokens,
                'total_credits_consumed': total_credits,
                'total_llm_cost': total_cost,
                'total_projects': total_projects,
                'new_projects': new_projects,
            }
        )
        
        return metrics
    
    def get_dashboard_data(self, days: int = 30) -> Dict:
        """Get dashboard data for Faibric admin."""
        from_date = timezone.now().date() - timedelta(days=days)
        
        metrics = PlatformMetrics.objects.filter(
            date__gte=from_date
        ).order_by('date')
        
        latest = metrics.last()
        
        return {
            'summary': {
                'total_users': latest.total_users if latest else 0,
                'total_tenants': latest.total_tenants if latest else 0,
                'mrr': float(latest.mrr) if latest else 0,
                'arr': float(latest.arr) if latest else 0,
                'total_projects': latest.total_projects if latest else 0,
            },
            'trends': {
                'dates': [m.date.isoformat() for m in metrics],
                'new_users': [m.new_users for m in metrics],
                'new_tenants': [m.new_tenants for m in metrics],
                'active_users': [m.active_users for m in metrics],
                'llm_requests': [m.total_llm_requests for m in metrics],
                'revenue': [float(m.daily_revenue) for m in metrics],
            },
            'subscription_breakdown': {
                'free': latest.free_tier_count if latest else 0,
                'starter': latest.starter_tier_count if latest else 0,
                'pro': latest.pro_tier_count if latest else 0,
            },
            'costs': {
                'total_llm_cost': sum(float(m.total_llm_cost) for m in metrics),
                'tokens_used': sum(m.total_tokens_used for m in metrics),
                'credits_consumed': sum(m.total_credits_consumed for m in metrics),
            }
        }


class FunnelService:
    """
    Service for funnel analytics.
    """
    
    @staticmethod
    def setup_default_funnels():
        """Create default funnels for Faibric."""
        funnels = {
            'signup': [
                ('visit_landing', 'Visit Landing Page'),
                ('click_signup', 'Click Sign Up'),
                ('complete_signup', 'Complete Signup'),
                ('verify_email', 'Verify Email'),
                ('create_project', 'Create First Project'),
            ],
            'upgrade': [
                ('view_pricing', 'View Pricing'),
                ('select_plan', 'Select Plan'),
                ('enter_payment', 'Enter Payment'),
                ('complete_upgrade', 'Complete Upgrade'),
            ],
            'activation': [
                ('signup', 'Sign Up'),
                ('create_project', 'Create Project'),
                ('generate_code', 'Generate Code'),
                ('deploy', 'Deploy'),
            ],
        }
        
        for funnel_name, steps in funnels.items():
            for i, (event_name, step_name) in enumerate(steps):
                FunnelStep.objects.get_or_create(
                    funnel_name=funnel_name,
                    step_order=i,
                    defaults={
                        'step_name': step_name,
                        'event_name': event_name,
                    }
                )
    
    def track_event(
        self,
        funnel_name: str,
        step_order: int,
        user_id: str = None,
        tenant_id: str = None,
        session_id: str = None,
        utm_source: str = None,
        utm_medium: str = None,
        utm_campaign: str = None,
        metadata: Dict = None,
    ):
        """Track a funnel event."""
        try:
            step = FunnelStep.objects.get(
                funnel_name=funnel_name,
                step_order=step_order
            )
        except FunnelStep.DoesNotExist:
            logger.warning(f"Funnel step not found: {funnel_name} step {step_order}")
            return None
        
        event = FunnelEvent.objects.create(
            user_id=user_id,
            tenant_id=tenant_id,
            funnel_step=step,
            session_id=session_id or '',
            utm_source=utm_source or '',
            utm_medium=utm_medium or '',
            utm_campaign=utm_campaign or '',
            metadata=metadata or {},
        )
        
        return event
    
    def generate_conversion_report(
        self,
        funnel_name: str,
        target_date: date = None
    ) -> FunnelConversion:
        """Generate conversion report for a funnel."""
        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        steps = FunnelStep.objects.filter(
            funnel_name=funnel_name
        ).order_by('step_order')
        
        if not steps:
            return None
        
        # Count events per step
        step_counts = {}
        for step in steps:
            count = FunnelEvent.objects.filter(
                funnel_step=step,
                timestamp__date=target_date
            ).count()
            step_counts[step.step_name] = count
        
        # Calculate step-to-step rates
        step_rates = {}
        step_list = list(steps)
        for i in range(len(step_list) - 1):
            current_step = step_list[i]
            next_step = step_list[i + 1]
            
            current_count = step_counts.get(current_step.step_name, 0)
            next_count = step_counts.get(next_step.step_name, 0)
            
            rate = (next_count / current_count * 100) if current_count > 0 else 0
            step_rates[f"{current_step.step_name} → {next_step.step_name}"] = round(rate, 2)
        
        # Overall conversion
        first_step = step_list[0]
        last_step = step_list[-1]
        started = step_counts.get(first_step.step_name, 0)
        completed = step_counts.get(last_step.step_name, 0)
        overall_rate = (completed / started * 100) if started > 0 else 0
        
        # By source
        by_source = dict(
            FunnelEvent.objects.filter(
                funnel_step=first_step,
                timestamp__date=target_date
            ).exclude(
                utm_source=''
            ).values('utm_source').annotate(count=Count('id')).values_list('utm_source', 'count')
        )
        
        conversion, _ = FunnelConversion.objects.update_or_create(
            funnel_name=funnel_name,
            date=target_date,
            defaults={
                'step_counts': step_counts,
                'step_to_step_rates': step_rates,
                'total_started': started,
                'total_completed': completed,
                'overall_conversion_rate': round(overall_rate, 2),
                'by_source': by_source,
            }
        )
        
        return conversion
    
    def get_funnel_report(
        self,
        funnel_name: str,
        days: int = 30
    ) -> Dict:
        """Get funnel report for period."""
        from_date = timezone.now().date() - timedelta(days=days)
        
        conversions = FunnelConversion.objects.filter(
            funnel_name=funnel_name,
            date__gte=from_date
        ).order_by('date')
        
        return {
            'funnel_name': funnel_name,
            'dates': [c.date.isoformat() for c in conversions],
            'started': [c.total_started for c in conversions],
            'completed': [c.total_completed for c in conversions],
            'conversion_rates': [c.overall_conversion_rate for c in conversions],
            'average_conversion_rate': sum(c.overall_conversion_rate for c in conversions) / len(conversions) if conversions else 0,
        }


class GoogleAdsService:
    """
    Service for Google Ads integration.
    """
    
    def __init__(self, tenant_id: str = None):
        self.tenant_id = tenant_id  # None = Faibric's own campaigns
        self.google_ads_client = None
    
    def _get_client(self):
        """Get Google Ads API client."""
        # TODO: Initialize with credentials
        # from google.ads.googleads.client import GoogleAdsClient
        # return GoogleAdsClient.load_from_storage()
        return None
    
    def create_campaign(
        self,
        name: str,
        daily_budget: Decimal,
        target_url: str,
        keywords: List[str] = None,
        start_date: date = None,
    ) -> AdCampaign:
        """Create a new ad campaign."""
        campaign = AdCampaign.objects.create(
            tenant_id=self.tenant_id,
            name=name,
            platform='google_ads',
            daily_budget=daily_budget,
            target_url=target_url,
            target_keywords=keywords or [],
            start_date=start_date or timezone.now().date(),
            status='draft',
        )
        
        # TODO: Create campaign in Google Ads API
        # client = self._get_client()
        # if client:
        #     # Create campaign via API
        #     external_id = create_google_campaign(...)
        #     campaign.external_campaign_id = external_id
        #     campaign.save()
        
        return campaign
    
    def sync_campaign_metrics(self, campaign: AdCampaign) -> bool:
        """Sync metrics from Google Ads API."""
        if not campaign.external_campaign_id:
            return False
        
        # TODO: Fetch from Google Ads API
        # client = self._get_client()
        # metrics = fetch_campaign_metrics(client, campaign.external_campaign_id)
        
        # For now, mock data
        campaign.total_impressions = 1000
        campaign.total_clicks = 50
        campaign.total_spend = Decimal('25.00')
        campaign.ctr = 5.0
        campaign.cpc = Decimal('0.50')
        campaign.last_synced_at = timezone.now()
        campaign.save()
        
        return True
    
    def sync_daily_metrics(self, campaign: AdCampaign, target_date: date = None) -> AdCampaignDaily:
        """Sync daily metrics from Google Ads API."""
        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        # TODO: Fetch from Google Ads API
        
        # Create or update daily record
        daily, _ = AdCampaignDaily.objects.update_or_create(
            campaign=campaign,
            date=target_date,
            defaults={
                'impressions': 100,
                'clicks': 5,
                'spend': Decimal('2.50'),
                'conversions': 1,
                'ctr': 5.0,
                'cpc': Decimal('0.50'),
            }
        )
        
        return daily
    
    def get_campaign_performance(
        self,
        campaign_id: str = None,
        days: int = 30
    ) -> Dict:
        """Get campaign performance data."""
        from_date = timezone.now().date() - timedelta(days=days)
        
        query = AdCampaign.objects.all()
        
        if self.tenant_id:
            query = query.filter(tenant_id=self.tenant_id)
        else:
            query = query.filter(tenant__isnull=True)
        
        if campaign_id:
            query = query.filter(id=campaign_id)
        
        campaigns = list(query)
        
        result = []
        for campaign in campaigns:
            daily = AdCampaignDaily.objects.filter(
                campaign=campaign,
                date__gte=from_date
            ).order_by('date')
            
            result.append({
                'campaign_id': str(campaign.id),
                'name': campaign.name,
                'status': campaign.status,
                'total_spend': float(campaign.total_spend),
                'total_impressions': campaign.total_impressions,
                'total_clicks': campaign.total_clicks,
                'total_conversions': campaign.total_conversions,
                'ctr': campaign.ctr,
                'cpc': float(campaign.cpc),
                'daily': [
                    {
                        'date': d.date.isoformat(),
                        'impressions': d.impressions,
                        'clicks': d.clicks,
                        'spend': float(d.spend),
                        'conversions': d.conversions,
                    }
                    for d in daily
                ]
            })
        
        return result
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a campaign."""
        try:
            campaign = AdCampaign.objects.get(id=campaign_id)
            campaign.status = 'paused'
            campaign.save()
            
            # TODO: Pause in Google Ads API
            
            return True
        except AdCampaign.DoesNotExist:
            return False
    
    def resume_campaign(self, campaign_id: str) -> bool:
        """Resume a campaign."""
        try:
            campaign = AdCampaign.objects.get(id=campaign_id)
            campaign.status = 'active'
            campaign.save()
            
            # TODO: Resume in Google Ads API
            
            return True
        except AdCampaign.DoesNotExist:
            return False


class SystemHealthService:
    """
    Service for monitoring system health.
    """
    
    def record_health_check(self) -> SystemHealth:
        """Record current system health."""
        from django.db import connection
        
        health = SystemHealth.objects.create(
            overall_status='healthy'
        )
        
        # TODO: Collect actual metrics
        # - API request counts from logs/metrics
        # - Database connection pool
        # - Redis queue lengths
        # - Storage usage
        
        return health
    
    def get_current_status(self) -> Dict:
        """Get current system status."""
        latest = SystemHealth.objects.order_by('-timestamp').first()
        
        if not latest:
            return {'status': 'unknown'}
        
        return {
            'status': latest.overall_status,
            'timestamp': latest.timestamp.isoformat(),
            'api': {
                'requests_1h': latest.api_requests_1h,
                'errors_1h': latest.api_errors_1h,
                'avg_response_ms': latest.api_avg_response_ms,
            },
            'llm': {
                'requests_1h': latest.llm_requests_1h,
                'errors_1h': latest.llm_errors_1h,
                'avg_response_ms': latest.llm_avg_response_ms,
            },
            'database': {
                'connections': latest.db_connections,
                'avg_query_ms': latest.db_query_avg_ms,
            },
            'queue': {
                'pending': latest.queue_pending,
                'failed': latest.queue_failed,
            },
            'storage': {
                'used_gb': latest.storage_used_gb,
                'limit_gb': latest.storage_limit_gb,
            }
        }









