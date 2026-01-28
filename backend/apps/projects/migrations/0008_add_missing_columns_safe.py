# Manual migration to add missing columns with raw SQL
# This migration is idempotent - safe to run multiple times
# Fixed to work with both PostgreSQL and SQLite

from django.db import migrations


def add_missing_columns(apps, schema_editor):
    """Add all missing columns to projects_project table."""
    from django.db import connection

    db_vendor = connection.vendor

    columns_to_add = [
        ("preferred_model", "VARCHAR(50)", "'claude-opus'"),
        ("github_repo", "VARCHAR(255)", "''"),
        ("last_github_sha", "VARCHAR(40)", "''"),
    ]

    with connection.cursor() as cursor:
        # Get existing columns based on database type
        if db_vendor == 'sqlite':
            cursor.execute("PRAGMA table_info(projects_project)")
            existing_columns = {row[1] for row in cursor.fetchall()}
        else:
            # PostgreSQL and others
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'projects_project'
            """)
            existing_columns = {row[0] for row in cursor.fetchall()}

        for col_name, col_type, default in columns_to_add:
            if col_name not in existing_columns:
                # Add the column - nullable to avoid NOT NULL errors
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
