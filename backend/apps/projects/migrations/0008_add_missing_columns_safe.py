# Manual migration to add missing columns with raw SQL
# This migration is idempotent - safe to run multiple times

from django.db import migrations


def add_missing_columns(apps, schema_editor):
    """Add all missing columns to projects_project table."""
    from django.db import connection

    columns_to_add = [
        ("preferred_model", "VARCHAR(50)", "'claude-opus'"),
        ("github_repo", "VARCHAR(255)", "''"),
        ("last_github_sha", "VARCHAR(40)", "''"),
    ]

    with connection.cursor() as cursor:
        for col_name, col_type, default in columns_to_add:
            # Check if column exists
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'projects_project' AND column_name = %s
            """, [col_name])

            if cursor.fetchone() is None:
                # Add the column
                sql = f"""
                    ALTER TABLE projects_project
                    ADD COLUMN {col_name} {col_type} DEFAULT {default}
                """
                print(f"Adding column: {col_name}")
                cursor.execute(sql)
            else:
                print(f"Column already exists: {col_name}")


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0007_placeholder'),
    ]

    operations = [
        migrations.RunPython(add_missing_columns, migrations.RunPython.noop),
    ]
