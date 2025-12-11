"""
Dashboard HTML generator for funnel visualization.
"""
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from .models import LandingSession, SessionEvent


def get_funnel_data():
    """Get funnel data for visualization."""
    sessions = LandingSession.objects.all()
    
    total = sessions.count()
    if total == 0:
        return None
    
    with_email = sessions.exclude(email="").count()
    link_sent = sessions.filter(status__in=[
        "magic_link_sent", "magic_link_clicked", 
        "account_created", "project_created", "deployed"
    ]).count()
    link_clicked = sessions.filter(status__in=[
        "magic_link_clicked", "account_created", 
        "project_created", "deployed"
    ]).count()
    accounts = sessions.filter(status__in=[
        "account_created", "project_created", "deployed"
    ]).count()
    deployed = sessions.filter(status="deployed").count()
    
    # Email changes
    email_changes = sessions.filter(email_change_count__gt=0).count()
    
    # By source
    by_source = dict(
        sessions.exclude(utm_source="")
        .values("utm_source")
        .annotate(count=Count("id"))
        .values_list("utm_source", "count")
    )
    
    # By campaign
    by_campaign = dict(
        sessions.exclude(utm_campaign="")
        .values("utm_campaign")
        .annotate(count=Count("id"))
        .values_list("utm_campaign", "count")
    )
    
    return {
        "total": total,
        "with_email": with_email,
        "link_sent": link_sent,
        "link_clicked": link_clicked,
        "accounts": accounts,
        "deployed": deployed,
        "email_changes": email_changes,
        "by_source": by_source,
        "by_campaign": by_campaign,
        "rates": {
            "email": round(with_email / total * 100, 1) if total > 0 else 0,
            "link_sent": round(link_sent / total * 100, 1) if total > 0 else 0,
            "link_clicked": round(link_clicked / total * 100, 1) if total > 0 else 0,
            "accounts": round(accounts / total * 100, 1) if total > 0 else 0,
            "deployed": round(deployed / total * 100, 1) if total > 0 else 0,
            "overall": round(accounts / total * 100, 1) if total > 0 else 0,
        }
    }


def generate_dashboard_html():
    """Generate HTML dashboard for funnel visualization."""
    data = get_funnel_data()
    
    if not data:
        return "<h1>No data yet</h1>"
    
    # Generate source breakdown HTML
    sources_html = ""
    for source, count in sorted(data["by_source"].items(), key=lambda x: -x[1]):
        sources_html += f'<div class="source-item"><span class="source-name">{source}</span><span class="source-count">{count}</span></div>'
    
    # Generate campaign breakdown HTML
    campaigns_html = ""
    for campaign, count in sorted(data["by_campaign"].items(), key=lambda x: -x[1]):
        campaigns_html += f'<div class="campaign-item"><span class="campaign-name">{campaign}</span><span class="campaign-count">{count}</span></div>'
    
    html = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faibric Admin - Conversion Funnel</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 40px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 50px;
        }}
        
        .header h1 {{
            font-size: 42px;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #8892b0;
            font-size: 18px;
        }}
        
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .funnel-container {{
            background: rgba(255,255,255,0.03);
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 40px;
            border: 1px solid rgba(255,255,255,0.08);
            backdrop-filter: blur(10px);
        }}
        
        .funnel {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: relative;
        }}
        
        .funnel-step {{
            text-align: center;
            flex: 1;
            position: relative;
        }}
        
        .funnel-step::after {{
            content: '→';
            position: absolute;
            right: -20px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 30px;
            color: #4a5568;
        }}
        
        .funnel-step:last-child::after {{
            display: none;
        }}
        
        .step-number {{
            font-size: 56px;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1;
        }}
        
        .step-label {{
            font-size: 14px;
            color: #8892b0;
            margin-top: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .step-rate {{
            font-size: 24px;
            color: #48bb78;
            margin-top: 8px;
            font-weight: 600;
        }}
        
        .step-rate.low {{
            color: #f56565;
        }}
        
        .step-rate.medium {{
            color: #ed8936;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
            margin-bottom: 40px;
        }}
        
        .metric-card {{
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        
        .metric-card h3 {{
            font-size: 14px;
            color: #8892b0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
        }}
        
        .metric-value {{
            font-size: 36px;
            font-weight: 700;
            color: #fff;
        }}
        
        .metric-value.highlight {{
            color: #48bb78;
        }}
        
        .metric-value.warning {{
            color: #ed8936;
        }}
        
        .breakdown {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
        }}
        
        .breakdown-card {{
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        
        .breakdown-card h3 {{
            font-size: 16px;
            color: #fff;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .source-item, .campaign-item {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        
        .source-name, .campaign-name {{
            color: #8892b0;
        }}
        
        .source-count, .campaign-count {{
            font-weight: 600;
            color: #fff;
        }}
        
        .alert {{
            background: linear-gradient(135deg, rgba(237, 137, 54, 0.1) 0%, rgba(245, 101, 101, 0.1) 100%);
            border: 1px solid rgba(237, 137, 54, 0.3);
            border-radius: 12px;
            padding: 16px 24px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .alert-icon {{
            font-size: 24px;
        }}
        
        .conversion-bar {{
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            margin-top: 20px;
            overflow: hidden;
        }}
        
        .conversion-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #48bb78 100%);
            border-radius: 4px;
            transition: width 0.5s ease;
        }}
        
        .timestamp {{
            text-align: center;
            color: #4a5568;
            font-size: 14px;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🚀 Faibric Conversion Funnel</h1>
            <p>Real-time onboarding analytics</p>
        </div>
        
        {"<div class='alert'><span class='alert-icon'>⚠️</span><span>" + str(data["email_changes"]) + " users changed their email after initial submission</span></div>" if data["email_changes"] > 0 else ""}
        
        <div class="funnel-container">
            <div class="funnel">
                <div class="funnel-step">
                    <div class="step-number">{data["total"]}</div>
                    <div class="step-label">Visitors</div>
                    <div class="step-rate">100%</div>
                </div>
                <div class="funnel-step">
                    <div class="step-number">{data["with_email"]}</div>
                    <div class="step-label">Gave Email</div>
                    <div class="step-rate {"low" if data["rates"]["email"] < 50 else "medium" if data["rates"]["email"] < 70 else ""}">{data["rates"]["email"]}%</div>
                </div>
                <div class="funnel-step">
                    <div class="step-number">{data["link_clicked"]}</div>
                    <div class="step-label">Verified</div>
                    <div class="step-rate {"low" if data["rates"]["link_clicked"] < 30 else "medium" if data["rates"]["link_clicked"] < 50 else ""}">{data["rates"]["link_clicked"]}%</div>
                </div>
                <div class="funnel-step">
                    <div class="step-number">{data["accounts"]}</div>
                    <div class="step-label">Accounts</div>
                    <div class="step-rate {"low" if data["rates"]["accounts"] < 20 else "medium" if data["rates"]["accounts"] < 40 else ""}">{data["rates"]["accounts"]}%</div>
                </div>
                <div class="funnel-step">
                    <div class="step-number">{data["deployed"]}</div>
                    <div class="step-label">Deployed</div>
                    <div class="step-rate highlight">{data["rates"]["deployed"]}%</div>
                </div>
            </div>
            
            <div class="conversion-bar">
                <div class="conversion-fill" style="width: {data["rates"]["overall"]}%"></div>
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Overall Conversion</h3>
                <div class="metric-value highlight">{data["rates"]["overall"]}%</div>
            </div>
            <div class="metric-card">
                <h3>Email → Verified</h3>
                <div class="metric-value">{round(data["link_clicked"] / data["with_email"] * 100, 1) if data["with_email"] > 0 else 0}%</div>
            </div>
            <div class="metric-card">
                <h3>Email Changes</h3>
                <div class="metric-value {"warning" if data["email_changes"] > 0 else ""}">{data["email_changes"]}</div>
            </div>
        </div>
        
        <div class="breakdown">
            <div class="breakdown-card">
                <h3>📊 Traffic Sources</h3>
                {sources_html if sources_html else '<div class="source-item"><span class="source-name">No data</span></div>'}
            </div>
            <div class="breakdown-card">
                <h3>🎯 Campaigns</h3>
                {campaigns_html if campaigns_html else '<div class="campaign-item"><span class="campaign-name">No data</span></div>'}
            </div>
        </div>
        
        <div class="timestamp">
            Last updated: {timezone.now().strftime("%B %d, %Y at %I:%M %p")}
        </div>
    </div>
</body>
</html>
'''
    return html






