"""
Unified messaging service for sending messages across channels.
"""
import logging
from typing import Dict, List, Optional, Union
from django.utils import timezone
from django.db import transaction

from .models import (
    MessagingConfig, MessageTemplate, Message, 
    InAppNotification, PushToken, MessageChannel
)
from .providers import (
    get_email_provider, get_sms_provider, get_push_provider,
    DeliveryResult
)

logger = logging.getLogger(__name__)


class MessagingService:
    """
    Unified messaging service that routes messages to appropriate channels.
    """
    
    def __init__(self, tenant: 'Tenant'):
        self.tenant = tenant
        self._config = None
    
    @property
    def config(self) -> MessagingConfig:
        if self._config is None:
            self._config, _ = MessagingConfig.objects.get_or_create(
                tenant=self.tenant
            )
        return self._config
    
    def send(
        self,
        recipient: str,
        channels: List[str],
        template_slug: str = None,
        subject: str = '',
        body: str = '',
        body_html: str = '',
        context: Dict = None,
        scheduled_at: str = None,
        **kwargs
    ) -> Dict[str, Message]:
        """
        Send a message across multiple channels.
        
        Args:
            recipient: Email, phone, or user_id depending on channel
            channels: List of channels ['email', 'sms', 'push', 'in_app']
            template_slug: Optional template to use
            subject: Message subject (for email)
            body: Plain text body
            body_html: HTML body (for email)
            context: Template variables
            scheduled_at: Optional scheduling datetime
        
        Returns:
            Dict of channel -> Message objects
        """
        context = context or {}
        results = {}
        
        # Get template if specified
        template = None
        if template_slug:
            for channel in channels:
                template = MessageTemplate.objects.filter(
                    tenant=self.tenant,
                    slug=template_slug,
                    channel=channel,
                    is_active=True
                ).first()
                if template:
                    break
        
        for channel in channels:
            # Get channel-specific template
            channel_template = None
            if template_slug:
                channel_template = MessageTemplate.objects.filter(
                    tenant=self.tenant,
                    slug=template_slug,
                    channel=channel,
                    is_active=True
                ).first()
            
            # Prepare content
            msg_subject = subject
            msg_body = body
            msg_body_html = body_html
            
            if channel_template:
                rendered = channel_template.render(context)
                msg_subject = rendered['subject'] or subject
                msg_body = rendered['body'] or body
                msg_body_html = rendered['body_html'] or body_html
            
            # Create message record
            message = Message.objects.create(
                tenant=self.tenant,
                channel=channel,
                recipient=recipient,
                recipient_name=kwargs.get('recipient_name', ''),
                template=channel_template,
                subject=msg_subject,
                body=msg_body,
                body_html=msg_body_html,
                context=context,
                scheduled_at=scheduled_at,
                status=Message.Status.PENDING
            )
            
            results[channel] = message
            
            # Send immediately if not scheduled
            if not scheduled_at:
                self._deliver_message(message)
        
        return results
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        body_html: str = '',
        from_email: str = None,
        from_name: str = None,
        **kwargs
    ) -> Message:
        """Send a single email."""
        message = Message.objects.create(
            tenant=self.tenant,
            channel=MessageChannel.EMAIL,
            recipient=to_email,
            subject=subject,
            body=body,
            body_html=body_html,
            context=kwargs,
            status=Message.Status.PENDING
        )
        
        self._deliver_message(
            message,
            from_email=from_email,
            from_name=from_name
        )
        
        return message
    
    def send_sms(
        self,
        to_number: str,
        body: str,
        from_number: str = None,
        **kwargs
    ) -> Message:
        """Send a single SMS."""
        message = Message.objects.create(
            tenant=self.tenant,
            channel=MessageChannel.SMS,
            recipient=to_number,
            body=body,
            context=kwargs,
            status=Message.Status.PENDING
        )
        
        self._deliver_message(message, from_number=from_number)
        
        return message
    
    def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Dict = None,
        **kwargs
    ) -> Message:
        """Send a push notification to a user's devices."""
        message = Message.objects.create(
            tenant=self.tenant,
            channel=MessageChannel.PUSH,
            recipient=user_id,
            subject=title,
            body=body,
            context=data or {},
            status=Message.Status.PENDING
        )
        
        self._deliver_message(message)
        
        return message
    
    def send_in_app(
        self,
        user_id: str,
        title: str,
        body: str,
        notification_type: str = 'info',
        action_url: str = '',
        action_label: str = '',
        data: Dict = None,
        expires_at: str = None,
        **kwargs
    ) -> InAppNotification:
        """Create an in-app notification."""
        notification = InAppNotification.objects.create(
            tenant=self.tenant,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            action_url=action_url,
            action_label=action_label,
            data=data or {},
            expires_at=expires_at
        )
        
        return notification
    
    def _deliver_message(self, message: Message, **kwargs) -> DeliveryResult:
        """Deliver a message through the appropriate channel."""
        message.status = Message.Status.SENDING
        message.save(update_fields=['status'])
        
        try:
            if message.channel == MessageChannel.EMAIL:
                result = self._deliver_email(message, **kwargs)
            elif message.channel == MessageChannel.SMS:
                result = self._deliver_sms(message, **kwargs)
            elif message.channel == MessageChannel.PUSH:
                result = self._deliver_push(message, **kwargs)
            else:
                result = DeliveryResult(success=False, error="Unknown channel")
            
            # Update message status
            if result.success:
                message.status = Message.Status.SENT
                message.sent_at = timezone.now()
                message.provider_message_id = result.provider_message_id
            else:
                message.status = Message.Status.FAILED
                message.error_message = result.error
            
            message.provider_response = result.response or {}
            message.save()
            
            return result
            
        except Exception as e:
            logger.exception(f"Message delivery error: {e}")
            message.status = Message.Status.FAILED
            message.error_message = str(e)
            message.save()
            return DeliveryResult(success=False, error=str(e))
    
    def _deliver_email(self, message: Message, **kwargs) -> DeliveryResult:
        """Deliver an email message."""
        provider = get_email_provider(self.config)
        if not provider:
            return DeliveryResult(success=False, error="Email not configured")
        
        from_email = kwargs.get('from_email') or self.config.default_from_email
        from_name = kwargs.get('from_name') or self.config.default_from_name
        
        return provider.send(
            to_email=message.recipient,
            from_email=from_email,
            from_name=from_name,
            subject=message.subject,
            body_text=message.body,
            body_html=message.body_html
        )
    
    def _deliver_sms(self, message: Message, **kwargs) -> DeliveryResult:
        """Deliver an SMS message."""
        provider = get_sms_provider(self.config)
        if not provider:
            return DeliveryResult(success=False, error="SMS not configured")
        
        from_number = kwargs.get('from_number') or self.config.twilio_phone_number
        
        return provider.send(
            to_number=message.recipient,
            from_number=from_number,
            body=message.body
        )
    
    def _deliver_push(self, message: Message, **kwargs) -> DeliveryResult:
        """Deliver a push notification."""
        provider = get_push_provider(self.config)
        if not provider:
            return DeliveryResult(success=False, error="Push not configured")
        
        # Get user's push tokens
        tokens = list(
            PushToken.objects.filter(
                tenant=self.tenant,
                user_id=message.recipient,
                is_active=True
            ).values_list('token', flat=True)
        )
        
        if not tokens:
            return DeliveryResult(success=False, error="No push tokens for user")
        
        return provider.send(
            tokens=tokens,
            title=message.subject,
            body=message.body,
            data=message.context
        )
    
    # ============= NOTIFICATIONS API =============
    
    def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[InAppNotification]:
        """Get in-app notifications for a user."""
        qs = InAppNotification.objects.filter(
            tenant=self.tenant,
            user_id=user_id
        )
        
        if unread_only:
            qs = qs.filter(is_read=False)
        
        # Exclude expired
        now = timezone.now()
        qs = qs.filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )
        
        return list(qs[:limit])
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        try:
            notification = InAppNotification.objects.get(
                id=notification_id,
                tenant=self.tenant
            )
            notification.mark_read()
            return True
        except InAppNotification.DoesNotExist:
            return False
    
    def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        count = InAppNotification.objects.filter(
            tenant=self.tenant,
            user_id=user_id,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return count
    
    # ============= PUSH TOKENS =============
    
    def register_push_token(
        self,
        user_id: str,
        token: str,
        device_type: str,
        device_name: str = ''
    ) -> PushToken:
        """Register a push notification token."""
        push_token, created = PushToken.objects.update_or_create(
            tenant=self.tenant,
            token=token,
            defaults={
                'user_id': user_id,
                'device_type': device_type,
                'device_name': device_name,
                'is_active': True
            }
        )
        return push_token
    
    def unregister_push_token(self, token: str) -> bool:
        """Unregister a push token."""
        count = PushToken.objects.filter(
            tenant=self.tenant,
            token=token
        ).update(is_active=False)
        return count > 0


# Import models for Q filter
from django.db import models







