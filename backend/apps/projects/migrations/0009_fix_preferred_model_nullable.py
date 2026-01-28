# Fix preferred_model column to allow NULL values
# This fixes: NOT NULL constraint failed: projects_project.preferred_model
#
# The issue: Migration 0008 added the column but Django doesn't include it
# in INSERT statements because the field is commented out in the model.
# PostgreSQL rejects INSERTs when a NOT NULL column isn't provided.

from django.db import migrations


def fix_preferred_model_column(apps, schema_editor):
    """Make preferred_model column nullable and set default for existing rows."""
    from django.db import connection

    db_vendor = connection.vendor

    with connection.cursor() as cursor:
        if db_vendor == 'postgresql':
            # Check if column exists
            cursor.execute("""
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'projects_project' AND column_name = 'preferred_model'
            """)
            result = cursor.fetchone()

            if result is None:
                # Column doesn't exist - add it as nullable
                print("Adding preferred_model column (nullable)")
                cursor.execute("""
                    ALTER TABLE projects_project
                    ADD COLUMN preferred_model VARCHAR(50) NULL DEFAULT 'claude-opus'
                """)
            else:
                # Column exists - make it nullable if it isn't
                is_nullable = result[1]
                if is_nullable == 'NO':
                    print("Making preferred_model column nullable")
                    cursor.execute("""
                        ALTER TABLE projects_project
                        ALTER COLUMN preferred_model DROP NOT NULL
                    """)
                    # Also set a default for future inserts
                    cursor.execute("""
                        ALTER TABLE projects_project
                        ALTER COLUMN preferred_model SET DEFAULT 'claude-opus'
                    """)
                else:
                    print("preferred_model column is already nullable")

        elif db_vendor == 'sqlite':
            # SQLite: Check if column exists
            cursor.execute("PRAGMA table_info(projects_project)")
            columns = {row[1]: row for row in cursor.fetchall()}

            if 'preferred_model' not in columns:
                # Add the column - SQLite columns are nullable by default
                print("Adding preferred_model column (SQLite)")
                cursor.execute("""
                    ALTER TABLE projects_project
                    ADD COLUMN preferred_model VARCHAR(50) DEFAULT 'claude-opus'
                """)
            else:
                # Column exists - SQLite can't easily alter NULL constraints
                # but it should already be nullable by default
                print("preferred_model column exists in SQLite (nullable by default)")
        else:
            print(f"Unknown database vendor: {db_vendor}")


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0008_add_missing_columns_safe'),
    ]

    operations = [
        migrations.RunPython(fix_preferred_model_column, migrations.RunPython.noop),
    ]
