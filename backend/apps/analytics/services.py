"""
Analytics Services for Faibric Admin Dashboard.
Handles: Health scores, alerts, reports, cohorts, AI insights.
"""
import logging
import anthropic
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q
from django.core.mail import send_mail
from datetime import datetime, timedelta
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


# =============================================================================
# ORIGINAL ANALYTICS SERVICES (for views.py compatibility)
# =============================================================================

FUNNEL_TEMPLATES = {
    'signup': {
        'name': 'User Signup Funnel',
        'steps': ['page_view', 'email_entered', 'email_verified', 'account_created'],
    },
    'conversion': {
        'name': 'Conversion Funnel', 
        'steps': ['page_view', 'request_submitted', 'build_started', 'deployed'],
    },
}


class AnalyticsProxy:
    """Proxy for forwarding events to external analytics services."""
    
    def __init__(self, config=None):
        self.config = config
    
    def track(self, event_name: str, properties: dict = None, user_id: str = None):
        """Track an event."""
        pass
    
    def identify(self, user_id: str, traits: dict = None):
        """Identify a user."""
        pass


class FunnelAnalyzer:
    """Analyze conversion funnels."""
    
    def __init__(self, funnel=None):
        self.funnel = funnel
    
    def analyze(self, start_date=None, end_date=None):
        """Analyze funnel performance."""
        return {
            'conversion_rate': 0,
            'steps': [],
        }
    
    def get_drop_offs(self):
        """Get drop-off points."""
        return []

ADMIN_EMAIL = 'amptiness@icloud.com'


# =============================================================================
# ACTIVITY FEED SERVICE
# =============================================================================

class ActivityFeedService:
    """Manage real-time activity feed."""
    
    @staticmethod
    def log_activity(
        activity_type: str,
        title: str,
        description: str = '',
        session_token: str = '',
        email: str = '',
        severity: str = 'info',
        related_data: dict = None
    ):
        """Log an activity to the feed."""
        from .models_dashboard import ActivityFeed
        
        try:
            ActivityFeed.objects.create(
                activity_type=activity_type,
                title=title,
                description=description,
                session_token=session_token,
                email=email,
                severity=severity,
                related_data=related_data or {},
            )
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
    
    @staticmethod
    def get_recent_activity(limit: int = 50):
        """Get recent activity feed items."""
        from .models_dashboard import ActivityFeed
        return list(ActivityFeed.objects.all()[:limit])
    
    @staticmethod
    def get_live_stats():
        """Get live statistics for dashboard."""
        from apps.onboarding.models import LandingSession
        from .models import APIUsageLog
        from .models_dashboard import BuildQueueItem
        
        now = timezone.now()
        five_min_ago = now - timedelta(minutes=5)
        today = now.date()
        
        return {
            'active_now': LandingSession.objects.filter(
                last_activity_at__gte=five_min_ago
            ).count(),
            'building_now': LandingSession.objects.filter(
                status='building'
            ).count(),
            'queue_depth': BuildQueueItem.objects.filter(
                status='queued'
            ).count(),
            'today_sessions': LandingSession.objects.filter(
                created_at__date=today
            ).count(),
            'today_deploys': LandingSession.objects.filter(
                created_at__date=today,
                status='deployed'
            ).count(),
            'today_cost': APIUsageLog.objects.filter(
                created_at__date=today
            ).aggregate(total=Sum('cost'))['total'] or Decimal('0'),
        }


# =============================================================================
# HEALTH SCORE SERVICE
# =============================================================================

class HealthScoreService:
    """Calculate and manage customer health scores."""
    
    @staticmethod
    def calculate_for_session(session_token: str):
        """Calculate health score for a session."""
        from apps.onboarding.models import LandingSession, SessionEvent, UserInput
        from .models import APIUsageLog
        from .models_dashboard import CustomerHealthScore
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
        except LandingSession.DoesNotExist:
            return None
        
        # Get or create health score
        health, created = CustomerHealthScore.objects.get_or_create(
            session_token=session_token,
            defaults={'email': session.email or ''}
        )
        
        # Calculate components
        events = SessionEvent.objects.filter(session=session)
        inputs = UserInput.objects.filter(session=session)
        
        # Build success rate
        build_events = events.filter(event_type__in=['build_completed', 'build_failed', 'deploy_completed'])
        success_count = events.filter(event_type__in=['build_completed', 'deploy_completed']).count()
        fail_count = events.filter(event_type='build_failed').count()
        total_builds = success_count + fail_count
        
        if total_builds > 0:
            health.build_success_rate = (success_count / total_builds) * 100
        else:
            health.build_success_rate = 50  # Neutral if no builds
        
        # Engagement score (based on time and modifications)
        health.total_time_minutes = session.total_time_seconds / 60 if session.total_time_seconds else 0
        modification_count = inputs.filter(input_type='follow_up').count()
        health.total_modifications = modification_count
        
        # Engagement = time spent + modifications (capped at 100)
        time_score = min(50, health.total_time_minutes * 5)  # 10 min = 50 points
        mod_score = min(50, modification_count * 10)  # 5 mods = 50 points
        health.engagement_score = time_score + mod_score
        
        # Return rate (did they come back?)
        seven_days_ago = timezone.now() - timedelta(days=7)
        if session.created_at < seven_days_ago:
            recent_activity = session.last_activity_at and session.last_activity_at > seven_days_ago
            health.return_rate = 100 if recent_activity else 0
        else:
            health.return_rate = 50  # Too early to tell
        
        # Feature adoption (used modifications, multiple builds)
        features_used = 0
        if modification_count > 0:
            features_used += 1
        if total_builds > 1:
            features_used += 1
        if session.status == 'deployed':
            features_used += 1
        health.feature_adoption = min(100, features_used * 33)
        
        # Satisfaction (inverse of error count)
        error_count = events.filter(event_type='error').count()
        health.satisfaction_score = max(0, 100 - (error_count * 20))
        
        # Update metadata
        health.total_builds = total_builds
        health.successful_builds = success_count
        health.email = session.email or health.email
        health.last_active_at = session.last_activity_at
        
        # Calculate overall
        health.calculate_score()
        
        return health
    
    @staticmethod
    def calculate_all():
        """Recalculate health scores for all active sessions."""
        from apps.onboarding.models import LandingSession
        
        recent = timezone.now() - timedelta(days=30)
        sessions = LandingSession.objects.filter(
            created_at__gte=recent
        ).values_list('session_token', flat=True)
        
        count = 0
        for token in sessions:
            HealthScoreService.calculate_for_session(token)
            count += 1
        
        logger.info(f"Calculated health scores for {count} sessions")
        return count
    
    @staticmethod
    def get_at_risk_users(limit: int = 20):
        """Get users at risk of churning."""
        from .models_dashboard import CustomerHealthScore
        
        return list(
            CustomerHealthScore.objects.filter(
                health_status__in=['at_risk', 'churning']
            ).order_by('overall_score')[:limit]
        )


# =============================================================================
# FUNNEL SERVICE
# =============================================================================

class FunnelService:
    """Calculate and track conversion funnel."""
    
    @staticmethod
    def calculate_daily_funnel(date=None):
        """Calculate funnel metrics for a day."""
        from apps.onboarding.models import LandingSession
        from .models_dashboard import FunnelSnapshot
        
        if date is None:
            date = timezone.now().date()
        
        # Get or create snapshot
        snapshot, created = FunnelSnapshot.objects.get_or_create(date=date)
        
        # Query sessions for this day
        sessions = LandingSession.objects.filter(created_at__date=date)
        
        snapshot.visitors = sessions.count()
        snapshot.requests_submitted = sessions.exclude(initial_request='').count()
        snapshot.emails_provided = sessions.exclude(email='').count()
        snapshot.emails_verified = sessions.filter(email_verified=True).count()
        snapshot.builds_started = sessions.filter(
            status__in=['building', 'deployed', 'project_created']
        ).count()
        snapshot.builds_completed = sessions.filter(
            status__in=['deployed', 'project_created']
        ).count()
        snapshot.deployed = sessions.filter(status='deployed').count()
        
        # Calculate by source
        by_source = {}
        sources = sessions.values('utm_source').annotate(
            count=Count('id'),
            deployed=Count('id', filter=Q(status='deployed'))
        )
        for s in sources:
            source = s['utm_source'] or 'direct'
            by_source[source] = {
                'visitors': s['count'],
                'deployed': s['deployed'],
            }
        snapshot.by_source = by_source
        
        snapshot.calculate_rates()
        
        return snapshot
    
    @staticmethod
    def get_funnel_data(days: int = 7):
        """Get funnel data for visualization."""
        from .models_dashboard import FunnelSnapshot
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        snapshots = list(
            FunnelSnapshot.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')
        )
        
        # Aggregate
        totals = {
            'visitors': sum(s.visitors for s in snapshots),
            'requests': sum(s.requests_submitted for s in snapshots),
            'emails': sum(s.emails_provided for s in snapshots),
            'verified': sum(s.emails_verified for s in snapshots),
            'builds': sum(s.builds_started for s in snapshots),
            'completed': sum(s.builds_completed for s in snapshots),
            'deployed': sum(s.deployed for s in snapshots),
        }
        
        return {
            'daily': snapshots,
            'totals': totals,
            'period_days': days,
        }


# =============================================================================
# COHORT SERVICE
# =============================================================================

class CohortService:
    """Manage cohort analysis."""
    
    @staticmethod
    def calculate_weekly_cohorts():
        """Calculate weekly cohorts for retention analysis."""
        from apps.onboarding.models import LandingSession
        from .models_dashboard import Cohort
        
        # Get sessions from last 12 weeks
        twelve_weeks_ago = timezone.now() - timedelta(weeks=12)
        sessions = LandingSession.objects.filter(
            created_at__gte=twelve_weeks_ago
        ).values('session_token', 'created_at', 'last_activity_at', 'status')
        
        # Group by week
        cohorts_data = {}
        for s in sessions:
            week_start = s['created_at'].date() - timedelta(days=s['created_at'].weekday())
            week_key = week_start.strftime('%Y-W%W')
            
            if week_key not in cohorts_data:
                cohorts_data[week_key] = {
                    'start': week_start,
                    'users': [],
                }
            cohorts_data[week_key]['users'].append(s)
        
        # Create/update cohort records
        for week_key, data in cohorts_data.items():
            cohort, _ = Cohort.objects.update_or_create(
                period_key=week_key,
                defaults={
                    'period_type': 'weekly',
                    'period_start': data['start'],
                    'period_end': data['start'] + timedelta(days=6),
                    'initial_users': len(data['users']),
                    'converted_to_deploy': len([u for u in data['users'] if u['status'] == 'deployed']),
                }
            )
            
            if cohort.initial_users > 0:
                cohort.conversion_rate = cohort.converted_to_deploy / cohort.initial_users
            
            # Calculate retention (simplified: active in week N)
            retention = {0: 100}  # Week 0 is 100%
            for week_offset in range(1, 8):
                week_cutoff = data['start'] + timedelta(weeks=week_offset)
                if week_cutoff > timezone.now().date():
                    break
                
                active_count = len([
                    u for u in data['users']
                    if u['last_activity_at'] and u['last_activity_at'].date() >= week_cutoff
                ])
                retention[week_offset] = round((active_count / len(data['users'])) * 100, 1)
            
            cohort.retention_data = retention
            cohort.save()
        
        return len(cohorts_data)


# =============================================================================
# ALERT SERVICE
# =============================================================================

class AlertService:
    """Manage alerts and notifications."""
    
    @staticmethod
    def check_all_rules():
        """Check all alert rules and trigger if needed."""
        from .models_dashboard import AlertRule
        
        rules = AlertRule.objects.filter(is_active=True)
        triggered = 0
        
        for rule in rules:
            if AlertService.check_rule(rule):
                triggered += 1
        
        return triggered
    
    @staticmethod
    def check_rule(rule) -> bool:
        """Check a single alert rule."""
        from .models import APIUsageLog
        from .models_dashboard import Alert, BuildQueueItem
        from apps.onboarding.models import LandingSession, SessionEvent
        
        if not rule.can_trigger():
            return False
        
        # Get current value based on metric type
        current_value = None
        window_start = timezone.now() - timedelta(minutes=rule.time_window_minutes)
        today = timezone.now().date()
        
        if rule.metric == 'error_rate':
            total = SessionEvent.objects.filter(
                timestamp__gte=window_start
            ).count()
            errors = SessionEvent.objects.filter(
                timestamp__gte=window_start,
                event_type='error'
            ).count()
            current_value = (errors / total * 100) if total > 0 else 0
            
        elif rule.metric == 'daily_cost':
            current_value = float(
                APIUsageLog.objects.filter(
                    created_at__date=today
                ).aggregate(total=Sum('cost'))['total'] or 0
            )
            
        elif rule.metric == 'build_queue':
            current_value = BuildQueueItem.objects.filter(
                status='queued'
            ).count()
            
        elif rule.metric == 'build_time':
            avg = BuildQueueItem.objects.filter(
                completed_at__gte=window_start,
                build_time_seconds__isnull=False
            ).aggregate(avg=Avg('build_time_seconds'))['avg']
            current_value = avg or 0
        
        if current_value is None:
            return False
        
        # Check condition
        should_trigger = False
        if rule.condition == 'gt' and current_value > rule.threshold:
            should_trigger = True
        elif rule.condition == 'lt' and current_value < rule.threshold:
            should_trigger = True
        elif rule.condition == 'eq' and current_value == rule.threshold:
            should_trigger = True
        
        if should_trigger:
            AlertService.trigger_alert(rule, current_value)
            return True
        
        return False
    
    @staticmethod
    def trigger_alert(rule, current_value: float):
        """Trigger an alert."""
        from .models_dashboard import Alert, AdminConfig
        
        # Determine severity
        severity = 'warning'
        if rule.metric == 'daily_cost':
            config = AdminConfig.get_config()
            if current_value >= float(config.daily_cost_critical):
                severity = 'critical'
        elif rule.metric == 'error_rate':
            config = AdminConfig.get_config()
            if current_value >= config.error_rate_critical * 100:
                severity = 'critical'
        
        # Create alert
        alert = Alert.objects.create(
            rule=rule,
            severity=severity,
            title=f"{rule.name} Alert",
            message=f"{rule.metric} is {current_value:.2f}, threshold is {rule.threshold}",
            current_value=current_value,
            threshold_value=rule.threshold,
        )
        
        # Update rule
        rule.last_triggered_at = timezone.now()
        rule.trigger_count += 1
        rule.save()
        
        # Log to activity feed
        ActivityFeedService.log_activity(
            activity_type='alert',
            title=alert.title,
            description=alert.message,
            severity='error' if severity == 'critical' else 'warning',
        )
        
        # Send notifications
        if rule.notify_email:
            AlertService.send_email_alert(alert)
        
        return alert
    
    @staticmethod
    def send_email_alert(alert):
        """Send email notification for alert."""
        from .models_dashboard import AdminConfig
        
        config = AdminConfig.get_config()
        
        try:
            send_mail(
                subject=f"[Faibric Alert] {alert.title}",
                message=f"""
Alert: {alert.title}
Severity: {alert.severity.upper()}

{alert.message}

Current Value: {alert.current_value}
Threshold: {alert.threshold_value}

Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

---
Faibric Admin Dashboard
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[config.admin_email],
                fail_silently=True,
            )
            alert.email_sent = True
            alert.save()
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")


# =============================================================================
# COST SERVICE
# =============================================================================

class CostService:
    """Cost tracking and forecasting."""
    
    @staticmethod
    def get_daily_costs(days: int = 30):
        """Get daily cost breakdown."""
        from .models import APIUsageLog
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        costs = list(
            APIUsageLog.objects.filter(
                created_at__date__gte=start_date
            ).values('created_at__date').annotate(
                total_cost=Sum('cost'),
                total_calls=Count('id'),
                input_tokens=Sum('input_tokens'),
                output_tokens=Sum('output_tokens'),
            ).order_by('created_at__date')
        )
        
        return costs
    
    @staticmethod
    def forecast_cost(days: int = 7):
        """Forecast cost for next N days based on trends."""
        daily_costs = CostService.get_daily_costs(days=14)
        
        if len(daily_costs) < 3:
            return None
        
        # Simple average-based forecast
        recent_avg = sum(
            float(d['total_cost'] or 0) for d in daily_costs[-7:]
        ) / min(7, len(daily_costs))
        
        return {
            'daily_avg': Decimal(str(round(recent_avg, 4))),
            'forecast_7d': Decimal(str(round(recent_avg * 7, 2))),
            'forecast_30d': Decimal(str(round(recent_avg * 30, 2))),
        }
    
    @staticmethod
    def get_cost_by_model():
        """Get cost breakdown by model."""
        from .models import APIUsageLog
        
        return list(
            APIUsageLog.objects.values('model').annotate(
                total_cost=Sum('cost'),
                total_calls=Count('id'),
                avg_cost=Avg('cost'),
            ).order_by('-total_cost')
        )
    
    @staticmethod
    def get_cost_per_user():
        """Get cost per user/session."""
        from .models import APIUsageLog
        
        return list(
            APIUsageLog.objects.exclude(session_token__isnull=True).values(
                'session_token'
            ).annotate(
                total_cost=Sum('cost'),
                total_calls=Count('id'),
            ).order_by('-total_cost')[:50]
        )


# =============================================================================
# AI SUMMARY SERVICE
# =============================================================================

class AISummaryService:
    """Generate AI-powered summaries and insights."""
    
    CHEAP_MODEL = "claude-3-5-haiku-20241022"
    
    @staticmethod
    def generate_daily_summary(date=None):
        """Generate AI summary for a day."""
        from apps.onboarding.models import LandingSession
        from .models import APIUsageLog
        from .models_dashboard import GeneratedReport, FunnelSnapshot, AdminConfig
        
        if date is None:
            date = timezone.now().date() - timedelta(days=1)  # Yesterday
        
        # Gather data
        sessions = LandingSession.objects.filter(created_at__date=date)
        costs = APIUsageLog.objects.filter(created_at__date=date)
        
        data = {
            'date': str(date),
            'total_users': sessions.count(),
            'deployed': sessions.filter(status='deployed').count(),
            'failed': sessions.filter(status='failed').count(),
            'total_cost': float(costs.aggregate(total=Sum('cost'))['total'] or 0),
            'total_api_calls': costs.count(),
        }
        
        # Get funnel data
        try:
            funnel = FunnelSnapshot.objects.get(date=date)
            data['conversion_rate'] = funnel.overall_rate
        except FunnelSnapshot.DoesNotExist:
            data['conversion_rate'] = 0
        
        # Generate AI summary
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            prompt = f"""Analyze this daily data for the Faibric AI website builder platform and provide:
1. A brief 2-3 sentence summary of the day
2. 3-5 key insights or patterns
3. 2-3 actionable recommendations

Data:
{json.dumps(data, indent=2)}

Format your response as JSON:
{{
    "summary": "...",
    "insights": ["insight1", "insight2", ...],
    "recommendations": ["rec1", "rec2", ...]
}}"""
            
            response = client.messages.create(
                model=AISummaryService.CHEAP_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result_text = response.content[0].text
            
            # Parse JSON
            try:
                result = json.loads(result_text)
            except:
                result = {
                    "summary": result_text[:500],
                    "insights": [],
                    "recommendations": [],
                }
            
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            result = {
                "summary": f"Daily summary for {date}: {data['total_users']} users, {data['deployed']} deploys, ${data['total_cost']:.2f} cost.",
                "insights": [],
                "recommendations": [],
            }
        
        # Create report
        report = GeneratedReport.objects.create(
            report_type='daily',
            period_start=date,
            period_end=date,
            title=f"Daily Summary: {date}",
            ai_summary=result.get('summary', ''),
            ai_insights=result.get('insights', []),
            ai_recommendations=result.get('recommendations', []),
            data_snapshot=data,
            html_content=AISummaryService._generate_report_html(data, result),
        )
        
        return report
    
    @staticmethod
    def _generate_report_html(data: dict, ai_result: dict) -> str:
        """Generate HTML content for report."""
        return f"""
<html>
<body style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #1e293b;">Faibric Daily Report</h1>
    <p style="color: #64748b;">{data['date']}</p>
    
    <h2 style="color: #3b82f6;">Summary</h2>
    <p>{ai_result.get('summary', 'No summary available.')}</p>
    
    <h2 style="color: #3b82f6;">Key Metrics</h2>
    <table style="width: 100%; border-collapse: collapse;">
        <tr style="background: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #e2e8f0;">Total Users</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>{data['total_users']}</strong></td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">Deployed</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>{data['deployed']}</strong></td>
        </tr>
        <tr style="background: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #e2e8f0;">Failed</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>{data['failed']}</strong></td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">API Cost</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>${data['total_cost']:.2f}</strong></td>
        </tr>
        <tr style="background: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #e2e8f0;">API Calls</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>{data['total_api_calls']}</strong></td>
        </tr>
    </table>
    
    <h2 style="color: #3b82f6;">Insights</h2>
    <ul>
        {''.join(f'<li>{insight}</li>' for insight in ai_result.get('insights', [])) or '<li>No insights available</li>'}
    </ul>
    
    <h2 style="color: #3b82f6;">Recommendations</h2>
    <ul>
        {''.join(f'<li>{rec}</li>' for rec in ai_result.get('recommendations', [])) or '<li>No recommendations</li>'}
    </ul>
    
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
    <p style="color: #94a3b8; font-size: 12px;">Faibric Admin Dashboard</p>
</body>
</html>
"""
    
    @staticmethod
    def send_daily_report_email(report):
        """Send daily report via email."""
        from .models_dashboard import AdminConfig
        
        config = AdminConfig.get_config()
        
        try:
            send_mail(
                subject=f"[Faibric] {report.title}",
                message=report.ai_summary,
                html_message=report.html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[config.admin_email],
                fail_silently=False,
            )
            report.sent_to = [config.admin_email]
            report.sent_at = timezone.now()
            report.save()
            logger.info(f"Daily report sent to {config.admin_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            return False


# =============================================================================
# COMPONENT GAP ANALYSIS SERVICE
# =============================================================================

class ComponentGapService:
    """Analyze gaps in component library."""
    
    @staticmethod
    def analyze_gaps():
        """Detect gaps in component library based on user requests."""
        from apps.onboarding.models import LandingSession
        from apps.code_library.models import LibraryItem
        from .models_dashboard import ComponentGapAnalysis
        
        # Get recent requests
        recent = timezone.now() - timedelta(days=30)
        requests = LandingSession.objects.filter(
            created_at__gte=recent
        ).values_list('initial_request', flat=True)
        
        # Extract common keywords/types
        type_counts = {}
        for req in requests:
            if not req:
                continue
            req_lower = req.lower()
            
            # Detect types
            types_to_check = [
                'restaurant', 'portfolio', 'blog', 'e-commerce', 'landing',
                'dashboard', 'booking', 'saas', 'agency', 'real estate',
                'fitness', 'medical', 'education', 'travel', 'music',
                'photography', 'lawyer', 'accounting', 'consulting',
            ]
            
            for t in types_to_check:
                if t in req_lower:
                    type_counts[t] = type_counts.get(t, 0) + 1
        
        # Check which types have library coverage
        library_keywords = set()
        for item in LibraryItem.objects.filter(is_active=True):
            for kw in (item.keywords or []):
                library_keywords.add(kw.lower())
        
        # Find gaps
        gaps_found = 0
        for type_name, count in type_counts.items():
            if count >= 3 and type_name not in library_keywords:
                # This is a gap
                gap, created = ComponentGapAnalysis.objects.update_or_create(
                    gap_type=type_name,
                    defaults={
                        'gap_description': f"Users requested '{type_name}' websites {count} times but no library component exists.",
                        'request_count': count,
                        'priority_score': count * 10,
                        'priority': 'high' if count >= 10 else 'medium' if count >= 5 else 'low',
                    }
                )
                if created:
                    gaps_found += 1
        
        logger.info(f"Gap analysis found {gaps_found} new gaps")
        return gaps_found


# =============================================================================
# PROMPT ANALYTICS SERVICE
# =============================================================================

class PromptAnalyticsService:
    """Track and analyze AI prompts."""
    
    @staticmethod
    def log_prompt(
        session_token: str,
        user_prompt: str,
        detected_type: str = '',
        was_successful: bool = True,
        generation_time: float = 0,
        tokens_used: int = 0,
        cost: Decimal = Decimal('0'),
        used_library: bool = False,
        error_message: str = ''
    ):
        """Log a prompt for analytics."""
        from .models_dashboard import PromptAnalytics
        
        # Extract keywords
        words = user_prompt.lower().split()
        keywords = [w for w in words if len(w) > 4][:20]
        
        # Detect industry
        industry_keywords = {
            'restaurant': ['restaurant', 'food', 'menu', 'cafe', 'dining'],
            'finance': ['stocks', 'trading', 'finance', 'investment', 'crypto'],
            'healthcare': ['medical', 'doctor', 'health', 'clinic', 'hospital'],
            'beauty': ['salon', 'beauty', 'hair', 'spa', 'makeup'],
            'technology': ['tech', 'saas', 'software', 'app', 'startup'],
            'education': ['school', 'education', 'course', 'training', 'learn'],
            'real_estate': ['real estate', 'property', 'housing', 'apartment'],
        }
        
        detected_industry = ''
        for industry, kws in industry_keywords.items():
            if any(kw in user_prompt.lower() for kw in kws):
                detected_industry = industry
                break
        
        PromptAnalytics.objects.create(
            session_token=session_token,
            user_prompt=user_prompt,
            prompt_length=len(user_prompt),
            detected_type=detected_type,
            detected_industry=detected_industry,
            keywords=keywords,
            was_successful=was_successful,
            error_message=error_message,
            generation_time_seconds=generation_time,
            tokens_used=tokens_used,
            cost=cost,
            used_library=used_library,
        )
    
    @staticmethod
    def get_prompt_stats():
        """Get prompt analytics stats."""
        from .models_dashboard import PromptAnalytics
        
        total = PromptAnalytics.objects.count()
        successful = PromptAnalytics.objects.filter(was_successful=True).count()
        
        by_type = list(
            PromptAnalytics.objects.values('detected_type').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
        )
        
        by_industry = list(
            PromptAnalytics.objects.exclude(detected_industry='').values(
                'detected_industry'
            ).annotate(count=Count('id')).order_by('-count')[:10]
        )
        
        avg_time = PromptAnalytics.objects.aggregate(
            avg=Avg('generation_time_seconds')
        )['avg'] or 0
        
        library_usage = PromptAnalytics.objects.filter(
            used_library=True
        ).count()
        
        return {
            'total': total,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'by_type': by_type,
            'by_industry': by_industry,
            'avg_generation_time': avg_time,
            'library_usage_rate': (library_usage / total * 100) if total > 0 else 0,
        }


# =============================================================================
# SCHEDULED TASKS
# =============================================================================

def run_daily_tasks():
    """Run all daily scheduled tasks."""
    logger.info("Running daily tasks...")
    
    # Calculate funnel for yesterday
    yesterday = timezone.now().date() - timedelta(days=1)
    FunnelService.calculate_daily_funnel(yesterday)
    
    # Calculate health scores
    HealthScoreService.calculate_all()
    
    # Update cohorts
    CohortService.calculate_weekly_cohorts()
    
    # Analyze component gaps
    ComponentGapService.analyze_gaps()
    
    # Generate and send daily report
    report = AISummaryService.generate_daily_summary()
    AISummaryService.send_daily_report_email(report)
    
    # Check alerts
    AlertService.check_all_rules()
    
    logger.info("Daily tasks completed")


def run_hourly_tasks():
    """Run hourly scheduled tasks."""
    # Check alerts
    AlertService.check_all_rules()
    
    # Update today's funnel
    FunnelService.calculate_daily_funnel()
