"""
Email service for sending transactional emails.
"""
import logging
from typing import Optional, List
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives

logger = logging.getLogger(__name__)


class EmailService:
    """
    Unified email service.
    Uses SendGrid if configured, falls back to Django email.
    """
    
    def __init__(self):
        self.sendgrid_key = getattr(settings, 'SENDGRID_API_KEY', '')
        self.default_from = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@faibric.com')
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str = None,
        from_email: str = None,
        reply_to: str = None,
    ) -> Optional[str]:
        """
        Send an email.
        
        Returns message ID if successful, None otherwise.
        """
        from_email = from_email or self.default_from
        
        # Generate text content from HTML if not provided
        if not text_content:
            import re
            text_content = re.sub('<[^<]+?>', '', html_content)
        
        if self.sendgrid_key:
            return self._send_via_sendgrid(
                to_email, subject, html_content, text_content, from_email, reply_to
            )
        else:
            return self._send_via_django(
                to_email, subject, html_content, text_content, from_email, reply_to
            )
    
    def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        from_email: str,
        reply_to: str = None,
    ) -> Optional[str]:
        """Send email via SendGrid."""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_key)
            
            message = Mail(
                from_email=Email(from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )
            
            if text_content:
                message.add_content(Content("text/plain", text_content))
            
            response = sg.send(message)
            
            # Get message ID from headers
            message_id = response.headers.get('X-Message-Id', '')
            
            logger.info(f"Sent email to {to_email} via SendGrid: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {e}")
            # Fallback to Django
            return self._send_via_django(
                to_email, subject, html_content, text_content, from_email, reply_to
            )
    
    def _send_via_django(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        from_email: str,
        reply_to: str = None,
    ) -> Optional[str]:
        """Send email via Django's email backend."""
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[to_email],
                reply_to=[reply_to] if reply_to else None,
            )
            email.attach_alternative(html_content, "text/html")
            
            sent = email.send(fail_silently=False)
            
            if sent:
                # Generate a fake message ID
                import uuid
                message_id = str(uuid.uuid4())
                logger.info(f"Sent email to {to_email} via Django: {message_id}")
                return message_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to send email via Django: {e}")
            # In development, just log the email
            if settings.DEBUG:
                logger.info(f"[DEV] Would send email to {to_email}: {subject}")
                return 'dev-email-logged'
            return None
    
    def send_bulk(
        self,
        recipients: List[str],
        subject: str,
        html_content: str,
        text_content: str = None,
        from_email: str = None,
    ) -> int:
        """
        Send bulk emails.
        Returns count of successfully sent emails.
        """
        sent_count = 0
        
        for email in recipients:
            if self.send_email(email, subject, html_content, text_content, from_email):
                sent_count += 1
        
        return sent_count







