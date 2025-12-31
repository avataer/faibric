"""
Seed default admin design rules and customer messages.
NOTE: This migration is designed to be resilient - it will skip
operations if tables don't exist (e.g., during initial setup).
"""
from django.db import migrations, connection


def seed_data(apps, schema_editor):
    """Seed default data - resilient to missing tables."""
    
    # Check if tables exist first
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'code_library_admindesignrules'
            );
        """)
        tables_exist = cursor.fetchone()[0]
    
    if not tables_exist:
        print("Skipping seed_data: Tables not yet created")
        return
    
    try:
        AdminDesignRules = apps.get_model('code_library', 'AdminDesignRules')
        
        # Create default design rules (if none exist)
        if not AdminDesignRules.objects.exists():
            AdminDesignRules.objects.create(
                name="Default Art Direction",
                is_active=True,
            )
    except Exception as e:
        print(f"Warning: Could not seed AdminDesignRules: {e}")
    
    try:
        CustomerMessage = apps.get_model('code_library', 'CustomerMessage')
        
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
    except Exception as e:
        print(f"Warning: Could not seed CustomerMessage: {e}")


def reverse_seed(apps, schema_editor):
    try:
        AdminDesignRules = apps.get_model('code_library', 'AdminDesignRules')
        AdminDesignRules.objects.filter(name="Default Art Direction").delete()
    except Exception:
        pass
    
    try:
        CustomerMessage = apps.get_model('code_library', 'CustomerMessage')
        CustomerMessage.objects.all().delete()
    except Exception:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('code_library', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_data, reverse_seed),
    ]



