"""
API views for Onboarding Flow.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse

from .models import LandingSession, SessionEvent, DailyReport, AdminNotification
from .serializers import (
    SubmitRequestSerializer,
    ProvideEmailSerializer,
    VerifyTokenSerializer,
    LandingSessionSerializer,
    LandingSessionListSerializer,
    SessionEventSerializer,
    DailyReportSerializer,
    DailyReportDetailSerializer,
    AdminNotificationSerializer,
)
from .services import OnboardingService, DailyReportService
from .input_tracker import InputTracker, InputAnalytics


# ============================================
# Public Endpoints (Landing Page Flow)
# ============================================

class LandingFlowView(APIView):
    """
    Main landing page flow endpoints.
    No authentication required.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 1: Submit initial request.
        
        User types something in the main input and submits.
        Returns a session token.
        """
        serializer = SubmitRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        session = OnboardingService.create_session(
            initial_request=serializer.validated_data['request'],
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            utm_source=serializer.validated_data.get('utm_source', ''),
            utm_medium=serializer.validated_data.get('utm_medium', ''),
            utm_campaign=serializer.validated_data.get('utm_campaign', ''),
            utm_content=serializer.validated_data.get('utm_content', ''),
            utm_term=serializer.validated_data.get('utm_term', ''),
            referrer=serializer.validated_data.get('referrer', ''),
            landing_page=serializer.validated_data.get('landing_page', ''),
        )
        
        return Response({
            'success': True,
            'session_token': session.session_token,
            'message': 'Please provide your email to continue.',
        })


class EmailFlowView(APIView):
    """
    Email collection endpoints.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 2: Provide email.
        
        User enters their email to receive the magic link.
        """
        serializer = ProvideEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            session = OnboardingService.provide_email(
                session_token=serializer.validated_data['session_token'],
                email=serializer.validated_data['email'],
            )
            
            # Automatically send magic link
            result = OnboardingService.send_magic_link(session.session_token)
            
            if result['success']:
                return Response({
                    'success': True,
                    'email': session.email,
                    'message': 'Check your email! We sent you a link to access your project.',
                    'email_changed': session.email_change_count > 0,
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to send email. Please try again.',
                }, status=500)
                
        except LandingSession.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invalid session. Please start over.',
            }, status=400)


class ChangeEmailView(APIView):
    """
    Change email endpoint - "provide different email" link.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        User clicks "provide different email" and enters a new one.
        """
        serializer = ProvideEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            session = OnboardingService.provide_email(
                session_token=serializer.validated_data['session_token'],
                email=serializer.validated_data['email'],
            )
            
            # Send magic link to new email
            result = OnboardingService.send_magic_link(session.session_token)
            
            return Response({
                'success': result['success'],
                'email': session.email,
                'email_change_count': session.email_change_count,
                'message': 'We sent a new link to your updated email address.',
            })
            
        except LandingSession.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invalid session.',
            }, status=400)


class VerifyMagicLinkView(APIView):
    """
    Magic link verification.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 3: Verify magic link and create account.
        
        User clicks the link in their email.
        """
        serializer = VerifyTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = OnboardingService.verify_magic_link(
            serializer.validated_data['token']
        )
        
        if result['success']:
            # Generate JWT for the user
            from rest_framework_simplejwt.tokens import RefreshToken
            from django.contrib.auth import get_user_model
            import threading
            
            User = get_user_model()
            user = User.objects.get(id=result['user_id'])
            
            refresh = RefreshToken.for_user(user)
            
            # Start building in background thread (no Celery)
            def run_build():
                from .build_service import BuildService
                BuildService.build_from_session(result['session_token'])
            
            thread = threading.Thread(target=run_build, daemon=True)
            thread.start()
            
            return Response({
                'success': True,
                'user_id': result['user_id'],
                'tenant_id': result['tenant_id'],
                'email': result['email'],
                'initial_request': result['initial_request'],
                'session_token': result['session_token'],
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Verification failed'),
            }, status=400)


class SessionStatusView(APIView):
    """
    Get session status (for polling during build).
    """
    permission_classes = [AllowAny]
    
    def get(self, request, session_token):
        """Get current session status."""
        import json
        try:
            session = LandingSession.objects.get(session_token=session_token)
            
            # Get recent events
            events = session.events.order_by('-timestamp')[:10]
            
            # Get deployment URL and generated code from project if exists
            deployment_url = None
            build_progress = 0
            generated_code = None
            
            if session.converted_to_project:
                project = session.converted_to_project
                deployment_url = project.deployment_url
                
                # Get generated code for live preview
                if project.frontend_code:
                    try:
                        # Try parsing as JSON first
                        code_data = json.loads(project.frontend_code)
                        if isinstance(code_data, dict) and 'App.tsx' in code_data:
                            generated_code = code_data.get('App.tsx', '')
                        elif isinstance(code_data, str):
                            generated_code = code_data
                    except (json.JSONDecodeError, TypeError):
                        # Fallback to raw string
                        generated_code = str(project.frontend_code)
                
                # Calculate build progress based on status
                if project.status == 'generating':
                    build_progress = 30
                elif project.status == 'ready':
                    build_progress = 70
                elif project.status == 'deploying':
                    build_progress = 85
                elif project.status == 'deployed':
                    build_progress = 100
                    session.status = 'deployed'
                    session.save()
            
            return Response({
                'status': session.status,
                'email': session.email,
                'is_converted': session.is_converted,
                'project_id': str(session.converted_to_project_id) if session.converted_to_project else None,
                'deployment_url': deployment_url,
                'build_progress': build_progress,
                'generated_code': generated_code,  # Include generated code for live preview
                'events': SessionEventSerializer(events, many=True).data,
            })
        except LandingSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)


# ============================================
# Activity Tracking (called from frontend)
# ============================================

class ActivityTrackingView(APIView):
    """
    Track user activity for session duration analytics.
    Called periodically from frontend (every 30 seconds).
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Log activity heartbeat."""
        session_token = request.data.get('session_token')
        event_type = request.data.get('event_type', 'heartbeat')
        
        if not session_token:
            return Response({'error': 'Session token required'}, status=400)
        
        if event_type == 'leave':
            InputTracker.log_page_leave(session_token)
        elif event_type == 'return':
            InputTracker.log_page_return(session_token)
        else:
            InputTracker.log_activity(session_token)
        
        return Response({'status': 'ok'})


class FollowUpInputView(APIView):
    """
    Log follow-up messages from users.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Log a follow-up message."""
        session_token = request.data.get('session_token')
        message = request.data.get('message')
        context = request.data.get('context', '')
        
        if not session_token or not message:
            return Response({'error': 'Session token and message required'}, status=400)
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
        except LandingSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
        
        InputTracker.log_follow_up(session, message, context)
        
        return Response({'status': 'logged'})


class ModifyBuildView(APIView):
    """
    Modify existing website - makes TARGETED changes, not full rebuild.
    Only rebuilds from scratch if explicitly requested or no existing code.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Modify existing code or rebuild if needed."""
        import logging
        import threading
        import json
        logger = logging.getLogger(__name__)
        
        session_token = request.data.get('session_token')
        user_request = request.data.get('request')
        
        if not session_token or not user_request:
            return Response({'error': 'Session token and request required'}, status=400)
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
        except LandingSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
        
        # Check if this is a modification or new project request
        is_new_project = any(phrase in user_request.lower() for phrase in [
            'new website', 'new project', 'start over', 'from scratch',
            'different website', 'another website', 'dont need this',
            "don't need this", 'completely different', 'i need a website',
            'i am a', 'i am an'  # New identity = new project
        ])
        
        has_existing_code = session.converted_to_project and session.converted_to_project.frontend_code
        
        if is_new_project or not has_existing_code:
            # FULL REBUILD - new project requested
            session.status = 'building'
            session.build_progress = 0
            session.initial_request = user_request
            session.save()
            
            # Clear old project reference
            if session.converted_to_project:
                session.converted_to_project = None
                session.save()
            
            SessionEvent.objects.create(
                session=session,
                event_type='build_progress',
                event_data={'message': 'Starting new build with updated request...'}
            )
            
            def run_full_build():
                from .build_service import BuildService
                try:
                    BuildService.build_from_session(session_token)
                except Exception as e:
                    logger.exception(f"Full rebuild failed: {e}")
            
            thread = threading.Thread(target=run_full_build, daemon=True)
            thread.start()
            
            return Response({
                'success': True,
                'mode': 'rebuild',
                'message': 'Starting new project from scratch',
            })
        
        else:
            # QUICK MODIFICATION - just change the existing code
            session.status = 'building'
            session.build_progress = 50  # Start at 50% since we already have code
            session.save()
            
            SessionEvent.objects.create(
                session=session,
                event_type='build_progress',
                event_data={'message': f'Applying changes: {user_request[:50]}...'}
            )
            
            def run_modification():
                from apps.ai_engine.v2.generator import AIGeneratorV2
                from apps.deployment.render_deployer import RenderDeployer
                from .models import UserInput
                
                try:
                    project = session.converted_to_project
                    
                    # Get existing code
                    try:
                        code_data = json.loads(project.frontend_code)
                        if isinstance(code_data, dict) and 'App.tsx' in code_data:
                            current_code = code_data['App.tsx']
                        else:
                            current_code = str(project.frontend_code)
                    except:
                        current_code = str(project.frontend_code)
                    
                    # BUILD FULL CLIENT CONTEXT - everything the client has ever said
                    context_parts = []
                    
                    # 1. Original request (most important!)
                    context_parts.append(f"ORIGINAL CLIENT REQUEST: {session.initial_request}")
                    
                    # 2. Project description if different
                    if project.description and project.description != session.initial_request:
                        context_parts.append(f"PROJECT DESCRIPTION: {project.description}")
                    
                    # 3. All follow-up messages from this session
                    follow_ups = UserInput.objects.filter(
                        session=session,
                        input_type='follow_up'
                    ).order_by('timestamp')
                    
                    if follow_ups.exists():
                        context_parts.append("PREVIOUS MESSAGES FROM CLIENT:")
                        for fu in follow_ups:
                            context_parts.append(f"  - {fu.input_text}")
                    
                    # 4. Current modification request
                    context_parts.append(f"CURRENT MODIFICATION REQUEST: {user_request}")
                    
                    full_context = "\n".join(context_parts)
                    
                    # Modify with AI (quick!)
                    SessionEvent.objects.create(
                        session=session,
                        event_type='build_progress',
                        event_data={'message': 'AI modifying code...'}
                    )
                    
                    generator = AIGeneratorV2()
                    new_code = generator.modify_app(
                        current_code=current_code,
                        user_request=full_context,  # Pass FULL context, not just modification
                        project_id=project.id
                    )
                    
                    # Store modified code
                    project.frontend_code = json.dumps({'App.tsx': new_code})
                    project.save()
                    
                    SessionEvent.objects.create(
                        session=session,
                        event_type='build_progress',
                        event_data={'message': 'Deploying changes...'}
                    )
                    
                    # Deploy
                    deployer = RenderDeployer()
                    deploy_result = deployer.deploy_react_app(project)
                    
                    # Update URLs
                    project.deployment_url = deploy_result.get('url', '')
                    project.save()
                    
                    session.status = 'deployed'
                    session.save()
                    
                    SessionEvent.objects.create(
                        session=session,
                        event_type='build_progress',
                        event_data={'message': f"Changes deployed: {deploy_result.get('url')}"}
                    )
                    
                except Exception as e:
                    logger.exception(f"Modification failed: {e}")
                    SessionEvent.objects.create(
                        session=session,
                        event_type='error',
                        event_data={'error': str(e)}
                    )
            
            thread = threading.Thread(target=run_modification, daemon=True)
            thread.start()
            
            return Response({
                'success': True,
                'mode': 'modify',
                'message': 'Applying quick changes to existing code',
            })


class TriggerBuildView(APIView):
    """
    Trigger app building for a session.
    Runs in-process (no Celery worker needed) for faster deploys.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Trigger the build process - runs in background thread."""
        import logging
        import threading
        logger = logging.getLogger(__name__)
        
        session_token = request.data.get('session_token')
        
        if not session_token:
            return Response({'error': 'Session token required'}, status=400)
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
        except LandingSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
        
        # Update session status immediately
        session.status = 'building'
        session.save()
        
        # Run build in background thread (no Celery needed)
        def run_build():
            from .build_service import BuildService
            try:
                BuildService.build_from_session(session_token)
            except Exception as e:
                logger.exception(f"Build failed: {e}")
        
        thread = threading.Thread(target=run_build, daemon=True)
        thread.start()
        
        return Response({
            'success': True,
            'message': 'Build started',
            'session_token': session_token,
        })


class StopBuildView(APIView):
    """Stop an ongoing build."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Stop the build process."""
        session_token = request.data.get('session_token')
        
        if not session_token:
            return Response({'error': 'Session token required'}, status=400)
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
        except LandingSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
        
        # Mark session as stopped
        session.status = 'stopped'
        session.save()
        
        # Add event
        SessionEvent.objects.create(
            session=session,
            event_type='build_progress',
            event_data={'message': 'Build stopped by user'}
        )
        
        return Response({
            'success': True,
            'message': 'Build stopped',
        })


# ============================================
# Visual Dashboard (HTML)
# ============================================

class FunnelDashboardView(APIView):
    """
    Visual funnel dashboard - HTML view for Safari.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        from .dashboard import generate_dashboard_html
        html = generate_dashboard_html()
        return HttpResponse(html, content_type='text/html')


class SessionDetailView(APIView):
    """
    Get detailed session data including all inputs and time spent.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, session_token):
        """Get full session details."""
        summary = InputTracker.get_session_summary(session_token)
        
        if not summary:
            return Response({'error': 'Session not found'}, status=404)
        
        return Response(summary)


class InputAnalyticsView(APIView):
    """
    Get input analytics for admin dashboard.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """Get input analytics."""
        return Response({
            'engagement': InputAnalytics.get_engagement_metrics(),
            'avg_session_duration': InputAnalytics.get_average_session_duration(),
            'common_requests': InputAnalytics.get_common_requests(limit=20),
            'volume_by_day': InputAnalytics.get_input_volume_by_day(days=30),
        })


class AllInputsView(APIView):
    """
    View all user inputs for learning and analysis.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """Get all user inputs paginated."""
        from .models import UserInput
        
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 50))
        input_type = request.query_params.get('type')
        
        inputs = UserInput.objects.all().select_related('session')
        
        if input_type:
            inputs = inputs.filter(input_type=input_type)
        
        start = (page - 1) * per_page
        end = start + per_page
        
        return Response({
            'total': inputs.count(),
            'page': page,
            'per_page': per_page,
            'inputs': [
                {
                    'id': str(inp.id),
                    'type': inp.input_type,
                    'text': inp.input_text,
                    'session_email': inp.session.email if inp.session else None,
                    'ai_response': inp.ai_response[:200] if inp.ai_response else None,
                    'was_successful': inp.was_successful,
                    'satisfaction': inp.user_satisfaction,
                    'timestamp': inp.timestamp.isoformat(),
                    'utm_source': inp.utm_source,
                }
                for inp in inputs[start:end]
            ]
        })


# ============================================
# Admin Endpoints (Faibric Staff)
# ============================================

class SessionAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin view of all landing sessions.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LandingSessionSerializer
        return LandingSessionListSerializer
    
    def get_queryset(self):
        qs = LandingSession.objects.all()
        
        # Filters
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        
        converted = self.request.query_params.get('converted')
        if converted == 'true':
            qs = qs.filter(converted_to_user__isnull=False)
        elif converted == 'false':
            qs = qs.filter(converted_to_user__isnull=True)
        
        email_changed = self.request.query_params.get('email_changed')
        if email_changed == 'true':
            qs = qs.filter(email_change_count__gt=0)
        
        utm_source = self.request.query_params.get('utm_source')
        if utm_source:
            qs = qs.filter(utm_source=utm_source)
        
        return qs.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get session statistics."""
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        last_7_days = today - timedelta(days=7)
        
        sessions = LandingSession.objects.filter(created_at__date__gte=last_7_days)
        
        stats = {
            'total_sessions': sessions.count(),
            'converted': sessions.filter(converted_to_user__isnull=False).count(),
            'email_changes': sessions.filter(email_change_count__gt=0).count(),
            'by_status': dict(
                sessions.values('status').annotate(count=Count('id')).values_list('status', 'count')
            ),
            'by_source': dict(
                sessions.exclude(utm_source='').values('utm_source').annotate(count=Count('id')).values_list('utm_source', 'count')
            ),
        }
        
        return Response(stats)


class DailyReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View daily reports.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = DailyReport.objects.all().order_by('-date')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DailyReportDetailSerializer
        return DailyReportSerializer
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate report for yesterday (or specific date)."""
        date_str = request.data.get('date')
        
        if date_str:
            from datetime import datetime
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            report_date = None
        
        report = DailyReportService.generate_report(report_date)
        
        return Response({
            'success': True,
            'report_id': str(report.id),
            'date': str(report.date),
        })
    
    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        """Send report email."""
        report = self.get_object()
        success = DailyReportService.send_daily_report_email(report)
        
        return Response({
            'success': success,
        })


class AdminNotificationViewSet(viewsets.ModelViewSet):
    """
    Admin notifications.
    """
    serializer_class = AdminNotificationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = AdminNotification.objects.all().order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'success': True})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        AdminNotification.objects.filter(is_read=False).update(is_read=True)
        return Response({'success': True})

