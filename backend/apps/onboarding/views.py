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

from apps.ai_engine.agent_mode import AgentModeService


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
        import traceback

        try:
            serializer = SubmitRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        except Exception as e:
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc(),
            }, status=500)


class PlanningFlowView(APIView):
    """
    Planning/Discussion Mode endpoints.
    For gathering requirements before building.
    Uses cheaper/faster Haiku model.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Start or continue a planning discussion.
        Creates session with mode=discussion.
        Uses PLANNING_PROMPT with Haiku model.
        Returns AI response (questions/clarifications).
        """
        import anthropic
        from django.conf import settings
        from apps.ai_engine.v3.prompts import PLANNING_PROMPT

        session_token = request.data.get('session_token')
        user_message = request.data.get('message', '')

        # If no session token, create a new discussion session
        if not session_token:
            initial_request = request.data.get('request', user_message)
            if not initial_request:
                return Response({
                    'success': False,
                    'error': 'Please provide a request or message to start planning.',
                }, status=400)

            session = OnboardingService.create_session(
                initial_request=initial_request,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                utm_source=request.data.get('utm_source', ''),
                utm_medium=request.data.get('utm_medium', ''),
                utm_campaign=request.data.get('utm_campaign', ''),
            )
            # Set mode to discussion
            session.mode = 'discussion'
            session.save()
            session_token = session.session_token
            # Use initial request as the first message
            user_message = initial_request
        else:
            # Get existing session
            try:
                session = LandingSession.objects.get(session_token=session_token)
            except LandingSession.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Session not found.',
                }, status=404)

            if not user_message:
                return Response({
                    'success': False,
                    'error': 'Please provide a message to continue the discussion.',
                }, status=400)

        # Build conversation history from session events
        messages = []
        planning_events = session.events.filter(
            event_type='chat_message'
        ).order_by('timestamp')

        for event in planning_events:
            event_data = event.event_data or {}
            role = event_data.get('role', 'user')
            content = event_data.get('content', event.user_input or '')
            if content:
                messages.append({'role': role, 'content': content})

        # Add current user message
        messages.append({'role': 'user', 'content': user_message})

        # Log user message as event
        SessionEvent.objects.create(
            session=session,
            event_type='chat_message',
            user_input=user_message,
            event_data={'role': 'user', 'content': user_message}
        )

        # Call Haiku model with planning prompt
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=1024,
                system=PLANNING_PROMPT,
                messages=messages
            )
            ai_response = response.content[0].text
        except Exception as e:
            return Response({
                'success': False,
                'error': f'AI service error: {str(e)}',
            }, status=500)

        # Log AI response as event
        SessionEvent.objects.create(
            session=session,
            event_type='chat_message',
            event_data={'role': 'assistant', 'content': ai_response}
        )

        # Update session activity
        session.update_activity()

        return Response({
            'success': True,
            'session_token': session_token,
            'response': ai_response,
            'mode': 'discussion',
        })


class PlanToBuildView(APIView):
    """
    Convert a planning session to a building session.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Convert planning session to building session.
        Changes session mode from discussion to building.
        Stores planning summary in requirements_checklist.
        Triggers normal build flow.
        """
        import threading

        session_token = request.data.get('session_token')
        planning_summary = request.data.get('planning_summary', '')

        if not session_token:
            return Response({
                'success': False,
                'error': 'Session token required.',
            }, status=400)

        try:
            session = LandingSession.objects.get(session_token=session_token)
        except LandingSession.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Session not found.',
            }, status=404)

        # Verify session is in discussion mode
        if session.mode != 'discussion':
            return Response({
                'success': False,
                'error': 'Session is not in discussion mode.',
            }, status=400)

        # Build planning summary from conversation if not provided
        if not planning_summary:
            planning_events = session.events.filter(
                event_type='chat_message'
            ).order_by('timestamp')

            conversation_parts = []
            for event in planning_events:
                event_data = event.event_data or {}
                role = event_data.get('role', 'user')
                content = event_data.get('content', event.user_input or '')
                if content:
                    prefix = 'User: ' if role == 'user' else 'Assistant: '
                    conversation_parts.append(f"{prefix}{content}")

            planning_summary = '\n\n'.join(conversation_parts)

        # Update session
        session.mode = 'building'
        session.requirements_checklist = planning_summary
        session.status = 'building'
        session.save()

        # Log conversion event
        SessionEvent.objects.create(
            session=session,
            event_type='build_started',
            event_data={
                'message': 'Converted from planning to building mode',
                'requirements_length': len(planning_summary)
            }
        )

        # Start build in background
        def run_build():
            from .build_service import BuildService
            import logging
            logger = logging.getLogger(__name__)
            try:
                BuildService.build_from_session(session_token)
            except Exception as e:
                logger.exception(f"Build from planning failed: {e}")

        thread = threading.Thread(target=run_build, daemon=True)
        thread.start()

        return Response({
            'success': True,
            'session_token': session_token,
            'mode': 'building',
            'message': 'Planning complete. Build started.',
        })


class DevFlowView(APIView):
    """
    DEV MODE: Skip email verification and go directly to building.
    This is for local development testing only.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Create session and immediately start building (no email required).
        """
        import threading
        from django.contrib.auth import get_user_model
        from apps.tenants.models import Tenant

        serializer = SubmitRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create session
        session = OnboardingService.create_session(
            initial_request=serializer.validated_data['request'],
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        # Auto-verify with dev user
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            email='dev@faibric.local',
            defaults={'is_active': True}
        )
        tenant = Tenant.objects.filter(owner=user).first()
        if not tenant:
            tenant = Tenant.objects.create(
                name='Dev Tenant',
                slug='dev-tenant',
                owner=user
            )

        session.email = 'dev@faibric.local'
        session.email_verified = True
        session.status = 'verified'
        session.converted_to_user = user
        session.converted_to_tenant = tenant
        session.save()

        # Start building in background
        def run_build():
            from .build_service import BuildService
            BuildService.build_from_session(session.session_token)

        thread = threading.Thread(target=run_build, daemon=True)
        thread.start()

        return Response({
            'success': True,
            'session_token': session.session_token,
            'message': 'Building started (dev mode - no email required)',
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
            
            # Get the latest progress from events (for smooth progress updates)
            latest_progress_event = session.events.filter(
                event_type='build_progress'
            ).order_by('-timestamp').first()
            
            if latest_progress_event and latest_progress_event.event_data:
                build_progress = latest_progress_event.event_data.get('progress', 0)
            
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
                
                # Only sync status from project if session is not currently building
                # This prevents race condition where polling overwrites 'building' status
                if project.status == 'deployed' and session.status != 'building':
                    build_progress = 100
                    session.status = 'deployed'
                    session.save()
                elif project.status == 'deploying' and build_progress < 85:
                    build_progress = 85
                elif project.status == 'ready' and build_progress < 70:
                    build_progress = 70
            
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


def _keyword_detect_intent(user_request: str, has_pending_change: bool = False) -> str:
    """
    Keyword-based intent detection fallback.
    Returns: 'conversation', 'change_request', or 'confirmation'
    """
    request_lower = user_request.lower().strip()

    # Confirmation patterns - short affirmative responses
    confirmation_words = [
        'yes', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay', 'go ahead',
        'do it', 'confirm', 'confirmed', 'proceed', 'approved', 'looks good',
        'go for it', 'absolutely', 'definitely', 'please do', 'make it so',
        'sounds good', 'lets go', "let's go", 'ship it', 'perfect',
    ]
    if has_pending_change:
        for word in confirmation_words:
            if request_lower == word or request_lower.rstrip('.!') == word:
                return 'confirmation'

    # Conversation patterns - greetings, thanks, questions, feedback
    conversation_indicators = [
        # Greetings
        'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
        # Thanks/positive feedback
        'thanks', 'thank you', 'great', 'awesome', 'nice', 'perfect',
        'love it', 'looks good', 'cool', 'sounds good', 'ok', 'got it',
        'amazing', 'wonderful', 'fantastic', 'brilliant', 'excellent',
        'nice work', 'good job', 'well done',
        # Questions
        'what ', 'which ', 'how ', 'can you ', 'could you ', 'would you ',
        'is it ', 'are there ', 'do you ', 'does ', 'why ', 'where ', 'when ',
        'tell me ', 'explain ', 'show me ', 'list ', 'suggestions',
        'options', 'ideas', 'recommend', 'what are', 'what is', 'how do',
        'can i ', 'should i ', 'what if', 'is there', 'are you able',
        # Feedback/opinions
        'i dont like', "i don't like", 'i think', 'looks ', 'too ',
        'not sure', 'maybe ', 'perhaps ', 'seems ', 'feels ',
        'i prefer', 'i wish', 'i want to understand', 'curious about',
        'wondering ', 'thoughts on', 'opinion on', 'feedback on',
        # Bug reports (conversational, not change requests)
        'still nothing', 'still not', 'not working', 'doesnt work',
        "doesn't work", 'broken', 'blank', 'empty', 'nothing happens',
        'nothing changed', 'same thing', 'no change', 'didnt work',
        "didn't work", 'still the same', 'still broken', 'still blank',
        'still empty',
    ]

    # Question mark = conversation
    if request_lower.rstrip().endswith('?'):
        return 'conversation'

    # Check conversation indicators
    for indicator in conversation_indicators:
        if request_lower.startswith(indicator) or request_lower == indicator or f' {indicator}' in request_lower:
            return 'conversation'

    # Short messages without explicit change verbs are likely conversational
    change_verbs = ['add ', 'change ', 'make ', 'remove ', 'delete ', 'update ', 'fix ', 'move ', 'replace ', 'put ', 'set ', 'create ']
    if len(request_lower) < 15:
        for verb in change_verbs:
            if request_lower.startswith(verb):
                return 'change_request'
        return 'conversation'

    # Default to change_request for longer messages with no conversation match
    return 'change_request'


def detect_intent(user_request: str, has_pending_change: bool = False) -> str:
    """
    Detect intent from user message using AI classification (Haiku).
    Falls back to keyword-based detection if AI call fails.
    Returns: 'conversation', 'change_request', or 'confirmation'
    """
    try:
        from apps.ai_engine.ai_client import AIClient

        pending_context = ""
        if has_pending_change:
            pending_context = "IMPORTANT: There is currently a PENDING CHANGE proposal that the user has not yet confirmed or rejected."

        classification_prompt = f"""Classify this website builder chat message into exactly one category.

{pending_context}

Categories:
- conversation: greetings, thanks, feedback, questions, general chat, compliments, opinions
- change_request: explicit request to modify, add, remove, or change something in the website
- confirmation: user confirming/approving a previously proposed change (yes, go ahead, do it, sure, ok, confirmed)

Message: "{user_request}"

Reply with ONLY the category name (conversation, change_request, or confirmation). Nothing else."""

        client = AIClient("claude-haiku")
        messages = [
            {"role": "user", "content": classification_prompt}
        ]
        result = client.chat_completion(messages, temperature=0.0, max_tokens=20)
        intent = result.strip().lower().replace('"', '').replace("'", "")

        # Validate the AI response is one of our categories
        if intent in ('conversation', 'change_request', 'confirmation'):
            return intent

        # AI returned unexpected value - fall back to keywords
        return _keyword_detect_intent(user_request, has_pending_change)

    except Exception:
        # AI call failed - use keyword fallback
        return _keyword_detect_intent(user_request, has_pending_change)


class ModifyBuildView(APIView):
    """
    Modify existing website - makes TARGETED changes, not full rebuild.
    Only rebuilds from scratch if explicitly requested or no existing code.
    """
    permission_classes = [AllowAny]

    def handle_conversation(self, session, user_request: str, intent: str):
        """
        Handle conversational messages (questions/feedback) without code modification.
        Uses fast Haiku model for quick responses.
        """
        from apps.ai_engine.ai_client import AIClient

        # Build context about the current project
        project_context = ""
        if session.converted_to_project:
            project = session.converted_to_project
            project_context = f"""
Current project: {project.name}
Description: {project.description}
Status: {project.status}
"""

        # Create conversational prompt
        system_prompt = f"""You are a helpful assistant for Faibric, an AI website builder.
The user is chatting with you about their website project.

{project_context}

Respond conversationally and helpfully. Be concise but friendly.
If they ask about colors, features, or design options, give them helpful suggestions.
If they have feedback, acknowledge it and ask clarifying questions.
Do NOT generate any code. Just have a natural conversation.
Keep responses under 3 sentences unless they need more detail."""

        try:
            client = AIClient("claude-haiku")  # Fast model for conversation
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_request}
            ]
            response = client.chat_completion(messages, temperature=0.7, max_tokens=500)
            return {
                'mode': 'conversation',
                'response': response,
                'intent': intent,
            }
        except Exception as e:
            return {
                'mode': 'conversation',
                'response': "I'd be happy to help! Could you tell me more about what you'd like to know?",
                'intent': intent,
                'error': str(e),
            }

    def handle_change_confirmation(self, session, project, user_request: str):
        """
        Generate a confirmation message for a change request.
        Stores the pending change and returns a confirmation prompt.
        """
        from apps.ai_engine.ai_client import AIClient

        # Store the pending modification
        try:
            project.pending_modification = user_request
            project.save(update_fields=['pending_modification'])
        except Exception:
            # If storing fails, let the build proceed directly
            return None

        # Generate a confirmation message using Haiku
        project_context = ""
        if project:
            project_context = f"Project: {project.name}\nDescription: {project.description}\n"

        confirmation_prompt = f"""You are a helpful assistant for Faibric, an AI website builder.
The user wants to make a change to their website. Before making it, confirm what will happen.

{project_context}

User's request: "{user_request}"

Write a SHORT confirmation message (2-3 sentences) that:
1. Acknowledges what they want changed
2. Briefly describes what will be modified
3. Asks them to confirm (e.g. "Should I go ahead?")

Be concise and friendly. Do NOT generate any code."""

        try:
            client = AIClient("claude-haiku")
            messages = [
                {"role": "user", "content": confirmation_prompt}
            ]
            response = client.chat_completion(messages, temperature=0.7, max_tokens=300)
            return {
                'mode': 'conversation',
                'response': response,
                'intent': 'change_confirmation',
                'pending_change': True,
            }
        except Exception:
            # If AI fails, use a simple template
            return {
                'mode': 'conversation',
                'response': f'I\'ll make this change: "{user_request[:100]}". Should I go ahead?',
                'intent': 'change_confirmation',
                'pending_change': True,
            }

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

        # Check if there's a pending modification for context
        has_pending_change = False
        project = session.converted_to_project
        if project and project.pending_modification:
            has_pending_change = True

        # INTENT DETECTION: AI-based with keyword fallback
        intent = detect_intent(user_request, has_pending_change)

        # Handle conversation intent (questions, thanks, greetings, feedback)
        if intent == 'conversation':
            result = self.handle_conversation(session, user_request, intent)
            return Response(result)

        # Handle confirmation intent
        if intent == 'confirmation':
            if has_pending_change and project:
                # Retrieve the pending change and trigger the actual build
                pending_request = project.pending_modification
                project.pending_modification = None
                project.save(update_fields=['pending_modification'])
                # Use the stored pending request as the actual modification
                user_request = pending_request
                # Fall through to the modification/rebuild logic below
            else:
                # No pending change - treat as conversation
                result = self.handle_conversation(session, user_request, 'conversation')
                return Response(result)

        # Handle change_request intent - ask for confirmation first
        if intent == 'change_request' and project:
            confirmation_result = self.handle_change_confirmation(session, project, user_request)
            if confirmation_result:
                return Response(confirmation_result)

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
                from apps.deployment.hybrid_deployer import get_hybrid_deployer
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

                    # Deploy using HybridDeployer with session_token
                    # CRITICAL: session_token must be passed so it's injected into the deployed HTML
                    # This allows future modifications to work (Builder uses session_token to call /api/onboarding/modify/)
                    hybrid = get_hybrid_deployer()

                    # Detect if originally deployed to Render - modifications must go to same provider
                    deploy_kwargs = dict(
                        project_name=project.name,
                        app_code=new_code,
                        project_id=str(project.id),
                        session_token=session_token,
                    )
                    current_url = getattr(project, 'deployment_url', '') or ''
                    if 'onrender.com' in current_url:
                        deploy_kwargs['force_provider'] = 'render'
                        deploy_kwargs['needs_backend'] = True

                    deploy_result = hybrid.deploy(**deploy_kwargs)
                    
                    # Update URLs (deploy_result is a DeploymentResult dataclass)
                    if deploy_result.success:
                        project.deployment_url = deploy_result.url or ''
                        project.status = 'deployed'
                        project.save()

                        session.status = 'deployed'
                        session.save()

                        SessionEvent.objects.create(
                            session=session,
                            event_type='build_progress',
                            event_data={'message': f"Changes deployed: {deploy_result.url}"}
                        )
                    else:
                        # Deployment failed
                        logger.error(f"Modification deployment failed: {deploy_result.error}")
                        SessionEvent.objects.create(
                            session=session,
                            event_type='error',
                            event_data={'error': f"Deployment failed: {deploy_result.error}"}
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

        # Paywall check: enforce app limits before allowing build
        if session.converted_to_tenant:
            from apps.billing.models import Subscription
            tenant = session.converted_to_tenant
            subscription = Subscription.objects.filter(tenant=tenant).first()
            app_count = tenant.projects.count()
            if subscription:
                if subscription.plan != 'enterprise' and app_count >= subscription.max_apps:
                    return Response({
                        'error': 'upgrade_required',
                        'message': f'{subscription.get_plan_display()} plan limited to {subscription.max_apps} apps. Upgrade to continue.',
                        'upgrade_url': '/pricing',
                    }, status=402)
            else:
                if app_count >= 3:
                    return Response({
                        'error': 'upgrade_required',
                        'message': 'Free plan limited to 3 apps. Upgrade to continue.',
                        'upgrade_url': '/pricing',
                    }, status=402)

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


# ============================================
# Visual Edit (from deployed previews)
# ============================================

class VisualEditView(APIView):
    """
    Handle visual edits from deployed previews.
    Users can click elements in the preview and request changes.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Apply a visual edit to the project.

        Accepts:
        - session_token: Session identifier
        - selector: CSS selector of the element
        - element_type: text, button, image, or style
        - current_value: Current value of the element
        - new_value: Desired new value
        """
        session_token = request.data.get('session_token')
        selector = request.data.get('selector', '')
        element_type = request.data.get('element_type', 'text')
        current_value = request.data.get('current_value', '')
        new_value = request.data.get('new_value', '')

        if not session_token:
            return Response({
                'success': False,
                'error': 'Session token required.',
            }, status=400)

        try:
            session = LandingSession.objects.get(session_token=session_token)
        except LandingSession.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Session not found.',
            }, status=404)

        if not session.converted_to_project:
            return Response({
                'success': False,
                'error': 'No project associated with this session.',
            }, status=404)

        # Build edit prompt from element info
        edit_prompt = f"Change the {element_type}"
        if selector:
            edit_prompt += f" at '{selector}'"
        if current_value:
            edit_prompt += f" from '{current_value}'"
        if new_value:
            edit_prompt += f" to '{new_value}'"

        # Log the visual edit event
        SessionEvent.objects.create(
            session=session,
            event_type='visual_edit',
            event_data={
                'selector': selector,
                'element_type': element_type,
                'current_value': current_value,
                'new_value': new_value,
                'edit_prompt': edit_prompt,
            }
        )

        return Response({
            'success': True,
            'message': 'Edit applied',
            'edit_prompt': edit_prompt,
        })


class SectionOperationsView(APIView):
    """
    Handle section-level operations for drag-and-drop page editor.
    Supports adding, removing, reordering, and duplicating page sections.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Perform section operations on existing page HTML.

        Accepts:
        - session_token: Session identifier (optional if project_id provided)
        - project_id: Project ID (optional if session_token provided)
        - action: One of add_section, remove_section, reorder_sections, duplicate_section
        - section_type: (for add_section) Type of section to add
        - position: (for add_section) Position index for the new section
        - section_id: (for remove_section, duplicate_section) ID of the target section
        - section_ids: (for reorder_sections) Ordered list of section IDs
        """
        import json
        import logging
        import uuid
        import anthropic
        from django.conf import settings
        from apps.projects.models import Project
        from apps.ai_engine.v3.prompts import (
            GENERATE_SECTION_PROMPT,
            REMOVE_SECTION_PROMPT,
            REORDER_SECTIONS_PROMPT,
            SECTION_TYPES,
        )

        logger = logging.getLogger(__name__)

        session_token = request.data.get('session_token')
        project_id = request.data.get('project_id')
        action = request.data.get('action')

        if not action:
            return Response({
                'success': False,
                'error': 'action is required.',
            }, status=400)

        if not session_token and not project_id:
            return Response({
                'success': False,
                'error': 'Either session_token or project_id is required.',
            }, status=400)

        valid_actions = ['add_section', 'remove_section', 'reorder_sections', 'duplicate_section']
        if action not in valid_actions:
            return Response({
                'success': False,
                'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}',
            }, status=400)

        # Resolve project from session_token or project_id
        session = None
        project = None

        if project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Project not found.',
                }, status=404)
            # Try to find associated session for event logging
            session = LandingSession.objects.filter(
                converted_to_project=project
            ).first()
        elif session_token:
            try:
                session = LandingSession.objects.get(session_token=session_token)
            except LandingSession.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Session not found.',
                }, status=404)
            project = session.converted_to_project

        if not project and session:
            # Auto-create a project for the session so the Section Editor
            # works even when the AI build service never ran.
            from django.contrib.auth import get_user_model as _get_user_model
            from apps.tenants.models import Tenant, TenantMembership
            import secrets as _secrets

            if not session.converted_to_user:
                _User = _get_user_model()
                _username = f"user_{_secrets.token_hex(4)}"
                _email = session.email or f"{_username}@faibric.app"
                _user = _User.objects.create_user(
                    username=_username, email=_email, password=None,
                )
                _tenant = Tenant.objects.create(
                    name=f"{_username}'s Workspace",
                    slug=f"ws-{_secrets.token_hex(4)}",
                    owner=_user,
                )
                TenantMembership.objects.create(
                    tenant=_tenant, user=_user, role='owner', is_active=True,
                )
                session.converted_to_user = _user
                session.converted_to_tenant = _tenant
                session.save()

            _clean_name = (session.initial_request or 'Untitled')[:40].replace(':', '').replace('/', ' ')
            _unique_suffix = _secrets.token_hex(4)
            project = Project.objects.create(
                tenant=session.converted_to_tenant,
                user=session.converted_to_user,
                name=f"{_clean_name}_{_unique_suffix}",
                description=session.initial_request or '',
                user_prompt=session.initial_request or '',
                status='draft',
            )
            session.converted_to_project = project
            session.save()

        if not project:
            return Response({
                'success': False,
                'error': 'No project found. Provide a valid session_token or project_id.',
            }, status=404)

        # Allow section operations even without existing frontend_code
        # This enables building pages from scratch via the Section Editor

        # Get existing code (may be empty if building from scratch)
        current_html = ''
        if project.frontend_code:
            try:
                code_data = json.loads(project.frontend_code)
                if isinstance(code_data, dict) and 'App.tsx' in code_data:
                    current_html = code_data['App.tsx']
                else:
                    current_html = str(project.frontend_code)
            except (json.JSONDecodeError, TypeError):
                current_html = str(project.frontend_code)

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        try:
            if action == 'add_section':
                section_type = request.data.get('section_type', '')
                position = request.data.get('position', -1)

                if section_type not in SECTION_TYPES:
                    return Response({
                        'success': False,
                        'error': f'Invalid section_type. Must be one of: {", ".join(SECTION_TYPES)}',
                    }, status=400)

                section_id = f'{section_type}-{uuid.uuid4().hex[:8]}'
                context = f'This section will be inserted at position {position} in the page.'
                if current_html:
                    context += f'\n\nEXISTING PAGE (for style consistency):\n{current_html[:2000]}'

                prompt = GENERATE_SECTION_PROMPT.format(
                    section_type=section_type,
                    section_id=section_id,
                    context=context,
                )

                response = client.messages.create(
                    model='claude-sonnet-4-20250514',
                    max_tokens=2048,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                new_section_html = response.content[0].text

                if session:
                    SessionEvent.objects.create(
                        session=session,
                        event_type='section_operation',
                        event_data={
                            'action': 'add_section',
                            'section_type': section_type,
                            'section_id': section_id,
                            'position': position,
                        }
                    )

                return Response({
                    'success': True,
                    'action': 'add_section',
                    'section_id': section_id,
                    'section_type': section_type,
                    'generated_html': new_section_html,
                    'position': position,
                })

            elif action == 'remove_section':
                section_id = request.data.get('section_id', '')
                if not section_id:
                    return Response({
                        'success': False,
                        'error': 'section_id is required for remove_section.',
                    }, status=400)

                prompt = REMOVE_SECTION_PROMPT.format(
                    current_html=current_html,
                    section_id=section_id,
                )

                response = client.messages.create(
                    model='claude-sonnet-4-20250514',
                    max_tokens=4096,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                updated_html = response.content[0].text

                project.frontend_code = json.dumps({'App.tsx': updated_html})
                project.save()

                if session:
                    SessionEvent.objects.create(
                        session=session,
                        event_type='section_operation',
                        event_data={
                            'action': 'remove_section',
                            'section_id': section_id,
                        }
                    )

                return Response({
                    'success': True,
                    'action': 'remove_section',
                    'section_id': section_id,
                    'updated_html': updated_html,
                })

            elif action == 'reorder_sections':
                section_ids = request.data.get('section_ids', [])
                if not section_ids or not isinstance(section_ids, list):
                    return Response({
                        'success': False,
                        'error': 'section_ids (list) is required for reorder_sections.',
                    }, status=400)

                section_order = '\n'.join(f'{i+1}. {sid}' for i, sid in enumerate(section_ids))
                prompt = REORDER_SECTIONS_PROMPT.format(
                    current_html=current_html,
                    section_order=section_order,
                )

                response = client.messages.create(
                    model='claude-sonnet-4-20250514',
                    max_tokens=4096,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                updated_html = response.content[0].text

                project.frontend_code = json.dumps({'App.tsx': updated_html})
                project.save()

                if session:
                    SessionEvent.objects.create(
                        session=session,
                        event_type='section_operation',
                        event_data={
                            'action': 'reorder_sections',
                            'section_ids': section_ids,
                        }
                    )

                return Response({
                    'success': True,
                    'action': 'reorder_sections',
                    'section_ids': section_ids,
                    'updated_html': updated_html,
                })

            elif action == 'duplicate_section':
                section_id = request.data.get('section_id', '')
                if not section_id:
                    return Response({
                        'success': False,
                        'error': 'section_id is required for duplicate_section.',
                    }, status=400)

                new_section_id = f'{section_id}-copy-{uuid.uuid4().hex[:6]}'

                prompt = f"""You are modifying an existing HTML page for a website builder.
The user wants to duplicate a section.

CURRENT PAGE HTML:
{current_html}

SECTION TO DUPLICATE: The section with id="{section_id}"

Create an exact copy of this section and insert it immediately after the original.
Change the id of the copy to "{new_section_id}".
Keep everything else exactly as-is.

Return the complete HTML with the duplicated section. No markdown, no backticks, no explanations."""

                response = client.messages.create(
                    model='claude-sonnet-4-20250514',
                    max_tokens=4096,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                updated_html = response.content[0].text

                project.frontend_code = json.dumps({'App.tsx': updated_html})
                project.save()

                if session:
                    SessionEvent.objects.create(
                        session=session,
                        event_type='section_operation',
                        event_data={
                            'action': 'duplicate_section',
                            'original_section_id': section_id,
                            'new_section_id': new_section_id,
                        }
                    )

                return Response({
                    'success': True,
                    'action': 'duplicate_section',
                    'original_section_id': section_id,
                    'new_section_id': new_section_id,
                    'updated_html': updated_html,
                })

        except Exception as e:
            logger.exception(f'Section operation failed: {e}')
            return Response({
                'success': False,
                'error': f'Section operation failed: {str(e)}',
            }, status=500)


class AgentModeView(APIView):
    """
    Agent Mode - Autonomous development with debugging and iteration.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Run an autonomous agent task.

        Accepts:
        - session_token: Session identifier
        - task_description: What the agent should do
        - current_code: Optional existing code to modify
        """
        session_token = request.data.get('session_token')
        task_description = request.data.get('task_description', '')
        current_code = request.data.get('current_code')

        if not session_token:
            return Response({
                'success': False,
                'error': 'Session token required.',
            }, status=400)

        if not task_description:
            return Response({
                'success': False,
                'error': 'Task description required.',
            }, status=400)

        try:
            session = LandingSession.objects.get(session_token=session_token)
        except LandingSession.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Session not found.',
            }, status=404)

        # Get project ID if exists
        project_id = None
        if session.converted_to_project:
            project_id = str(session.converted_to_project.id)

        # Run agent task
        agent = AgentModeService(project_id=project_id)
        result = agent.run_agent_task(
            task_description=task_description,
            current_code=current_code
        )

        # Log the agent run
        SessionEvent.objects.create(
            session=session,
            event_type='agent_mode',
            event_data={
                'task': task_description,
                'status': result.get('status'),
                'iterations': result.get('iterations'),
            }
        )

        return Response({
            'success': True,
            'status': result.get('status'),
            'result': result.get('result'),
            'iterations': result.get('iterations'),
        })

