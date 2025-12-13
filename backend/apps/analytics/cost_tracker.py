"""
Cost tracking for AI API usage.
Tracks per-user costs based on Anthropic pricing.
"""
import logging
from decimal import Decimal
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)

# Anthropic Pricing (per million tokens) - Updated Dec 2024
ANTHROPIC_PRICING = {
    'claude-sonnet-4-20250514': {  # Claude Opus 4.5
        'input': Decimal('15.00'),   # $15 per million input tokens
        'output': Decimal('75.00'),  # $75 per million output tokens
    },
    'claude-sonnet-4-20250514': {  # Claude Sonnet 4
        'input': Decimal('3.00'),
        'output': Decimal('15.00'),
    },
    'claude-3-5-haiku-20241022': {  # Claude Haiku 3.5
        'input': Decimal('0.80'),
        'output': Decimal('4.00'),
    },
    'claude-3-haiku-20240307': {  # Claude Haiku 3
        'input': Decimal('0.25'),
        'output': Decimal('1.25'),
    },
}

# Model tiers
EXPENSIVE_MODEL = 'claude-sonnet-4-20250514'  # For new code generation
CHEAP_MODEL = 'claude-3-5-haiku-20241022'      # For summaries, reuse, analysis


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Calculate cost for an API call."""
    pricing = ANTHROPIC_PRICING.get(model, ANTHROPIC_PRICING[EXPENSIVE_MODEL])
    
    input_cost = (Decimal(input_tokens) / Decimal('1000000')) * pricing['input']
    output_cost = (Decimal(output_tokens) / Decimal('1000000')) * pricing['output']
    
    return input_cost + output_cost


def get_model_for_task(task_type: str, has_library_match: bool = False) -> str:
    """
    Get the appropriate model for a task.
    Uses cheap model when possible, expensive only for new code.
    """
    # Tasks that always use cheap model
    cheap_tasks = [
        'classify',      # Classifying user prompts
        'summarize',     # Summarizing chats/logs
        'analyze',       # Analyzing user behavior
        'modify_simple', # Simple modifications to existing code
        'reuse',         # Customizing existing library code
    ]
    
    # Tasks that need expensive model
    expensive_tasks = [
        'generate_new',  # Generating brand new code
    ]
    
    if task_type in cheap_tasks:
        return CHEAP_MODEL
    
    if task_type in expensive_tasks:
        # But if we have library match, use cheap model to customize
        if has_library_match:
            return CHEAP_MODEL
        return EXPENSIVE_MODEL
    
    # Default to cheap for unknown tasks
    return CHEAP_MODEL


class APIUsageTracker:
    """Track API usage per session/user."""
    
    @staticmethod
    def log_usage(
        session_token: str = None,
        user_id: int = None,
        model: str = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        task_type: str = 'unknown',
        success: bool = True,
        metadata: dict = None
    ):
        """Log an API usage event."""
        from apps.analytics.models import APIUsageLog
        
        cost = calculate_cost(model or EXPENSIVE_MODEL, input_tokens, output_tokens)
        
        try:
            log = APIUsageLog.objects.create(
                session_token=session_token,
                user_id=user_id,
                model=model or EXPENSIVE_MODEL,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                task_type=task_type,
                success=success,
                metadata=metadata or {},
            )
            logger.info(f"API usage logged: {model} - ${cost:.6f}")
            return log
        except Exception as e:
            logger.error(f"Failed to log API usage: {e}")
            return None
    
    @staticmethod
    def get_user_stats(user_id: int = None, session_token: str = None):
        """Get usage stats for a user or session."""
        from apps.analytics.models import APIUsageLog
        from django.db.models import Sum, Count, Avg
        
        qs = APIUsageLog.objects.all()
        
        if user_id:
            qs = qs.filter(user_id=user_id)
        elif session_token:
            qs = qs.filter(session_token=session_token)
        else:
            return None
        
        stats = qs.aggregate(
            total_calls=Count('id'),
            total_input_tokens=Sum('input_tokens'),
            total_output_tokens=Sum('output_tokens'),
            total_cost=Sum('cost'),
            success_rate=Avg('success'),
        )
        
        # Add breakdown by model
        model_breakdown = list(
            qs.values('model').annotate(
                calls=Count('id'),
                cost=Sum('cost'),
            ).order_by('-cost')
        )
        
        stats['model_breakdown'] = model_breakdown
        
        return stats
    
    @staticmethod
    def get_daily_stats(date=None):
        """Get stats for a specific day."""
        from apps.analytics.models import APIUsageLog
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        if date is None:
            date = timezone.now().date()
        
        start = datetime.combine(date, datetime.min.time())
        end = start + timedelta(days=1)
        
        qs = APIUsageLog.objects.filter(created_at__gte=start, created_at__lt=end)
        
        return qs.aggregate(
            total_calls=Count('id'),
            total_cost=Sum('cost'),
            unique_sessions=Count('session_token', distinct=True),
        )
