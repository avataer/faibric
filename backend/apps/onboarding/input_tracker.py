"""
Input Tracking Service.

Logs ALL user inputs for learning and analytics.
This is Faibric's own analytics - not third-party.
"""
import logging
from typing import Optional, Dict
from django.utils import timezone

from .models import LandingSession, SessionEvent, UserInput

logger = logging.getLogger(__name__)


class InputTracker:
    """
    Tracks all user inputs throughout their journey.
    
    This data is used for:
    1. Understanding what users want to build
    2. Improving AI responses
    3. Identifying common patterns
    4. Session analytics (time spent, engagement)
    """
    
    @staticmethod
    def log_initial_request(
        session: LandingSession,
        request_text: str,
        time_to_type_seconds: int = None,
    ) -> UserInput:
        """Log the initial landing page request."""
        user_input = UserInput.objects.create(
            session=session,
            input_type='initial_request',
            input_text=request_text,
            time_to_type_seconds=time_to_type_seconds,
            device_type=session.device_type,
            browser=session.browser,
            utm_source=session.utm_source,
            utm_campaign=session.utm_campaign,
        )
        
        # Update session stats
        session.total_inputs += 1
        session.total_characters_typed += len(request_text)
        session.update_activity()
        
        # Also log as event
        SessionEvent.objects.create(
            session=session,
            event_type='request_submitted',
            user_input=request_text,
            event_data={
                'char_count': len(request_text),
                'word_count': len(request_text.split()),
                'time_to_type': time_to_type_seconds,
            }
        )
        
        return user_input
    
    @staticmethod
    def log_request_edit(
        session: LandingSession,
        new_text: str,
        previous_text: str = None,
    ) -> UserInput:
        """Log when user edits their request before submitting."""
        user_input = UserInput.objects.create(
            session=session,
            input_type='request_edit',
            input_text=new_text,
            context=f"Previous: {previous_text}" if previous_text else "",
        )
        
        session.total_inputs += 1
        session.total_characters_typed += len(new_text)
        session.update_activity()
        
        SessionEvent.objects.create(
            session=session,
            event_type='request_modified',
            user_input=new_text,
            event_data={
                'previous_text': previous_text[:200] if previous_text else None,
            }
        )
        
        return user_input
    
    @staticmethod
    def log_follow_up(
        session: LandingSession,
        message: str,
        context: str = None,
        user=None,
    ) -> UserInput:
        """Log a follow-up message after initial request."""
        # Find the previous input
        previous = UserInput.objects.filter(session=session).order_by('-timestamp').first()
        
        user_input = UserInput.objects.create(
            session=session,
            user=user,
            input_type='follow_up',
            input_text=message,
            context=context or "",
            previous_input=previous,
        )
        
        session.total_inputs += 1
        session.total_characters_typed += len(message)
        session.update_activity()
        
        SessionEvent.objects.create(
            session=session,
            event_type='chat_message',
            user_input=message,
        )
        
        return user_input
    
    @staticmethod
    def log_feature_request(
        session: LandingSession,
        feature_text: str,
        user=None,
    ) -> UserInput:
        """Log when user requests an additional feature."""
        user_input = UserInput.objects.create(
            session=session,
            user=user,
            input_type='feature_add',
            input_text=feature_text,
        )
        
        session.total_inputs += 1
        session.update_activity()
        
        SessionEvent.objects.create(
            session=session,
            event_type='feature_request',
            user_input=feature_text,
        )
        
        return user_input
    
    @staticmethod
    def log_activity(session_token: str) -> bool:
        """Update session activity (called periodically from frontend)."""
        try:
            session = LandingSession.objects.get(session_token=session_token)
            session.update_activity()
            return True
        except LandingSession.DoesNotExist:
            return False
    
    @staticmethod
    def log_page_leave(session_token: str):
        """Log when user leaves the page."""
        try:
            session = LandingSession.objects.get(session_token=session_token)
            session.update_activity()
            
            SessionEvent.objects.create(
                session=session,
                event_type='page_leave',
                event_data={
                    'total_time_minutes': session.duration_minutes,
                }
            )
        except LandingSession.DoesNotExist:
            pass
    
    @staticmethod
    def log_page_return(session_token: str):
        """Log when user returns to the page."""
        try:
            session = LandingSession.objects.get(session_token=session_token)
            
            SessionEvent.objects.create(
                session=session,
                event_type='page_return',
            )
            
            session.update_activity()
        except LandingSession.DoesNotExist:
            pass
    
    @staticmethod
    def get_session_summary(session_token: str) -> Dict:
        """Get summary of all inputs and time spent for a session."""
        try:
            session = LandingSession.objects.get(session_token=session_token)
        except LandingSession.DoesNotExist:
            return None
        
        inputs = UserInput.objects.filter(session=session).order_by('timestamp')
        events = SessionEvent.objects.filter(session=session).order_by('timestamp')
        
        return {
            'session_id': str(session.id),
            'email': session.email,
            'status': session.status,
            
            # Time tracking
            'duration_minutes': session.duration_minutes,
            'total_time_seconds': session.total_time_seconds,
            'started_at': session.created_at.isoformat(),
            'last_activity': session.last_activity_at.isoformat() if session.last_activity_at else None,
            
            # Input tracking
            'total_inputs': session.total_inputs,
            'total_characters': session.total_characters_typed,
            
            # The initial request
            'initial_request': session.initial_request,
            
            # All inputs chronologically
            'all_inputs': [
                {
                    'type': inp.input_type,
                    'text': inp.input_text,
                    'timestamp': inp.timestamp.isoformat(),
                    'time_to_type': inp.time_to_type_seconds,
                }
                for inp in inputs
            ],
            
            # Timeline of events
            'events': [
                {
                    'type': e.event_type,
                    'data': e.event_data,
                    'input': e.user_input[:100] if e.user_input else None,
                    'timestamp': e.timestamp.isoformat(),
                }
                for e in events
            ],
            
            # Attribution
            'utm_source': session.utm_source,
            'utm_campaign': session.utm_campaign,
            'device': session.device_type,
            'browser': session.browser,
        }


class InputAnalytics:
    """
    Analytics on user inputs for insights.
    """
    
    @staticmethod
    def get_common_requests(limit: int = 20) -> list:
        """Get the most common types of requests."""
        from django.db.models import Count
        from django.db.models.functions import Lower
        
        # Group by similar requests (simplified - could use ML clustering)
        requests = UserInput.objects.filter(
            input_type='initial_request'
        ).values('input_text').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        return list(requests)
    
    @staticmethod
    def get_average_session_duration() -> float:
        """Get average session duration in minutes."""
        from django.db.models import Avg
        
        avg = LandingSession.objects.filter(
            total_time_seconds__gt=0
        ).aggregate(avg=Avg('total_time_seconds'))
        
        return round((avg['avg'] or 0) / 60, 1)
    
    @staticmethod
    def get_input_volume_by_day(days: int = 30) -> list:
        """Get input volume trends."""
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        
        return list(
            UserInput.objects.filter(timestamp__gte=since)
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
    
    @staticmethod
    def get_engagement_metrics() -> Dict:
        """Get engagement metrics."""
        from django.db.models import Avg, Sum, Count
        
        sessions = LandingSession.objects.filter(total_inputs__gt=0)
        
        return {
            'avg_inputs_per_session': sessions.aggregate(avg=Avg('total_inputs'))['avg'] or 0,
            'avg_chars_per_session': sessions.aggregate(avg=Avg('total_characters_typed'))['avg'] or 0,
            'avg_duration_minutes': InputAnalytics.get_average_session_duration(),
            'total_sessions': sessions.count(),
            'total_inputs': UserInput.objects.count(),
        }







