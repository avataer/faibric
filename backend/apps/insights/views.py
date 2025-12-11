"""
API views for Customer Insights.
Staff-only views for Faibric admin.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Q

from apps.tenants.models import Tenant, TenantMembership

from .models import (
    CustomerInput,
    QualityReview,
    AdminFix,
    CustomerHealth,
    InsightReport,
)
from .serializers import (
    CustomerInputSerializer,
    CustomerInputListSerializer,
    LogInputSerializer,
    RecordFeedbackSerializer,
    QualityReviewSerializer,
    CreateReviewSerializer,
    AdminFixSerializer,
    CreateManualFixSerializer,
    CreateRegenerateFixSerializer,
    CustomerHealthSerializer,
    InsightReportSerializer,
)
from .services import (
    InputLoggingService,
    QualityReviewService,
    AdminFixService,
    CustomerHealthService,
    InsightReportService,
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


# ============================================
# Customer-facing endpoints (log their inputs)
# ============================================

class InputLoggingViewSet(TenantMixin, viewsets.ViewSet):
    """
    API for logging customer inputs (used by Faibric frontend).
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def log(self, request):
        """Log a customer input."""
        serializer = LogInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        customer_input = InputLoggingService.log_input(
            tenant_id=str(tenant.id),
            user_id=str(request.user.id),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            **serializer.validated_data
        )
        
        return Response({
            'success': True,
            'input_id': str(customer_input.id),
        })
    
    @action(detail=True, methods=['post'])
    def feedback(self, request, pk=None):
        """Record feedback on an input."""
        serializer = RecordFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        customer_input = InputLoggingService.record_feedback(
            pk,
            rating=serializer.validated_data.get('rating'),
            accepted=serializer.validated_data.get('accepted'),
            feedback=serializer.validated_data.get('feedback', ''),
        )
        
        return Response({
            'success': True,
            'quality_status': customer_input.quality_status,
        })


# ============================================
# Admin-only endpoints (Faibric staff)
# ============================================

class InsightsDashboardView(APIView):
    """
    Main insights dashboard for Faibric admin.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        data = InsightReportService.get_dashboard_data()
        return Response(data)


class CustomerInputAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View all customer inputs (admin only).
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerInputListSerializer
        return CustomerInputSerializer
    
    def get_queryset(self):
        qs = CustomerInput.objects.select_related('user', 'tenant', 'project')
        
        # Filters
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(quality_status=status)
        
        needs_attention = self.request.query_params.get('needs_attention')
        if needs_attention == 'true':
            qs = qs.filter(
                Q(quality_status__in=['needs_review', 'flagged']) |
                Q(user_rating__lte=2) |
                Q(user_accepted=False) |
                Q(was_error=True)
            )
        
        input_type = self.request.query_params.get('type')
        if input_type:
            qs = qs.filter(input_type=input_type)
        
        tenant_id = self.request.query_params.get('tenant')
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        
        user_id = self.request.query_params.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)
        
        return qs.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """Get inputs pending review."""
        inputs = QualityReviewService.get_pending_reviews(limit=50)
        serializer = CustomerInputListSerializer(inputs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get review statistics."""
        stats = QualityReviewService.get_review_stats()
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Create a review for an input."""
        serializer = CreateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        review = QualityReviewService.create_review(
            input_id=pk,
            reviewer_id=str(request.user.id),
            outcome=serializer.validated_data['outcome'],
            notes=serializer.validated_data.get('notes', ''),
            quality_score=serializer.validated_data.get('quality_score'),
            issue_category=serializer.validated_data.get('issue_category', ''),
        )
        
        return Response({
            'success': True,
            'review_id': str(review.id),
        })
    
    @action(detail=True, methods=['post'])
    def fix_manual(self, request, pk=None):
        """Create a manual fix for an input."""
        serializer = CreateManualFixSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        fix = AdminFixService.create_fix_manual(
            input_id=pk,
            admin_id=str(request.user.id),
            improved_response=serializer.validated_data['improved_response'],
            notes=serializer.validated_data.get('notes', ''),
        )
        
        return Response({
            'success': True,
            'fix_id': str(fix.id),
        })
    
    @action(detail=True, methods=['post'])
    def fix_regenerate(self, request, pk=None):
        """Regenerate response using Claude Opus 4.5."""
        serializer = CreateRegenerateFixSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        fix = AdminFixService.create_fix_regenerate(
            input_id=pk,
            admin_id=str(request.user.id),
            improved_prompt=serializer.validated_data.get('improved_prompt'),
            notes=serializer.validated_data.get('notes', ''),
        )
        
        return Response({
            'success': True,
            'fix_id': str(fix.id),
            'improved_response': fix.improved_response,
        })


class AdminFixViewSet(viewsets.ModelViewSet):
    """
    View and manage admin fixes.
    """
    serializer_class = AdminFixSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return AdminFix.objects.select_related(
            'customer_input__user',
            'customer_input__tenant',
            'admin'
        ).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def notify(self, request, pk=None):
        """Send notification email to customer."""
        success = AdminFixService.notify_customer(pk)
        
        return Response({
            'success': success,
            'message': 'Notification sent' if success else 'Failed to send notification',
        })
    
    @action(detail=False, methods=['get'])
    def pending_notification(self, request):
        """Get fixes that haven't been notified yet."""
        fixes = AdminFix.objects.filter(
            customer_notified=False
        ).select_related('customer_input__user')[:20]
        
        serializer = AdminFixSerializer(fixes, many=True)
        return Response(serializer.data)


class CustomerHealthViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View customer health scores (admin only).
    """
    serializer_class = CustomerHealthSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        qs = CustomerHealth.objects.select_related('tenant')
        
        at_risk = self.request.query_params.get('at_risk')
        if at_risk == 'true':
            qs = qs.filter(is_at_risk=True)
        
        return qs.order_by('health_score')
    
    @action(detail=False, methods=['get'])
    def at_risk(self, request):
        """Get at-risk customers."""
        customers = CustomerHealthService.get_at_risk_customers(limit=20)
        serializer = CustomerHealthSerializer(customers, many=True)
        return Response(serializer.data)


class InsightReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View insight reports (admin only).
    """
    serializer_class = InsightReportSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        report_type = self.request.query_params.get('type', 'daily')
        return InsightReport.objects.filter(report_type=report_type).order_by('-period_start')
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new daily report."""
        report = InsightReportService.generate_daily_report()
        serializer = InsightReportSerializer(report)
        return Response(serializer.data)


# ============================================
# Customer-facing: View their fixes
# ============================================

class CustomerFixView(TenantMixin, APIView):
    """
    Customers view their fixes.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, fix_id):
        """Get a fix for the customer."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        try:
            fix = AdminFix.objects.select_related(
                'customer_input'
            ).get(
                id=fix_id,
                customer_input__tenant=tenant,
                customer_input__user=request.user
            )
        except AdminFix.DoesNotExist:
            return Response({'error': 'Fix not found'}, status=404)
        
        # Mark as viewed
        AdminFixService.mark_viewed(str(fix.id))
        
        return Response({
            'id': str(fix.id),
            'original_request': fix.customer_input.user_input,
            'original_response': fix.customer_input.llm_response,
            'improved_response': fix.improved_response,
            'fix_notes': fix.fix_notes,
            'created_at': fix.created_at.isoformat(),
        })
    
    def post(self, request, fix_id):
        """Customer responds to fix."""
        tenant = self.get_tenant()
        if not tenant:
            return Response({'error': 'No tenant'}, status=400)
        
        try:
            fix = AdminFix.objects.get(
                id=fix_id,
                customer_input__tenant=tenant,
                customer_input__user=request.user
            )
        except AdminFix.DoesNotExist:
            return Response({'error': 'Fix not found'}, status=404)
        
        accepted = request.data.get('accepted')
        feedback = request.data.get('feedback', '')
        
        AdminFixService.record_customer_response(
            str(fix.id),
            accepted=accepted,
            feedback=feedback
        )
        
        return Response({'success': True})






