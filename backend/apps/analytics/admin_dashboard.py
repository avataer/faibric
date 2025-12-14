"""
Faibric Admin Dashboard - Complete admin interface with all features.
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
        }
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 240px;
            height: 100vh;
            background: #0a0f1a;
            border-right: 1px solid #1e293b;
            padding: 20px 0;
            overflow-y: auto;
        }
        .sidebar-logo {
            padding: 0 20px 20px;
            font-size: 22px;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            border-bottom: 1px solid #1e293b;
            margin-bottom: 20px;
        }
        .sidebar-section {
            padding: 10px 20px 5px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #64748b;
        }
        .sidebar a {
            display: block;
            padding: 10px 20px;
            color: #94a3b8;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.2s;
        }
        .sidebar a:hover {
            background: #1e293b;
            color: #f1f5f9;
        }
        .sidebar a.active {
            background: linear-gradient(90deg, rgba(59,130,246,0.2), transparent);
            color: #3b82f6;
            border-left: 3px solid #3b82f6;
        }
        .main-content {
            margin-left: 240px;
            padding: 24px;
            min-height: 100vh;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }
        .header h1 {
            font-size: 24px;
            font-weight: 600;
            color: #f1f5f9;
        }
        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .live-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(34, 197, 94, 0.1);
            border-radius: 20px;
            font-size: 13px;
            color: #22c55e;
        }
        .live-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
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
        .stat-card.warning {
            background: linear-gradient(135deg, #78350f, #92400e);
            border: none;
        }
        .stat-card.success {
            background: linear-gradient(135deg, #065f46, #047857);
            border: none;
        }
        .stat-label {
            font-size: 12px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .stat-card.highlight .stat-label,
        .stat-card.warning .stat-label,
        .stat-card.success .stat-label {
            color: rgba(255,255,255,0.7);
        }
        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #f1f5f9;
        }
        .stat-card.highlight .stat-value,
        .stat-card.warning .stat-value,
        .stat-card.success .stat-value {
            color: #fff;
        }
        .stat-subtext {
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }
        .stat-trend {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            padding: 2px 8px;
            border-radius: 4px;
            margin-top: 8px;
        }
        .stat-trend.up {
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
        }
        .stat-trend.down {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }
        .section {
            margin-bottom: 24px;
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .section-title {
            font-size: 16px;
            font-weight: 600;
            color: #f1f5f9;
        }
        .card {
            background: #1e293b;
            border-radius: 12px;
            border: 1px solid #334155;
            overflow: hidden;
        }
        .card-header {
            padding: 16px 20px;
            border-bottom: 1px solid #334155;
            font-weight: 600;
        }
        .card-body {
            padding: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }
        th {
            background: #0f172a;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #94a3b8;
        }
        td {
            font-size: 14px;
        }
        tr:hover {
            background: rgba(59, 130, 246, 0.05);
        }
        .status {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 500;
        }
        .status.deployed { background: #065f46; color: #6ee7b7; }
        .status.building { background: #1e40af; color: #93c5fd; }
        .status.pending { background: #78350f; color: #fcd34d; }
        .status.failed { background: #7f1d1d; color: #fca5a5; }
        .status.healthy { background: #065f46; color: #6ee7b7; }
        .status.at_risk { background: #78350f; color: #fcd34d; }
        .status.churning { background: #7f1d1d; color: #fca5a5; }
        .cost { font-family: 'SF Mono', monospace; color: #4ade80; }
        .truncate {
            max-width: 250px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; }
        @media (max-width: 1200px) { .grid-3 { grid-template-columns: 1fr 1fr; } }
        @media (max-width: 900px) { 
            .grid-2, .grid-3 { grid-template-columns: 1fr; }
            .sidebar { display: none; }
            .main-content { margin-left: 0; }
        }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            font-size: 13px;
            transition: all 0.2s;
            cursor: pointer;
            border: none;
        }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-secondary { background: #334155; color: #e2e8f0; }
        .btn-secondary:hover { background: #475569; }
        .btn-danger { background: #dc2626; color: white; }
        .btn-success { background: #16a34a; color: white; }
        .activity-feed {
            max-height: 400px;
            overflow-y: auto;
        }
        .activity-item {
            display: flex;
            gap: 12px;
            padding: 12px 16px;
            border-bottom: 1px solid #334155;
        }
        .activity-item:hover { background: rgba(59, 130, 246, 0.05); }
        .activity-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            flex-shrink: 0;
        }
        .activity-icon.info { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
        .activity-icon.success { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
        .activity-icon.warning { background: rgba(234, 179, 8, 0.2); color: #eab308; }
        .activity-icon.error { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .activity-content { flex: 1; min-width: 0; }
        .activity-title { font-size: 14px; color: #f1f5f9; margin-bottom: 2px; }
        .activity-time { font-size: 11px; color: #64748b; }
        .funnel {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 20px 0;
        }
        .funnel-step {
            flex: 1;
            text-align: center;
            padding: 16px 8px;
            background: linear-gradient(180deg, #1e293b, #0f172a);
            border-radius: 8px;
            position: relative;
        }
        .funnel-step::after {
            content: '→';
            position: absolute;
            right: -16px;
            top: 50%;
            transform: translateY(-50%);
            color: #64748b;
            font-size: 18px;
        }
        .funnel-step:last-child::after { display: none; }
        .funnel-value { font-size: 24px; font-weight: 700; color: #3b82f6; }
        .funnel-label { font-size: 11px; color: #94a3b8; margin-top: 4px; }
        .funnel-rate { font-size: 12px; color: #22c55e; margin-top: 4px; }
        .progress-bar {
            height: 8px;
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            border-radius: 4px;
        }
        .chart-placeholder {
            height: 200px;
            background: linear-gradient(180deg, rgba(59,130,246,0.1), transparent);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
        }
        .alert-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 8px;
        }
        .alert-item.warning { background: rgba(234, 179, 8, 0.1); border-left: 3px solid #eab308; }
        .alert-item.critical { background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; }
        .alert-item.info { background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3b82f6; }
        .health-bar {
            display: flex;
            gap: 2px;
            margin-top: 8px;
        }
        .health-segment {
            flex: 1;
            height: 4px;
            border-radius: 2px;
        }
        .cohort-table {
            overflow-x: auto;
        }
        .cohort-table td {
            text-align: center;
            padding: 8px;
            font-size: 12px;
        }
        .cohort-cell {
            padding: 8px;
            border-radius: 4px;
        }
        .insight-card {
            padding: 16px;
            background: rgba(59, 130, 246, 0.1);
            border-radius: 8px;
            border-left: 3px solid #3b82f6;
            margin-bottom: 12px;
        }
        .insight-title { font-weight: 600; margin-bottom: 4px; }
        .insight-text { font-size: 14px; color: #94a3b8; }
        .component-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }
        .component-card {
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #334155;
        }
        .component-preview {
            height: 140px;
            background: #0f172a;
            padding: 12px;
            font-family: 'SF Mono', monospace;
            font-size: 10px;
            color: #64748b;
            overflow: hidden;
        }
        .component-info { padding: 12px 16px; }
        .component-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
        .component-meta { font-size: 12px; color: #64748b; display: flex; gap: 12px; }
        .back-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: #94a3b8;
            text-decoration: none;
            margin-bottom: 16px;
            font-size: 14px;
        }
        .back-link:hover { color: #3b82f6; }
        .user-header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 24px;
        }
        .user-avatar {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: 700;
            color: white;
        }
        .user-info h2 { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
        .user-info p { color: #94a3b8; font-size: 14px; }
        .log-entry {
            padding: 12px 16px;
            border-bottom: 1px solid #334155;
        }
        .log-time { font-size: 11px; color: #64748b; margin-bottom: 4px; }
        .log-type { font-size: 12px; font-weight: 500; color: #3b82f6; }
        .log-content { font-size: 14px; color: #e2e8f0; }
        .code-block {
            background: #0f172a;
            border-radius: 8px;
            padding: 16px;
            font-family: 'SF Mono', monospace;
            font-size: 12px;
            color: #a5b4fc;
            max-height: 400px;
            overflow: auto;
            white-space: pre-wrap;
        }
        .tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 16px;
            border-bottom: 1px solid #334155;
        }
        .tab {
            padding: 12px 20px;
            color: #94a3b8;
            text-decoration: none;
            font-size: 14px;
            border-bottom: 2px solid transparent;
            margin-bottom: -1px;
        }
        .tab:hover { color: #f1f5f9; }
        .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    """


def generate_sidebar(active='overview'):
    """Generate sidebar navigation."""
    links = [
        ('overview', 'Overview', '/api/analytics/dashboard/'),
        ('activity', 'Live Activity', '/api/analytics/dashboard/activity/'),
        ('users', 'Users', '/api/analytics/dashboard/users/'),
        ('health', 'Health Scores', '/api/analytics/dashboard/health/'),
        ('funnel', 'Funnel', '/api/analytics/dashboard/funnel/'),
        ('cohorts', 'Cohorts', '/api/analytics/dashboard/cohorts/'),
        ('costs', 'Costs', '/api/analytics/dashboard/costs/'),
        ('components', 'Components', '/api/analytics/dashboard/components/'),
        ('prompts', 'Prompt Analytics', '/api/analytics/dashboard/prompts/'),
        ('alerts', 'Alerts', '/api/analytics/dashboard/alerts/'),
        ('reports', 'Reports', '/api/analytics/dashboard/reports/'),
        ('settings', 'Settings', '/api/analytics/dashboard/settings/'),
        ('map', '🗺️ Project Map', '/api/analytics/dashboard/map/'),
    ]
    
    return f"""
    <div class="sidebar">
        <div class="sidebar-logo">Faibric Admin</div>
        <div class="sidebar-section">Dashboard</div>
        {''.join(f'<a href="{url}" class="{"active" if key == active else ""}">{label}</a>' for key, label, url in links[:2])}
        <div class="sidebar-section">Analytics</div>
        {''.join(f'<a href="{url}" class="{"active" if key == active else ""}">{label}</a>' for key, label, url in links[2:8])}
        <div class="sidebar-section">AI & Library</div>
        {''.join(f'<a href="{url}" class="{"active" if key == active else ""}">{label}</a>' for key, label, url in links[8:10])}
        <div class="sidebar-section">System</div>
        {''.join(f'<a href="{url}" class="{"active" if key == active else ""}">{label}</a>' for key, label, url in links[10:])}
    </div>
    """


def generate_admin_dashboard_html():
    """Generate the main overview dashboard."""
    from apps.onboarding.models import LandingSession
    from .models import APIUsageLog
    from .services import ActivityFeedService, CostService, HealthScoreService
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # Get stats
    live_stats = ActivityFeedService.get_live_stats()
    
    # Yesterday comparison
    yesterday_sessions = LandingSession.objects.filter(created_at__date=yesterday).count()
    yesterday_deployed = LandingSession.objects.filter(created_at__date=yesterday, status='deployed').count()
    
    # Calculate trends
    session_trend = ((live_stats['today_sessions'] - yesterday_sessions) / max(yesterday_sessions, 1)) * 100
    
    # Cost forecast
    forecast = CostService.forecast_cost()
    
    # At risk users
    at_risk = HealthScoreService.get_at_risk_users(limit=5)
    
    # Recent activity
    recent_activity = ActivityFeedService.get_recent_activity(limit=10)
    
    # Recent sessions
    recent_sessions = list(
        LandingSession.objects.order_by('-created_at')[:10]
        .values('session_token', 'initial_request', 'status', 'created_at', 'email')
    )
    
    activity_icons = {
        'new_user': '👤', 'build_started': '🔨', 'build_completed': '✅',
        'build_failed': '❌', 'deployed': '🚀', 'modification': '✏️',
        'error': '⚠️', 'alert': '🔔', 'system': '⚙️',
    }
    
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
    {generate_sidebar('overview')}
    
    <div class="main-content">
        <div class="header">
            <h1>Dashboard Overview</h1>
            <div class="header-actions">
                <div class="live-indicator">
                    <span class="live-dot"></span>
                    <span>{live_stats['active_now']} active now</span>
                </div>
                <button class="btn btn-primary" onclick="location.reload()">Refresh</button>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card highlight">
                <div class="stat-label">Users Today</div>
                <div class="stat-value">{live_stats['today_sessions']}</div>
                <div class="stat-trend {'up' if session_trend >= 0 else 'down'}">
                    {'↑' if session_trend >= 0 else '↓'} {abs(session_trend):.0f}% vs yesterday
                </div>
            </div>
            <div class="stat-card success">
                <div class="stat-label">Deployed Today</div>
                <div class="stat-value">{live_stats['today_deploys']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Building Now</div>
                <div class="stat-value">{live_stats['building_now']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Queue Depth</div>
                <div class="stat-value">{live_stats['queue_depth']}</div>
            </div>
            <div class="stat-card {'warning' if float(live_stats['today_cost']) > 20 else ''}">
                <div class="stat-label">Cost Today</div>
                <div class="stat-value cost">${live_stats['today_cost']:.2f}</div>
                {f'<div class="stat-subtext">Forecast 7d: ${forecast["forecast_7d"]:.2f}</div>' if forecast else ''}
            </div>
        </div>
        
        <div class="grid-2">
            <div class="section">
                <div class="section-header">
                    <h2 class="section-title">Live Activity Feed</h2>
                    <a href="/api/analytics/dashboard/activity/" class="btn btn-secondary">View All</a>
                </div>
                <div class="card">
                    <div class="activity-feed">
                        {''.join(f"""
                        <div class="activity-item">
                            <div class="activity-icon {a.severity}">{activity_icons.get(a.activity_type, '📌')}</div>
                            <div class="activity-content">
                                <div class="activity-title">{html.escape(a.title)}</div>
                                <div class="activity-time">{a.created_at.strftime('%H:%M:%S')} - {a.email or a.session_token[:12] + '...' if a.session_token else 'System'}</div>
                            </div>
                        </div>
                        """ for a in recent_activity) if recent_activity else '<div class="activity-item"><div class="activity-content">No recent activity</div></div>'}
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-header">
                    <h2 class="section-title">At-Risk Users</h2>
                    <a href="/api/analytics/dashboard/health/" class="btn btn-secondary">View All</a>
                </div>
                <div class="card">
                    <table>
                        <thead>
                            <tr>
                                <th>User</th>
                                <th>Score</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(f"""
                            <tr onclick="window.location='/api/analytics/dashboard/user/{u.session_token}'" style="cursor:pointer">
                                <td>{u.email or u.session_token[:16] + '...'}</td>
                                <td>{u.overall_score:.0f}</td>
                                <td><span class="status {u.health_status}">{u.health_status}</span></td>
                            </tr>
                            """ for u in at_risk) if at_risk else '<tr><td colspan="3">No at-risk users</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">
                <h2 class="section-title">Recent Sessions</h2>
                <a href="/api/analytics/dashboard/users/" class="btn btn-secondary">View All</a>
            </div>
            <div class="card">
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
                            <td class="truncate">{html.escape(s['initial_request'][:60] if s['initial_request'] else 'N/A')}</td>
                            <td><span class="status {s['status']}">{s['status']}</span></td>
                            <td>{s['email'] or '-'}</td>
                            <td>{s['created_at'].strftime('%H:%M')}</td>
                        </tr>
                        """ for s in recent_sessions)}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""
    return html_content


def generate_activity_html():
    """Generate live activity page."""
    from .services import ActivityFeedService
    
    activity = ActivityFeedService.get_recent_activity(limit=100)
    live_stats = ActivityFeedService.get_live_stats()
    
    activity_icons = {
        'new_user': '👤', 'build_started': '🔨', 'build_completed': '✅',
        'build_failed': '❌', 'deployed': '🚀', 'modification': '✏️',
        'error': '⚠️', 'alert': '🔔', 'system': '⚙️',
    }
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Live Activity - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('activity')}
    <div class="main-content">
        <div class="header">
            <h1>Live Activity</h1>
            <div class="live-indicator">
                <span class="live-dot"></span>
                <span>{live_stats['active_now']} active | {live_stats['building_now']} building</span>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card highlight">
                <div class="stat-label">Active Now</div>
                <div class="stat-value">{live_stats['active_now']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Building</div>
                <div class="stat-value">{live_stats['building_now']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Queue</div>
                <div class="stat-value">{live_stats['queue_depth']}</div>
            </div>
            <div class="stat-card success">
                <div class="stat-label">Deployed Today</div>
                <div class="stat-value">{live_stats['today_deploys']}</div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">Activity Feed (Last 100)</div>
            <div class="activity-feed" style="max-height: none;">
                {''.join(f"""
                <div class="activity-item">
                    <div class="activity-icon {a.severity}">{activity_icons.get(a.activity_type, '📌')}</div>
                    <div class="activity-content">
                        <div class="activity-title">{html.escape(a.title)}</div>
                        <div class="activity-time">{a.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {a.activity_type}</div>
                        {f'<div style="font-size:12px;color:#64748b;margin-top:4px;">{html.escape(a.description[:200])}</div>' if a.description else ''}
                    </div>
                </div>
                """ for a in activity) if activity else '<div class="activity-item">No activity yet</div>'}
            </div>
        </div>
    </div>
    <script>setTimeout(() => location.reload(), 10000);</script>
</body>
</html>
"""


def generate_funnel_html():
    """Generate funnel visualization page."""
    from .services import FunnelService
    
    funnel_data = FunnelService.get_funnel_data(days=7)
    totals = funnel_data['totals']
    
    # Calculate rates
    def rate(a, b):
        return f"{(a/b*100):.1f}%" if b > 0 else "0%"
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Conversion Funnel - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('funnel')}
    <div class="main-content">
        <div class="header">
            <h1>Conversion Funnel</h1>
            <span style="color:#94a3b8">Last 7 days</span>
        </div>
        
        <div class="funnel">
            <div class="funnel-step">
                <div class="funnel-value">{totals['visitors']}</div>
                <div class="funnel-label">Visitors</div>
                <div class="funnel-rate">100%</div>
            </div>
            <div class="funnel-step">
                <div class="funnel-value">{totals['requests']}</div>
                <div class="funnel-label">Requests</div>
                <div class="funnel-rate">{rate(totals['requests'], totals['visitors'])}</div>
            </div>
            <div class="funnel-step">
                <div class="funnel-value">{totals['emails']}</div>
                <div class="funnel-label">Emails</div>
                <div class="funnel-rate">{rate(totals['emails'], totals['requests'])}</div>
            </div>
            <div class="funnel-step">
                <div class="funnel-value">{totals['verified']}</div>
                <div class="funnel-label">Verified</div>
                <div class="funnel-rate">{rate(totals['verified'], totals['emails'])}</div>
            </div>
            <div class="funnel-step">
                <div class="funnel-value">{totals['builds']}</div>
                <div class="funnel-label">Builds</div>
                <div class="funnel-rate">{rate(totals['builds'], totals['verified'])}</div>
            </div>
            <div class="funnel-step">
                <div class="funnel-value">{totals['deployed']}</div>
                <div class="funnel-label">Deployed</div>
                <div class="funnel-rate">{rate(totals['deployed'], totals['builds'])}</div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card highlight">
                <div class="stat-label">Overall Conversion</div>
                <div class="stat-value">{rate(totals['deployed'], totals['visitors'])}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Biggest Drop-off</div>
                <div class="stat-value">Email → Verified</div>
                <div class="stat-subtext">{100 - (totals['verified']/max(totals['emails'],1)*100):.1f}% lost</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">Daily Breakdown</h2>
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Visitors</th>
                            <th>Requests</th>
                            <th>Emails</th>
                            <th>Verified</th>
                            <th>Deployed</th>
                            <th>Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(f"""
                        <tr>
                            <td>{d.date}</td>
                            <td>{d.visitors}</td>
                            <td>{d.requests_submitted}</td>
                            <td>{d.emails_provided}</td>
                            <td>{d.emails_verified}</td>
                            <td>{d.deployed}</td>
                            <td>{d.overall_rate*100:.1f}%</td>
                        </tr>
                        """ for d in funnel_data['daily']) if funnel_data['daily'] else '<tr><td colspan="7">No data</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""


def generate_health_html():
    """Generate health scores page."""
    from .models_dashboard import CustomerHealthScore
    
    all_scores = list(CustomerHealthScore.objects.all()[:100])
    healthy = len([s for s in all_scores if s.health_status == 'healthy'])
    at_risk = len([s for s in all_scores if s.health_status == 'at_risk'])
    churning = len([s for s in all_scores if s.health_status == 'churning'])
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Health Scores - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('health')}
    <div class="main-content">
        <div class="header">
            <h1>Customer Health Scores</h1>
            <form method="post" action="/api/analytics/dashboard/health/recalculate/" style="display:inline">
                <button type="submit" class="btn btn-primary">Recalculate All</button>
            </form>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card success">
                <div class="stat-label">Healthy</div>
                <div class="stat-value">{healthy}</div>
                <div class="stat-subtext">Score 70+</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">At Risk</div>
                <div class="stat-value">{at_risk}</div>
                <div class="stat-subtext">Score 40-69</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #7f1d1d, #991b1b);">
                <div class="stat-label" style="color:rgba(255,255,255,0.7)">Churning</div>
                <div class="stat-value" style="color:#fff">{churning}</div>
                <div class="stat-subtext" style="color:rgba(255,255,255,0.5)">Score &lt;40</div>
            </div>
        </div>
        
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Score</th>
                        <th>Status</th>
                        <th>Trend</th>
                        <th>Builds</th>
                        <th>Success Rate</th>
                        <th>Last Active</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f"""
                    <tr onclick="window.location='/api/analytics/dashboard/user/{s.session_token}'" style="cursor:pointer">
                        <td>{s.email or s.session_token[:16] + '...'}</td>
                        <td><strong>{s.overall_score:.0f}</strong></td>
                        <td><span class="status {s.health_status}">{s.health_status}</span></td>
                        <td><span class="stat-trend {'up' if s.trend == 'improving' else 'down' if s.trend == 'declining' else ''}">{s.trend}</span></td>
                        <td>{s.total_builds}</td>
                        <td>{s.build_success_rate:.0f}%</td>
                        <td>{s.last_active_at.strftime('%Y-%m-%d %H:%M') if s.last_active_at else '-'}</td>
                    </tr>
                    """ for s in all_scores) if all_scores else '<tr><td colspan="7">No health scores calculated yet. Click "Recalculate All" to start.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


def generate_cohorts_html():
    """Generate cohort analysis page."""
    from .models_dashboard import Cohort
    
    cohorts = list(Cohort.objects.filter(period_type='weekly').order_by('-period_start')[:12])
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Cohort Analysis - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('cohorts')}
    <div class="main-content">
        <div class="header">
            <h1>Cohort Analysis</h1>
            <span style="color:#94a3b8">Weekly retention</span>
        </div>
        
        <div class="card">
            <div class="card-header">Retention by Weekly Cohort</div>
            <div class="cohort-table">
                <table>
                    <thead>
                        <tr>
                            <th>Cohort</th>
                            <th>Users</th>
                            <th>Week 0</th>
                            <th>Week 1</th>
                            <th>Week 2</th>
                            <th>Week 3</th>
                            <th>Week 4</th>
                            <th>Converted</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(f"""
                        <tr>
                            <td>{c.period_key}</td>
                            <td>{c.initial_users}</td>
                            {''.join(f'<td><div class="cohort-cell" style="background: rgba(59,130,246,{(c.retention_data.get(str(i), 0))/100 * 0.5 + 0.1})">{c.retention_data.get(str(i), "-")}%</div></td>' for i in range(5))}
                            <td>{c.conversion_rate*100:.1f}%</td>
                        </tr>
                        """ for c in cohorts) if cohorts else '<tr><td colspan="8">No cohort data yet</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""


def generate_costs_html():
    """Generate costs analysis page."""
    from .services import CostService
    
    daily_costs = CostService.get_daily_costs(days=30)
    forecast = CostService.forecast_cost()
    by_model = CostService.get_cost_by_model()
    
    total_cost = sum(float(d['total_cost'] or 0) for d in daily_costs)
    total_calls = sum(d['total_calls'] or 0 for d in daily_costs)
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Cost Analysis - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('costs')}
    <div class="main-content">
        <div class="header">
            <h1>Cost Analysis</h1>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card highlight">
                <div class="stat-label">Total Spend (30d)</div>
                <div class="stat-value cost">${total_cost:.2f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">API Calls (30d)</div>
                <div class="stat-value">{total_calls:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Daily Cost</div>
                <div class="stat-value cost">${forecast['daily_avg'] if forecast else 0:.2f}</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">7-Day Forecast</div>
                <div class="stat-value cost">${forecast['forecast_7d'] if forecast else 0:.2f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">30-Day Forecast</div>
                <div class="stat-value cost">${forecast['forecast_30d'] if forecast else 0:.2f}</div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="section">
                <h2 class="section-title">Cost by Model</h2>
                <div class="card">
                    <table>
                        <thead>
                            <tr><th>Model</th><th>Calls</th><th>Cost</th></tr>
                        </thead>
                        <tbody>
                            {''.join(f"""
                            <tr>
                                <td>{m['model'][:35] if m['model'] else 'Unknown'}</td>
                                <td>{m['total_calls']}</td>
                                <td class="cost">${float(m['total_cost'] or 0):.4f}</td>
                            </tr>
                            """ for m in by_model) if by_model else '<tr><td colspan="3">No data</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="section">
                <h2 class="section-title">Daily Costs</h2>
                <div class="card" style="max-height: 400px; overflow-y: auto;">
                    <table>
                        <thead>
                            <tr><th>Date</th><th>Calls</th><th>Cost</th></tr>
                        </thead>
                        <tbody>
                            {''.join(f"""
                            <tr>
                                <td>{d['created_at__date']}</td>
                                <td>{d['total_calls']}</td>
                                <td class="cost">${float(d['total_cost'] or 0):.4f}</td>
                            </tr>
                            """ for d in reversed(daily_costs[-14:])) if daily_costs else '<tr><td colspan="3">No data</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


def generate_alerts_html():
    """Generate alerts management page."""
    from .models_dashboard import Alert, AlertRule
    
    alerts = list(Alert.objects.order_by('-created_at')[:50])
    rules = list(AlertRule.objects.all())
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Alerts - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('alerts')}
    <div class="main-content">
        <div class="header">
            <h1>Alerts</h1>
            <a href="/api/analytics/dashboard/alerts/rules/" class="btn btn-secondary">Manage Rules</a>
        </div>
        
        <div class="section">
            <h2 class="section-title">Recent Alerts</h2>
            {''.join(f"""
            <div class="alert-item {a.severity}">
                <div style="flex:1">
                    <strong>{html.escape(a.title)}</strong>
                    <div style="font-size:13px;color:#94a3b8;margin-top:4px">{html.escape(a.message)}</div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:12px;color:#64748b">{a.created_at.strftime('%Y-%m-%d %H:%M')}</div>
                    <span class="status {'deployed' if a.is_acknowledged else 'pending'}">{('Ack' if a.is_acknowledged else 'New')}</span>
                </div>
            </div>
            """ for a in alerts) if alerts else '<div class="alert-item info">No alerts yet</div>'}
        </div>
        
        <div class="section">
            <h2 class="section-title">Alert Rules ({len(rules)})</h2>
            <div class="card">
                <table>
                    <thead>
                        <tr><th>Name</th><th>Metric</th><th>Condition</th><th>Threshold</th><th>Active</th><th>Triggered</th></tr>
                    </thead>
                    <tbody>
                        {''.join(f"""
                        <tr>
                            <td>{html.escape(r.name)}</td>
                            <td>{r.metric}</td>
                            <td>{r.condition}</td>
                            <td>{r.threshold}</td>
                            <td><span class="status {'deployed' if r.is_active else 'failed'}">{('Yes' if r.is_active else 'No')}</span></td>
                            <td>{r.trigger_count}x</td>
                        </tr>
                        """ for r in rules) if rules else '<tr><td colspan="6">No alert rules configured</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""


def generate_prompts_html():
    """Generate prompt analytics page."""
    from .services import PromptAnalyticsService
    
    stats = PromptAnalyticsService.get_prompt_stats()
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Prompt Analytics - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('prompts')}
    <div class="main-content">
        <div class="header">
            <h1>Prompt Analytics</h1>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card highlight">
                <div class="stat-label">Total Prompts</div>
                <div class="stat-value">{stats['total']}</div>
            </div>
            <div class="stat-card success">
                <div class="stat-label">Success Rate</div>
                <div class="stat-value">{stats['success_rate']:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Generation Time</div>
                <div class="stat-value">{stats['avg_generation_time']:.1f}s</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Library Usage</div>
                <div class="stat-value">{stats['library_usage_rate']:.1f}%</div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="section">
                <h2 class="section-title">By Site Type</h2>
                <div class="card">
                    <table>
                        <thead><tr><th>Type</th><th>Count</th></tr></thead>
                        <tbody>
                            {''.join(f"<tr><td>{t['detected_type'] or 'Unknown'}</td><td>{t['count']}</td></tr>" for t in stats['by_type']) if stats['by_type'] else '<tr><td colspan="2">No data</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="section">
                <h2 class="section-title">By Industry</h2>
                <div class="card">
                    <table>
                        <thead><tr><th>Industry</th><th>Count</th></tr></thead>
                        <tbody>
                            {''.join(f"<tr><td>{i['detected_industry']}</td><td>{i['count']}</td></tr>" for i in stats['by_industry']) if stats['by_industry'] else '<tr><td colspan="2">No data</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


def generate_reports_html():
    """Generate reports page."""
    from .models_dashboard import GeneratedReport
    
    reports = list(GeneratedReport.objects.order_by('-created_at')[:20])
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Reports - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('reports')}
    <div class="main-content">
        <div class="header">
            <h1>Reports</h1>
            <form method="post" action="/api/analytics/dashboard/reports/generate/" style="display:inline">
                <button type="submit" class="btn btn-primary">Generate Daily Report</button>
            </form>
        </div>
        
        <div class="card">
            <table>
                <thead>
                    <tr><th>Title</th><th>Period</th><th>Sent</th><th>Actions</th></tr>
                </thead>
                <tbody>
                    {''.join(f"""
                    <tr>
                        <td>{html.escape(r.title)}</td>
                        <td>{r.period_start} - {r.period_end}</td>
                        <td><span class="status {'deployed' if r.sent_at else 'pending'}">{('Sent' if r.sent_at else 'Draft')}</span></td>
                        <td><a href="/api/analytics/dashboard/report/{r.id}/" class="btn btn-secondary">View</a></td>
                    </tr>
                    """ for r in reports) if reports else '<tr><td colspan="4">No reports generated yet</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


def generate_settings_html():
    """Generate settings page."""
    from .models_dashboard import AdminConfig
    
    config = AdminConfig.get_config()
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Settings - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('settings')}
    <div class="main-content">
        <div class="header">
            <h1>Settings</h1>
        </div>
        
        <div class="grid-2">
            <div class="card">
                <div class="card-header">Notification Settings</div>
                <div class="card-body">
                    <p><strong>Admin Email:</strong> {config.admin_email}</p>
                    <p><strong>Email Alerts:</strong> {'Enabled' if config.enable_email_alerts else 'Disabled'}</p>
                    <p><strong>Slack Alerts:</strong> {'Enabled' if config.enable_slack_alerts else 'Disabled'}</p>
                    <p><strong>Daily Report:</strong> {'Enabled' if config.send_daily_report else 'Disabled'} at {config.daily_report_hour}:00</p>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">Alert Thresholds</div>
                <div class="card-body">
                    <p><strong>Daily Cost Warning:</strong> ${config.daily_cost_warning}</p>
                    <p><strong>Daily Cost Critical:</strong> ${config.daily_cost_critical}</p>
                    <p><strong>Error Rate Warning:</strong> {config.error_rate_warning*100}%</p>
                    <p><strong>Error Rate Critical:</strong> {config.error_rate_critical*100}%</p>
                    <p><strong>Queue Depth Warning:</strong> {config.queue_depth_warning}</p>
                    <p><strong>Queue Depth Critical:</strong> {config.queue_depth_critical}</p>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


def generate_users_list_html():
    """Generate users list page."""
    from apps.onboarding.models import LandingSession
    from .models import APIUsageLog
    
    sessions = list(
        LandingSession.objects.order_by('-created_at')[:100]
        .values('session_token', 'initial_request', 'status', 'created_at', 'email')
    )
    
    session_costs = {}
    for s in sessions:
        cost_data = APIUsageLog.objects.filter(session_token=s['session_token']).aggregate(
            total_cost=Sum('cost'), total_calls=Count('id'),
        )
        session_costs[s['session_token']] = cost_data
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Users - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('users')}
    <div class="main-content">
        <div class="header"><h1>All Users</h1></div>
        <div class="card">
            <table>
                <thead>
                    <tr><th>Email</th><th>Request</th><th>Status</th><th>Calls</th><th>Cost</th><th>Date</th></tr>
                </thead>
                <tbody>
                    {''.join(f"""
                    <tr onclick="window.location='/api/analytics/dashboard/user/{s['session_token']}'" style="cursor:pointer">
                        <td>{s['email'] or 'Anonymous'}</td>
                        <td class="truncate">{html.escape(s['initial_request'][:40] if s['initial_request'] else '-')}</td>
                        <td><span class="status {s['status']}">{s['status']}</span></td>
                        <td>{session_costs.get(s['session_token'], {}).get('total_calls') or 0}</td>
                        <td class="cost">${float(session_costs.get(s['session_token'], {}).get('total_cost') or 0):.4f}</td>
                        <td>{s['created_at'].strftime('%Y-%m-%d %H:%M')}</td>
                    </tr>
                    """ for s in sessions)}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


def generate_user_detail_html(session_token):
    """Generate user detail page."""
    from apps.onboarding.models import LandingSession, SessionEvent, UserInput
    from .models import APIUsageLog
    from .models_dashboard import CustomerHealthScore
    
    try:
        session = LandingSession.objects.get(session_token=session_token)
    except LandingSession.DoesNotExist:
        return "<h1>User not found</h1>"
    
    events = list(SessionEvent.objects.filter(session=session).order_by('timestamp'))
    inputs = list(UserInput.objects.filter(session=session).order_by('timestamp'))
    api_usage = list(APIUsageLog.objects.filter(session_token=session_token).order_by('-created_at')[:50])
    
    total_cost = sum(u.cost for u in api_usage)
    
    # Health score
    try:
        health = CustomerHealthScore.objects.get(session_token=session_token)
    except CustomerHealthScore.DoesNotExist:
        health = None
    
    project = session.converted_to_project
    project_url = project.deployment_url if project and hasattr(project, 'deployment_url') else None
    
    email_initial = (session.email[0].upper() if session.email else 'A')
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>User: {session.email or 'Anonymous'} - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('users')}
    <div class="main-content">
        <a href="/api/analytics/dashboard/users/" class="back-link">← Back to Users</a>
        
        <div class="user-header">
            <div class="user-avatar">{email_initial}</div>
            <div class="user-info">
                <h2>{session.email or 'Anonymous'}</h2>
                <p><span class="status {session.status}">{session.status}</span> · Created {session.created_at.strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            <div style="margin-left: auto; display: flex; gap: 8px;">
                <form method="post" action="/api/analytics/dashboard/user/{session_token}/retry/" style="display:inline">
                    <button type="submit" class="btn btn-primary">Retry Build</button>
                </form>
                <form method="post" action="/api/analytics/dashboard/user/{session_token}/redeploy/" style="display:inline">
                    <button type="submit" class="btn btn-secondary">Force Redeploy</button>
                </form>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">API Calls</div>
                <div class="stat-value">{len(api_usage)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Cost</div>
                <div class="stat-value cost">${total_cost:.4f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Events</div>
                <div class="stat-value">{len(events)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Messages</div>
                <div class="stat-value">{len(inputs)}</div>
            </div>
            {f'''<div class="stat-card {'success' if health and health.health_status == 'healthy' else 'warning' if health and health.health_status == 'at_risk' else ''}">
                <div class="stat-label">Health Score</div>
                <div class="stat-value">{health.overall_score:.0f if health else 'N/A'}</div>
            </div>''' if health else ''}
        </div>
        
        <div class="section">
            <h2 class="section-title">Initial Request</h2>
            <div class="card"><div class="card-body">{html.escape(session.initial_request or 'No request')}</div></div>
        </div>
        
        {f'<div class="section"><h2 class="section-title">Deployed Site</h2><div class="card"><div class="card-body"><a href="{project_url}" target="_blank" class="btn btn-primary">View Live Site</a> <span style="margin-left:12px;color:#94a3b8">{project_url}</span></div></div></div>' if project_url else ''}
        
        <div class="grid-2">
            <div class="section">
                <h2 class="section-title">Messages ({len(inputs)})</h2>
                <div class="card" style="max-height:400px;overflow-y:auto">
                    {''.join(f'<div class="log-entry"><div class="log-time">{inp.timestamp.strftime("%H:%M:%S")}</div><div class="log-type">{inp.input_type}</div><div class="log-content">{html.escape(inp.input_text[:300])}</div></div>' for inp in inputs) if inputs else '<div class="log-entry">No messages</div>'}
                </div>
            </div>
            <div class="section">
                <h2 class="section-title">Events ({len(events)})</h2>
                <div class="card" style="max-height:400px;overflow-y:auto">
                    {''.join(f'<div class="log-entry"><div class="log-time">{ev.timestamp.strftime("%H:%M:%S")}</div><div class="log-type">{ev.event_type}</div><div class="log-content">{html.escape(str(ev.event_data)[:200]) if ev.event_data else ""}</div></div>' for ev in events) if events else '<div class="log-entry">No events</div>'}
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">API Usage</h2>
            <div class="card">
                <table>
                    <thead><tr><th>Time</th><th>Model</th><th>Task</th><th>Tokens</th><th>Cost</th></tr></thead>
                    <tbody>
                        {''.join(f'<tr><td>{u.created_at.strftime("%H:%M:%S")}</td><td>{u.model[:25]}</td><td>{u.task_type}</td><td>{u.input_tokens + u.output_tokens}</td><td class="cost">${u.cost:.6f}</td></tr>' for u in api_usage) if api_usage else '<tr><td colspan="5">No API usage</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""


def generate_components_html():
    """Generate components gallery page."""
    from apps.code_library.models import LibraryItem
    
    components = list(LibraryItem.objects.filter(is_active=True).order_by('-usage_count')[:50])
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Components - Faibric Admin</title>
    <style>{get_base_styles()}</style>
</head>
<body>
    {generate_sidebar('components')}
    <div class="main-content">
        <div class="header"><h1>Component Library</h1></div>
        
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
        
        <div class="component-grid">
            {''.join(f"""
            <div class="component-card">
                <div class="component-preview"><pre>{html.escape(c.code[:400]) if c.code else 'No code'}...</pre></div>
                <div class="component-info">
                    <div class="component-name">{html.escape(c.name[:40])}</div>
                    <div class="component-meta">
                        <span>Used {c.usage_count}x</span>
                        <span>Score: {c.quality_score:.0f}</span>
                    </div>
                </div>
            </div>
            """ for c in components) if components else '<p style="color:#94a3b8">No components yet</p>'}
        </div>
    </div>
</body>
</html>
"""
