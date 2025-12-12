"""
Customer Insights & Quality Assurance Services.
"""
import logging
from typing import Dict, List, Optional
from datetime import timedelta
from django.db import transaction
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from django.conf import settings

from .models import (
    CustomerInput,
    QualityReview,
    AdminFix,
    CustomerPattern,
    InsightReport,
    CustomerHealth,
)

logger = logging.getLogger(__name__)


class InputLoggingService:
    """
    Service for logging all customer inputs.
    """
    
    @staticmethod
    def log_input(
        tenant_id: str,
        user_id: str,
        input_type: str,
        user_input: str,
        llm_response: str,
        model_used: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        response_time_ms: int = None,
        context: str = '',
        project_id: str = None,
        session_id: str = '',
        was_error: bool = False,
        ip_address: str = None,
        user_agent: str = '',
    ) -> CustomerInput:
        """
        Log a customer input for tracking and analysis.
        Auto-detects quality issues.
        """
        # Determine initial quality status
        quality_status = 'pending'
        response_too_short = False
        
        # Auto-detect issues
        if was_error:
            quality_status = 'needs_review'
        elif len(llm_response) < 50 and input_type in ['code_generation', 'code_modification']:
            quality_status = 'needs_review'
            response_too_short = True
        
        customer_input = CustomerInput.objects.create(
            tenant_id=tenant_id,
            user_id=user_id,
            input_type=input_type,
            user_input=user_input,
            context=context,
            llm_response=llm_response,
            model_used=model_used,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            response_time_ms=response_time_ms,
            project_id=project_id,
            quality_status=quality_status,
            was_error=was_error,
            response_too_short=response_too_short,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # Update customer health
        CustomerHealthService.update_on_input(tenant_id, customer_input)
        
        return customer_input
    
    @staticmethod
    def record_feedback(
        input_id: str,
        rating: int = None,
        accepted: bool = None,
        feedback: str = ''
    ) -> CustomerInput:
        """
        Record user feedback on a response.
        """
        customer_input = CustomerInput.objects.get(id=input_id)
        
        if rating is not None:
            customer_input.user_rating = rating
            # Flag low ratings for review
            if rating <= 2:
                customer_input.quality_status = 'needs_review'
        
        if accepted is not None:
            customer_input.user_accepted = accepted
            if not accepted:
                customer_input.quality_status = 'needs_review'
        
        if feedback:
            customer_input.user_feedback = feedback
        
        customer_input.save()
        
        # Update customer health
        CustomerHealthService.update_on_feedback(
            str(customer_input.tenant_id),
            customer_input
        )
        
        return customer_input


class QualityReviewService:
    """
    Service for admin quality reviews.
    """
    
    @staticmethod
    def get_pending_reviews(limit: int = 50) -> List[CustomerInput]:
        """
        Get inputs that need admin review.
        Prioritized by urgency.
        """
        return CustomerInput.objects.filter(
            Q(quality_status='needs_review') |
            Q(quality_status='flagged') |
            Q(user_rating__lte=2) |
            Q(user_accepted=False) |
            Q(was_error=True)
        ).select_related(
            'user', 'tenant', 'project'
        ).order_by(
            '-was_error',  # Errors first
            'user_rating',  # Low ratings next
            '-created_at'  # Then by recency
        )[:limit]
    
    @staticmethod
    def get_review_stats() -> Dict:
        """
        Get review statistics for dashboard.
        """
        total_pending = CustomerInput.objects.filter(
            quality_status__in=['pending', 'needs_review', 'flagged']
        ).count()
        
        needs_immediate = CustomerInput.objects.filter(
            Q(was_error=True) | Q(user_rating__lte=2)
        ).exclude(quality_status='fixed').count()
        
        fixed_today = AdminFix.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        # Recent quality trend
        last_7_days = CustomerInput.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        )
        avg_rating = last_7_days.filter(
            user_rating__isnull=False
        ).aggregate(avg=Avg('user_rating'))['avg']
        
        acceptance_rate = None
        with_feedback = last_7_days.filter(user_accepted__isnull=False)
        if with_feedback.exists():
            accepted = with_feedback.filter(user_accepted=True).count()
            acceptance_rate = accepted / with_feedback.count()
        
        return {
            'total_pending': total_pending,
            'needs_immediate_attention': needs_immediate,
            'fixed_today': fixed_today,
            'average_rating_7d': avg_rating,
            'acceptance_rate_7d': acceptance_rate,
        }
    
    @staticmethod
    @transaction.atomic
    def create_review(
        input_id: str,
        reviewer_id: str,
        outcome: str,
        notes: str = '',
        quality_score: int = None,
        issue_category: str = ''
    ) -> QualityReview:
        """
        Create an admin review for an input.
        """
        customer_input = CustomerInput.objects.get(id=input_id)
        
        review = QualityReview.objects.create(
            customer_input=customer_input,
            reviewer_id=reviewer_id,
            outcome=outcome,
            admin_notes=notes,
            quality_score=quality_score,
            issue_category=issue_category,
        )
        
        # Update input status
        if outcome == 'approved':
            customer_input.quality_status = 'good'
        elif outcome in ['needs_fix', 'fixed']:
            customer_input.quality_status = 'flagged'
        elif outcome == 'fixed':
            customer_input.quality_status = 'fixed'
        
        customer_input.save()
        
        return review


class AdminFixService:
    """
    Service for admin fixes and customer notifications.
    """
    
    @staticmethod
    @transaction.atomic
    def create_fix_manual(
        input_id: str,
        admin_id: str,
        improved_response: str,
        notes: str = ''
    ) -> AdminFix:
        """
        Create a manual fix for a customer input.
        """
        customer_input = CustomerInput.objects.get(id=input_id)
        
        fix = AdminFix.objects.create(
            customer_input=customer_input,
            admin_id=admin_id,
            improved_response=improved_response,
            fix_notes=notes,
            fix_method='manual',
        )
        
        customer_input.quality_status = 'fixed'
        customer_input.save()
        
        return fix
    
    @staticmethod
    @transaction.atomic
    def create_fix_regenerate(
        input_id: str,
        admin_id: str,
        improved_prompt: str = None,
        notes: str = ''
    ) -> AdminFix:
        """
        Regenerate a response using Claude Opus 4.5 with improved prompt.
        """
        from apps.ai_engine.llm_config import llm_client, TaskType
        
        customer_input = CustomerInput.objects.get(id=input_id)
        
        # Use improved prompt or original
        prompt = improved_prompt or customer_input.user_input
        
        # Add context about what went wrong
        system_prompt = """You are an expert software engineer using Claude Opus 4.5.
This is a regeneration of a previous response that didn't meet quality standards.
Provide a comprehensive, accurate, and well-documented response.
Focus on correctness, clarity, and best practices."""
        
        if customer_input.context:
            system_prompt += f"\n\nOriginal context: {customer_input.context}"
        
        if notes:
            system_prompt += f"\n\nAdmin notes about the issue: {notes}"
        
        # Regenerate with Opus 4.5
        result = llm_client.generate(
            TaskType.CODE_GENERATION,
            prompt,
            system_prompt,
        )
        
        fix = AdminFix.objects.create(
            customer_input=customer_input,
            admin_id=admin_id,
            improved_response=result['content'],
            improved_prompt=improved_prompt or '',
            fix_notes=notes,
            fix_method='regenerated',
        )
        
        customer_input.quality_status = 'fixed'
        customer_input.save()
        
        return fix
    
    @staticmethod
    def notify_customer(fix_id: str) -> bool:
        """
        Send email notification to customer about the fix.
        """
        from apps.messaging.email_service import EmailService
        
        fix = AdminFix.objects.select_related(
            'customer_input__user',
            'customer_input__tenant'
        ).get(id=fix_id)
        
        customer_input = fix.customer_input
        user = customer_input.user
        
        # Build email
        subject = "🔧 We've improved your request in Faibric"
        
        # Generate view URL
        view_url = f"{settings.FRONTEND_URL}/fixes/{fix.id}"
        
        html_content = f"""
        <h2>Hi {user.first_name or user.email.split('@')[0]},</h2>
        
        <p>Our team noticed that the response to your recent request might not have been 
        as helpful as it could be. We've created an improved version for you!</p>
        
        <h3>Your Original Request:</h3>
        <blockquote style="background: #f5f5f5; padding: 15px; border-left: 3px solid #3b82f6;">
            {customer_input.user_input[:500]}{'...' if len(customer_input.user_input) > 500 else ''}
        </blockquote>
        
        <h3>What We Improved:</h3>
        <p>{fix.fix_notes or 'We regenerated a more comprehensive and accurate response.'}</p>
        
        <p style="text-align: center; margin: 30px 0;">
            <a href="{view_url}" style="background: #3b82f6; color: white; padding: 12px 30px; 
               text-decoration: none; border-radius: 6px; font-weight: bold;">
                View Improved Response
            </a>
        </p>
        
        <p>We're constantly working to improve Faibric. Thank you for being a valued customer!</p>
        
        <p>Best,<br>The Faibric Team</p>
        """
        
        try:
            email_service = EmailService()
            email_id = email_service.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                from_email='support@faibric.com',
            )
            
            fix.customer_notified = True
            fix.notification_sent_at = timezone.now()
            fix.notification_email_id = email_id or ''
            fix.save()
            
            return True
        except Exception as e:
            logger.error(f"Failed to send fix notification: {e}")
            return False
    
    @staticmethod
    def mark_viewed(fix_id: str):
        """Mark fix as viewed by customer."""
        AdminFix.objects.filter(id=fix_id).update(
            customer_viewed=True,
            customer_viewed_at=timezone.now()
        )
    
    @staticmethod
    def record_customer_response(
        fix_id: str,
        accepted: bool,
        feedback: str = ''
    ):
        """Record customer response to fix."""
        fix = AdminFix.objects.get(id=fix_id)
        fix.customer_accepted_fix = accepted
        fix.customer_feedback = feedback
        fix.save()
        
        # Update customer health
        CustomerHealthService.update_on_fix_response(
            str(fix.customer_input.tenant_id),
            accepted
        )


class CustomerHealthService:
    """
    Service for tracking customer health scores.
    """
    
    @staticmethod
    def get_or_create(tenant_id: str) -> CustomerHealth:
        """Get or create health record for tenant."""
        health, _ = CustomerHealth.objects.get_or_create(
            tenant_id=tenant_id
        )
        return health
    
    @staticmethod
    def update_on_input(tenant_id: str, customer_input: CustomerInput):
        """Update health when new input is logged."""
        health = CustomerHealthService.get_or_create(tenant_id)
        
        health.total_inputs += 1
        health.last_activity_at = timezone.now()
        
        if customer_input.was_error:
            health.unresolved_issues += 1
        
        health.calculate_health()
    
    @staticmethod
    def update_on_feedback(tenant_id: str, customer_input: CustomerInput):
        """Update health when feedback is received."""
        health = CustomerHealthService.get_or_create(tenant_id)
        
        if customer_input.user_accepted is True:
            health.total_accepted += 1
        elif customer_input.user_accepted is False:
            health.total_rejected += 1
            health.unresolved_issues += 1
        
        # Recalculate average rating
        ratings = CustomerInput.objects.filter(
            tenant_id=tenant_id,
            user_rating__isnull=False
        ).aggregate(avg=Avg('user_rating'))
        health.average_rating = ratings['avg']
        
        health.calculate_health()
    
    @staticmethod
    def update_on_fix_response(tenant_id: str, accepted: bool):
        """Update health when customer responds to fix."""
        health = CustomerHealthService.get_or_create(tenant_id)
        
        if accepted:
            health.unresolved_issues = max(0, health.unresolved_issues - 1)
            health.total_accepted += 1
        
        health.calculate_health()
    
    @staticmethod
    def get_at_risk_customers(limit: int = 20) -> List[CustomerHealth]:
        """Get customers at risk of churning."""
        return CustomerHealth.objects.filter(
            is_at_risk=True
        ).select_related('tenant').order_by('health_score')[:limit]


class InsightReportService:
    """
    Service for generating insight reports.
    """
    
    @staticmethod
    def generate_daily_report(date=None) -> InsightReport:
        """Generate daily insight report."""
        if date is None:
            date = (timezone.now() - timedelta(days=1)).date()
        
        next_date = date + timedelta(days=1)
        
        inputs = CustomerInput.objects.filter(created_at__date=date)
        
        # Basic metrics
        total_inputs = inputs.count()
        total_users = inputs.values('user').distinct().count()
        total_tenants = inputs.values('tenant').distinct().count()
        
        # Quality metrics
        rated = inputs.filter(user_rating__isnull=False)
        avg_rating = rated.aggregate(avg=Avg('user_rating'))['avg']
        
        with_acceptance = inputs.filter(user_accepted__isnull=False)
        acceptance_rate = None
        if with_acceptance.exists():
            acceptance_rate = with_acceptance.filter(user_accepted=True).count() / with_acceptance.count()
        
        errors = inputs.filter(was_error=True)
        error_rate = errors.count() / total_inputs if total_inputs > 0 else 0
        
        needs_review = inputs.filter(quality_status__in=['needs_review', 'flagged']).count()
        fixed = AdminFix.objects.filter(created_at__date=date).count()
        
        # Breakdowns
        by_input_type = dict(inputs.values('input_type').annotate(count=Count('id')).values_list('input_type', 'count'))
        by_quality_status = dict(inputs.values('quality_status').annotate(count=Count('id')).values_list('quality_status', 'count'))
        by_model = dict(inputs.values('model_used').annotate(count=Count('id')).values_list('model_used', 'count'))
        
        # Top issues (from reviews)
        reviews = QualityReview.objects.filter(created_at__date=date, issue_category__isnull=False)
        top_issues = list(reviews.values('issue_category').annotate(
            count=Count('id')
        ).order_by('-count')[:5])
        
        # Customers needing attention
        at_risk = CustomerHealth.objects.filter(is_at_risk=True).values(
            'tenant__name', 'tenant__id', 'health_score', 'risk_reasons'
        )[:10]
        
        report, _ = InsightReport.objects.update_or_create(
            report_type='daily',
            period_start=date,
            defaults={
                'period_end': next_date,
                'total_inputs': total_inputs,
                'total_users': total_users,
                'total_tenants': total_tenants,
                'average_rating': avg_rating,
                'acceptance_rate': acceptance_rate,
                'error_rate': error_rate,
                'needs_review_count': needs_review,
                'fixed_count': fixed,
                'by_input_type': by_input_type,
                'by_quality_status': by_quality_status,
                'by_model': by_model,
                'top_issues': top_issues,
                'customers_needing_attention': list(at_risk),
            }
        )
        
        return report
    
    @staticmethod
    def get_dashboard_data() -> Dict:
        """Get data for admin insights dashboard."""
        today = timezone.now().date()
        last_7_days = today - timedelta(days=7)
        last_30_days = today - timedelta(days=30)
        
        # Recent inputs
        recent_inputs = CustomerInput.objects.filter(created_at__date__gte=last_7_days)
        
        # Pending reviews
        pending = QualityReviewService.get_review_stats()
        
        # At-risk customers
        at_risk = CustomerHealthService.get_at_risk_customers(10)
        
        # Recent fixes
        recent_fixes = AdminFix.objects.filter(
            created_at__date__gte=last_7_days
        ).select_related('customer_input__user', 'admin')[:10]
        
        # Trends
        daily_counts = CustomerInput.objects.filter(
            created_at__date__gte=last_30_days
        ).values('created_at__date').annotate(
            count=Count('id'),
            avg_rating=Avg('user_rating')
        ).order_by('created_at__date')
        
        return {
            'summary': {
                'total_inputs_7d': recent_inputs.count(),
                'pending_reviews': pending['total_pending'],
                'needs_immediate': pending['needs_immediate_attention'],
                'fixed_today': pending['fixed_today'],
                'avg_rating_7d': pending['average_rating_7d'],
                'acceptance_rate_7d': pending['acceptance_rate_7d'],
                'at_risk_customers': len(at_risk),
            },
            'at_risk_customers': [
                {
                    'tenant_id': str(h.tenant_id),
                    'tenant_name': h.tenant.name,
                    'health_score': h.health_score,
                    'risk_reasons': h.risk_reasons,
                }
                for h in at_risk
            ],
            'recent_fixes': [
                {
                    'id': str(f.id),
                    'user_email': f.customer_input.user.email,
                    'input_type': f.customer_input.input_type,
                    'fix_method': f.fix_method,
                    'notified': f.customer_notified,
                    'created_at': f.created_at.isoformat(),
                }
                for f in recent_fixes
            ],
            'trends': {
                'dates': [str(d['created_at__date']) for d in daily_counts],
                'counts': [d['count'] for d in daily_counts],
                'ratings': [d['avg_rating'] for d in daily_counts],
            },
        }









