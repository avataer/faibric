"""
API views for marketing analysis.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tenants.models import Tenant, TenantMembership

from .models import (
    Competitor,
    CompetitorChange,
    CompetitorSnapshot,
    Keyword,
    KeywordRanking,
    MarketingConfig,
    MarketingReport,
    ReportTemplate,
)
from .serializers import (
    CompetitorSerializer,
    CompetitorCreateSerializer,
    CompetitorChangeSerializer,
    CompetitorSnapshotSerializer,
    KeywordSerializer,
    KeywordCreateSerializer,
    KeywordRankingSerializer,
    MarketingConfigSerializer,
    MarketingReportSerializer,
    MarketingReportDetailSerializer,
    ReportTemplateSerializer,
    DashboardSerializer,
    GenerateReportRequestSerializer,
    ScrapeCompetitorRequestSerializer,
    CheckKeywordsRequestSerializer,
)
from .tasks import (
    scrape_competitor_task,
    scrape_all_competitors_task,
    check_keyword_task,
    check_all_keywords_task,
    generate_report_task,
)
from .analysis import InsightGenerator
from .keyword_tracker import RankingAnalyzer


class TenantMixin:
    """Mixin to filter querysets by tenant."""
    
    def get_tenant(self):
        """Get current tenant from request."""
        tenant_id = self.request.headers.get('X-Tenant-ID')
        if tenant_id:
            return Tenant.objects.filter(id=tenant_id).first()
        
        # Default to first owned/member tenant
        membership = TenantMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).first()
        return membership.tenant if membership else None


class MarketingConfigViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for marketing configuration.
    """
    serializer_class = MarketingConfigSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return MarketingConfig.objects.none()
        return MarketingConfig.objects.filter(tenant=tenant)
    
    def get_object(self):
        tenant = self.get_tenant()
        if not tenant:
            return None
        
        config, _ = MarketingConfig.objects.get_or_create(tenant=tenant)
        return config
    
    def list(self, request, *args, **kwargs):
        """Get the marketing config for current tenant."""
        obj = self.get_object()
        if not obj:
            return Response({'error': 'No tenant'}, status=400)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Update or create config."""
        return self.update(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update the marketing config."""
        obj = self.get_object()
        if not obj:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CompetitorViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for competitors.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CompetitorCreateSerializer
        return CompetitorSerializer
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return Competitor.objects.none()
        
        qs = Competitor.objects.filter(tenant=tenant)
        
        # Filter by active status
        is_active = self.request.query_params.get('active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        
        return qs.order_by('name')
    
    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['post'])
    def scrape(self, request, pk=None):
        """Trigger scraping for this competitor."""
        competitor = self.get_object()
        scrape_competitor_task.delay(str(competitor.id))
        
        return Response({
            'message': 'Scraping queued',
            'competitor': competitor.name,
        })
    
    @action(detail=False, methods=['post'])
    def scrape_all(self, request):
        """Trigger scraping for all competitors."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        scrape_all_competitors_task.delay(str(tenant.id))
        
        return Response({
            'message': 'Scraping queued for all competitors',
        })
    
    @action(detail=True, methods=['get'])
    def changes(self, request, pk=None):
        """Get changes for this competitor."""
        competitor = self.get_object()
        
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        
        changes = CompetitorChange.objects.filter(
            competitor=competitor,
            created_at__gte=since
        ).order_by('-created_at')
        
        serializer = CompetitorChangeSerializer(changes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def snapshots(self, request, pk=None):
        """Get snapshots for this competitor."""
        competitor = self.get_object()
        
        page_type = request.query_params.get('page_type')
        
        qs = CompetitorSnapshot.objects.filter(
            competitor=competitor
        ).order_by('-created_at')
        
        if page_type:
            qs = qs.filter(page_type=page_type)
        
        # Limit to most recent
        snapshots = qs[:50]
        
        serializer = CompetitorSnapshotSerializer(snapshots, many=True)
        return Response(serializer.data)


class CompetitorChangeViewSet(TenantMixin, viewsets.ReadOnlyModelViewSet):
    """
    API viewset for competitor changes (read-only).
    """
    serializer_class = CompetitorChangeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return CompetitorChange.objects.none()
        
        qs = CompetitorChange.objects.filter(
            competitor__tenant=tenant
        ).order_by('-created_at')
        
        # Filters
        change_type = self.request.query_params.get('type')
        if change_type:
            qs = qs.filter(change_type=change_type)
        
        competitor_id = self.request.query_params.get('competitor')
        if competitor_id:
            qs = qs.filter(competitor_id=competitor_id)
        
        min_importance = self.request.query_params.get('min_importance')
        if min_importance:
            qs = qs.filter(importance_score__gte=int(min_importance))
        
        days = self.request.query_params.get('days')
        if days:
            since = timezone.now() - timedelta(days=int(days))
            qs = qs.filter(created_at__gte=since)
        
        return qs
    
    @action(detail=True, methods=['post'])
    def mark_reviewed(self, request, pk=None):
        """Mark a change as reviewed."""
        change = self.get_object()
        change.is_reviewed = True
        change.reviewed_by = request.user
        change.reviewed_at = timezone.now()
        change.save()
        
        return Response({'status': 'reviewed'})


class KeywordViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for keywords.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return KeywordCreateSerializer
        return KeywordSerializer
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return Keyword.objects.none()
        
        qs = Keyword.objects.filter(tenant=tenant)
        
        is_active = self.request.query_params.get('active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        
        return qs.order_by('keyword')
    
    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['post'])
    def check(self, request, pk=None):
        """Trigger ranking check for this keyword."""
        keyword = self.get_object()
        check_keyword_task.delay(str(keyword.id))
        
        return Response({
            'message': 'Keyword check queued',
            'keyword': keyword.keyword,
        })
    
    @action(detail=False, methods=['post'])
    def check_all(self, request):
        """Trigger ranking check for all keywords."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        check_all_keywords_task.delay(str(tenant.id))
        
        return Response({
            'message': 'Keyword checks queued for all keywords',
        })
    
    @action(detail=True, methods=['get'])
    def rankings(self, request, pk=None):
        """Get ranking history for this keyword."""
        keyword = self.get_object()
        
        domain = request.query_params.get('domain', keyword.your_domain)
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        
        rankings = KeywordRanking.objects.filter(
            keyword=keyword,
            domain=domain,
            created_at__gte=since
        ).order_by('-created_at')
        
        serializer = KeywordRankingSerializer(rankings, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def trends(self, request, pk=None):
        """Get ranking trends for this keyword."""
        keyword = self.get_object()
        
        days = int(request.query_params.get('days', 30))
        
        analyzer = RankingAnalyzer(str(keyword.tenant_id))
        trends = analyzer.get_ranking_trends(str(keyword.id), days)
        
        return Response(trends)


class MarketingReportViewSet(TenantMixin, viewsets.ReadOnlyModelViewSet):
    """
    API viewset for marketing reports.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MarketingReportDetailSerializer
        return MarketingReportSerializer
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return MarketingReport.objects.none()
        
        qs = MarketingReport.objects.filter(tenant=tenant).order_by('-created_at')
        
        report_type = self.request.query_params.get('type')
        if report_type:
            qs = qs.filter(report_type=report_type)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        return qs
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new report."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        serializer = GenerateReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        generate_report_task.delay(str(tenant.id))
        
        return Response({
            'message': 'Report generation started',
        })
    
    @action(detail=True, methods=['get'])
    def html(self, request, pk=None):
        """Get the HTML content of a report."""
        report = self.get_object()
        
        if not report.html_content:
            return Response({'error': 'No HTML content'}, status=404)
        
        from django.http import HttpResponse
        return HttpResponse(report.html_content, content_type='text/html')
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend a report via email."""
        report = self.get_object()
        
        from .reports import ReportDelivery
        delivery = ReportDelivery(report)
        success = delivery.send_email()
        
        if success:
            return Response({'message': 'Report resent'})
        else:
            return Response({'error': 'Failed to send report'}, status=500)


class ReportTemplateViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for report templates.
    """
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return ReportTemplate.objects.none()
        
        # Include tenant templates and system templates
        return ReportTemplate.objects.filter(
            tenant__in=[tenant, None],
            is_active=True
        ).order_by('name')
    
    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set this template as default."""
        template = self.get_object()
        tenant = self.get_tenant()
        
        # Unset other defaults
        ReportTemplate.objects.filter(
            tenant=tenant,
            is_default=True
        ).update(is_default=False)
        
        template.is_default = True
        template.save()
        
        return Response({'status': 'Set as default'})


class MarketingDashboardViewSet(TenantMixin, viewsets.ViewSet):
    """
    API viewset for marketing dashboard.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get marketing dashboard data."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        since = timezone.now() - timedelta(days=7)
        
        # Count data
        competitors_tracked = Competitor.objects.filter(
            tenant=tenant,
            is_active=True
        ).count()
        
        keywords_tracked = Keyword.objects.filter(
            tenant=tenant,
            is_active=True
        ).count()
        
        changes_last_7_days = CompetitorChange.objects.filter(
            competitor__tenant=tenant,
            created_at__gte=since
        ).count()
        
        reports_generated = MarketingReport.objects.filter(
            tenant=tenant
        ).count()
        
        # Top changes
        top_changes = CompetitorChange.objects.filter(
            competitor__tenant=tenant,
            created_at__gte=since
        ).order_by('-importance_score')[:5]
        
        # Keyword summary
        keywords = Keyword.objects.filter(tenant=tenant, is_active=True)
        keyword_summary = []
        
        for keyword in keywords[:10]:
            latest = KeywordRanking.objects.filter(
                keyword=keyword,
                domain=keyword.your_domain
            ).order_by('-created_at').first()
            
            keyword_summary.append({
                'keyword': keyword.keyword,
                'position': latest.position if latest else None,
                'trend': latest.position_change if latest else 0,
            })
        
        # Recent reports
        recent_reports = MarketingReport.objects.filter(
            tenant=tenant
        ).order_by('-created_at')[:5]
        
        # Insights
        insight_gen = InsightGenerator(str(tenant.id))
        insights = (
            insight_gen.get_competitor_insights() +
            insight_gen.get_ranking_insights()
        )
        
        return Response({
            'competitors_tracked': competitors_tracked,
            'keywords_tracked': keywords_tracked,
            'changes_last_7_days': changes_last_7_days,
            'reports_generated': reports_generated,
            'top_changes': CompetitorChangeSerializer(top_changes, many=True).data,
            'keyword_summary': keyword_summary,
            'recent_reports': MarketingReportSerializer(recent_reports, many=True).data,
            'insights': insights,
        })
    
    @action(detail=False, methods=['get'])
    def ranking_summary(self, request):
        """Get ranking summary."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        days = int(request.query_params.get('days', 30))
        
        analyzer = RankingAnalyzer(str(tenant.id))
        summary = analyzer.get_ranking_summary(days)
        
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def insights(self, request):
        """Get marketing insights."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        days = int(request.query_params.get('days', 30))
        
        insight_gen = InsightGenerator(str(tenant.id))
        
        return Response({
            'competitor_insights': insight_gen.get_competitor_insights(days),
            'ranking_insights': insight_gen.get_ranking_insights(days),
        })






