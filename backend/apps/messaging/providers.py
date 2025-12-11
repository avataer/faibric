"""
Message delivery providers for Email, SMS, and Push notifications.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeliveryResult:
    """Result of a message delivery attempt."""
    success: bool
    provider_message_id: str = ''
    error: str = ''
    response: Dict = None


# ============= EMAIL PROVIDERS =============

class BaseEmailProvider(ABC):
    """Base class for email providers."""
    
    @abstractmethod
    def send(
        self,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        body_text: str,
        body_html: str = ''
    ) -> DeliveryResult:
        pass


class SMTPProvider(BaseEmailProvider):
    """SMTP email provider."""
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool = True
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
    
    def send(
        self,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        body_text: str,
        body_html: str = ''
    ) -> DeliveryResult:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = to_email
            
            msg.attach(MIMEText(body_text, 'plain'))
            if body_html:
                msg.attach(MIMEText(body_html, 'html'))
            
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            
            return DeliveryResult(success=True)
            
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return DeliveryResult(success=False, error=str(e))


class SendGridProvider(BaseEmailProvider):
    """SendGrid email provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def send(
        self,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        body_text: str,
        body_html: str = ''
    ) -> DeliveryResult:
        import requests
        
        try:
            content = [{"type": "text/plain", "value": body_text}]
            if body_html:
                content.append({"type": "text/html", "value": body_html})
            
            data = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_email, "name": from_name},
                "subject": subject,
                "content": content
            }
            
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=data,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                message_id = response.headers.get('X-Message-Id', '')
                return DeliveryResult(
                    success=True,
                    provider_message_id=message_id,
                    response={'status_code': response.status_code}
                )
            else:
                return DeliveryResult(
                    success=False,
                    error=response.text,
                    response={'status_code': response.status_code}
                )
                
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return DeliveryResult(success=False, error=str(e))


# ============= SMS PROVIDERS =============

class BaseSMSProvider(ABC):
    """Base class for SMS providers."""
    
    @abstractmethod
    def send(
        self,
        to_number: str,
        from_number: str,
        body: str
    ) -> DeliveryResult:
        pass


class TwilioProvider(BaseSMSProvider):
    """Twilio SMS provider."""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
    
    def send(
        self,
        to_number: str,
        from_number: str = None,
        body: str = ''
    ) -> DeliveryResult:
        import requests
        from requests.auth import HTTPBasicAuth
        
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            
            data = {
                "From": from_number or self.from_number,
                "To": to_number,
                "Body": body
            }
            
            response = requests.post(
                url,
                data=data,
                auth=HTTPBasicAuth(self.account_sid, self.auth_token),
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code in [200, 201]:
                return DeliveryResult(
                    success=True,
                    provider_message_id=result.get('sid', ''),
                    response=result
                )
            else:
                return DeliveryResult(
                    success=False,
                    error=result.get('message', str(result)),
                    response=result
                )
                
        except Exception as e:
            logger.error(f"Twilio error: {e}")
            return DeliveryResult(success=False, error=str(e))


# ============= PUSH PROVIDERS =============

class BasePushProvider(ABC):
    """Base class for push notification providers."""
    
    @abstractmethod
    def send(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict = None
    ) -> DeliveryResult:
        pass


class FirebaseProvider(BasePushProvider):
    """Firebase Cloud Messaging provider."""
    
    def __init__(self, server_key: str, project_id: str = ''):
        self.server_key = server_key
        self.project_id = project_id
    
    def send(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict = None
    ) -> DeliveryResult:
        import requests
        
        try:
            # FCM HTTP v1 API
            url = "https://fcm.googleapis.com/fcm/send"
            
            headers = {
                "Authorization": f"key={self.server_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "registration_ids": tokens,
                "notification": {
                    "title": title,
                    "body": body
                }
            }
            
            if data:
                payload["data"] = data
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code == 200:
                success_count = result.get('success', 0)
                failure_count = result.get('failure', 0)
                
                return DeliveryResult(
                    success=success_count > 0,
                    provider_message_id=str(result.get('multicast_id', '')),
                    response={
                        'success_count': success_count,
                        'failure_count': failure_count,
                        'results': result.get('results', [])
                    }
                )
            else:
                return DeliveryResult(
                    success=False,
                    error=str(result),
                    response=result
                )
                
        except Exception as e:
            logger.error(f"Firebase error: {e}")
            return DeliveryResult(success=False, error=str(e))


# ============= FACTORY =============

def get_email_provider(config: 'MessagingConfig') -> Optional[BaseEmailProvider]:
    """Get email provider based on config."""
    if not config.email_enabled:
        return None
    
    if config.email_provider == 'sendgrid' and config.sendgrid_api_key:
        return SendGridProvider(config.sendgrid_api_key)
    elif config.email_provider == 'smtp':
        return SMTPProvider(
            host=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_username,
            password=config.smtp_password,
            use_tls=config.smtp_use_tls
        )
    return None


def get_sms_provider(config: 'MessagingConfig') -> Optional[BaseSMSProvider]:
    """Get SMS provider based on config."""
    if not config.sms_enabled:
        return None
    
    if config.sms_provider == 'twilio':
        if config.twilio_account_sid and config.twilio_auth_token:
            return TwilioProvider(
                account_sid=config.twilio_account_sid,
                auth_token=config.twilio_auth_token,
                from_number=config.twilio_phone_number
            )
    return None


def get_push_provider(config: 'MessagingConfig') -> Optional[BasePushProvider]:
    """Get push notification provider based on config."""
    if not config.push_enabled:
        return None
    
    if config.push_provider == 'firebase' and config.firebase_server_key:
        return FirebaseProvider(
            server_key=config.firebase_server_key,
            project_id=config.firebase_project_id
        )
    return None






