#!/usr/bin/env python3
"""
Pre-migration schema fix script.
Adds missing columns directly via raw SQL before Django migrations run.
This ensures idempotent schema fixes even when Django's migration state is inconsistent.
"""
import os
import sys

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faibric_backend.settings')

import django
django.setup()

from django.db import connection


def fix_onboarding_schema():
    """Add missing columns to onboarding_landingsession table."""
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
                print(f"[fix_schema] Adding column: {col_name}")
                cursor.execute(sql)
            else:
                print(f"[fix_schema] Column already exists: {col_name}")


if __name__ == '__main__':
    print("[fix_schema] Running pre-migration schema fixes...")
    try:
        fix_onboarding_schema()
        print("[fix_schema] Schema fixes complete.")
    except Exception as e:
        print(f"[fix_schema] Warning: {e}")
        # Don't fail the startup - just warn
        sys.exit(0)
