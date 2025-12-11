from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .utils import create_tenant_for_user

User = get_user_model()


@receiver(post_save, sender=User)
def create_tenant_for_new_user(sender, instance, created, **kwargs):
    """
    Automatically create a tenant for new users.
    This ensures every user has at least one tenant.
    """
    if created and not instance.is_superuser:
        # Check if user already has a tenant (shouldn't happen for new users)
        from .models import TenantMembership
        if not TenantMembership.objects.filter(user=instance).exists():
            create_tenant_for_user(instance)

