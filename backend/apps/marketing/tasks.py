"""
Celery tasks for marketing analysis.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_competitor_task(self, competitor_id: str):
    """
    Scrape a single competitor and detect changes.
    """
    from .models import Competitor
    from .scrapers import scrape_competitor_sync
    
    try:
        competitor = Competitor.objects.get(id=competitor_id)
        results = scrape_competitor_sync(competitor)
        
        logger.info(
            f"Scraped {competitor.name}: {len(results.get('snapshots', []))} snapshots, "
            f"{len(results.get('changes', []))} changes"
        )
        
        return {
            'competitor': str(competitor_id),
            'success': results.get('success', False),
            'snapshots': len(results.get('snapshots', [])),
            'changes': len(results.get('changes', [])),
        }
        
    except Competitor.DoesNotExist:
        logger.error(f"Competitor {competitor_id} not found")
        return {'error': 'Competitor not found'}
    except Exception as e:
        logger.error(f"Error scraping competitor {competitor_id}: {e}")
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def scrape_all_competitors_task(self, tenant_id: str):
    """
    Scrape all active competitors for a tenant.
    """
    from apps.tenants.models import Tenant
    from .models import Competitor
    
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        competitors = Competitor.objects.filter(tenant=tenant, is_active=True)
        
        for competitor in competitors:
            scrape_competitor_task.delay(str(competitor.id))
        
        return {
            'tenant': str(tenant_id),
            'competitors_queued': competitors.count(),
        }
        
    except Tenant.DoesNotExist:
        logger.error(f"Tenant {tenant_id} not found")
        return {'error': 'Tenant not found'}


@shared_task(bind=True, max_retries=3)
def check_keyword_task(self, keyword_id: str):
    """
    Check rankings for a single keyword.
    """
    from .models import Keyword
    from .keyword_tracker import check_keyword_sync
    
    try:
        keyword = Keyword.objects.get(id=keyword_id)
        rankings = check_keyword_sync(keyword)
        
        logger.info(f"Checked keyword '{keyword.keyword}': {len(rankings)} rankings")
        
        return {
            'keyword': str(keyword_id),
            'rankings_created': len(rankings),
        }
        
    except Keyword.DoesNotExist:
        logger.error(f"Keyword {keyword_id} not found")
        return {'error': 'Keyword not found'}
    except Exception as e:
        logger.error(f"Error checking keyword {keyword_id}: {e}")
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def check_all_keywords_task(self, tenant_id: str):
    """
    Check rankings for all active keywords in a tenant.
    """
    from apps.tenants.models import Tenant
    from .models import Keyword
    
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        keywords = Keyword.objects.filter(tenant=tenant, is_active=True)
        
        for keyword in keywords:
            check_keyword_task.delay(str(keyword.id))
        
        return {
            'tenant': str(tenant_id),
            'keywords_queued': keywords.count(),
        }
        
    except Tenant.DoesNotExist:
        logger.error(f"Tenant {tenant_id} not found")
        return {'error': 'Tenant not found'}


@shared_task(bind=True, max_retries=3)
def generate_report_task(self, tenant_id: str, report_type: str = 'scheduled'):
    """
    Generate a marketing report for a tenant.
    """
    from .reports import generate_and_send_report
    
    try:
        report = generate_and_send_report(tenant_id)
        
        logger.info(f"Generated report {report.id} for tenant {tenant_id}: {report.status}")
        
        return {
            'report_id': str(report.id),
            'status': report.status,
            'sent_to': report.sent_to,
        }
        
    except Exception as e:
        logger.error(f"Error generating report for tenant {tenant_id}: {e}")
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def generate_weekly_reports():
    """
    Generate weekly reports for all tenants with marketing enabled.
    This should be scheduled to run weekly (e.g., every Monday morning).
    """
    from apps.tenants.models import Tenant
    from .models import MarketingConfig
    
    configs = MarketingConfig.objects.filter(
        report_enabled=True,
        report_frequency='weekly'
    )
    
    count = 0
    for config in configs:
        # Check if report is due
        if config.next_report_at and config.next_report_at > timezone.now():
            continue
        
        generate_report_task.delay(str(config.tenant_id))
        
        # Update next report time
        config.next_report_at = timezone.now() + timedelta(days=7)
        config.save(update_fields=['next_report_at'])
        
        count += 1
    
    logger.info(f"Queued {count} weekly marketing reports")
    return {'reports_queued': count}


@shared_task
def generate_daily_reports():
    """
    Generate daily reports for tenants that have daily frequency.
    """
    from .models import MarketingConfig
    
    configs = MarketingConfig.objects.filter(
        report_enabled=True,
        report_frequency='daily'
    )
    
    count = 0
    for config in configs:
        if config.next_report_at and config.next_report_at > timezone.now():
            continue
        
        generate_report_task.delay(str(config.tenant_id))
        
        config.next_report_at = timezone.now() + timedelta(days=1)
        config.save(update_fields=['next_report_at'])
        
        count += 1
    
    logger.info(f"Queued {count} daily marketing reports")
    return {'reports_queued': count}


@shared_task
def run_daily_scraping():
    """
    Run daily competitor scraping for all tenants.
    """
    from apps.tenants.models import Tenant
    from .models import Competitor
    
    # Get all tenants with active competitors
    tenant_ids = Competitor.objects.filter(
        is_active=True
    ).values_list('tenant_id', flat=True).distinct()
    
    count = 0
    for tenant_id in tenant_ids:
        scrape_all_competitors_task.delay(str(tenant_id))
        count += 1
    
    logger.info(f"Queued competitor scraping for {count} tenants")
    return {'tenants_queued': count}


@shared_task
def run_weekly_keyword_check():
    """
    Run weekly keyword ranking checks for all tenants.
    """
    from apps.tenants.models import Tenant
    from .models import Keyword
    
    # Get all tenants with active keywords
    tenant_ids = Keyword.objects.filter(
        is_active=True
    ).values_list('tenant_id', flat=True).distinct()
    
    count = 0
    for tenant_id in tenant_ids:
        check_all_keywords_task.delay(str(tenant_id))
        count += 1
    
    logger.info(f"Queued keyword checks for {count} tenants")
    return {'tenants_queued': count}


@shared_task
def ai_analyze_changes_task(competitor_id: str, days: int = 7):
    """
    Run AI analysis on recent changes for a competitor.
    """
    from .models import Competitor, CompetitorChange
    from .analysis import ai_analyze_changes_sync
    
    try:
        competitor = Competitor.objects.get(id=competitor_id)
        since = timezone.now() - timedelta(days=days)
        
        changes = list(CompetitorChange.objects.filter(
            competitor=competitor,
            created_at__gte=since,
            ai_summary=''  # Only analyze changes without AI summary
        ))
        
        if not changes:
            return {'message': 'No changes to analyze'}
        
        result = ai_analyze_changes_sync(changes, competitor)
        
        # Update changes with AI analysis
        for change in changes:
            change.ai_summary = result.get('summary', '')[:2000]
            change.save(update_fields=['ai_summary'])
        
        return {
            'competitor': competitor.name,
            'changes_analyzed': len(changes),
        }
        
    except Competitor.DoesNotExist:
        return {'error': 'Competitor not found'}
    except Exception as e:
        logger.error(f"Error analyzing changes for {competitor_id}: {e}")
        return {'error': str(e)}









