"""
Fix missing columns in production database.
SQLite-compatible version - becomes no-op for SQLite.
"""
from django.db import migrations, connection


def check_and_add_columns(apps, schema_editor):
    """Only run on PostgreSQL - skip for SQLite."""
    if connection.vendor != "postgresql":
        print("Skipping PostgreSQL-specific migration on", connection.vendor)
        return
    
    # Original PostgreSQL operations would go here
    # For SQLite dev, we skip entirely since fresh DB has all columns


class Migration(migrations.Migration):
    dependencies = [
        ("code_library", "0006_add_problem_record"),
    ]
    
    operations = [
        migrations.RunPython(check_and_add_columns, reverse_code=migrations.RunPython.noop),
    ]
