"""
Seed default admin design rules and customer messages.
"""
from django.db import migrations


def seed_data(apps, schema_editor):
    AdminDesignRules = apps.get_model('code_library', 'AdminDesignRules')
    CustomerMessage = apps.get_model('code_library', 'CustomerMessage')
    
    # Create default design rules (if none exist)
    if not AdminDesignRules.objects.exists():
        AdminDesignRules.objects.create(
            name="Default Art Direction",
            is_active=True,
        )
    
    # Create customer messages
    messages = [
        ('start', "Let's build something amazing...", ["Starting your project...", "Getting ready..."]),
        ('analyzing', "Understanding your vision...", ["Analyzing your request...", "Reading your requirements..."]),
        ('designing', "Designing your perfect layout...", ["Creating the design...", "Planning your site..."]),
        ('building_hero', "Building your homepage...", ["Creating the main section...", "Crafting your hero..."]),
        ('building_sections', "Adding your content sections...", ["Building more sections...", "Adding content..."]),
        ('styling', "Applying beautiful styling...", ["Making it look great...", "Adding finishing touches..."]),
        ('polishing', "Polishing the design...", ["Final adjustments...", "Perfecting details..."]),
        ('finalizing', "Finalizing your website...", ["Almost there...", "Wrapping up..."]),
        ('deploying', "Publishing your website...", ["Going live...", "Deploying to the web..."]),
        ('complete', "Your website is ready!", ["All done!", "Ready to go!"]),
    ]
    
    for key, message, variants in messages:
        CustomerMessage.objects.get_or_create(
            operation_key=key,
            defaults={
                'customer_message': message,
                'message_variants': variants,
                'min_display_seconds': 2,
                'is_active': True,
            }
        )


def reverse_seed(apps, schema_editor):
    AdminDesignRules = apps.get_model('code_library', 'AdminDesignRules')
    CustomerMessage = apps.get_model('code_library', 'CustomerMessage')
    AdminDesignRules.objects.filter(name="Default Art Direction").delete()
    CustomerMessage.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('code_library', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_data, reverse_seed),
    ]
