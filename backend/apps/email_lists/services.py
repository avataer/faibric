"""
Email provider services for Mailchimp, SendGrid, and ConvertKit.
"""
import logging
from typing import Dict, Any, Optional, List
from django.conf import settings

logger = logging.getLogger(__name__)


class MailchimpService:
    """
    Mailchimp integration service.
    """
    
    def __init__(self, api_key: str, server_prefix: str):
        self.api_key = api_key
        self.server_prefix = server_prefix
        self._enabled = bool(api_key and server_prefix)
        self.base_url = f"https://{server_prefix}.api.mailchimp.com/3.0" if server_prefix else ""
    
    @property
    def is_enabled(self):
        return self._enabled
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make authenticated request to Mailchimp."""
        if not self.is_enabled:
            return None
        
        import requests
        from requests.auth import HTTPBasicAuth
        
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.request(
                method,
                url,
                json=data,
                auth=HTTPBasicAuth('anystring', self.api_key),
                timeout=10
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except Exception as e:
            logger.error(f"Mailchimp error: {e}")
            return None
    
    def add_subscriber(self, list_id: str, email: str, 
                       first_name: str = '', last_name: str = '',
                       tags: List[str] = None) -> bool:
        """Add subscriber to Mailchimp list."""
        import hashlib
        
        subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()
        
        data = {
            "email_address": email,
            "status": "subscribed",
            "merge_fields": {}
        }
        
        if first_name:
            data["merge_fields"]["FNAME"] = first_name
        if last_name:
            data["merge_fields"]["LNAME"] = last_name
        if tags:
            data["tags"] = tags
        
        result = self._request(
            'PUT',
            f"lists/{list_id}/members/{subscriber_hash}",
            data
        )
        
        return result is not None
    
    def remove_subscriber(self, list_id: str, email: str) -> bool:
        """Remove subscriber from Mailchimp list."""
        import hashlib
        
        subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()
        
        result = self._request(
            'PATCH',
            f"lists/{list_id}/members/{subscriber_hash}",
            {"status": "unsubscribed"}
        )
        
        return result is not None
    
    def get_lists(self) -> List[Dict]:
        """Get all lists."""
        result = self._request('GET', 'lists')
        if result:
            return result.get('lists', [])
        return []


class SendGridService:
    """
    SendGrid integration service.
    """
    
    BASE_URL = "https://api.sendgrid.com/v3"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._enabled = bool(api_key)
    
    @property
    def is_enabled(self):
        return self._enabled
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make authenticated request to SendGrid."""
        if not self.is_enabled:
            return None
        
        import requests
        
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.request(
                method,
                url,
                json=data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return None
    
    def add_contact(self, email: str, first_name: str = '', 
                    last_name: str = '', list_ids: List[str] = None) -> bool:
        """Add contact to SendGrid."""
        data = {
            "contacts": [{
                "email": email,
                "first_name": first_name,
                "last_name": last_name
            }]
        }
        
        if list_ids:
            data["list_ids"] = list_ids
        
        result = self._request('PUT', 'marketing/contacts', data)
        return result is not None
    
    def remove_contact(self, email: str) -> bool:
        """Remove contact from SendGrid."""
        # First get contact ID
        search_result = self._request(
            'POST',
            'marketing/contacts/search',
            {"query": f"email = '{email}'"}
        )
        
        if not search_result or not search_result.get('result'):
            return False
        
        contact_id = search_result['result'][0]['id']
        
        result = self._request(
            'DELETE',
            f'marketing/contacts?ids={contact_id}'
        )
        
        return result is not None
    
    def send_email(self, to_email: str, from_email: str, from_name: str,
                   subject: str, html_content: str) -> bool:
        """Send a single email via SendGrid."""
        data = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email, "name": from_name},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_content}]
        }
        
        result = self._request('POST', 'mail/send', data)
        return result is not None or result == {}  # SendGrid returns empty on success


class ConvertKitService:
    """
    ConvertKit integration service.
    """
    
    BASE_URL = "https://api.convertkit.com/v3"
    
    def __init__(self, api_key: str, api_secret: str = ''):
        self.api_key = api_key
        self.api_secret = api_secret
        self._enabled = bool(api_key)
    
    @property
    def is_enabled(self):
        return self._enabled
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make request to ConvertKit."""
        if not self.is_enabled:
            return None
        
        import requests
        
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            
            # Add API key to data
            if data is None:
                data = {}
            data['api_key'] = self.api_key
            
            if method == 'GET':
                response = requests.get(url, params=data, timeout=10)
            else:
                response = requests.request(method, url, json=data, timeout=10)
            
            response.raise_for_status()
            return response.json() if response.text else {}
        except Exception as e:
            logger.error(f"ConvertKit error: {e}")
            return None
    
    def add_subscriber_to_form(self, form_id: str, email: str, 
                               first_name: str = '') -> bool:
        """Add subscriber to a ConvertKit form."""
        data = {
            "email": email,
        }
        if first_name:
            data["first_name"] = first_name
        
        result = self._request('POST', f'forms/{form_id}/subscribe', data)
        return result is not None
    
    def unsubscribe(self, email: str) -> bool:
        """Unsubscribe from all ConvertKit lists."""
        result = self._request('PUT', 'unsubscribe', {"email": email})
        return result is not None
    
    def get_forms(self) -> List[Dict]:
        """Get all forms."""
        result = self._request('GET', 'forms')
        if result:
            return result.get('forms', [])
        return []


class EmailListService:
    """
    Main service for managing email list subscriptions.
    Coordinates between internal storage and external providers.
    """
    
    def __init__(self, config: 'EmailConfig'):
        self.config = config
        
        self.mailchimp = MailchimpService(
            config.mailchimp_api_key,
            config.mailchimp_server_prefix
        ) if config.mailchimp_enabled else None
        
        self.sendgrid = SendGridService(
            config.sendgrid_api_key
        ) if config.sendgrid_enabled else None
        
        self.convertkit = ConvertKitService(
            config.convertkit_api_key,
            config.convertkit_api_secret
        ) if config.convertkit_enabled else None
    
    def subscribe(self, email_list: 'EmailList', email: str,
                  first_name: str = '', last_name: str = '',
                  source: str = '', ip_address: str = None,
                  custom_fields: Dict = None) -> 'Subscriber':
        """Subscribe to an email list."""
        from .models import Subscriber
        
        # Check if already exists
        subscriber, created = Subscriber.objects.get_or_create(
            email_list=email_list,
            email=email.lower(),
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'source': source,
                'ip_address': ip_address,
                'custom_fields': custom_fields or {},
                'status': 'pending' if email_list.double_optin else 'subscribed',
            }
        )
        
        if not created:
            # Re-subscribe if previously unsubscribed
            if subscriber.status == 'unsubscribed':
                subscriber.status = 'pending' if email_list.double_optin else 'subscribed'
                subscriber.unsubscribed_at = None
                subscriber.unsubscribe_reason = ''
                subscriber.save()
        
        # If no double opt-in, sync to external providers
        if not email_list.double_optin or subscriber.status == 'subscribed':
            self._sync_to_providers(email_list, subscriber)
        
        email_list.update_subscriber_count()
        
        return subscriber
    
    def confirm_subscription(self, token: str) -> Optional['Subscriber']:
        """Confirm a pending subscription."""
        from .models import Subscriber
        
        try:
            subscriber = Subscriber.objects.get(
                confirmation_token=token,
                status='pending'
            )
            subscriber.confirm()
            
            # Sync to external providers
            self._sync_to_providers(subscriber.email_list, subscriber)
            
            return subscriber
        except Subscriber.DoesNotExist:
            return None
    
    def unsubscribe(self, token: str, reason: str = '') -> Optional['Subscriber']:
        """Unsubscribe using token."""
        from .models import Subscriber
        
        try:
            subscriber = Subscriber.objects.get(unsubscribe_token=token)
            subscriber.unsubscribe(reason)
            
            # Remove from external providers
            self._remove_from_providers(subscriber.email_list, subscriber)
            
            return subscriber
        except Subscriber.DoesNotExist:
            return None
    
    def _sync_to_providers(self, email_list: 'EmailList', subscriber: 'Subscriber'):
        """Sync subscriber to external providers."""
        # Mailchimp
        if self.mailchimp and self.mailchimp.is_enabled and email_list.mailchimp_list_id:
            self.mailchimp.add_subscriber(
                email_list.mailchimp_list_id,
                subscriber.email,
                subscriber.first_name,
                subscriber.last_name
            )
        
        # SendGrid
        if self.sendgrid and self.sendgrid.is_enabled and email_list.sendgrid_list_id:
            self.sendgrid.add_contact(
                subscriber.email,
                subscriber.first_name,
                subscriber.last_name,
                [email_list.sendgrid_list_id]
            )
        
        # ConvertKit
        if self.convertkit and self.convertkit.is_enabled and email_list.convertkit_form_id:
            self.convertkit.add_subscriber_to_form(
                email_list.convertkit_form_id,
                subscriber.email,
                subscriber.first_name
            )
    
    def _remove_from_providers(self, email_list: 'EmailList', subscriber: 'Subscriber'):
        """Remove subscriber from external providers."""
        if self.mailchimp and self.mailchimp.is_enabled and email_list.mailchimp_list_id:
            self.mailchimp.remove_subscriber(
                email_list.mailchimp_list_id,
                subscriber.email
            )
        
        if self.sendgrid and self.sendgrid.is_enabled:
            self.sendgrid.remove_contact(subscriber.email)
        
        if self.convertkit and self.convertkit.is_enabled:
            self.convertkit.unsubscribe(subscriber.email)

