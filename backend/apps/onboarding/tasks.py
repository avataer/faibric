"""
Celery tasks for Onboarding.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def build_app_from_session_task(self, session_token: str):
    """
    Complete flow: Create project -> Generate with AI -> Deploy to Render
    This is triggered after successful email verification or DEV skip.
    """
    from .models import LandingSession, SessionEvent
    from .services import OnboardingService
    from apps.projects.models import Project
    from apps.ai_engine.v2.generator import AIGeneratorV2
    from apps.deployment.tasks import deploy_app_task
    
    try:
        session = LandingSession.objects.get(session_token=session_token)
        
        # Step 1: Create project if not exists
        if not session.converted_to_project:
            logger.info(f"Creating project for session {session_token}")
            
            # Need a user - create anonymous if not exists
            if not session.converted_to_user:
                from django.contrib.auth import get_user_model
                from apps.tenants.models import Tenant, TenantMembership
                import secrets
                
                User = get_user_model()
                
                # Create anonymous user
                username = f"user_{secrets.token_hex(4)}"
                email = session.email or f"{username}@faibric.app"
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=None,
                )
                
                # Create tenant
                tenant = Tenant.objects.create(
                    name=f"{username}'s Workspace",
                    slug=f"ws-{secrets.token_hex(4)}",
                    owner=user,
                )
                TenantMembership.objects.create(
                    tenant=tenant,
                    user=user,
                    role='owner',
                    is_active=True,
                )
                
                session.converted_to_user = user
                session.converted_to_tenant = tenant
                session.save()
            
            # Create project
            project = Project.objects.create(
                tenant=session.converted_to_tenant,
                user=session.converted_to_user,
                name=f"App: {session.initial_request[:50]}",
                description=session.initial_request,
                user_prompt=session.initial_request,
                status='generating',
            )
            
            session.converted_to_project = project
            session.status = 'building'
            session.save()
            
            SessionEvent.objects.create(
                session=session,
                event_type='project_created',
                event_data={'project_id': str(project.id)},
            )
        else:
            project = session.converted_to_project
        
        # Step 2: Generate with AI
        logger.info(f"Generating app for project {project.id}")
        
        SessionEvent.objects.create(
            session=session,
            event_type='build_started',
            event_data={'project_id': str(project.id)},
        )
        
        generator = AIGeneratorV2()
        result = generator.generate_app(
            user_prompt=project.user_prompt or project.description,
            project_id=project.id
        )
        
        # Store the generated code
        if 'frontend' in result:
            components = result['frontend']
        else:
            components = result.get('components', {})
        
        frontend_code = {
            'App.tsx': '',
            'components': {}
        }
        
        for name, code in components.items():
            clean_name = name.replace('components/', '')
            if clean_name == 'App' or clean_name == 'App.tsx':
                frontend_code['App.tsx'] = code
            else:
                frontend_code['components'][clean_name] = code
        
        # If no App.tsx, create one
        if not frontend_code['App.tsx']:
            comp_imports = '\n'.join([f"import {c} from './components/{c}';" for c in frontend_code['components'].keys()])
            comp_uses = '\n        '.join([f"<{c} />" for c in frontend_code['components'].keys()])
            frontend_code['App.tsx'] = f"""import React from 'react';
{comp_imports}

function App() {{
  return (
    <div>
        {comp_uses}
    </div>
  );
}}

export default App;
"""
        
        project.frontend_code = str(frontend_code)
        project.status = 'ready'
        project.save()
        
        SessionEvent.objects.create(
            session=session,
            event_type='build_progress',
            event_data={'progress': 100, 'message': 'Code generated successfully'},
        )
        
        # Step 3: Deploy
        logger.info(f"Deploying project {project.id}")
        deploy_app_task.delay(project.id)
        
        return {
            'success': True,
            'project_id': project.id,
            'session_token': session_token,
        }
        
    except Exception as e:
        logger.error(f"Error building app from session: {e}")
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
            SessionEvent.objects.create(
                session=session,
                event_type='error',
                event_data={'error': str(e)[:500]},
            )
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        
        return {'success': False, 'error': str(e)}


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







