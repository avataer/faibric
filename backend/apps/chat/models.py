import uuid
from django.db import models
from django.utils import timezone


class LLMProvider(models.TextChoices):
    """Supported LLM providers."""
    OPENAI = 'openai', 'OpenAI (GPT-4o)'
    ANTHROPIC = 'anthropic', 'Anthropic (Claude)'
    GEMINI = 'gemini', 'Google (Gemini)'
    GROK = 'grok', 'xAI (Grok)'


class ChatWidget(models.Model):
    """
    Configuration for an embeddable chat widget.
    Each tenant can have multiple widgets for different purposes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='chat_widgets'
    )
    
    # Widget identity
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Appearance
    theme = models.CharField(max_length=20, default='light', choices=[
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto (system)'),
    ])
    primary_color = models.CharField(max_length=7, default='#3B82F6')  # Tailwind blue-500
    position = models.CharField(max_length=20, default='bottom-right', choices=[
        ('bottom-right', 'Bottom Right'),
        ('bottom-left', 'Bottom Left'),
    ])
    
    # Widget text
    welcome_message = models.TextField(
        default="👋 Hi! How can I help you today?"
    )
    placeholder_text = models.CharField(
        max_length=200,
        default="Type your message..."
    )
    
    # AI Configuration
    llm_provider = models.CharField(
        max_length=20,
        choices=LLMProvider.choices,
        default=LLMProvider.OPENAI
    )
    model_name = models.CharField(max_length=50, default='gpt-4o-mini')
    
    # System prompt for the AI
    system_prompt = models.TextField(
        default="You are a helpful customer support assistant. Be friendly, concise, and helpful."
    )
    
    # Knowledge base (optional context for AI)
    knowledge_base = models.TextField(
        blank=True,
        help_text="Additional context for the AI (product info, FAQs, etc.)"
    )
    
    # Features
    collect_email = models.BooleanField(default=False)
    show_powered_by = models.BooleanField(default=True)
    enable_file_upload = models.BooleanField(default=False)
    
    # Rate limiting
    max_messages_per_session = models.PositiveIntegerField(default=50)
    max_sessions_per_day = models.PositiveIntegerField(default=100)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class ChatSession(models.Model):
    """
    A chat session between an end-user and the AI.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    widget = models.ForeignKey(
        ChatWidget,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    # Session identification
    visitor_id = models.CharField(max_length=100)  # Anonymous visitor ID
    user_email = models.EmailField(blank=True)
    user_name = models.CharField(max_length=100, blank=True)
    
    # Context
    page_url = models.URLField(blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    escalated = models.BooleanField(default=False)  # Human handoff requested
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['widget', 'visitor_id']),
            models.Index(fields=['widget', 'started_at']),
        ]
    
    def __str__(self):
        return f"Session {self.id} ({self.widget.name})"
    
    @property
    def message_count(self):
        return self.messages.count()


class ChatMessage(models.Model):
    """
    A message in a chat session.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    
    # AI-specific metadata
    model_used = models.CharField(max_length=50, blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    
    # Feedback
    helpful = models.BooleanField(null=True, blank=True)  # User feedback
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
    
    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.role}: {preview}"


class LLMConfig(models.Model):
    """
    LLM API configuration for a tenant.
    Customers can bring their own API keys.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='llm_config'
    )
    
    # Use Faibric's pooled keys or customer's own
    use_own_keys = models.BooleanField(default=False)
    
    # Customer's API keys (encrypted in production)
    openai_api_key = models.CharField(max_length=200, blank=True)
    anthropic_api_key = models.CharField(max_length=200, blank=True)
    gemini_api_key = models.CharField(max_length=200, blank=True)
    grok_api_key = models.CharField(max_length=200, blank=True)
    
    # Default provider preference
    default_provider = models.CharField(
        max_length=20,
        choices=LLMProvider.choices,
        default=LLMProvider.OPENAI
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"LLM config for {self.tenant.name}"
    
    def get_api_key(self, provider: str) -> str:
        """Get API key for a provider."""
        if not self.use_own_keys:
            # Use Faibric's pooled keys from settings
            from django.conf import settings
            keys = {
                'openai': getattr(settings, 'OPENAI_API_KEY', ''),
                'anthropic': getattr(settings, 'ANTHROPIC_API_KEY', ''),
                'gemini': getattr(settings, 'GEMINI_API_KEY', ''),
                'grok': getattr(settings, 'GROK_API_KEY', ''),
            }
            return keys.get(provider, '')
        
        keys = {
            'openai': self.openai_api_key,
            'anthropic': self.anthropic_api_key,
            'gemini': self.gemini_api_key,
            'grok': self.grok_api_key,
        }
        return keys.get(provider, '')






