"""
Seed default admin design rules and customer messages.
NOTE: This migration is now a NO-OP to avoid migration issues.
The seed data is created on-demand in the application code.
"""
from django.db import migrations


def seed_data(apps, schema_editor):
    """NO-OP - seed data is created on-demand in application code."""
    # This migration previously tried to seed data but caused issues
    # when the database schema was not fully migrated.
    # Now we skip this and let the application create defaults if needed.
    pass


def reverse_seed(apps, schema_editor):
    """NO-OP reverse."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('code_library', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_data, reverse_seed),
    ]



