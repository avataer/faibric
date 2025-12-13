"""
Faibric Admin Dashboard - Clean interface for monitoring users, costs, and analytics.
"""
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F
from datetime import datetime, timedelta
from decimal import Decimal


def generate_admin_dashboard_html():
    """Generate the admin dashboard HTML."""
    from apps.onboarding.models import LandingSession
    from apps.analytics.models import APIUsageLog, UserSummary
    from apps.code_library.models import LibraryItem
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    
    # Today's stats
    today_sessions = LandingSession.objects.filter(created_at__date=today).count()
    today_deployed = LandingSession.objects.filter(created_at__date=today, status='deployed').count()
    
    # Get cost stats
    today_costs = APIUsageLog.objects.filter(
        created_at__date=today
    ).aggregate(
        total_cost=Sum('cost'),
        total_calls=Count('id'),
        avg_cost=Avg('cost'),
    )
    
    total_costs = APIUsageLog.objects.aggregate(
        total_cost=Sum('cost'),
        total_calls=Count('id'),
    )
    
    # Library stats
    library_items = LibraryItem.objects.count()
    library_reuses = LibraryItem.objects.aggregate(total=Sum('usage_count'))['total'] or 0
    
    # Top components by usage
    top_components = list(
        LibraryItem.objects.filter(usage_count__gt=0)
        .order_by('-usage_count')
        .values('name', 'usage_count', 'quality_score')[:10]
    )
    
    # Recent sessions with details
    recent_sessions = list(
        LandingSession.objects.select_related('converted_to_project')
        .order_by('-created_at')[:20]
        .values(
            'session_token', 'initial_request', 'status', 
            'created_at', 'email'
        )
    )
    
    # Cost by model
    cost_by_model = list(
        APIUsageLog.objects.values('model')
        .annotate(
            total_cost=Sum('cost'),
            call_count=Count('id'),
            avg_tokens=Avg(F('input_tokens') + F('output_tokens')),
        )
        .order_by('-total_cost')
    )
    
    # Build the HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faibric Admin Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', sans-serif;
        }}
        body {{
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
            padding: 24px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            padding-bottom: 16px;
            border-bottom: 1px solid #334155;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header .date {{
            color: #94a3b8;
            font-size: 14px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .stat-card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }}
        .stat-card.highlight {{
            background: linear-gradient(135deg, #1e40af, #7c3aed);
            border: none;
        }}
        .stat-label {{
            font-size: 13px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .stat-card.highlight .stat-label {{
            color: rgba(255,255,255,0.7);
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: #f1f5f9;
        }}
        .stat-card.highlight .stat-value {{
            color: #fff;
        }}
        .stat-subtext {{
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }}
        .section {{
            margin-bottom: 32px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #f1f5f9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }}
        th {{
            background: #0f172a;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #94a3b8;
        }}
        td {{
            font-size: 14px;
        }}
        tr:hover {{
            background: #334155;
        }}
        .status {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }}
        .status.deployed {{
            background: #065f46;
            color: #6ee7b7;
        }}
        .status.building {{
            background: #1e40af;
            color: #93c5fd;
        }}
        .status.pending {{
            background: #78350f;
            color: #fcd34d;
        }}
        .cost {{
            font-family: 'SF Mono', monospace;
            color: #4ade80;
        }}
        .truncate {{
            max-width: 300px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .two-cols {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}
        @media (max-width: 900px) {{
            .two-cols {{
                grid-template-columns: 1fr;
            }}
        }}
        .refresh-btn {{
            background: #3b82f6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
        }}
        .refresh-btn:hover {{
            background: #2563eb;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Faibric Admin Dashboard</h1>
        <div>
            <span class="date">{today.strftime('%B %d, %Y')} • {timezone.now().strftime('%H:%M')}</span>
            <button class="refresh-btn" onclick="location.reload()">Refresh</button>
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card highlight">
            <div class="stat-label">Users Today</div>
            <div class="stat-value">{today_sessions}</div>
            <div class="stat-subtext">{today_deployed} deployed</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">API Calls Today</div>
            <div class="stat-value">{today_costs['total_calls'] or 0}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Cost Today</div>
            <div class="stat-value cost">${today_costs['total_cost'] or Decimal('0'):.4f}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Cost (All Time)</div>
            <div class="stat-value cost">${total_costs['total_cost'] or Decimal('0'):.2f}</div>
            <div class="stat-subtext">{total_costs['total_calls'] or 0} total calls</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Library Components</div>
            <div class="stat-value">{library_items}</div>
            <div class="stat-subtext">{library_reuses} reuses</div>
        </div>
    </div>
    
    <div class="two-cols">
        <div class="section">
            <h2 class="section-title">Recent Sessions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Request</th>
                        <th>Status</th>
                        <th>Email</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td class="truncate">{s['initial_request'][:50] if s['initial_request'] else 'N/A'}...</td>
                        <td><span class="status {s['status']}">{s['status']}</span></td>
                        <td>{s['email'] or '-'}</td>
                        <td>{s['created_at'].strftime('%H:%M') if s['created_at'] else '-'}</td>
                    </tr>
                    ''' for s in recent_sessions)}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">Cost by Model</h2>
            <table>
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Calls</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{m['model'][:30]}</td>
                        <td>{m['call_count']}</td>
                        <td class="cost">${m['total_cost'] or 0:.4f}</td>
                    </tr>
                    ''' for m in cost_by_model) if cost_by_model else '<tr><td colspan="3">No data yet</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Top Reused Components</h2>
        <table>
            <thead>
                <tr>
                    <th>Component</th>
                    <th>Reuses</th>
                    <th>Quality Score</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f'''
                <tr>
                    <td>{c['name'][:60]}</td>
                    <td>{c['usage_count']}</td>
                    <td>{c['quality_score']:.0f}</td>
                </tr>
                ''' for c in top_components) if top_components else '<tr><td colspan="3">No components reused yet - build some projects first!</td></tr>'}
            </tbody>
        </table>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""
    return html
