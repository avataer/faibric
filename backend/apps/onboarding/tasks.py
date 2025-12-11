"""
Celery tasks for Onboarding.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_and_send_daily_report():
    """
    Generate and send the daily report.
    Run this task every day at a specific time (e.g., 8 AM).
    
    Add to celery beat schedule:
    'generate-daily-report': {
        'task': 'apps.onboarding.tasks.generate_and_send_daily_report',
        'schedule': crontab(hour=8, minute=0),
    },
    """
    from .services import DailyReportService
    
    try:
        # Generate report for yesterday
        report = DailyReportService.generate_report()
        logger.info(f"Generated daily report for {report.date}")
        
        # Send email
        success = DailyReportService.send_daily_report_email(report)
        
        if success:
            logger.info(f"Sent daily report email for {report.date}")
        else:
            logger.error(f"Failed to send daily report email for {report.date}")
        
        return {
            'success': True,
            'report_id': str(report.id),
            'email_sent': success,
        }
        
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        return {
            'success': False,
            'error': str(e),
        }


@shared_task
def cleanup_abandoned_sessions():
    """
    Mark old sessions as abandoned and clean up.
    Run daily.
    """
    from .models import LandingSession, SessionEvent
    
    # Mark sessions older than 24 hours without conversion as abandoned
    cutoff = timezone.now() - timedelta(hours=24)
    
    abandoned = LandingSession.objects.filter(
        created_at__lt=cutoff,
        converted_to_user__isnull=True,
        status__in=['request_submitted', 'email_requested', 'email_provided', 'magic_link_sent']
    )
    
    count = abandoned.count()
    
    for session in abandoned:
        session.status = 'abandoned'
        session.save()
        
        SessionEvent.objects.create(
            session=session,
            event_type='session_timeout',
        )
    
    logger.info(f"Marked {count} sessions as abandoned")
    
    return {'abandoned_count': count}


@shared_task
def check_at_risk_customers():
    """
    Check for at-risk customers and notify admin.
    Run every few hours.
    """
    from apps.insights.models import CustomerHealth
    from .models import AdminNotification
    
    at_risk = CustomerHealth.objects.filter(
        is_at_risk=True,
        health_score__lt=30  # Very at risk
    ).select_related('tenant')[:10]
    
    for health in at_risk:
        # Check if we already notified about this customer recently
        recent_notification = AdminNotification.objects.filter(
            notification_type='at_risk_customer',
            data__tenant_id=str(health.tenant_id),
            created_at__gte=timezone.now() - timedelta(days=1),
        ).exists()
        
        if not recent_notification:
            AdminNotification.objects.create(
                notification_type='at_risk_customer',
                title=f"⚠️ At-Risk Customer: {health.tenant.name}",
                message=f"Health score: {health.health_score}. Reasons: {', '.join(health.risk_reasons)}",
                data={
                    'tenant_id': str(health.tenant_id),
                    'tenant_name': health.tenant.name,
                    'health_score': health.health_score,
                    'risk_reasons': health.risk_reasons,
                },
            )
    
    return {'at_risk_count': at_risk.count()}


@shared_task
def sync_google_ads_metrics():
    """
    Sync Google Ads metrics for reporting.
    Run daily.
    """
    from apps.platform_admin.models import AdCampaign
    from apps.platform_admin.services import GoogleAdsService
    
    # Sync Faibric's campaigns
    campaigns = AdCampaign.objects.filter(
        tenant__isnull=True,
        status='active'
    )
    
    service = GoogleAdsService()
    synced = 0
    
    for campaign in campaigns:
        try:
            service.sync_campaign_metrics(campaign)
            service.sync_daily_metrics(campaign)
            synced += 1
        except Exception as e:
            logger.error(f"Error syncing campaign {campaign.id}: {e}")
    
    return {'synced_campaigns': synced}







