"""
Billing signals - auto-create billing profile for new tenants.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='tenants.Tenant')
def create_billing_profile_for_tenant(sender, instance, created, **kwargs):
    """
    Automatically create a billing profile and subscription for new tenants.
    """
    if created:
        from .models import BillingProfile, Subscription
        
        # Create billing profile
        BillingProfile.objects.get_or_create(
            tenant=instance,
            defaults={
                'billing_email': instance.owner.email,
                'billing_name': instance.name,
            }
        )
        
        # Create free subscription
        Subscription.objects.get_or_create(
            tenant=instance,
            defaults={
                'plan': 'free',
                'status': 'active',
                'max_apps': 3,
                'max_ai_tokens_per_month': 50000,
                'max_storage_gb': 1,
            }
        )

