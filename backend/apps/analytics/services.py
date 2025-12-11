"""
Analytics services for forwarding events to external providers.
"""
import json
import base64
import logging
import hashlib
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class MixpanelService:
    """
    Mixpanel analytics integration.
    """
    
    TRACK_URL = "https://api.mixpanel.com/track"
    ENGAGE_URL = "https://api.mixpanel.com/engage"
    
    def __init__(self, token: str, api_secret: str = ''):
        self.token = token
        self.api_secret = api_secret
        self._enabled = bool(token)
    
    @property
    def is_enabled(self):
        return self._enabled
    
    def track(self, distinct_id: str, event_name: str, properties: Dict = None) -> bool:
        """Track an event in Mixpanel."""
        if not self.is_enabled:
            return False
        
        import requests
        
        try:
            data = {
                "event": event_name,
                "properties": {
                    "token": self.token,
                    "distinct_id": distinct_id,
                    "time": int(timezone.now().timestamp()),
                    **(properties or {})
                }
            }
            
            encoded = base64.b64encode(json.dumps([data]).encode()).decode()
            
            response = requests.post(
                self.TRACK_URL,
                data={"data": encoded},
                timeout=5
            )
            
            return response.status_code == 200 and response.text == "1"
            
        except Exception as e:
            logger.error(f"Mixpanel track error: {e}")
            return False
    
    def identify(self, distinct_id: str, properties: Dict) -> bool:
        """Set user profile properties in Mixpanel."""
        if not self.is_enabled:
            return False
        
        import requests
        
        try:
            data = {
                "$token": self.token,
                "$distinct_id": distinct_id,
                "$set": properties
            }
            
            encoded = base64.b64encode(json.dumps([data]).encode()).decode()
            
            response = requests.post(
                self.ENGAGE_URL,
                data={"data": encoded},
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Mixpanel identify error: {e}")
            return False


class GoogleAnalyticsService:
    """
    Google Analytics 4 integration via Measurement Protocol.
    """
    
    MEASUREMENT_URL = "https://www.google-analytics.com/mp/collect"
    
    def __init__(self, measurement_id: str, api_secret: str):
        self.measurement_id = measurement_id
        self.api_secret = api_secret
        self._enabled = bool(measurement_id and api_secret)
    
    @property
    def is_enabled(self):
        return self._enabled
    
    def track(self, client_id: str, event_name: str, params: Dict = None) -> bool:
        """Send event to Google Analytics 4."""
        if not self.is_enabled:
            return False
        
        import requests
        
        try:
            url = f"{self.MEASUREMENT_URL}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"
            
            payload = {
                "client_id": client_id,
                "events": [{
                    "name": event_name,
                    "params": params or {}
                }]
            }
            
            response = requests.post(
                url,
                json=payload,
                timeout=5
            )
            
            # GA4 returns 204 on success
            return response.status_code in [200, 204]
            
        except Exception as e:
            logger.error(f"GA4 track error: {e}")
            return False


class WebhookService:
    """
    Forward events to customer's custom webhook.
    """
    
    def __init__(self, webhook_url: str, secret: str = ''):
        self.webhook_url = webhook_url
        self.secret = secret
        self._enabled = bool(webhook_url)
    
    @property
    def is_enabled(self):
        return self._enabled
    
    def send(self, event_data: Dict) -> bool:
        """Send event to webhook."""
        if not self.is_enabled:
            return False
        
        import requests
        import hmac
        
        try:
            payload = json.dumps(event_data)
            headers = {"Content-Type": "application/json"}
            
            # Add signature if secret is configured
            if self.secret:
                signature = hmac.new(
                    self.secret.encode(),
                    payload.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Faibric-Signature"] = f"sha256={signature}"
            
            response = requests.post(
                self.webhook_url,
                data=payload,
                headers=headers,
                timeout=10
            )
            
            return response.status_code in [200, 201, 202, 204]
            
        except Exception as e:
            logger.error(f"Webhook send error: {e}")
            return False


class AnalyticsProxy:
    """
    Main analytics service that routes events to all configured providers.
    """
    
    def __init__(self, config: 'AnalyticsConfig'):
        self.config = config
        
        # Initialize services based on config
        self.mixpanel = MixpanelService(
            config.mixpanel_token,
            config.mixpanel_api_secret
        ) if config.mixpanel_enabled else None
        
        self.ga = GoogleAnalyticsService(
            config.ga_measurement_id,
            config.ga_api_secret
        ) if config.ga_enabled else None
        
        self.webhook = WebhookService(
            config.webhook_url,
            config.webhook_secret
        ) if config.webhook_enabled else None
    
    def track_event(self, event: 'Event') -> Dict[str, bool]:
        """
        Track event across all configured services.
        Returns dict of {service: success} status.
        """
        results = {}
        
        # Forward to Mixpanel
        if self.mixpanel and self.mixpanel.is_enabled:
            results['mixpanel'] = self.mixpanel.track(
                event.distinct_id,
                event.event_name,
                event.properties
            )
            if results['mixpanel']:
                event.forwarded_to_mixpanel = True
        
        # Forward to Google Analytics
        if self.ga and self.ga.is_enabled:
            # GA uses client_id, we'll use distinct_id hashed
            client_id = hashlib.md5(event.distinct_id.encode()).hexdigest()
            results['ga'] = self.ga.track(
                client_id,
                event.event_name,
                event.properties
            )
            if results['ga']:
                event.forwarded_to_ga = True
        
        # Forward to custom webhook
        if self.webhook and self.webhook.is_enabled:
            results['webhook'] = self.webhook.send({
                'event': event.event_name,
                'distinct_id': event.distinct_id,
                'properties': event.properties,
                'timestamp': event.timestamp.isoformat(),
                'context': event.context,
            })
            if results['webhook']:
                event.forwarded_to_webhook = True
        
        # Save forwarding status
        event.save(update_fields=['forwarded_to_mixpanel', 'forwarded_to_ga', 'forwarded_to_webhook'])
        
        return results
    
    def identify_user(self, distinct_id: str, properties: Dict) -> Dict[str, bool]:
        """Identify user across services."""
        results = {}
        
        if self.mixpanel and self.mixpanel.is_enabled:
            results['mixpanel'] = self.mixpanel.identify(distinct_id, properties)
        
        return results


class FunnelAnalyzer:
    """
    Analyze funnel performance and calculate conversion rates.
    """
    
    @staticmethod
    def get_funnel_stats(funnel: 'Funnel', days: int = 30) -> Dict[str, Any]:
        """Get funnel statistics for the given period."""
        from .models import Event, FunnelConversion
        from django.db.models import Count
        
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        # Get all conversions in period
        conversions = FunnelConversion.objects.filter(
            funnel=funnel,
            started_at__gte=start_date
        )
        
        total_started = conversions.count()
        total_completed = conversions.filter(is_completed=True).count()
        
        # Calculate step-by-step conversion
        steps = funnel.steps.all().order_by('order')
        step_stats = []
        
        for step in steps:
            at_step = conversions.filter(current_step__gte=step.order).count()
            step_stats.append({
                'step': step.order,
                'name': step.name,
                'event_name': step.event_name,
                'count': at_step,
                'rate': (at_step / total_started * 100) if total_started > 0 else 0
            })
        
        return {
            'funnel_id': str(funnel.id),
            'funnel_name': funnel.name,
            'period_days': days,
            'total_started': total_started,
            'total_completed': total_completed,
            'overall_conversion_rate': (total_completed / total_started * 100) if total_started > 0 else 0,
            'steps': step_stats
        }
    
    @staticmethod
    def process_event_for_funnels(event: 'Event'):
        """Check if an event advances any funnel conversions."""
        from .models import Funnel, FunnelStep, FunnelConversion
        
        # Find all active funnels for this tenant
        funnels = Funnel.objects.filter(
            tenant=event.tenant,
            is_active=True
        ).prefetch_related('steps')
        
        for funnel in funnels:
            steps = list(funnel.steps.order_by('order'))
            if not steps:
                continue
            
            # Check if this event matches any step
            matching_step = None
            for step in steps:
                if step.event_name == event.event_name:
                    # Check property filters if any
                    if step.property_filters:
                        if not all(
                            event.properties.get(k) == v 
                            for k, v in step.property_filters.items()
                        ):
                            continue
                    matching_step = step
                    break
            
            if not matching_step:
                continue
            
            # Get or create conversion for this user
            conversion, created = FunnelConversion.objects.get_or_create(
                funnel=funnel,
                distinct_id=event.distinct_id,
                is_completed=False,
                defaults={'current_step': 0}
            )
            
            # Check if this is the next expected step
            if matching_step.order == conversion.current_step + 1:
                # Advance the funnel
                conversion.current_step = matching_step.order
                conversion.completed_steps.append({
                    'step_order': matching_step.order,
                    'timestamp': event.timestamp.isoformat()
                })
                
                # Check if funnel is complete
                if matching_step.order == len(steps):
                    conversion.is_completed = True
                    conversion.completed_at = event.timestamp
                
                conversion.save()


# Pre-built funnel templates
FUNNEL_TEMPLATES = {
    'signup': {
        'name': 'User Signup',
        'description': 'Track user registration flow',
        'steps': [
            {'name': 'Visit Signup Page', 'event_name': 'page_view', 'property_filters': {'page': '/signup'}},
            {'name': 'Start Registration', 'event_name': 'signup_started'},
            {'name': 'Submit Form', 'event_name': 'signup_submitted'},
            {'name': 'Verify Email', 'event_name': 'email_verified'},
            {'name': 'Complete Profile', 'event_name': 'profile_completed'},
        ]
    },
    'purchase': {
        'name': 'Purchase Flow',
        'description': 'Track e-commerce purchase funnel',
        'steps': [
            {'name': 'View Product', 'event_name': 'product_viewed'},
            {'name': 'Add to Cart', 'event_name': 'add_to_cart'},
            {'name': 'Start Checkout', 'event_name': 'checkout_started'},
            {'name': 'Enter Payment', 'event_name': 'payment_info_entered'},
            {'name': 'Complete Purchase', 'event_name': 'purchase_completed'},
        ]
    },
    'onboarding': {
        'name': 'User Onboarding',
        'description': 'Track new user onboarding',
        'steps': [
            {'name': 'First Login', 'event_name': 'first_login'},
            {'name': 'View Tutorial', 'event_name': 'tutorial_started'},
            {'name': 'Complete Tutorial', 'event_name': 'tutorial_completed'},
            {'name': 'Create First Item', 'event_name': 'first_item_created'},
            {'name': 'Invite Team', 'event_name': 'team_invited'},
        ]
    },
    'engagement': {
        'name': 'User Engagement',
        'description': 'Track user return and engagement',
        'steps': [
            {'name': 'First Visit', 'event_name': 'page_view'},
            {'name': 'Return Visit', 'event_name': 'return_visit'},
            {'name': 'Feature Used', 'event_name': 'feature_used'},
            {'name': 'Content Created', 'event_name': 'content_created'},
        ]
    }
}

