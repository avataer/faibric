"""
Cabinet services for end-user management.
"""
import logging
from typing import Optional, Dict, List
from django.db import transaction
from django.utils import timezone

from .models import (
    CabinetConfig, EndUser, EndUserSession,
    EmailVerification, PasswordReset,
    SupportTicket, TicketMessage, Notification, Activity
)

logger = logging.getLogger(__name__)


class CabinetAuthService:
    """Authentication service for end-users."""
    
    def __init__(self, tenant: 'Tenant'):
        self.tenant = tenant
        self._config = None
    
    @property
    def config(self) -> CabinetConfig:
        if self._config is None:
            self._config, _ = CabinetConfig.objects.get_or_create(
                tenant=self.tenant
            )
        return self._config
    
    @transaction.atomic
    def register(
        self,
        email: str,
        password: str,
        first_name: str = '',
        last_name: str = '',
        **extra_fields
    ) -> EndUser:
        """Register a new end-user."""
        if not self.config.allow_registration:
            raise ValueError("Registration is disabled")
        
        if len(password) < self.config.password_min_length:
            raise ValueError(f"Password must be at least {self.config.password_min_length} characters")
        
        if EndUser.objects.filter(tenant=self.tenant, email=email).exists():
            raise ValueError("Email already registered")
        
        user = EndUser(
            tenant=self.tenant,
            email=email,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        user.set_password(password)
        user.save()
        
        # Create verification token
        if self.config.require_email_verification:
            EmailVerification.create_verification(user)
            # TODO: Send verification email
        else:
            user.is_verified = True
            user.verified_at = timezone.now()
            user.save()
        
        # Log activity
        Activity.objects.create(
            user=user,
            activity_type='account',
            title='Account Created',
            description='Welcome! Your account has been created.',
            icon='🎉'
        )
        
        return user
    
    def login(
        self,
        email: str,
        password: str,
        user_agent: str = '',
        ip_address: str = None
    ) -> Optional[Dict]:
        """Login an end-user."""
        try:
            user = EndUser.objects.get(
                tenant=self.tenant,
                email=email,
                is_active=True
            )
        except EndUser.DoesNotExist:
            return None
        
        if not user.check_password(password):
            return None
        
        if self.config.require_email_verification and not user.is_verified:
            raise ValueError("Please verify your email first")
        
        # Create session
        session = EndUserSession.create_session(
            user,
            hours=self.config.session_timeout_hours,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Update last login
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])
        
        return {
            'token': session.token,
            'expires_at': session.expires_at.isoformat(),
            'user': {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'avatar_url': user.avatar_url
            }
        }
    
    def logout(self, token: str) -> bool:
        """Logout an end-user."""
        try:
            session = EndUserSession.objects.get(token=token)
            session.is_active = False
            session.save(update_fields=['is_active'])
            return True
        except EndUserSession.DoesNotExist:
            return False
    
    def validate_session(self, token: str) -> Optional[EndUser]:
        """Validate a session token."""
        try:
            session = EndUserSession.objects.select_related('user').get(
                token=token,
                is_active=True
            )
            
            if session.is_expired:
                session.is_active = False
                session.save(update_fields=['is_active'])
                return None
            
            session.last_used_at = timezone.now()
            session.save(update_fields=['last_used_at'])
            
            return session.user
        except EndUserSession.DoesNotExist:
            return None
    
    def verify_email(self, token: str) -> bool:
        """Verify email with token."""
        try:
            verification = EmailVerification.objects.select_related('user').get(
                token=token,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            
            verification.user.is_verified = True
            verification.user.verified_at = timezone.now()
            verification.user.save(update_fields=['is_verified', 'verified_at'])
            
            verification.is_used = True
            verification.save(update_fields=['is_used'])
            
            return True
        except EmailVerification.DoesNotExist:
            return False
    
    def request_password_reset(self, email: str) -> bool:
        """Request password reset."""
        try:
            user = EndUser.objects.get(tenant=self.tenant, email=email)
            PasswordReset.create_reset(user)
            # TODO: Send password reset email
            return True
        except EndUser.DoesNotExist:
            return False
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password with token."""
        if len(new_password) < self.config.password_min_length:
            raise ValueError(f"Password must be at least {self.config.password_min_length} characters")
        
        try:
            reset = PasswordReset.objects.select_related('user').get(
                token=token,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            
            reset.user.set_password(new_password)
            reset.user.save(update_fields=['password_hash'])
            
            reset.is_used = True
            reset.save(update_fields=['is_used'])
            
            # Invalidate all sessions
            EndUserSession.objects.filter(user=reset.user).update(is_active=False)
            
            return True
        except PasswordReset.DoesNotExist:
            return False


class CabinetService:
    """Service for cabinet operations."""
    
    def __init__(self, tenant: 'Tenant', user: EndUser = None):
        self.tenant = tenant
        self.user = user
        self._config = None
    
    @property
    def config(self) -> CabinetConfig:
        if self._config is None:
            self._config, _ = CabinetConfig.objects.get_or_create(
                tenant=self.tenant
            )
        return self._config
    
    # ============= PROFILE =============
    
    def update_profile(self, **fields) -> EndUser:
        """Update user profile."""
        allowed_fields = [
            'first_name', 'last_name', 'display_name', 'avatar_url', 'phone',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country',
            'timezone', 'language', 'preferences'
        ]
        
        for field, value in fields.items():
            if field in allowed_fields:
                setattr(self.user, field, value)
        
        self.user.save()
        
        Activity.objects.create(
            user=self.user,
            activity_type='profile',
            title='Profile Updated',
            icon='✏️'
        )
        
        return self.user
    
    def change_password(self, current_password: str, new_password: str) -> bool:
        """Change user password."""
        if not self.user.check_password(current_password):
            raise ValueError("Current password is incorrect")
        
        auth_service = CabinetAuthService(self.tenant)
        if len(new_password) < auth_service.config.password_min_length:
            raise ValueError(f"Password must be at least {auth_service.config.password_min_length} characters")
        
        self.user.set_password(new_password)
        self.user.save(update_fields=['password_hash'])
        
        Activity.objects.create(
            user=self.user,
            activity_type='security',
            title='Password Changed',
            icon='🔐'
        )
        
        return True
    
    # ============= DASHBOARD =============
    
    def get_dashboard_data(self) -> Dict:
        """Get dashboard summary data."""
        from apps.checkout.models import Order
        from apps.storage.models import File
        
        data = {
            'user': {
                'id': str(self.user.id),
                'email': self.user.email,
                'full_name': self.user.full_name,
                'avatar_url': self.user.avatar_url
            },
            'stats': {}
        }
        
        # Orders
        if self.config.orders_enabled:
            orders = Order.objects.filter(
                tenant=self.tenant,
                customer_id=str(self.user.id)
            )
            data['stats']['orders'] = {
                'total': orders.count(),
                'pending': orders.filter(status='pending').count(),
                'recent': orders.order_by('-created_at')[:5].values(
                    'id', 'order_number', 'status', 'total_amount', 'created_at'
                )
            }
        
        # Files
        if self.config.files_enabled:
            files = File.objects.filter(
                tenant=self.tenant,
                owner_id=str(self.user.id),
                is_deleted=False
            )
            total_size = sum(f.file_size for f in files)
            data['stats']['files'] = {
                'count': files.count(),
                'total_size_bytes': total_size
            }
        
        # Support tickets
        if self.config.support_enabled:
            tickets = SupportTicket.objects.filter(
                tenant=self.tenant,
                user=self.user
            )
            data['stats']['support'] = {
                'total': tickets.count(),
                'open': tickets.filter(status__in=['open', 'in_progress']).count()
            }
        
        # Notifications
        if self.config.notifications_enabled:
            data['stats']['notifications'] = {
                'unread': Notification.objects.filter(
                    user=self.user,
                    is_read=False
                ).count()
            }
        
        return data
    
    def get_activities(self, limit: int = 20) -> List[Activity]:
        """Get recent activities."""
        return list(
            Activity.objects.filter(user=self.user)[:limit]
        )
    
    # ============= NOTIFICATIONS =============
    
    def get_notifications(self, unread_only: bool = False, limit: int = 50) -> List[Notification]:
        """Get user notifications."""
        qs = Notification.objects.filter(user=self.user)
        if unread_only:
            qs = qs.filter(is_read=False)
        return list(qs[:limit])
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        try:
            notification = Notification.objects.get(id=notification_id, user=self.user)
            notification.mark_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    def mark_all_notifications_read(self) -> int:
        """Mark all notifications as read."""
        count = Notification.objects.filter(
            user=self.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return count
    
    def create_notification(
        self,
        title: str,
        message: str,
        notification_type: str = 'system',
        action_url: str = '',
        action_text: str = '',
        metadata: dict = None
    ) -> Notification:
        """Create a notification for the user."""
        return Notification.objects.create(
            user=self.user,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            action_text=action_text,
            metadata=metadata or {}
        )
    
    # ============= SUPPORT =============
    
    def create_ticket(
        self,
        subject: str,
        message: str,
        category: str = '',
        priority: str = 'medium',
        related_order_id: str = ''
    ) -> SupportTicket:
        """Create a support ticket."""
        ticket = SupportTicket.objects.create(
            tenant=self.tenant,
            user=self.user,
            subject=subject,
            category=category,
            priority=priority,
            related_order_id=related_order_id
        )
        
        # Add first message
        TicketMessage.objects.create(
            ticket=ticket,
            is_staff_reply=False,
            sender_name=self.user.full_name,
            sender_email=self.user.email,
            content=message
        )
        
        Activity.objects.create(
            user=self.user,
            activity_type='support',
            title='Support Ticket Created',
            description=f'Ticket #{ticket.ticket_number}: {subject}',
            entity_type='ticket',
            entity_id=str(ticket.id),
            icon='🎫'
        )
        
        return ticket
    
    def get_tickets(self, status: str = None) -> List[SupportTicket]:
        """Get user's support tickets."""
        qs = SupportTicket.objects.filter(
            tenant=self.tenant,
            user=self.user
        )
        if status:
            qs = qs.filter(status=status)
        return list(qs)
    
    def get_ticket(self, ticket_id: str) -> Optional[SupportTicket]:
        """Get a ticket with messages."""
        try:
            return SupportTicket.objects.prefetch_related('messages').get(
                id=ticket_id,
                user=self.user
            )
        except SupportTicket.DoesNotExist:
            return None
    
    def reply_to_ticket(self, ticket: SupportTicket, message: str) -> TicketMessage:
        """Reply to a support ticket."""
        if ticket.status == 'closed':
            raise ValueError("Cannot reply to closed ticket")
        
        msg = TicketMessage.objects.create(
            ticket=ticket,
            is_staff_reply=False,
            sender_name=self.user.full_name,
            sender_email=self.user.email,
            content=message
        )
        
        # Update ticket status
        if ticket.status == 'waiting':
            ticket.status = 'open'
            ticket.save(update_fields=['status', 'updated_at'])
        
        return msg
    
    # ============= ORDERS =============
    
    def get_orders(self, status: str = None, limit: int = 50) -> List:
        """Get user's orders."""
        from apps.checkout.models import Order
        
        qs = Order.objects.filter(
            tenant=self.tenant,
            customer_id=str(self.user.id)
        ).prefetch_related('items')
        
        if status:
            qs = qs.filter(status=status)
        
        return list(qs[:limit])
    
    def get_order(self, order_id: str):
        """Get a specific order."""
        from apps.checkout.models import Order
        
        try:
            return Order.objects.prefetch_related('items', 'payments').get(
                id=order_id,
                customer_id=str(self.user.id)
            )
        except Order.DoesNotExist:
            return None









