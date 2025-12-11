"""
Onboarding Flow Services.
"""
import logging
import secrets
from typing import Dict, Optional, List
from datetime import timedelta, date
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import (
    LandingSession,
    SessionEvent,
    DailyReport,
    AdminNotification,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class OnboardingService:
    """
    Service for managing the onboarding flow.
    """
    
    @staticmethod
    def create_session(
        initial_request: str,
        ip_address: str = None,
        user_agent: str = '',
        utm_source: str = '',
        utm_medium: str = '',
        utm_campaign: str = '',
        utm_content: str = '',
        utm_term: str = '',
        referrer: str = '',
        landing_page: str = '',
    ) -> LandingSession:
        """
        Create a new landing session when user submits their request.
        """
        session_token = secrets.token_urlsafe(32)
        
        # Parse user agent for device info
        device_type = ''
        browser = ''
        os = ''
        if user_agent:
            ua_lower = user_agent.lower()
            if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
                device_type = 'mobile'
            elif 'tablet' in ua_lower or 'ipad' in ua_lower:
                device_type = 'tablet'
            else:
                device_type = 'desktop'
            
            # Simple browser detection
            if 'chrome' in ua_lower:
                browser = 'Chrome'
            elif 'firefox' in ua_lower:
                browser = 'Firefox'
            elif 'safari' in ua_lower:
                browser = 'Safari'
            elif 'edge' in ua_lower:
                browser = 'Edge'
        
        session = LandingSession.objects.create(
            session_token=session_token,
            initial_request=initial_request,
            status='request_submitted',
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
            browser=browser,
            os=os,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            referrer=referrer,
            landing_page=landing_page,
        )
        
        # Log event
        SessionEvent.objects.create(
            session=session,
            event_type='request_submitted',
            event_data={'request': initial_request[:500]},
        )
        
        return session
    
    @staticmethod
    def provide_email(session_token: str, email: str) -> LandingSession:
        """
        User provides their email.
        """
        session = LandingSession.objects.get(session_token=session_token)
        
        old_email = session.email
        is_change = bool(old_email) and old_email != email
        
        if is_change:
            # Track email change
            session.email_change_count += 1
            if old_email:
                session.previous_emails.append(old_email)
            session.status = 'email_changed'
            
            SessionEvent.objects.create(
                session=session,
                event_type='email_changed',
                old_email=old_email,
                new_email=email,
                event_data={'change_count': session.email_change_count},
            )
        else:
            session.status = 'email_provided'
            SessionEvent.objects.create(
                session=session,
                event_type='email_entered',
                event_data={'email': email},
            )
        
        session.email = email
        session.save()
        
        return session
    
    @staticmethod
    def send_magic_link(session_token: str) -> Dict:
        """
        Send magic link to the user's email.
        """
        session = LandingSession.objects.get(session_token=session_token)
        
        if not session.email:
            raise ValueError("No email provided")
        
        # Generate magic token
        magic_token = session.generate_magic_token()
        
        # Build magic link URL
        magic_link = f"{settings.FRONTEND_URL}/verify?token={magic_token}"
        
        # Send email
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #1a1a2e; margin-bottom: 24px;">🚀 Your Faibric Project is Ready!</h1>
            
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Great news! We're building your project based on your request:
            </p>
            
            <div style="background: #f5f7fa; border-left: 4px solid #3b82f6; padding: 16px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0; font-style: italic; color: #555;">
                    "{session.initial_request[:200]}{'...' if len(session.initial_request) > 200 else ''}"
                </p>
            </div>
            
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Click the button below to access your account and watch your project being built in real-time:
            </p>
            
            <div style="text-align: center; margin: 32px 0;">
                <a href="{magic_link}" style="display: inline-block; background: linear-gradient(135deg, #3b82f6, #8b5cf6); 
                   color: white; padding: 16px 48px; text-decoration: none; border-radius: 8px; 
                   font-weight: bold; font-size: 18px; box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);">
                    Open My Project →
                </a>
            </div>
            
            <p style="font-size: 14px; color: #666;">
                This link expires in 24 hours. If you didn't request this, you can safely ignore this email.
            </p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;">
            
            <p style="font-size: 12px; color: #999; text-align: center;">
                © {timezone.now().year} Faibric · Build anything with AI
            </p>
        </div>
        """
        
        try:
            # Try to send email
            try:
                from apps.messaging.email_service import EmailService
                email_service = EmailService()
                email_service.send_email(
                    to_email=session.email,
                    subject="🚀 Your Faibric Project is Ready!",
                    html_content=html_content,
                    from_email='hello@faibric.com',
                )
            except ImportError:
                # Email service not available, log it
                logger.warning(f"Email service not available, magic link: {magic_link}")
            except Exception as email_error:
                logger.warning(f"Email sending failed: {email_error}")
            
            session.status = 'magic_link_sent'
            session.magic_link_sent_at = timezone.now()
            session.save()
            
            SessionEvent.objects.create(
                session=session,
                event_type='magic_link_sent',
                event_data={'email': session.email, 'magic_link': magic_link},
            )
            
            return {'success': True, 'email': session.email, 'magic_link': magic_link}
            
        except Exception as e:
            logger.error(f"Failed to send magic link: {e}")
            
            SessionEvent.objects.create(
                session=session,
                event_type='error',
                error_message=str(e),
                event_data={'action': 'send_magic_link'},
            )
            
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    @transaction.atomic
    def verify_magic_link(magic_token: str) -> Dict:
        """
        Verify magic link and create account.
        """
        from apps.tenants.models import Tenant, TenantMembership
        
        try:
            session = LandingSession.objects.get(magic_token=magic_token)
        except LandingSession.DoesNotExist:
            return {'success': False, 'error': 'Invalid or expired link'}
        
        if not session.is_magic_token_valid(magic_token):
            SessionEvent.objects.create(
                session=session,
                event_type='magic_link_expired',
            )
            return {'success': False, 'error': 'Link has expired'}
        
        # Mark as clicked
        session.status = 'magic_link_clicked'
        session.magic_link_clicked_at = timezone.now()
        session.email_verified = True
        session.save()
        
        SessionEvent.objects.create(
            session=session,
            event_type='magic_link_clicked',
        )
        
        # Check if user already exists
        user = User.objects.filter(email=session.email).first()
        
        if not user:
            # Create user
            username = session.email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=session.email,
                password=None,  # No password, magic link only
            )
            
            SessionEvent.objects.create(
                session=session,
                event_type='account_created',
                event_data={'user_id': str(user.id)},
            )
        
        # Create tenant if needed
        tenant = None
        membership = TenantMembership.objects.filter(user=user, is_active=True).first()
        
        if membership:
            tenant = membership.tenant
        else:
            tenant = Tenant.objects.create(
                name=f"{user.email}'s Workspace",
                slug=f"workspace-{secrets.token_hex(4)}",
                owner=user,
            )
            TenantMembership.objects.create(
                tenant=tenant,
                user=user,
                role='owner',
                is_active=True,
            )
        
        session.status = 'account_created'
        session.converted_to_user = user
        session.converted_to_tenant = tenant
        session.save()
        
        return {
            'success': True,
            'user_id': str(user.id),
            'tenant_id': str(tenant.id),
            'email': session.email,
            'initial_request': session.initial_request,
            'session_token': session.session_token,
        }
    
    @staticmethod
    def create_project_from_session(session_token: str) -> Dict:
        """
        Create the project based on the user's initial request.
        """
        from apps.projects.models import Project
        
        session = LandingSession.objects.get(session_token=session_token)
        
        if not session.converted_to_user or not session.converted_to_tenant:
            return {'success': False, 'error': 'Account not created yet'}
        
        # Create project
        project = Project.objects.create(
            tenant=session.converted_to_tenant,
            name=f"Project from request",
            description=session.initial_request,
            created_by=session.converted_to_user,
        )
        
        session.status = 'project_created'
        session.converted_to_project = project
        session.save()
        
        SessionEvent.objects.create(
            session=session,
            event_type='project_created',
            event_data={'project_id': str(project.id)},
        )
        
        return {
            'success': True,
            'project_id': str(project.id),
        }
    
    @staticmethod
    def log_build_progress(session_token: str, progress: int, message: str = ''):
        """Log build progress."""
        session = LandingSession.objects.get(session_token=session_token)
        
        if session.status != 'building':
            session.status = 'building'
            session.save()
            
            SessionEvent.objects.create(
                session=session,
                event_type='build_started',
            )
        
        SessionEvent.objects.create(
            session=session,
            event_type='build_progress',
            event_data={'progress': progress, 'message': message},
        )
    
    @staticmethod
    def mark_deployed(session_token: str):
        """Mark session as deployed."""
        session = LandingSession.objects.get(session_token=session_token)
        
        session.status = 'deployed'
        session.completed_at = timezone.now()
        session.save()
        
        SessionEvent.objects.create(
            session=session,
            event_type='deploy_completed',
        )


class DailyReportService:
    """
    Service for generating daily reports.
    """
    
    @staticmethod
    def generate_report(report_date: date = None) -> DailyReport:
        """
        Generate daily report for Faibric Admin.
        """
        from apps.insights.models import CustomerInput, AdminFix, CustomerHealth
        from apps.platform_admin.models import AdCampaign, AdCampaignDaily
        
        if report_date is None:
            report_date = (timezone.now() - timedelta(days=1)).date()
        
        next_date = report_date + timedelta(days=1)
        
        # ============================================
        # Landing/Onboarding Metrics
        # ============================================
        
        sessions = LandingSession.objects.filter(created_at__date=report_date)
        
        total_visitors = sessions.count()
        total_requests = sessions.filter(status__in=[
            'request_submitted', 'email_requested', 'email_provided',
            'magic_link_sent', 'magic_link_clicked', 'account_created',
            'project_created', 'building', 'deployed'
        ]).count()
        
        emails_collected = sessions.filter(email__isnull=False).exclude(email='').count()
        email_changes = sessions.filter(email_change_count__gt=0).count()
        magic_links_sent = sessions.filter(magic_link_sent_at__isnull=False).count()
        magic_links_clicked = sessions.filter(magic_link_clicked_at__isnull=False).count()
        accounts_created = sessions.filter(converted_to_user__isnull=False).count()
        projects_created = sessions.filter(converted_to_project__isnull=False).count()
        
        # Funnel rates
        request_to_email_rate = emails_collected / total_requests if total_requests > 0 else None
        email_to_click_rate = magic_links_clicked / magic_links_sent if magic_links_sent > 0 else None
        click_to_account_rate = accounts_created / magic_links_clicked if magic_links_clicked > 0 else None
        overall_conversion_rate = accounts_created / total_visitors if total_visitors > 0 else None
        
        # ============================================
        # Usage Metrics (from Insights)
        # ============================================
        
        inputs = CustomerInput.objects.filter(created_at__date=report_date)
        total_llm_requests = inputs.count()
        total_tokens = inputs.aggregate(Sum('tokens_output'))['tokens_output__sum'] or 0
        avg_rating = inputs.filter(user_rating__isnull=False).aggregate(Avg('user_rating'))['user_rating__avg']
        issues_flagged = inputs.filter(quality_status__in=['needs_review', 'flagged']).count()
        issues_fixed = AdminFix.objects.filter(created_at__date=report_date).count()
        
        # ============================================
        # Customer Health
        # ============================================
        
        at_risk = CustomerHealth.objects.filter(is_at_risk=True).count()
        healthy = CustomerHealth.objects.filter(is_at_risk=False, health_score__gte=70).count()
        
        # ============================================
        # Google Ads Metrics
        # ============================================
        
        ad_metrics = AdCampaignDaily.objects.filter(
            date=report_date,
            campaign__tenant__isnull=True  # Faibric's own campaigns
        ).aggregate(
            impressions=Sum('impressions'),
            clicks=Sum('clicks'),
            spend=Sum('spend'),
            conversions=Sum('conversions'),
        )
        
        ad_impressions = ad_metrics['impressions'] or 0
        ad_clicks = ad_metrics['clicks'] or 0
        ad_spend = ad_metrics['spend'] or Decimal('0')
        ad_conversions = ad_metrics['conversions'] or 0
        ad_ctr = (ad_clicks / ad_impressions * 100) if ad_impressions > 0 else None
        ad_cpc = (ad_spend / ad_clicks) if ad_clicks > 0 else None
        ad_cpa = (ad_spend / ad_conversions) if ad_conversions > 0 else None
        
        # ============================================
        # Attribution Breakdown
        # ============================================
        
        conversions_by_source = dict(
            sessions.filter(converted_to_user__isnull=False)
            .exclude(utm_source='')
            .values('utm_source')
            .annotate(count=Count('id'))
            .values_list('utm_source', 'count')
        )
        
        conversions_by_campaign = dict(
            sessions.filter(converted_to_user__isnull=False)
            .exclude(utm_campaign='')
            .values('utm_campaign')
            .annotate(count=Count('id'))
            .values_list('utm_campaign', 'count')
        )
        
        # ============================================
        # Top Requests
        # ============================================
        
        top_requests = list(
            sessions.values('initial_request')[:20]
        )
        
        # ============================================
        # All Sessions (detailed log)
        # ============================================
        
        all_sessions = []
        for s in sessions.order_by('-created_at')[:100]:
            events = list(s.events.values('event_type', 'timestamp', 'event_data', 'error_message'))
            all_sessions.append({
                'id': str(s.id),
                'email': s.email,
                'status': s.status,
                'initial_request': s.initial_request[:200],
                'utm_source': s.utm_source,
                'utm_campaign': s.utm_campaign,
                'email_changes': s.email_change_count,
                'previous_emails': s.previous_emails,
                'converted': s.is_converted,
                'events': events,
                'created_at': s.created_at.isoformat(),
            })
        
        # ============================================
        # Create Report
        # ============================================
        
        report, _ = DailyReport.objects.update_or_create(
            date=report_date,
            defaults={
                'total_visitors': total_visitors,
                'total_requests': total_requests,
                'emails_collected': emails_collected,
                'email_changes': email_changes,
                'magic_links_sent': magic_links_sent,
                'magic_links_clicked': magic_links_clicked,
                'accounts_created': accounts_created,
                'projects_created': projects_created,
                'request_to_email_rate': request_to_email_rate,
                'email_to_click_rate': email_to_click_rate,
                'click_to_account_rate': click_to_account_rate,
                'overall_conversion_rate': overall_conversion_rate,
                'total_llm_requests': total_llm_requests,
                'total_tokens_used': total_tokens,
                'average_rating': avg_rating,
                'issues_flagged': issues_flagged,
                'issues_fixed': issues_fixed,
                'at_risk_customers': at_risk,
                'healthy_customers': healthy,
                'ad_impressions': ad_impressions,
                'ad_clicks': ad_clicks,
                'ad_spend': ad_spend,
                'ad_conversions': ad_conversions,
                'ad_ctr': ad_ctr,
                'ad_cpc': ad_cpc,
                'ad_cpa': ad_cpa,
                'conversions_by_source': conversions_by_source,
                'conversions_by_campaign': conversions_by_campaign,
                'top_requests': top_requests,
                'all_sessions': all_sessions,
            }
        )
        
        return report
    
    @staticmethod
    def send_daily_report_email(report: DailyReport) -> bool:
        """
        Send daily report email to Faibric Admin.
        """
        from apps.messaging.email_service import EmailService
        
        # Build email
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #1a1a2e; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">
                📊 Faibric Daily Report - {report.date}
            </h1>
            
            <!-- Conversion Funnel -->
            <div style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: white; padding: 24px; border-radius: 12px; margin: 20px 0;">
                <h2 style="margin-top: 0;">🎯 Conversion Funnel</h2>
                <div style="display: flex; justify-content: space-between; text-align: center;">
                    <div>
                        <div style="font-size: 32px; font-weight: bold;">{report.total_visitors}</div>
                        <div style="opacity: 0.8;">Visitors</div>
                    </div>
                    <div style="font-size: 24px; line-height: 60px;">→</div>
                    <div>
                        <div style="font-size: 32px; font-weight: bold;">{report.emails_collected}</div>
                        <div style="opacity: 0.8;">Emails</div>
                    </div>
                    <div style="font-size: 24px; line-height: 60px;">→</div>
                    <div>
                        <div style="font-size: 32px; font-weight: bold;">{report.magic_links_clicked}</div>
                        <div style="opacity: 0.8;">Verified</div>
                    </div>
                    <div style="font-size: 24px; line-height: 60px;">→</div>
                    <div>
                        <div style="font-size: 32px; font-weight: bold;">{report.accounts_created}</div>
                        <div style="opacity: 0.8;">Accounts</div>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 16px; font-size: 18px;">
                    Overall Conversion: <strong>{(report.overall_conversion_rate or 0) * 100:.1f}%</strong>
                </div>
            </div>
            
            <!-- Key Metrics -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0;">
                <div style="background: #f0f9ff; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #0369a1;">{report.total_llm_requests}</div>
                    <div style="color: #666;">LLM Requests</div>
                </div>
                <div style="background: #f0fdf4; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #15803d;">{report.average_rating or 'N/A'}</div>
                    <div style="color: #666;">Avg Rating</div>
                </div>
                <div style="background: #fef2f2; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #dc2626;">{report.issues_flagged}</div>
                    <div style="color: #666;">Issues Flagged</div>
                </div>
                <div style="background: #fefce8; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #ca8a04;">{report.at_risk_customers}</div>
                    <div style="color: #666;">At-Risk Customers</div>
                </div>
            </div>
            
            <!-- Google Ads -->
            <h2 style="color: #1a1a2e; margin-top: 32px;">📢 Google Ads Performance</h2>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="background: #f5f5f5;">
                    <td style="padding: 12px; border: 1px solid #ddd;"><strong>Impressions</strong></td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{report.ad_impressions:,}</td>
                    <td style="padding: 12px; border: 1px solid #ddd;"><strong>CTR</strong></td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{(report.ad_ctr or 0):.2f}%</td>
                </tr>
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd;"><strong>Clicks</strong></td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{report.ad_clicks:,}</td>
                    <td style="padding: 12px; border: 1px solid #ddd;"><strong>CPC</strong></td>
                    <td style="padding: 12px; border: 1px solid #ddd;">${report.ad_cpc or 0:.2f}</td>
                </tr>
                <tr style="background: #f5f5f5;">
                    <td style="padding: 12px; border: 1px solid #ddd;"><strong>Spend</strong></td>
                    <td style="padding: 12px; border: 1px solid #ddd;">${report.ad_spend:.2f}</td>
                    <td style="padding: 12px; border: 1px solid #ddd;"><strong>CPA</strong></td>
                    <td style="padding: 12px; border: 1px solid #ddd;">${report.ad_cpa or 0:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd;"><strong>Conversions</strong></td>
                    <td style="padding: 12px; border: 1px solid #ddd;" colspan="3">{report.ad_conversions}</td>
                </tr>
            </table>
            
            <!-- Email Changes Alert -->
            {'<div style="background: #fef3c7; border: 1px solid #f59e0b; padding: 16px; border-radius: 8px; margin: 20px 0;"><strong>⚠️ Email Changes:</strong> ' + str(report.email_changes) + ' users changed their email after initial submission.</div>' if report.email_changes > 0 else ''}
            
            <!-- Attribution -->
            <h2 style="color: #1a1a2e; margin-top: 32px;">📈 Attribution</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h3>By Source</h3>
                    <ul>
                        {''.join([f'<li><strong>{k}:</strong> {v} conversions</li>' for k, v in (report.conversions_by_source or {}).items()]) or '<li>No attributed conversions</li>'}
                    </ul>
                </div>
                <div>
                    <h3>By Campaign</h3>
                    <ul>
                        {''.join([f'<li><strong>{k}:</strong> {v} conversions</li>' for k, v in (report.conversions_by_campaign or {}).items()]) or '<li>No campaign data</li>'}
                    </ul>
                </div>
            </div>
            
            <!-- Top Requests -->
            <h2 style="color: #1a1a2e; margin-top: 32px;">💡 What People Are Asking For</h2>
            <ol style="background: #f9fafb; padding: 20px 40px; border-radius: 8px;">
                {''.join([f'<li style="margin: 8px 0;">{r.get("initial_request", "")[:100]}...</li>' for r in (report.top_requests or [])[:10]]) or '<li>No requests today</li>'}
            </ol>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;">
            
            <p style="text-align: center; color: #666;">
                <a href="{settings.FRONTEND_URL}/admin/reports/{report.id}" style="color: #3b82f6;">
                    View Full Report in Dashboard →
                </a>
            </p>
        </div>
        """
        
        try:
            email_service = EmailService()
            
            # Get admin emails
            admin_emails = list(
                User.objects.filter(
                    is_staff=True,
                    is_active=True
                ).values_list('email', flat=True)
            )
            
            if not admin_emails:
                admin_emails = [settings.DEFAULT_FROM_EMAIL]
            
            for email in admin_emails:
                email_service.send_email(
                    to_email=email,
                    subject=f"📊 Faibric Daily Report - {report.date}",
                    html_content=html_content,
                    from_email='reports@faibric.com',
                )
            
            report.report_sent = True
            report.report_sent_at = timezone.now()
            report.save()
            
            # Create notification
            AdminNotification.objects.create(
                notification_type='daily_report',
                title=f"Daily Report - {report.date}",
                message=f"Report generated with {report.total_visitors} visitors and {report.accounts_created} new accounts.",
                daily_report=report,
                email_sent=True,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            return False

