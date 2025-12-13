"""
Faibric Admin Dashboard - Complete admin interface.
"""
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F
from datetime import datetime, timedelta
from decimal import Decimal
import html
import json


def get_base_styles():
    """Common CSS styles for all pages."""
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', sans-serif;
        }
        body {
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
            padding: 24px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            padding-bottom: 16px;
            border-bottom: 1px solid #334155;
        }
        .header h1 {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header .date {
            color: #94a3b8;
            font-size: 14px;
        }
        .nav {
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
        }
        .nav a {
            color: #94a3b8;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .nav a:hover, .nav a.active {
            background: #1e293b;
            color: #3b82f6;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        .stat-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }
        .stat-card.highlight {
            background: linear-gradient(135deg, #1e40af, #7c3aed);
            border: none;
        }
        .stat-label {
            font-size: 13px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .stat-card.highlight .stat-label {
            color: rgba(255,255,255,0.7);
        }
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            color: #f1f5f9;
        }
        .stat-card.highlight .stat-value {
            color: #fff;
        }
        .stat-subtext {
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }
        .section {
            margin-bottom: 32px;
        }
        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #f1f5f9;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
        }
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }
        th {
            background: #0f172a;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #94a3b8;
        }
        td {
            font-size: 14px;
        }
        tr:hover {
            background: #334155;
        }
        .status {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .status.deployed {
            background: #065f46;
            color: #6ee7b7;
        }
        .status.building {
            background: #1e40af;
            color: #93c5fd;
        }
        .status.pending {
            background: #78350f;
            color: #fcd34d;
        }
        .cost {
            font-family: 'SF Mono', monospace;
            color: #4ade80;
        }
        .truncate {
            max-width: 300px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .two-cols {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        @media (max-width: 900px) {
            .two-cols {
                grid-template-columns: 1fr;
            }
        }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #3b82f6;
            color: white;
        }
        .btn-primary:hover {
            background: #2563eb;
        }
        .btn-secondary {
            background: #334155;
            color: #e2e8f0;
        }
        .btn-secondary:hover {
            background: #475569;
        }
        .component-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        .component-card {
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #334155;
        }
        .component-preview {
            height: 200px;
            background: #0f172a;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            position: relative;
        }
        .component-preview iframe {
            width: 200%;
            height: 200%;
            border: none;
            transform: scale(0.5);
            transform-origin: top left;
            pointer-events: none;
        }
        .component-info {
            padding: 16px;
        }
        .component-name {
            font-weight: 600;
            margin-bottom: 8px;
            color: #f1f5f9;
        }
        .component-meta {
            font-size: 12px;
            color: #94a3b8;
            display: flex;
            gap: 12px;
        }
        .component-actions {
            display: flex;
            gap: 8px;
            padding: 12px 16px;
            border-top: 1px solid #334155;
        }
        .back-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: #94a3b8;
            text-decoration: none;
            margin-bottom: 16px;
        }
        .back-link:hover {
            color: #3b82f6;
        }
        .user-header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 24px;
        }
        .user-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            font-weight: 700;
            color: white;
        }
        .user-info h2 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .user-info p {
            color: #94a3b8;
            font-size: 14px;
        }
        .log-entry {
            padding: 12px 16px;
            border-bottom: 1px solid #334155;
        }
        .log-entry:hover {
            background: #1e293b;
        }
        .log-time {
            font-size: 11px;
            color: #64748b;
            margin-bottom: 4px;
        }
        .log-type {
            font-size: 12px;
            font-weight: 500;
            color: #3b82f6;
            margin-bottom: 4px;
        }
        .log-content {
            font-size: 14px;
            color: #e2e8f0;
        }
        .code-block {
            background: #0f172a;
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            font-family: 'SF Mono', 'Monaco', monospace;
            font-size: 12px;
            color: #a5b4fc;
            margin-top: 16px;
            max-height: 400px;
            overflow-y: auto;
        }
    """


def generate_nav(active='dashboard'):
    """Generate navigation HTML."""
    return f"""
    <div class="nav">
        <a href="/api/analytics/dashboard/" class="{'active' if active == 'dashboard' else ''}">Dashboard</a>
        <a href="/api/analytics/dashboard/users/" class="{'active' if active == 'users' else ''}">Users</a>
        <a href="/api/analytics/dashboard/components/" class="{'active' if active == 'components' else ''}">Components</a>
        <a href="/api/analytics/dashboard/costs/" class="{'active' if active == 'costs' else ''}">Costs</a>
    </div>
    """


def generate_admin_dashboard_html():
    """Generate the main admin dashboard HTML."""
    from apps.onboarding.models import LandingSession
    from apps.analytics.models import APIUsageLog, UserSummary
    from apps.code_library.models import LibraryItem
    
    today = timezone.now().date()
    
    # Today's stats
    today_sessions = LandingSession.objects.filter(created_at__date=today).count()
    today_deployed = LandingSession.objects.filter(created_at__date=today, status='deployed').count()
    total_sessions = LandingSession.objects.count()
    
    # Get cost stats
    today_costs = APIUsageLog.objects.filter(
        created_at__date=today
    ).aggregate(
        total_cost=Sum('cost'),
        total_calls=Count('id'),
    )
    
    total_costs = APIUsageLog.objects.aggregate(
        total_cost=Sum('cost'),
        total_calls=Count('id'),
    )
    
    # Library stats
    library_items = LibraryItem.objects.count()
    library_reuses = LibraryItem.objects.aggregate(total=Sum('usage_count'))['total'] or 0
    
    # Recent sessions with details
    recent_sessions = list(
        LandingSession.objects.select_related('converted_to_project')
        .order_by('-created_at')[:15]
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
        )
        .order_by('-total_cost')
    )
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faibric Admin Dashboard</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    <div class="header">
        <h1>Faibric Admin</h1>
        <div>
            <span class="date">{today.strftime('%B %d, %Y')} - {timezone.now().strftime('%H:%M')}</span>
            <button class="btn btn-primary" onclick="location.reload()" style="margin-left: 12px;">Refresh</button>
        </div>
    </div>
    
    {generate_nav('dashboard')}
    
    <div class="stats-grid">
        <div class="stat-card highlight">
            <div class="stat-label">Users Today</div>
            <div class="stat-value">{today_sessions}</div>
            <div class="stat-subtext">{today_deployed} deployed / {total_sessions} total</div>
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
            <div class="stat-label">Total Cost</div>
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
            <h2 class="section-title">Recent Users (Click to View Details)</h2>
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
                    {''.join(f"""
                    <tr onclick="window.location='/api/analytics/dashboard/user/{s['session_token']}'" style="cursor:pointer">
                        <td class="truncate">{html.escape(s['initial_request'][:50] if s['initial_request'] else 'N/A')}...</td>
                        <td><span class="status {s['status']}">{s['status']}</span></td>
                        <td>{s['email'] or '-'}</td>
                        <td>{s['created_at'].strftime('%H:%M') if s['created_at'] else '-'}</td>
                    </tr>
                    """ for s in recent_sessions)}
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
                    {''.join(f"""
                    <tr>
                        <td>{m['model'][:35] if m['model'] else 'Unknown'}</td>
                        <td>{m['call_count']}</td>
                        <td class="cost">${m['total_cost'] or 0:.4f}</td>
                    </tr>
                    """ for m in cost_by_model) if cost_by_model else '<tr><td colspan="3">No API calls yet</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""
    return html_content


def generate_users_list_html():
    """Generate the users list page."""
    from apps.onboarding.models import LandingSession
    from apps.analytics.models import APIUsageLog
    
    # Get all sessions with their costs
    sessions = list(
        LandingSession.objects.order_by('-created_at')[:100]
        .values(
            'session_token', 'initial_request', 'status', 
            'created_at', 'email', 'total_inputs'
        )
    )
    
    # Get cost per session
    session_costs = {}
    for s in sessions:
        cost_data = APIUsageLog.objects.filter(
            session_token=s['session_token']
        ).aggregate(
            total_cost=Sum('cost'),
            total_calls=Count('id'),
        )
        session_costs[s['session_token']] = cost_data
    
    today = timezone.now().date()
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Users - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    <div class="header">
        <h1>Faibric Admin - Users</h1>
        <span class="date">{today.strftime('%B %d, %Y')}</span>
    </div>
    
    {generate_nav('users')}
    
    <div class="section">
        <h2 class="section-title">All Users ({len(sessions)})</h2>
        <table>
            <thead>
                <tr>
                    <th>Email</th>
                    <th>Request</th>
                    <th>Status</th>
                    <th>API Calls</th>
                    <th>Cost</th>
                    <th>Date</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f"""
                <tr>
                    <td>{s['email'] or 'Anonymous'}</td>
                    <td class="truncate">{html.escape(s['initial_request'][:40] if s['initial_request'] else '-')}...</td>
                    <td><span class="status {s['status']}">{s['status']}</span></td>
                    <td>{session_costs.get(s['session_token'], {}).get('total_calls') or 0}</td>
                    <td class="cost">${session_costs.get(s['session_token'], {}).get('total_cost') or 0:.4f}</td>
                    <td>{s['created_at'].strftime('%Y-%m-%d %H:%M') if s['created_at'] else '-'}</td>
                    <td><a href="/api/analytics/dashboard/user/{s['session_token']}" class="btn btn-secondary">View</a></td>
                </tr>
                """ for s in sessions)}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    return html_content


def generate_user_detail_html(session_token):
    """Generate the user detail page with all logs."""
    from apps.onboarding.models import LandingSession, SessionEvent, UserInput
    from apps.analytics.models import APIUsageLog
    from apps.projects.models import Project
    
    try:
        session = LandingSession.objects.get(session_token=session_token)
    except LandingSession.DoesNotExist:
        return "<h1>User not found</h1>"
    
    # Get all events
    events = list(SessionEvent.objects.filter(session=session).order_by('timestamp'))
    
    # Get all user inputs
    inputs = list(UserInput.objects.filter(session=session).order_by('timestamp'))
    
    # Get API usage
    api_usage = list(
        APIUsageLog.objects.filter(session_token=session_token)
        .order_by('-created_at')
    )
    
    total_cost = sum(u.cost for u in api_usage)
    total_calls = len(api_usage)
    
    # Get project if exists
    project = session.converted_to_project
    project_url = None
    if project:
        project_url = project.deployment_url if hasattr(project, 'deployment_url') else None
    
    today = timezone.now().date()
    email_initial = (session.email[0].upper() if session.email else 'A')
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User: {session.email or 'Anonymous'} - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    <a href="/api/analytics/dashboard/users/" class="back-link">Back to Users</a>
    
    <div class="user-header">
        <div class="user-avatar">{email_initial}</div>
        <div class="user-info">
            <h2>{session.email or 'Anonymous User'}</h2>
            <p>Session: {session_token[:16]}... | Status: <span class="status {session.status}">{session.status}</span></p>
            <p>Created: {session.created_at.strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Total API Calls</div>
            <div class="stat-value">{total_calls}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Cost</div>
            <div class="stat-value cost">${total_cost:.4f}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Events Logged</div>
            <div class="stat-value">{len(events)}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Messages Sent</div>
            <div class="stat-value">{len(inputs)}</div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Initial Request</h2>
        <div style="background: #1e293b; padding: 20px; border-radius: 12px; font-size: 16px;">
            {html.escape(session.initial_request or 'No request')}
        </div>
    </div>
    
    {f'''
    <div class="section">
        <h2 class="section-title">Deployed Website</h2>
        <div style="background: #1e293b; padding: 20px; border-radius: 12px;">
            <a href="{project_url}" target="_blank" class="btn btn-primary">View Live Site</a>
            <span style="margin-left: 12px; color: #94a3b8;">{project_url}</span>
        </div>
    </div>
    ''' if project_url else ''}
    
    <div class="two-cols">
        <div class="section">
            <h2 class="section-title">All Messages ({len(inputs)})</h2>
            <div style="background: #1e293b; border-radius: 12px; max-height: 500px; overflow-y: auto;">
                {''.join(f"""
                <div class="log-entry">
                    <div class="log-time">{inp.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</div>
                    <div class="log-type">{inp.input_type}</div>
                    <div class="log-content">{html.escape(inp.input_text[:500])}</div>
                </div>
                """ for inp in inputs) if inputs else '<div class="log-entry">No messages yet</div>'}
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">Event Log ({len(events)})</h2>
            <div style="background: #1e293b; border-radius: 12px; max-height: 500px; overflow-y: auto;">
                {''.join(f"""
                <div class="log-entry">
                    <div class="log-time">{ev.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</div>
                    <div class="log-type">{ev.event_type}</div>
                    <div class="log-content">{html.escape(ev.user_input[:200]) if ev.user_input else html.escape(str(ev.event_data)[:200])}</div>
                </div>
                """ for ev in events) if events else '<div class="log-entry">No events yet</div>'}
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">API Usage Log ({len(api_usage)})</h2>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Model</th>
                    <th>Task</th>
                    <th>Tokens</th>
                    <th>Cost</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f"""
                <tr>
                    <td>{u.created_at.strftime('%H:%M:%S')}</td>
                    <td>{u.model[:30]}</td>
                    <td>{u.task_type}</td>
                    <td>{u.input_tokens + u.output_tokens}</td>
                    <td class="cost">${u.cost:.6f}</td>
                </tr>
                """ for u in api_usage[:50]) if api_usage else '<tr><td colspan="5">No API usage yet</td></tr>'}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    return html_content


def generate_components_html():
    """Generate the components gallery page."""
    from apps.code_library.models import LibraryItem, LibraryItemUsage
    from apps.projects.models import Project
    
    # Get all components with their original projects
    components = list(
        LibraryItem.objects.filter(is_active=True)
        .order_by('-usage_count', '-created_at')[:50]
    )
    
    today = timezone.now().date()
    
    # Build component cards
    component_cards = []
    for comp in components:
        # Find original project
        original_project = None
        project_url = None
        first_usage = LibraryItemUsage.objects.filter(item=comp).order_by('created_at').first()
        if first_usage:
            original_project = first_usage.project
            project_url = original_project.deployment_url if hasattr(original_project, 'deployment_url') else None
        
        # Escape code for preview
        code_preview = html.escape(comp.code[:500]) if comp.code else ''
        
        component_cards.append(f"""
        <div class="component-card">
            <div class="component-preview">
                <div style="padding: 20px; font-family: monospace; font-size: 10px; color: #94a3b8; white-space: pre-wrap; overflow: hidden;">
{code_preview}...
                </div>
            </div>
            <div class="component-info">
                <div class="component-name">{html.escape(comp.name[:50])}</div>
                <div class="component-meta">
                    <span>Used {comp.usage_count}x</span>
                    <span>Quality: {comp.quality_score:.0f}</span>
                    <span>{comp.item_type}</span>
                </div>
            </div>
            <div class="component-actions">
                <a href="/api/analytics/dashboard/component/{comp.id}" class="btn btn-secondary">View Code</a>
                {f'<a href="{project_url}" target="_blank" class="btn btn-primary">See Original Site</a>' if project_url else ''}
            </div>
        </div>
        """)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Components - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    <div class="header">
        <h1>Faibric Admin - Component Library</h1>
        <span class="date">{today.strftime('%B %d, %Y')}</span>
    </div>
    
    {generate_nav('components')}
    
    <div class="stats-grid">
        <div class="stat-card highlight">
            <div class="stat-label">Total Components</div>
            <div class="stat-value">{len(components)}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Reuses</div>
            <div class="stat-value">{sum(c.usage_count for c in components)}</div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">All Components (Sorted by Usage)</h2>
        <div class="component-grid">
            {''.join(component_cards) if component_cards else '<p style="color: #94a3b8;">No components yet. Build some projects to populate the library!</p>'}
        </div>
    </div>
</body>
</html>
"""
    return html_content


def generate_component_detail_html(component_id):
    """Generate detailed view for a single component."""
    from apps.code_library.models import LibraryItem, LibraryItemUsage
    
    try:
        comp = LibraryItem.objects.get(id=component_id)
    except LibraryItem.DoesNotExist:
        return "<h1>Component not found</h1>"
    
    # Get all usages
    usages = list(LibraryItemUsage.objects.filter(item=comp).select_related('project').order_by('-created_at')[:20])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(comp.name)} - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    <a href="/api/analytics/dashboard/components/" class="back-link">Back to Components</a>
    
    <div class="header">
        <h1>{html.escape(comp.name)}</h1>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Usage Count</div>
            <div class="stat-value">{comp.usage_count}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Quality Score</div>
            <div class="stat-value">{comp.quality_score:.0f}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Type</div>
            <div class="stat-value" style="font-size: 18px;">{comp.item_type}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Language</div>
            <div class="stat-value" style="font-size: 18px;">{comp.language}</div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Description</h2>
        <div style="background: #1e293b; padding: 20px; border-radius: 12px;">
            {html.escape(comp.description) if comp.description else 'No description'}
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Keywords</h2>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            {''.join(f'<span style="background: #334155; padding: 4px 12px; border-radius: 20px; font-size: 12px;">{html.escape(str(k))}</span>' for k in (comp.keywords or [])) or '<span style="color: #94a3b8;">No keywords</span>'}
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Code</h2>
        <div class="code-block">
            <pre>{html.escape(comp.code)}</pre>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Used In Projects ({len(usages)})</h2>
        <table>
            <thead>
                <tr>
                    <th>Project</th>
                    <th>Usage Type</th>
                    <th>Date</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f"""
                <tr>
                    <td>{html.escape(u.project.name if u.project else 'Unknown')}</td>
                    <td>{u.usage_type}</td>
                    <td>{u.created_at.strftime('%Y-%m-%d')}</td>
                    <td>
                        {f'<a href="{u.project.deployment_url}" target="_blank" class="btn btn-primary">View Site</a>' if u.project and hasattr(u.project, 'deployment_url') and u.project.deployment_url else '-'}
                    </td>
                </tr>
                """ for u in usages) if usages else '<tr><td colspan="4">No usages recorded</td></tr>'}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    return html_content


def generate_costs_html():
    """Generate the costs breakdown page."""
    from apps.analytics.models import APIUsageLog
    from datetime import timedelta
    
    today = timezone.now().date()
    
    # Daily costs for last 7 days
    daily_costs = []
    for i in range(7):
        day = today - timedelta(days=i)
        stats = APIUsageLog.objects.filter(
            created_at__date=day
        ).aggregate(
            total_cost=Sum('cost'),
            total_calls=Count('id'),
            input_tokens=Sum('input_tokens'),
            output_tokens=Sum('output_tokens'),
        )
        daily_costs.append({
            'date': day,
            **stats
        })
    
    # By task type
    by_task = list(
        APIUsageLog.objects.values('task_type')
        .annotate(
            total_cost=Sum('cost'),
            call_count=Count('id'),
        )
        .order_by('-total_cost')
    )
    
    # By model
    by_model = list(
        APIUsageLog.objects.values('model')
        .annotate(
            total_cost=Sum('cost'),
            call_count=Count('id'),
            input_tokens=Sum('input_tokens'),
            output_tokens=Sum('output_tokens'),
        )
        .order_by('-total_cost')
    )
    
    total = APIUsageLog.objects.aggregate(
        total_cost=Sum('cost'),
        total_calls=Count('id'),
    )
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Costs - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    <div class="header">
        <h1>Faibric Admin - Cost Analysis</h1>
        <span class="date">{today.strftime('%B %d, %Y')}</span>
    </div>
    
    {generate_nav('costs')}
    
    <div class="stats-grid">
        <div class="stat-card highlight">
            <div class="stat-label">Total Spend</div>
            <div class="stat-value cost">${total['total_cost'] or 0:.2f}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total API Calls</div>
            <div class="stat-value">{total['total_calls'] or 0}</div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Daily Costs (Last 7 Days)</h2>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>API Calls</th>
                    <th>Input Tokens</th>
                    <th>Output Tokens</th>
                    <th>Cost</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f"""
                <tr>
                    <td>{d['date'].strftime('%Y-%m-%d')}</td>
                    <td>{d['total_calls'] or 0}</td>
                    <td>{d['input_tokens'] or 0:,}</td>
                    <td>{d['output_tokens'] or 0:,}</td>
                    <td class="cost">${d['total_cost'] or 0:.4f}</td>
                </tr>
                """ for d in daily_costs)}
            </tbody>
        </table>
    </div>
    
    <div class="two-cols">
        <div class="section">
            <h2 class="section-title">Cost by Task Type</h2>
            <table>
                <thead>
                    <tr>
                        <th>Task</th>
                        <th>Calls</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f"""
                    <tr>
                        <td>{t['task_type']}</td>
                        <td>{t['call_count']}</td>
                        <td class="cost">${t['total_cost'] or 0:.4f}</td>
                    </tr>
                    """ for t in by_task) if by_task else '<tr><td colspan="3">No data</td></tr>'}
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
                    {''.join(f"""
                    <tr>
                        <td>{m['model'][:30] if m['model'] else 'Unknown'}</td>
                        <td>{m['call_count']}</td>
                        <td class="cost">${m['total_cost'] or 0:.4f}</td>
                    </tr>
                    """ for m in by_model) if by_model else '<tr><td colspan="3">No data</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    return html_content
