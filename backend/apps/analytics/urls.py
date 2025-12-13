from django.urls import path, include
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from .views import (
    AnalyticsConfigViewSet, TrackEventView, IdentifyUserView,
    EventViewSet, FunnelViewSet, UserProfileViewSet
)

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'funnels', FunnelViewSet, basename='funnel')
router.register(r'users', UserProfileViewSet, basename='user-profile')


# Dashboard Views
def dashboard_view(request):
    from .admin_dashboard import generate_admin_dashboard_html
    return HttpResponse(generate_admin_dashboard_html(), content_type='text/html')

def activity_view(request):
    from .admin_dashboard import generate_activity_html
    return HttpResponse(generate_activity_html(), content_type='text/html')

def users_list_view(request):
    from .admin_dashboard import generate_users_list_html
    return HttpResponse(generate_users_list_html(), content_type='text/html')

def user_detail_view(request, session_token):
    from .admin_dashboard import generate_user_detail_html
    return HttpResponse(generate_user_detail_html(session_token), content_type='text/html')

def health_view(request):
    from .admin_dashboard import generate_health_html
    return HttpResponse(generate_health_html(), content_type='text/html')

def funnel_view(request):
    from .admin_dashboard import generate_funnel_html
    return HttpResponse(generate_funnel_html(), content_type='text/html')

def cohorts_view(request):
    from .admin_dashboard import generate_cohorts_html
    return HttpResponse(generate_cohorts_html(), content_type='text/html')

def costs_view(request):
    from .admin_dashboard import generate_costs_html
    return HttpResponse(generate_costs_html(), content_type='text/html')

def components_view(request):
    from .admin_dashboard import generate_components_html
    return HttpResponse(generate_components_html(), content_type='text/html')

def prompts_view(request):
    from .admin_dashboard import generate_prompts_html
    return HttpResponse(generate_prompts_html(), content_type='text/html')

def alerts_view(request):
    from .admin_dashboard import generate_alerts_html
    return HttpResponse(generate_alerts_html(), content_type='text/html')

def reports_view(request):
    from .admin_dashboard import generate_reports_html
    return HttpResponse(generate_reports_html(), content_type='text/html')

def settings_view(request):
    from .admin_dashboard import generate_settings_html
    return HttpResponse(generate_settings_html(), content_type='text/html')


# Action Endpoints
@csrf_exempt
def recalculate_health(request):
    if request.method == 'POST':
        from .services import HealthScoreService
        count = HealthScoreService.calculate_all()
        return HttpResponseRedirect('/api/analytics/dashboard/health/')
    return HttpResponse("Method not allowed", status=405)

@csrf_exempt
def generate_report(request):
    if request.method == 'POST':
        from .services import AISummaryService
        report = AISummaryService.generate_daily_summary()
        AISummaryService.send_daily_report_email(report)
        return HttpResponseRedirect('/api/analytics/dashboard/reports/')
    return HttpResponse("Method not allowed", status=405)

@csrf_exempt
def run_daily_tasks(request):
    if request.method == 'POST':
        from .services import run_daily_tasks as run_tasks
        run_tasks()
        return HttpResponse("Daily tasks completed", status=200)
    return HttpResponse("Method not allowed", status=405)

@csrf_exempt
def retry_build(request, session_token):
    """Retry a failed build."""
    if request.method == 'POST':
        import threading
        from apps.onboarding.models import LandingSession
        from apps.onboarding.build_service import BuildService
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
            session.status = 'building'
            session.save()
            
            # Run in background
            thread = threading.Thread(
                target=BuildService.build_from_session,
                args=(session_token,)
            )
            thread.start()
            
            return HttpResponseRedirect(f'/api/analytics/dashboard/user/{session_token}')
        except LandingSession.DoesNotExist:
            return HttpResponse("Session not found", status=404)
    return HttpResponse("Method not allowed", status=405)

@csrf_exempt
def force_redeploy(request, session_token):
    """Force redeploy an existing project."""
    if request.method == 'POST':
        import threading
        from apps.onboarding.models import LandingSession
        from apps.deployment.render_deployer import RenderDeployer
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
            project = session.converted_to_project
            
            if not project:
                return HttpResponse("No project to redeploy", status=400)
            
            def do_redeploy():
                deployer = RenderDeployer()
                deployer.deploy_react_app(project)
            
            thread = threading.Thread(target=do_redeploy)
            thread.start()
            
            return HttpResponseRedirect(f'/api/analytics/dashboard/user/{session_token}')
        except LandingSession.DoesNotExist:
            return HttpResponse("Session not found", status=404)
    return HttpResponse("Method not allowed", status=405)

def report_detail_view(request, report_id):
    from .models_dashboard import GeneratedReport
    try:
        report = GeneratedReport.objects.get(id=report_id)
        return HttpResponse(report.html_content, content_type='text/html')
    except GeneratedReport.DoesNotExist:
        return HttpResponse("Report not found", status=404)


urlpatterns = [
    path('', include(router.urls)),
    
    # FAIBRIC ADMIN DASHBOARD - Main Pages
    path('dashboard/', dashboard_view, name='admin-dashboard'),
    path('dashboard/activity/', activity_view, name='admin-activity'),
    path('dashboard/users/', users_list_view, name='admin-users'),
    path('dashboard/user/<str:session_token>', user_detail_view, name='admin-user-detail'),
    path('dashboard/health/', health_view, name='admin-health'),
    path('dashboard/funnel/', funnel_view, name='admin-funnel'),
    path('dashboard/cohorts/', cohorts_view, name='admin-cohorts'),
    path('dashboard/costs/', costs_view, name='admin-costs'),
    path('dashboard/components/', components_view, name='admin-components'),
    path('dashboard/prompts/', prompts_view, name='admin-prompts'),
    path('dashboard/alerts/', alerts_view, name='admin-alerts'),
    path('dashboard/reports/', reports_view, name='admin-reports'),
    path('dashboard/report/<str:report_id>/', report_detail_view, name='admin-report-detail'),
    path('dashboard/settings/', settings_view, name='admin-settings'),
    
    # Action Endpoints
    path('dashboard/health/recalculate/', recalculate_health, name='admin-recalculate-health'),
    path('dashboard/reports/generate/', generate_report, name='admin-generate-report'),
    path('dashboard/run-daily/', run_daily_tasks, name='admin-run-daily'),
    path('dashboard/user/<str:session_token>/retry/', retry_build, name='admin-retry-build'),
    path('dashboard/user/<str:session_token>/redeploy/', force_redeploy, name='admin-force-redeploy'),
    
    # Config endpoints
    path('config/', AnalyticsConfigViewSet.as_view({'get': 'config'}), name='analytics-config'),
    path('config/update/', AnalyticsConfigViewSet.as_view({'put': 'update_config', 'patch': 'update_config'}), name='analytics-config-update'),
    
    # Public tracking endpoints (for customer's apps)
    path('track/', TrackEventView.as_view(), name='analytics-track'),
    path('identify/', IdentifyUserView.as_view(), name='analytics-identify'),
]
