"""
Credit and LLM logging services.
"""
import logging
import time
from typing import Optional, Dict
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import (
    SubscriptionTier,
    CreditBalance,
    LLMRequest,
    CreditTransaction,
    UsageReport,
)

logger = logging.getLogger(__name__)


# LLM cost per 1000 tokens (Faibric's cost)
LLM_COSTS = {
    # Primary - Claude Opus 4.5 for code generation
    'claude-opus-4.5': {'input': 0.015, 'output': 0.075},
    # Secondary - Claude Sonnet 4 for chat
    'claude-sonnet-4': {'input': 0.003, 'output': 0.015},
    # Fast tasks - Claude Haiku 3.5
    'claude-haiku-3.5': {'input': 0.0008, 'output': 0.004},
    # Embeddings - OpenAI
    'text-embedding-3-small': {'input': 0.00002, 'output': 0},
    # Legacy models (for old records)
    'gpt-4': {'input': 0.03, 'output': 0.06},
    'claude-3-opus': {'input': 0.015, 'output': 0.075},
}


class CreditService:
    """
    Service for managing credits.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def get_or_create_balance(self) -> CreditBalance:
        """Get or create credit balance for tenant."""
        from apps.tenants.models import Tenant
        
        tenant = Tenant.objects.get(id=self.tenant_id)
        
        balance, created = CreditBalance.objects.get_or_create(
            tenant=tenant,
            defaults={
                'period_start': timezone.now(),
                'period_end': timezone.now() + timezone.timedelta(days=30),
                'credits_remaining': 0,
            }
        )
        
        # Check if period needs reset
        if balance.period_end < timezone.now():
            balance.reset_period()
        
        return balance
    
    def get_usage_summary(self) -> Dict:
        """Get usage summary for current period."""
        balance = self.get_or_create_balance()
        
        return {
            'tier': balance.subscription_tier.name if balance.subscription_tier else 'Free',
            'credits_remaining': balance.credits_remaining,
            'credits_used': balance.credits_used_this_period,
            'purchased_credits': balance.purchased_credits,
            'total_available': balance.credits_remaining + balance.purchased_credits,
            'tokens_used': balance.tokens_used_this_period,
            'period_start': balance.period_start.isoformat(),
            'period_end': balance.period_end.isoformat(),
            'total_requests': balance.total_requests,
        }
    
    def check_credits(self, amount: int = 1) -> Dict:
        """Check if tenant has enough credits."""
        balance = self.get_or_create_balance()
        has_credits = balance.has_credits(amount)
        
        return {
            'has_credits': has_credits,
            'credits_remaining': balance.credits_remaining,
            'purchased_credits': balance.purchased_credits,
            'total_available': balance.credits_remaining + balance.purchased_credits,
        }
    
    @transaction.atomic
    def use_credits(
        self,
        amount: int = 1,
        tokens: int = 0,
        llm_request: Optional[LLMRequest] = None,
        description: str = ''
    ) -> bool:
        """Use credits and log transaction."""
        balance = self.get_or_create_balance()
        
        if not balance.use_credit(amount, tokens):
            return False
        
        # Log transaction
        CreditTransaction.objects.create(
            tenant_id=self.tenant_id,
            transaction_type='usage',
            credits=-amount,
            description=description or f"LLM request ({tokens} tokens)",
            llm_request=llm_request,
            balance_after=balance.credits_remaining + balance.purchased_credits,
        )
        
        return True
    
    @transaction.atomic
    def purchase_credits(
        self,
        amount: int,
        price: Decimal,
        stripe_payment_id: str = ''
    ) -> CreditTransaction:
        """Purchase additional credits."""
        balance = self.get_or_create_balance()
        balance.add_purchased_credits(amount)
        
        transaction = CreditTransaction.objects.create(
            tenant_id=self.tenant_id,
            transaction_type='purchase',
            credits=amount,
            amount_paid=price,
            stripe_payment_id=stripe_payment_id,
            description=f"Purchased {amount} credits",
            balance_after=balance.credits_remaining + balance.purchased_credits,
        )
        
        return transaction
    
    @transaction.atomic
    def apply_subscription(self, tier: SubscriptionTier) -> CreditBalance:
        """Apply subscription tier to tenant."""
        balance = self.get_or_create_balance()
        
        old_tier = balance.subscription_tier
        balance.subscription_tier = tier
        
        # Add monthly credits
        if old_tier != tier:
            balance.credits_remaining = tier.monthly_credits
            balance.period_start = timezone.now()
            balance.period_end = timezone.now() + timezone.timedelta(days=30)
        
        balance.save()
        
        # Log transaction
        CreditTransaction.objects.create(
            tenant_id=self.tenant_id,
            transaction_type='subscription',
            credits=tier.monthly_credits,
            description=f"Monthly credits from {tier.name} subscription",
            balance_after=balance.credits_remaining + balance.purchased_credits,
        )
        
        return balance


class LLMLoggingService:
    """
    Service for logging LLM requests and responses.
    """
    
    def __init__(self, tenant_id: str, user_id: str = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.credit_service = CreditService(tenant_id)
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """Calculate Faibric's cost for the request."""
        costs = LLM_COSTS.get(model, {'input': 0.01, 'output': 0.03})
        
        input_cost = (input_tokens / 1000) * costs['input']
        output_cost = (output_tokens / 1000) * costs['output']
        
        return Decimal(str(input_cost + output_cost))
    
    @transaction.atomic
    def log_request(
        self,
        request_type: str,
        model: str,
        prompt: str,
        response: str,
        input_tokens: int,
        output_tokens: int,
        response_time_ms: int = None,
        project_id: str = None,
        session_id: str = None,
        system_prompt: str = '',
        was_error: bool = False,
        error_message: str = '',
        request_metadata: Dict = None,
        response_metadata: Dict = None,
    ) -> LLMRequest:
        """
        Log an LLM request and charge credits.
        """
        total_tokens = input_tokens + output_tokens
        estimated_cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        # Create the log entry
        llm_request = LLMRequest.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            request_type=request_type,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            response=response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            credits_charged=1,  # 1 credit per request
            project_id=project_id,
            session_id=session_id or '',
            response_time_ms=response_time_ms,
            was_error=was_error,
            error_message=error_message,
            request_metadata=request_metadata or {},
            response_metadata=response_metadata or {},
        )
        
        # Charge credits (1 per request + track tokens)
        if not was_error:
            self.credit_service.use_credits(
                amount=1,
                tokens=total_tokens,
                llm_request=llm_request,
                description=f"{request_type} using {model}"
            )
        
        return llm_request
    
    def rate_request(
        self,
        request_id: str,
        rating: int = None,
        was_accepted: bool = None,
        was_modified: bool = None
    ) -> bool:
        """Record user feedback on a request."""
        try:
            request = LLMRequest.objects.get(id=request_id)
            
            if rating is not None:
                request.user_rating = min(5, max(1, rating))
            if was_accepted is not None:
                request.was_accepted = was_accepted
            if was_modified is not None:
                request.was_modified = was_modified
            
            request.save()
            return True
        except LLMRequest.DoesNotExist:
            return False


class UsageReportService:
    """
    Service for generating usage reports.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def generate_daily_report(self, date=None) -> UsageReport:
        """Generate daily usage report."""
        from datetime import date as date_type
        
        if date is None:
            date = (timezone.now() - timezone.timedelta(days=1)).date()
        
        next_date = date + timezone.timedelta(days=1)
        
        # Get all requests for the day
        requests = LLMRequest.objects.filter(
            tenant_id=self.tenant_id,
            created_at__date=date
        )
        
        # Aggregate stats
        total_requests = requests.count()
        total_tokens = sum(r.total_tokens for r in requests)
        total_input = sum(r.input_tokens for r in requests)
        total_output = sum(r.output_tokens for r in requests)
        total_cost = sum(r.estimated_cost for r in requests)
        
        # By model
        usage_by_model = {}
        for r in requests:
            if r.model not in usage_by_model:
                usage_by_model[r.model] = {'requests': 0, 'tokens': 0}
            usage_by_model[r.model]['requests'] += 1
            usage_by_model[r.model]['tokens'] += r.total_tokens
        
        # By type
        usage_by_type = {}
        for r in requests:
            if r.request_type not in usage_by_type:
                usage_by_type[r.request_type] = {'requests': 0, 'tokens': 0}
            usage_by_type[r.request_type]['requests'] += 1
            usage_by_type[r.request_type]['tokens'] += r.total_tokens
        
        # Quality metrics
        rated = requests.filter(user_rating__isnull=False)
        avg_rating = rated.aggregate(avg=models.Avg('user_rating'))['avg'] if rated.exists() else None
        
        accepted = requests.filter(was_accepted__isnull=False)
        acceptance_rate = (
            accepted.filter(was_accepted=True).count() / accepted.count()
            if accepted.exists() else None
        )
        
        # Create or update report
        report, _ = UsageReport.objects.update_or_create(
            tenant_id=self.tenant_id,
            period_type='daily',
            period_start=date,
            defaults={
                'period_end': next_date,
                'total_requests': total_requests,
                'total_credits_used': total_requests,  # 1 credit per request
                'total_tokens': total_tokens,
                'total_input_tokens': total_input,
                'total_output_tokens': total_output,
                'usage_by_model': usage_by_model,
                'usage_by_type': usage_by_type,
                'estimated_cost': total_cost,
                'average_rating': avg_rating,
                'acceptance_rate': acceptance_rate,
            }
        )
        
        return report


def setup_default_tiers():
    """
    Create default subscription tiers.
    Call this in a migration or management command.
    """
    tiers = [
        {
            'name': 'Free',
            'slug': 'free',
            'price_monthly': Decimal('0'),
            'price_yearly': Decimal('0'),
            'monthly_credits': 50,
            'max_projects': 1,
            'max_team_members': 1,
            'max_storage_gb': 1,
            'max_api_calls_daily': 100,
            'features': [
                'Basic code generation',
                'Community support',
                '1 project',
            ],
            'display_order': 0,
        },
        {
            'name': 'Starter',
            'slug': 'starter',
            'price_monthly': Decimal('19.99'),
            'price_yearly': Decimal('199.99'),
            'monthly_credits': 500,
            'max_projects': 5,
            'max_team_members': 3,
            'max_storage_gb': 10,
            'max_api_calls_daily': 1000,
            'is_popular': True,
            'features': [
                'Advanced code generation',
                'All AI models',
                'Email support',
                '5 projects',
                '3 team members',
                'Custom domains',
            ],
            'display_order': 1,
        },
        {
            'name': 'Pro',
            'slug': 'pro',
            'price_monthly': Decimal('99.99'),
            'price_yearly': Decimal('999.99'),
            'monthly_credits': 5000,
            'max_projects': 50,
            'max_team_members': 20,
            'max_storage_gb': 100,
            'max_api_calls_daily': 10000,
            'features': [
                'Unlimited code generation',
                'All AI models',
                'Priority support',
                'Unlimited projects',
                '20 team members',
                'Custom domains',
                'White-label',
                'API access',
                'Analytics',
            ],
            'display_order': 2,
        },
    ]
    
    for tier_data in tiers:
        SubscriptionTier.objects.update_or_create(
            slug=tier_data['slug'],
            defaults=tier_data
        )


# Import for aggregate
from django.db import models

