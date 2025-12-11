"""
Report generation for marketing analysis.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.utils import timezone

from .models import (
    Competitor,
    CompetitorChange,
    Keyword,
    KeywordRanking,
    MarketingConfig,
    MarketingReport,
    ReportTemplate,
)
from .analysis import AIAnalyzer, InsightGenerator

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates marketing analysis reports.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.ai_analyzer = AIAnalyzer()
    
    def _get_period_dates(self, frequency: str) -> tuple:
        """
        Get the period start and end dates based on frequency.
        """
        today = date.today()
        
        if frequency == 'daily':
            start = today - timedelta(days=1)
            end = today
        elif frequency == 'weekly':
            start = today - timedelta(days=7)
            end = today
        elif frequency == 'biweekly':
            start = today - timedelta(days=14)
            end = today
        else:  # monthly
            start = today - timedelta(days=30)
            end = today
        
        return start, end
    
    def _gather_competitor_data(
        self,
        period_start: date,
        period_end: date
    ) -> dict:
        """
        Gather competitor analysis data for the period.
        """
        from apps.tenants.models import Tenant
        
        tenant = Tenant.objects.get(id=self.tenant_id)
        competitors = Competitor.objects.filter(tenant=tenant, is_active=True)
        
        data = {
            'competitors': [],
            'total_changes': 0,
            'by_change_type': {},
        }
        
        for competitor in competitors:
            changes = CompetitorChange.objects.filter(
                competitor=competitor,
                created_at__date__gte=period_start,
                created_at__date__lte=period_end
            ).order_by('-importance_score')
            
            comp_data = {
                'name': competitor.name,
                'domain': competitor.domain,
                'changes': [
                    {
                        'type': c.change_type,
                        'title': c.title,
                        'description': c.description,
                        'importance': c.importance_score,
                        'ai_summary': c.ai_summary,
                        'page_url': c.page_url,
                    }
                    for c in changes
                ],
                'change_count': changes.count(),
            }
            
            data['competitors'].append(comp_data)
            data['total_changes'] += changes.count()
            
            # Count by type
            for change in changes:
                if change.change_type not in data['by_change_type']:
                    data['by_change_type'][change.change_type] = 0
                data['by_change_type'][change.change_type] += 1
        
        return data
    
    def _gather_keyword_data(
        self,
        period_start: date,
        period_end: date
    ) -> dict:
        """
        Gather keyword ranking data for the period.
        """
        from apps.tenants.models import Tenant
        
        tenant = Tenant.objects.get(id=self.tenant_id)
        keywords = Keyword.objects.filter(tenant=tenant, is_active=True)
        
        data = {
            'keywords': [],
            'improved': 0,
            'declined': 0,
            'unchanged': 0,
        }
        
        for keyword in keywords:
            # Get current and previous rankings
            latest = KeywordRanking.objects.filter(
                keyword=keyword,
                domain=keyword.your_domain,
                created_at__date__lte=period_end
            ).order_by('-created_at').first()
            
            previous = KeywordRanking.objects.filter(
                keyword=keyword,
                domain=keyword.your_domain,
                created_at__date__lt=period_start
            ).order_by('-created_at').first()
            
            keyword_data = {
                'keyword': keyword.keyword,
                'your_domain': keyword.your_domain,
                'current_position': latest.position if latest else None,
                'previous_position': previous.position if previous else None,
                'change': 0,
                'competitors': [],
            }
            
            if latest and previous and latest.position and previous.position:
                keyword_data['change'] = previous.position - latest.position
                if keyword_data['change'] > 0:
                    data['improved'] += 1
                elif keyword_data['change'] < 0:
                    data['declined'] += 1
                else:
                    data['unchanged'] += 1
            elif latest and latest.position:
                data['unchanged'] += 1
            
            # Get competitor rankings
            if keyword.track_competitors:
                competitors = Competitor.objects.filter(
                    tenant=tenant,
                    is_active=True
                )
                
                for competitor in competitors:
                    comp_ranking = KeywordRanking.objects.filter(
                        keyword=keyword,
                        domain=competitor.domain,
                        created_at__date__lte=period_end
                    ).order_by('-created_at').first()
                    
                    if comp_ranking:
                        keyword_data['competitors'].append({
                            'name': competitor.name,
                            'domain': competitor.domain,
                            'position': comp_ranking.position,
                        })
            
            data['keywords'].append(keyword_data)
        
        return data
    
    def _generate_recommendations(
        self,
        competitor_data: dict,
        keyword_data: dict
    ) -> list:
        """
        Generate recommendations based on the data.
        """
        recommendations = []
        
        # Pricing change recommendations
        pricing_changes = competitor_data['by_change_type'].get('pricing_change', 0)
        if pricing_changes > 0:
            recommendations.append({
                'type': 'pricing',
                'priority': 'high',
                'title': 'Review Pricing Strategy',
                'description': f'{pricing_changes} competitors updated pricing. Consider reviewing your pricing structure.',
            })
        
        # Feature gap recommendations
        new_features = competitor_data['by_change_type'].get('new_feature', 0)
        if new_features >= 3:
            recommendations.append({
                'type': 'product',
                'priority': 'high',
                'title': 'Feature Gap Analysis Needed',
                'description': f'{new_features} new competitor features detected. Evaluate for potential roadmap additions.',
            })
        
        # Content recommendations
        blog_posts = competitor_data['by_change_type'].get('new_blog_post', 0)
        if blog_posts >= 5:
            recommendations.append({
                'type': 'content',
                'priority': 'medium',
                'title': 'Increase Content Output',
                'description': f'Competitors published {blog_posts} new blog posts. Consider ramping up content marketing.',
            })
        
        # SEO recommendations
        if keyword_data['declined'] > keyword_data['improved']:
            recommendations.append({
                'type': 'seo',
                'priority': 'high',
                'title': 'SEO Attention Required',
                'description': f'{keyword_data["declined"]} keywords declined in rankings. Review SEO strategy.',
            })
        
        # Top 10 opportunities
        not_ranked = [k for k in keyword_data['keywords'] if k['current_position'] is None]
        if len(not_ranked) > 0:
            recommendations.append({
                'type': 'seo',
                'priority': 'medium',
                'title': 'Ranking Opportunities',
                'description': f'{len(not_ranked)} keywords not in top 100. Focus on content and backlinks for these terms.',
            })
        
        return recommendations
    
    def _render_html_report(
        self,
        report: MarketingReport,
        template: Optional[ReportTemplate] = None
    ) -> str:
        """
        Render the report as HTML.
        """
        if template and template.html_template:
            # Use custom template
            tpl = Template(template.html_template)
        else:
            # Use default template
            tpl = Template(self._get_default_template())
        
        context = Context({
            'report': report,
            'title': report.title,
            'period_start': report.period_start,
            'period_end': report.period_end,
            'executive_summary': report.ai_executive_summary or report.summary,
            'competitor_analysis': report.competitor_analysis,
            'keyword_rankings': report.keyword_rankings,
            'changes_detected': report.changes_detected,
            'recommendations': report.recommendations,
            'insights': report.ai_key_insights,
            'action_items': report.ai_action_items,
            'primary_color': template.primary_color if template else '#3B82F6',
            'logo_url': template.logo_url if template else '',
        })
        
        return tpl.render(context)
    
    def _get_default_template(self) -> str:
        """
        Get the default HTML report template.
        """
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1a1a2e;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f8fafc;
        }
        .header {
            background: linear-gradient(135deg, {{ primary_color }} 0%, #1e40af 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 24px;
        }
        .header .period {
            opacity: 0.9;
            font-size: 14px;
        }
        .section {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: {{ primary_color }};
            font-size: 18px;
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }
        .summary {
            background: #f1f5f9;
            padding: 20px;
            border-radius: 8px;
            white-space: pre-wrap;
        }
        .change-item {
            padding: 12px;
            border-left: 4px solid {{ primary_color }};
            background: #f8fafc;
            margin-bottom: 10px;
            border-radius: 0 8px 8px 0;
        }
        .change-item .type {
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
        }
        .change-item .title {
            font-weight: 600;
            color: #1e293b;
        }
        .recommendation {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
        }
        .recommendation.high {
            background: #fef2f2;
            border-left: 4px solid #ef4444;
        }
        .recommendation.medium {
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
        }
        .recommendation.low {
            background: #f0fdf4;
            border-left: 4px solid #22c55e;
        }
        .keyword-table {
            width: 100%;
            border-collapse: collapse;
        }
        .keyword-table th, .keyword-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        .keyword-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #475569;
        }
        .trend-up {
            color: #22c55e;
        }
        .trend-down {
            color: #ef4444;
        }
        .footer {
            text-align: center;
            color: #64748b;
            font-size: 14px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="header">
        {% if logo_url %}<img src="{{ logo_url }}" alt="Logo" style="height: 40px; margin-bottom: 10px;">{% endif %}
        <h1>📊 {{ title }}</h1>
        <div class="period">{{ period_start }} - {{ period_end }}</div>
    </div>
    
    <div class="section">
        <h2>Executive Summary</h2>
        <div class="summary">{{ executive_summary }}</div>
    </div>
    
    {% if competitor_analysis.competitors %}
    <div class="section">
        <h2>Competitor Activity</h2>
        <p>{{ competitor_analysis.total_changes }} changes detected across {{ competitor_analysis.competitors|length }} competitors.</p>
        
        {% for comp in competitor_analysis.competitors %}
        {% if comp.changes %}
        <h3>{{ comp.name }} ({{ comp.domain }})</h3>
        {% for change in comp.changes %}
        <div class="change-item">
            <div class="type">{{ change.type }}</div>
            <div class="title">{{ change.title }}</div>
            {% if change.description %}<div>{{ change.description }}</div>{% endif %}
        </div>
        {% endfor %}
        {% endif %}
        {% endfor %}
    </div>
    {% endif %}
    
    {% if keyword_rankings.keywords %}
    <div class="section">
        <h2>Keyword Rankings</h2>
        <p>{{ keyword_rankings.improved }} improved | {{ keyword_rankings.declined }} declined | {{ keyword_rankings.unchanged }} unchanged</p>
        
        <table class="keyword-table">
            <thead>
                <tr>
                    <th>Keyword</th>
                    <th>Position</th>
                    <th>Change</th>
                </tr>
            </thead>
            <tbody>
                {% for kw in keyword_rankings.keywords %}
                <tr>
                    <td>{{ kw.keyword }}</td>
                    <td>{% if kw.current_position %}#{{ kw.current_position }}{% else %}Not ranked{% endif %}</td>
                    <td>
                        {% if kw.change > 0 %}<span class="trend-up">↑{{ kw.change }}</span>
                        {% elif kw.change < 0 %}<span class="trend-down">↓{{ kw.change|abs }}</span>
                        {% else %}-{% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}
    
    {% if recommendations %}
    <div class="section">
        <h2>Recommendations</h2>
        {% for rec in recommendations %}
        <div class="recommendation {{ rec.priority }}">
            <strong>{{ rec.title }}</strong>
            <p>{{ rec.description }}</p>
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="footer">
        This report was automatically generated by Faibric Marketing Analysis.
    </div>
</body>
</html>
"""
    
    def generate_report(
        self,
        report_type: str = 'scheduled',
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> MarketingReport:
        """
        Generate a marketing analysis report.
        """
        from apps.tenants.models import Tenant
        
        tenant = Tenant.objects.get(id=self.tenant_id)
        
        # Get config
        try:
            config = MarketingConfig.objects.get(tenant=tenant)
        except MarketingConfig.DoesNotExist:
            config = MarketingConfig.objects.create(tenant=tenant)
        
        # Determine period
        if not period_start or not period_end:
            period_start, period_end = self._get_period_dates(config.report_frequency)
        
        # Create report record
        report = MarketingReport.objects.create(
            tenant=tenant,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            title=f"Marketing Analysis Report - {period_start.strftime('%b %d')} to {period_end.strftime('%b %d, %Y')}",
            status='generating',
        )
        
        try:
            # Gather data
            competitor_data = self._gather_competitor_data(period_start, period_end)
            keyword_data = self._gather_keyword_data(period_start, period_end)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(competitor_data, keyword_data)
            
            # Get insights
            insight_gen = InsightGenerator(self.tenant_id)
            competitor_insights = insight_gen.get_competitor_insights()
            ranking_insights = insight_gen.get_ranking_insights()
            
            # Update report
            report.competitor_analysis = competitor_data
            report.keyword_rankings = keyword_data
            report.recommendations = recommendations
            report.ai_key_insights = competitor_insights + ranking_insights
            
            # Generate summary
            report.summary = self._generate_summary(competitor_data, keyword_data)
            
            # Render HTML
            template = ReportTemplate.objects.filter(
                tenant=tenant,
                is_default=True,
                is_active=True
            ).first()
            
            report.html_content = self._render_html_report(report, template)
            report.status = 'generated'
            report.save()
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            report.status = 'failed'
            report.error_message = str(e)
            report.save()
            raise
        
        return report
    
    def _generate_summary(
        self,
        competitor_data: dict,
        keyword_data: dict
    ) -> str:
        """
        Generate a text summary of the report.
        """
        lines = []
        
        lines.append(f"Tracked {len(competitor_data['competitors'])} competitors with {competitor_data['total_changes']} changes detected.")
        
        if competitor_data['by_change_type']:
            type_summary = ", ".join([
                f"{count} {ctype.replace('_', ' ')}"
                for ctype, count in competitor_data['by_change_type'].items()
            ])
            lines.append(f"Changes: {type_summary}.")
        
        lines.append(f"\nKeyword rankings: {keyword_data['improved']} improved, {keyword_data['declined']} declined.")
        
        return "\n".join(lines)


class ReportDelivery:
    """
    Handles delivery of marketing reports via email.
    """
    
    def __init__(self, report: MarketingReport):
        self.report = report
    
    def _get_recipients(self) -> list:
        """
        Get list of email recipients.
        """
        recipients = []
        
        try:
            config = MarketingConfig.objects.get(tenant=self.report.tenant)
            
            # Primary recipient
            if config.report_email:
                recipients.append(config.report_email)
            else:
                recipients.append(self.report.tenant.owner.email)
            
            # Additional recipients
            recipients.extend(config.additional_recipients or [])
            
        except MarketingConfig.DoesNotExist:
            recipients.append(self.report.tenant.owner.email)
        
        return list(set(recipients))  # Remove duplicates
    
    def send_email(self) -> bool:
        """
        Send the report via email.
        """
        recipients = self._get_recipients()
        
        if not recipients:
            logger.warning(f"No recipients for report {self.report.id}")
            return False
        
        try:
            self.report.status = 'sending'
            self.report.save(update_fields=['status'])
            
            # Create email
            subject = self.report.title
            
            # Plain text version
            text_content = f"""
{self.report.title}
{'=' * len(self.report.title)}

Period: {self.report.period_start} to {self.report.period_end}

{self.report.summary}

View the full report online or check the HTML attachment.

---
This report was automatically generated by Faibric Marketing Analysis.
"""
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients,
            )
            
            # Attach HTML version
            if self.report.html_content:
                msg.attach_alternative(self.report.html_content, "text/html")
            
            msg.send()
            
            # Update report status
            self.report.status = 'sent'
            self.report.sent_to = recipients
            self.report.sent_at = timezone.now()
            self.report.save()
            
            logger.info(f"Report {self.report.id} sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending report {self.report.id}: {e}")
            self.report.status = 'failed'
            self.report.error_message = str(e)
            self.report.save()
            return False


def generate_and_send_report(tenant_id: str) -> MarketingReport:
    """
    Generate and send a marketing report.
    Convenience function for Celery tasks.
    """
    generator = ReportGenerator(tenant_id)
    report = generator.generate_report()
    
    if report.status == 'generated':
        delivery = ReportDelivery(report)
        delivery.send_email()
    
    return report






