"""
Chat service for handling conversations with AI.
"""
import logging
from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.db import transaction

from .models import ChatWidget, ChatSession, ChatMessage as ChatMessageModel, LLMConfig
from .llm_providers import get_provider, ChatMessage, LLMResponse

logger = logging.getLogger(__name__)


class ChatService:
    """
    Main service for handling chat conversations.
    """
    
    def __init__(self, widget: ChatWidget):
        self.widget = widget
        self.tenant = widget.tenant
        self._llm_config = None
    
    @property
    def llm_config(self) -> LLMConfig:
        if self._llm_config is None:
            self._llm_config, _ = LLMConfig.objects.get_or_create(
                tenant=self.tenant
            )
        return self._llm_config
    
    def get_or_create_session(
        self,
        visitor_id: str,
        page_url: str = '',
        user_agent: str = '',
        ip_address: str = None,
        metadata: Dict = None
    ) -> ChatSession:
        """Get existing active session or create a new one."""
        
        # Look for recent active session
        session = ChatSession.objects.filter(
            widget=self.widget,
            visitor_id=visitor_id,
            is_active=True,
            started_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).first()
        
        if session:
            # Update last activity
            session.last_message_at = timezone.now()
            session.save(update_fields=['last_message_at'])
            return session
        
        # Create new session
        return ChatSession.objects.create(
            widget=self.widget,
            visitor_id=visitor_id,
            page_url=page_url,
            user_agent=user_agent[:500] if user_agent else '',
            ip_address=ip_address,
            metadata=metadata or {}
        )
    
    def send_message(
        self,
        session: ChatSession,
        user_message: str,
        **kwargs
    ) -> ChatMessageModel:
        """
        Process a user message and get AI response.
        Returns the assistant's response message.
        """
        
        # Check rate limits
        if session.messages.count() >= self.widget.max_messages_per_session:
            raise ValueError("Message limit reached for this session")
        
        # Save user message
        ChatMessageModel.objects.create(
            session=session,
            role='user',
            content=user_message
        )
        
        # Build conversation context
        messages = self._build_conversation(session)
        
        # Get AI response
        try:
            response = self._get_ai_response(messages, **kwargs)
            
            # Save assistant message
            assistant_msg = ChatMessageModel.objects.create(
                session=session,
                role='assistant',
                content=response.content,
                model_used=response.model,
                tokens_used=response.tokens_used
            )
            
            # Track usage
            self._track_usage(response.tokens_used)
            
            return assistant_msg
            
        except Exception as e:
            logger.error(f"AI response error: {e}")
            # Return error message
            return ChatMessageModel.objects.create(
                session=session,
                role='assistant',
                content="I'm sorry, I'm having trouble responding right now. Please try again.",
                model_used='error'
            )
    
    def _build_conversation(self, session: ChatSession) -> List[ChatMessage]:
        """Build the conversation context for the AI."""
        messages = []
        
        # System prompt
        system_content = self.widget.system_prompt
        
        # Add knowledge base if available
        if self.widget.knowledge_base:
            system_content += f"\n\n### Knowledge Base:\n{self.widget.knowledge_base}"
        
        # Add session context
        if session.page_url:
            system_content += f"\n\nThe user is currently on page: {session.page_url}"
        
        messages.append(ChatMessage(role='system', content=system_content))
        
        # Add conversation history (last N messages)
        history = session.messages.order_by('created_at')[:20]
        for msg in history:
            messages.append(ChatMessage(role=msg.role, content=msg.content))
        
        return messages
    
    def _get_ai_response(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        """Get response from the configured LLM provider."""
        
        provider_name = self.widget.llm_provider
        model = self.widget.model_name or None
        api_key = self.llm_config.get_api_key(provider_name)
        
        if not api_key:
            raise ValueError(f"No API key configured for {provider_name}")
        
        provider = get_provider(provider_name, api_key, model)
        return provider.chat(messages, **kwargs)
    
    def _track_usage(self, tokens: int):
        """Track token usage for billing."""
        from apps.billing.services import UsageTrackingService
        
        try:
            UsageTrackingService.record_usage(
                tenant=self.tenant,
                usage_type='ai_tokens',
                amount=tokens
            )
        except Exception as e:
            logger.warning(f"Failed to track usage: {e}")
    
    def get_session_messages(self, session: ChatSession) -> List[Dict]:
        """Get all messages in a session."""
        messages = session.messages.all()
        return [
            {
                'id': str(msg.id),
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
            }
            for msg in messages
        ]
    
    def end_session(self, session: ChatSession):
        """End a chat session."""
        session.is_active = False
        session.ended_at = timezone.now()
        session.save(update_fields=['is_active', 'ended_at'])
    
    def escalate_session(self, session: ChatSession, reason: str = ''):
        """Escalate session to human support."""
        session.escalated = True
        session.save(update_fields=['escalated'])
        
        # Add system message
        ChatMessageModel.objects.create(
            session=session,
            role='system',
            content=f"Session escalated to human support. Reason: {reason or 'User requested'}"
        )
        
        # TODO: Send notification to support team
        logger.info(f"Session {session.id} escalated: {reason}")
    
    def rate_message(self, message_id: str, helpful: bool):
        """Rate a message as helpful or not."""
        try:
            message = ChatMessageModel.objects.get(id=message_id)
            message.helpful = helpful
            message.save(update_fields=['helpful'])
        except ChatMessageModel.DoesNotExist:
            pass


class WidgetService:
    """Service for managing chat widgets."""
    
    @staticmethod
    def get_widget_embed_code(widget: ChatWidget) -> str:
        """Generate embed code for a widget."""
        from django.conf import settings
        
        base_url = getattr(settings, 'FAIBRIC_BASE_URL', 'http://localhost:8000')
        
        return f'''<!-- Faibric Chat Widget -->
<script>
  (function(w,d,s,c){{
    w.FaibricChat={{widgetId:c}};
    var f=d.getElementsByTagName(s)[0],j=d.createElement(s);
    j.async=true;j.src='{base_url}/static/chat-widget.js';
    f.parentNode.insertBefore(j,f);
  }})(window,document,'script','{widget.id}');
</script>'''
    
    @staticmethod
    def get_widget_config(widget: ChatWidget) -> Dict:
        """Get widget configuration for frontend."""
        return {
            'id': str(widget.id),
            'theme': widget.theme,
            'primaryColor': widget.primary_color,
            'position': widget.position,
            'welcomeMessage': widget.welcome_message,
            'placeholderText': widget.placeholder_text,
            'collectEmail': widget.collect_email,
            'showPoweredBy': widget.show_powered_by,
            'enableFileUpload': widget.enable_file_upload,
        }







