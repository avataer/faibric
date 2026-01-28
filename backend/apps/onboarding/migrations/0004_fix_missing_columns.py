# Manual migration to ensure mode and requirements_checklist columns exist
# This migration is idempotent - safe to run multiple times
# Created to fix production database where 0003 may have been marked as applied but failed

from django.db import migrations


def add_missing_columns(apps, schema_editor):
    """Add mode and requirements_checklist columns if they don't exist."""
    from django.db import connection

    columns_to_add = [
        ("mode", "VARCHAR(20)", "'building'"),
        ("requirements_checklist", "TEXT", "NULL"),
    ]

    with connection.cursor() as cursor:
        for col_name, col_type, default in columns_to_add:
            # Check if column exists
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'onboarding_landingsession' AND column_name = %s
            """, [col_name])

            if cursor.fetchone() is None:
                # Add the column
                if default == "NULL":
                    sql = f"""
                        ALTER TABLE onboarding_landingsession
                        ADD COLUMN {col_name} {col_type} NULL
                    """
                else:
                    sql = f"""
                        ALTER TABLE onboarding_landingsession
                        ADD COLUMN {col_name} {col_type} DEFAULT {default}
                    """
                print(f"Adding column: {col_name}")
                cursor.execute(sql)
            else:
                print(f"Column already exists: {col_name}")


class Migration(migrations.Migration):

    dependencies = [
        ('onboarding', '0003_landingsession_mode_and_more'),
    ]

    operations = [
        migrations.RunPython(add_missing_columns, migrations.RunPython.noop),
    ]
