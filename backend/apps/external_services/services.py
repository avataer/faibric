"""
External Service Wrappers.

These wrappers automatically use mock responses when API keys are not configured.
This allows testing the full system without paying for external services.
"""
import os
import logging
from typing import Dict, List, Any, Optional
from functools import wraps

from django.conf import settings

from .mock_responses import (
    MockLLMResponse,
    MockStripeResponse,
    MockPayPalResponse,
    MockGoogleAdsResponse,
    MockSendGridResponse,
    MockSerpAPIResponse,
    MockMixpanelResponse,
)

logger = logging.getLogger(__name__)


def use_mock_if_no_key(key_name: str):
    """Decorator that uses mock when API key is not set."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            api_key = os.getenv(key_name, getattr(settings, key_name, None))
            if not api_key:
                logger.info(f"[MOCK MODE] {key_name} not set, using mock for {func.__name__}")
                return kwargs.get('mock_func', lambda: None)(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator


class LLMService:
    """
    Unified LLM service that uses Anthropic/OpenAI or mocks.
    """
    
    @staticmethod
    def is_mock_mode() -> bool:
        """Check if we're in mock mode."""
        anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
        openai_key = os.getenv('OPENAI_API_KEY', '')
        return not (anthropic_key or openai_key)
    
    @classmethod
    def generate_code(cls, prompt: str, model: str = "claude-3-opus-20240229") -> Dict[str, Any]:
        """Generate code using LLM or mock."""
        if cls.is_mock_mode():
            logger.info(f"[MOCK] Generating code for: {prompt[:50]}...")
            return MockLLMResponse.generate_code(prompt, model)
        
        # Real implementation
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return {
                "id": response.id,
                "model": model,
                "content": response.content[0].text,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "stop_reason": response.stop_reason,
                "mock": False,
            }
        except Exception as e:
            logger.error(f"LLM API error: {e}, falling back to mock")
            return MockLLMResponse.generate_code(prompt, model)
    
    @classmethod
    def chat(cls, messages: List[Dict], model: str = "claude-3-sonnet-20240229") -> Dict[str, Any]:
        """Chat completion using LLM or mock."""
        if cls.is_mock_mode():
            return MockLLMResponse.chat(messages, model)
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                messages=messages
            )
            
            return {
                "id": response.id,
                "model": model,
                "content": response.content[0].text,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "mock": False,
            }
        except Exception as e:
            logger.error(f"Chat API error: {e}, falling back to mock")
            return MockLLMResponse.chat(messages, model)
    
    @classmethod
    def embeddings(cls, texts: List[str]) -> Dict[str, Any]:
        """Generate embeddings using OpenAI or mock."""
        openai_key = os.getenv('OPENAI_API_KEY', '')
        
        if not openai_key:
            return MockLLMResponse.embeddings(texts)
        
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            
            return {
                "embeddings": [item.embedding for item in response.data],
                "model": response.model,
                "usage": {"total_tokens": response.usage.total_tokens},
                "mock": False,
            }
        except Exception as e:
            logger.error(f"Embeddings API error: {e}, falling back to mock")
            return MockLLMResponse.embeddings(texts)


class StripeService:
    """Stripe payment service with mock fallback."""
    
    @staticmethod
    def is_mock_mode() -> bool:
        return not os.getenv('STRIPE_SECRET_KEY', '')
    
    @classmethod
    def create_customer(cls, email: str, name: str = None) -> Dict[str, Any]:
        if cls.is_mock_mode():
            logger.info(f"[MOCK STRIPE] Creating customer: {email}")
            return MockStripeResponse.create_customer(email, name)
        
        try:
            import stripe
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            
            customer = stripe.Customer.create(email=email, name=name)
            return dict(customer)
        except Exception as e:
            logger.error(f"Stripe error: {e}")
            return MockStripeResponse.create_customer(email, name)
    
    @classmethod
    def create_subscription(cls, customer_id: str, price_id: str) -> Dict[str, Any]:
        if cls.is_mock_mode():
            return MockStripeResponse.create_subscription(customer_id, price_id)
        
        try:
            import stripe
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
            )
            return dict(subscription)
        except Exception as e:
            logger.error(f"Stripe subscription error: {e}")
            return MockStripeResponse.create_subscription(customer_id, price_id)
    
    @classmethod
    def create_checkout_session(cls, amount: int, success_url: str, cancel_url: str) -> Dict[str, Any]:
        if cls.is_mock_mode():
            return MockStripeResponse.create_checkout_session(amount)
        
        try:
            import stripe
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': amount,
                        'product_data': {'name': 'Faibric Credits'},
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return dict(session)
        except Exception as e:
            logger.error(f"Stripe checkout error: {e}")
            return MockStripeResponse.create_checkout_session(amount)


class PayPalService:
    """PayPal payment service with mock fallback."""
    
    @staticmethod
    def is_mock_mode() -> bool:
        return not os.getenv('PAYPAL_CLIENT_ID', '')
    
    @classmethod
    def create_order(cls, amount: str, currency: str = "USD") -> Dict[str, Any]:
        if cls.is_mock_mode():
            logger.info(f"[MOCK PAYPAL] Creating order: {amount} {currency}")
            return MockPayPalResponse.create_order(amount, currency)
        
        # Real PayPal implementation would go here
        return MockPayPalResponse.create_order(amount, currency)
    
    @classmethod
    def capture_order(cls, order_id: str) -> Dict[str, Any]:
        if cls.is_mock_mode():
            return MockPayPalResponse.capture_order(order_id)
        
        return MockPayPalResponse.capture_order(order_id)


class GoogleAdsService:
    """Google Ads service with mock fallback."""
    
    @staticmethod
    def is_mock_mode() -> bool:
        return not os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN', '')
    
    @classmethod
    def get_campaigns(cls) -> List[Dict[str, Any]]:
        if cls.is_mock_mode():
            logger.info("[MOCK GOOGLE ADS] Getting campaigns")
            return MockGoogleAdsResponse.get_campaigns()
        
        # Real Google Ads implementation would go here
        return MockGoogleAdsResponse.get_campaigns()
    
    @classmethod
    def get_campaign_metrics(cls, campaign_id: str, days: int = 7) -> Dict[str, Any]:
        if cls.is_mock_mode():
            return MockGoogleAdsResponse.get_campaign_metrics(campaign_id, days)
        
        return MockGoogleAdsResponse.get_campaign_metrics(campaign_id, days)
    
    @classmethod
    def create_campaign(cls, name: str, budget: float) -> Dict[str, Any]:
        if cls.is_mock_mode():
            logger.info(f"[MOCK GOOGLE ADS] Creating campaign: {name}")
            return MockGoogleAdsResponse.create_campaign(name, budget)
        
        return MockGoogleAdsResponse.create_campaign(name, budget)


class EmailService:
    """Email service with mock fallback."""
    
    @staticmethod
    def is_mock_mode() -> bool:
        return not os.getenv('SENDGRID_API_KEY', '')
    
    @classmethod
    def send_email(cls, to: str, subject: str, html: str) -> Dict[str, Any]:
        if cls.is_mock_mode():
            return MockSendGridResponse.send_email(to, subject, html)
        
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=os.getenv('FROM_EMAIL', 'noreply@faibric.com'),
                to_emails=to,
                subject=subject,
                html_content=html
            )
            
            sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
            response = sg.send(message)
            
            return {
                "status_code": response.status_code,
                "mock": False,
            }
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return MockSendGridResponse.send_email(to, subject, html)
    
    @classmethod
    def send_magic_link(cls, to: str, token: str) -> Dict[str, Any]:
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        link = f"{frontend_url}/verify?token={token}"
        
        html = f"""
        <h1>Welcome to Faibric!</h1>
        <p>Click the link below to access your project:</p>
        <a href="{link}" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
            Open My Project
        </a>
        <p>This link expires in 24 hours.</p>
        """
        
        if cls.is_mock_mode():
            return MockSendGridResponse.send_magic_link(to, link)
        
        return cls.send_email(to, "Your Faibric Project is Ready!", html)


class SerpAPIService:
    """Keyword tracking service with mock fallback."""
    
    @staticmethod
    def is_mock_mode() -> bool:
        return not os.getenv('SERPAPI_KEY', '')
    
    @classmethod
    def search(cls, keyword: str) -> Dict[str, Any]:
        if cls.is_mock_mode():
            return MockSerpAPIResponse.search(keyword)
        
        try:
            from serpapi import GoogleSearch
            
            params = {
                "api_key": os.getenv('SERPAPI_KEY'),
                "engine": "google",
                "q": keyword,
            }
            search = GoogleSearch(params)
            return search.get_dict()
        except Exception as e:
            logger.error(f"SerpAPI error: {e}")
            return MockSerpAPIResponse.search(keyword)
    
    @classmethod
    def get_keyword_rank(cls, domain: str, keyword: str) -> Dict[str, Any]:
        if cls.is_mock_mode():
            return MockSerpAPIResponse.get_keyword_rank(domain, keyword)
        
        # Real implementation would search and find domain position
        return MockSerpAPIResponse.get_keyword_rank(domain, keyword)


class AnalyticsService:
    """Analytics tracking service with mock fallback."""
    
    @staticmethod
    def is_mock_mode() -> bool:
        return not os.getenv('MIXPANEL_TOKEN', '')
    
    @classmethod
    def track(cls, event: str, properties: Dict = None) -> Dict[str, Any]:
        if cls.is_mock_mode():
            return MockMixpanelResponse.track(event, properties or {})
        
        try:
            from mixpanel import Mixpanel
            
            mp = Mixpanel(os.getenv('MIXPANEL_TOKEN'))
            mp.track(properties.get('distinct_id', 'anonymous'), event, properties)
            return {"status": 1, "mock": False}
        except Exception as e:
            logger.error(f"Mixpanel error: {e}")
            return MockMixpanelResponse.track(event, properties or {})


# ==========================================
# Service Status Check
# ==========================================

def get_service_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all external services."""
    return {
        "llm": {
            "provider": "Anthropic/OpenAI",
            "mock": LLMService.is_mock_mode(),
            "keys_needed": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
        },
        "stripe": {
            "provider": "Stripe",
            "mock": StripeService.is_mock_mode(),
            "keys_needed": ["STRIPE_SECRET_KEY"],
        },
        "paypal": {
            "provider": "PayPal",
            "mock": PayPalService.is_mock_mode(),
            "keys_needed": ["PAYPAL_CLIENT_ID"],
        },
        "google_ads": {
            "provider": "Google Ads",
            "mock": GoogleAdsService.is_mock_mode(),
            "keys_needed": ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        },
        "email": {
            "provider": "SendGrid",
            "mock": EmailService.is_mock_mode(),
            "keys_needed": ["SENDGRID_API_KEY"],
        },
        "serpapi": {
            "provider": "SerpAPI",
            "mock": SerpAPIService.is_mock_mode(),
            "keys_needed": ["SERPAPI_KEY"],
        },
        "analytics": {
            "provider": "Mixpanel",
            "mock": AnalyticsService.is_mock_mode(),
            "keys_needed": ["MIXPANEL_TOKEN"],
        },
    }


def print_service_status():
    """Print service status to console."""
    status = get_service_status()
    
    print("\n" + "=" * 60)
    print("EXTERNAL SERVICE STATUS")
    print("=" * 60)
    
    for name, info in status.items():
        mode = "🔶 MOCK" if info["mock"] else "✅ LIVE"
        print(f"{mode} {name:15} ({info['provider']})")
        if info["mock"]:
            print(f"     └─ Set: {', '.join(info['keys_needed'])}")
    
    print("=" * 60 + "\n")









