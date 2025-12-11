"""
Mock responses for external services.
Used when API keys are not configured.
"""
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any


class MockLLMResponse:
    """Mock responses for LLM APIs (Anthropic/OpenAI)."""
    
    SAMPLE_CODE = '''
import React, { useState, useEffect } from 'react';
import { Card, CardContent, Typography, Grid, Button } from '@mui/material';

const Dashboard = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await fetch('/api/data');
      const result = await response.json();
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <Grid container spacing={3}>
      {data.map((item) => (
        <Grid item xs={12} md={4} key={item.id}>
          <Card>
            <CardContent>
              <Typography variant="h6">{item.title}</Typography>
              <Typography color="textSecondary">{item.description}</Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default Dashboard;
'''

    SAMPLE_BACKEND = '''
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum

from .models import Item, Order
from .serializers import ItemSerializer, OrderSerializer


class ItemViewSet(viewsets.ModelViewSet):
    """API endpoint for items."""
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Item.objects.filter(tenant=self.request.tenant)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get item statistics."""
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'active': qs.filter(is_active=True).count(),
            'total_value': qs.aggregate(Sum('price'))['price__sum'] or 0,
        })
'''

    @classmethod
    def generate_code(cls, prompt: str, model: str = "claude-3-opus") -> Dict[str, Any]:
        """Generate mock code response."""
        time.sleep(random.uniform(0.5, 2.0))  # Simulate API latency
        
        # Determine what type of code to generate based on prompt
        if any(word in prompt.lower() for word in ['react', 'frontend', 'dashboard', 'ui']):
            code = cls.SAMPLE_CODE
            language = "typescript"
        else:
            code = cls.SAMPLE_BACKEND
            language = "python"
        
        input_tokens = len(prompt.split()) * 2
        output_tokens = len(code.split()) * 2
        
        return {
            "id": f"mock-{uuid.uuid4().hex[:8]}",
            "model": model,
            "content": code,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "stop_reason": "end_turn",
            "mock": True,
            "message": f"[MOCK MODE] Generated {language} code for: {prompt[:50]}...",
        }
    
    @classmethod
    def chat(cls, messages: List[Dict], model: str = "claude-3-sonnet") -> Dict[str, Any]:
        """Generate mock chat response."""
        time.sleep(random.uniform(0.3, 1.0))
        
        last_message = messages[-1]["content"] if messages else ""
        
        responses = [
            f"I understand you want to {last_message[:50]}. Let me help you with that.",
            "That's a great idea! Here's how we can implement it:",
            "I can definitely help with that. Let me break it down:",
            "Based on your requirements, I suggest the following approach:",
        ]
        
        response_text = random.choice(responses)
        
        return {
            "id": f"mock-chat-{uuid.uuid4().hex[:8]}",
            "model": model,
            "content": response_text,
            "input_tokens": sum(len(m.get("content", "").split()) for m in messages) * 2,
            "output_tokens": len(response_text.split()) * 2,
            "mock": True,
        }
    
    @classmethod
    def embeddings(cls, texts: List[str]) -> Dict[str, Any]:
        """Generate mock embeddings."""
        time.sleep(random.uniform(0.1, 0.3))
        
        # Generate fake 1536-dimensional embeddings
        embeddings = []
        for text in texts:
            # Use text hash to generate consistent fake embeddings
            seed = hash(text) % 10000
            random.seed(seed)
            embedding = [random.uniform(-1, 1) for _ in range(1536)]
            embeddings.append(embedding)
        
        return {
            "embeddings": embeddings,
            "model": "text-embedding-3-small",
            "usage": {"total_tokens": sum(len(t.split()) for t in texts)},
            "mock": True,
        }


class MockStripeResponse:
    """Mock responses for Stripe API."""
    
    @classmethod
    def create_customer(cls, email: str, name: str = None) -> Dict[str, Any]:
        """Create mock Stripe customer."""
        return {
            "id": f"cus_mock_{uuid.uuid4().hex[:14]}",
            "object": "customer",
            "email": email,
            "name": name,
            "created": int(time.time()),
            "livemode": False,
            "mock": True,
        }
    
    @classmethod
    def create_subscription(cls, customer_id: str, price_id: str) -> Dict[str, Any]:
        """Create mock subscription."""
        return {
            "id": f"sub_mock_{uuid.uuid4().hex[:14]}",
            "object": "subscription",
            "customer": customer_id,
            "status": "active",
            "current_period_start": int(time.time()),
            "current_period_end": int(time.time()) + 30 * 24 * 60 * 60,
            "items": {
                "data": [{"price": {"id": price_id, "unit_amount": 9999}}]
            },
            "livemode": False,
            "mock": True,
        }
    
    @classmethod
    def create_checkout_session(cls, amount: int, currency: str = "usd") -> Dict[str, Any]:
        """Create mock checkout session."""
        return {
            "id": f"cs_mock_{uuid.uuid4().hex[:24]}",
            "object": "checkout.session",
            "url": f"https://checkout.stripe.com/mock/{uuid.uuid4().hex}",
            "amount_total": amount,
            "currency": currency,
            "status": "open",
            "livemode": False,
            "mock": True,
        }
    
    @classmethod
    def create_payment_intent(cls, amount: int, currency: str = "usd") -> Dict[str, Any]:
        """Create mock payment intent."""
        return {
            "id": f"pi_mock_{uuid.uuid4().hex[:24]}",
            "object": "payment_intent",
            "amount": amount,
            "currency": currency,
            "status": "succeeded",
            "client_secret": f"pi_mock_secret_{uuid.uuid4().hex}",
            "livemode": False,
            "mock": True,
        }


class MockPayPalResponse:
    """Mock responses for PayPal API."""
    
    @classmethod
    def create_order(cls, amount: str, currency: str = "USD") -> Dict[str, Any]:
        """Create mock PayPal order."""
        return {
            "id": f"MOCK{uuid.uuid4().hex[:17].upper()}",
            "status": "CREATED",
            "links": [
                {
                    "href": f"https://www.sandbox.paypal.com/mock/approve/{uuid.uuid4().hex}",
                    "rel": "approve",
                    "method": "GET",
                }
            ],
            "mock": True,
        }
    
    @classmethod
    def capture_order(cls, order_id: str) -> Dict[str, Any]:
        """Capture mock PayPal order."""
        return {
            "id": order_id,
            "status": "COMPLETED",
            "purchase_units": [
                {
                    "payments": {
                        "captures": [
                            {
                                "id": f"MOCK{uuid.uuid4().hex[:17].upper()}",
                                "status": "COMPLETED",
                            }
                        ]
                    }
                }
            ],
            "mock": True,
        }


class MockGoogleAdsResponse:
    """Mock responses for Google Ads API."""
    
    @classmethod
    def get_campaigns(cls) -> List[Dict[str, Any]]:
        """Get mock campaigns."""
        campaigns = [
            {
                "id": "mock_campaign_1",
                "name": "SaaS Founders Campaign",
                "status": "ENABLED",
                "budget": {"amount_micros": 75000000},  # $75
            },
            {
                "id": "mock_campaign_2", 
                "name": "Fintech Launch",
                "status": "ENABLED",
                "budget": {"amount_micros": 60000000},  # $60
            },
            {
                "id": "mock_campaign_3",
                "name": "Developers",
                "status": "ENABLED", 
                "budget": {"amount_micros": 50000000},  # $50
            },
        ]
        return [{"campaign": c, "mock": True} for c in campaigns]
    
    @classmethod
    def get_campaign_metrics(cls, campaign_id: str, days: int = 7) -> Dict[str, Any]:
        """Get mock campaign metrics."""
        base_impressions = random.randint(5000, 10000)
        clicks = int(base_impressions * random.uniform(0.06, 0.09))
        conversions = int(clicks * random.uniform(0.15, 0.25))
        spend = clicks * random.uniform(0.40, 0.60)
        
        return {
            "campaign_id": campaign_id,
            "impressions": base_impressions,
            "clicks": clicks,
            "conversions": conversions,
            "cost_micros": int(spend * 1000000),
            "ctr": clicks / base_impressions * 100 if base_impressions > 0 else 0,
            "cpc": spend / clicks if clicks > 0 else 0,
            "cpa": spend / conversions if conversions > 0 else 0,
            "mock": True,
        }
    
    @classmethod
    def create_campaign(cls, name: str, budget: float) -> Dict[str, Any]:
        """Create mock campaign."""
        return {
            "id": f"mock_campaign_{uuid.uuid4().hex[:8]}",
            "name": name,
            "status": "ENABLED",
            "budget": {"amount_micros": int(budget * 1000000)},
            "mock": True,
        }


class MockSendGridResponse:
    """Mock responses for SendGrid API."""
    
    @classmethod
    def send_email(cls, to: str, subject: str, html: str) -> Dict[str, Any]:
        """Send mock email."""
        print(f"[MOCK EMAIL] To: {to}, Subject: {subject}")
        return {
            "status_code": 202,
            "message_id": f"mock_{uuid.uuid4().hex}",
            "mock": True,
        }
    
    @classmethod
    def send_magic_link(cls, to: str, link: str) -> Dict[str, Any]:
        """Send mock magic link email."""
        print(f"[MOCK MAGIC LINK] To: {to}, Link: {link}")
        return {
            "status_code": 202,
            "message_id": f"mock_magic_{uuid.uuid4().hex}",
            "mock": True,
            "link": link,  # Include link for testing
        }


class MockSerpAPIResponse:
    """Mock responses for SerpAPI (keyword tracking)."""
    
    @classmethod
    def search(cls, keyword: str) -> Dict[str, Any]:
        """Mock search results."""
        return {
            "search_metadata": {
                "id": f"mock_{uuid.uuid4().hex[:16]}",
                "status": "Success",
            },
            "organic_results": [
                {
                    "position": i,
                    "title": f"Result {i} for {keyword}",
                    "link": f"https://example{i}.com/{keyword.replace(' ', '-')}",
                    "snippet": f"This is a mock result for {keyword}...",
                }
                for i in range(1, 11)
            ],
            "mock": True,
        }
    
    @classmethod
    def get_keyword_rank(cls, domain: str, keyword: str) -> Dict[str, Any]:
        """Get mock keyword ranking."""
        # Simulate finding domain in results sometimes
        found = random.random() > 0.3
        position = random.randint(1, 50) if found else None
        
        return {
            "keyword": keyword,
            "domain": domain,
            "position": position,
            "found": found,
            "mock": True,
        }


class MockMixpanelResponse:
    """Mock responses for Mixpanel."""
    
    @classmethod
    def track(cls, event: str, properties: Dict) -> Dict[str, Any]:
        """Track mock event."""
        print(f"[MOCK MIXPANEL] Event: {event}, Properties: {properties}")
        return {
            "status": 1,
            "mock": True,
        }
    
    @classmethod
    def identify(cls, user_id: str, properties: Dict) -> Dict[str, Any]:
        """Identify mock user."""
        print(f"[MOCK MIXPANEL] Identify: {user_id}")
        return {
            "status": 1,
            "mock": True,
        }







