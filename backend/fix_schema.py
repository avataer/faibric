#!/usr/bin/env python3
"""
Pre-migration schema fix script.
Adds missing columns directly via raw SQL before Django migrations run.
This ensures idempotent schema fixes even when Django's migration state is inconsistent.
"""
import os
import sys
import traceback

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faibric_backend.settings')

import django
django.setup()

from django.db import connection


def fix_onboarding_schema():
    """Add missing columns to onboarding_landingsession table."""
    columns_to_add = [
        ("mode", "VARCHAR(20)", "'building'"),
        ("requirements_checklist", "TEXT", None),
    ]

    with connection.cursor() as cursor:
        for col_name, col_type, default in columns_to_add:
            try:
                # Use PostgreSQL-specific syntax for checking column existence
                # and adding column IF NOT EXISTS
                if default is None:
                    sql = f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'onboarding_landingsession'
                                AND column_name = '{col_name}'
                            ) THEN
                                ALTER TABLE onboarding_landingsession
                                ADD COLUMN {col_name} {col_type} NULL;
                                RAISE NOTICE 'Added column: {col_name}';
                            ELSE
                                RAISE NOTICE 'Column already exists: {col_name}';
                            END IF;
                        END $$;
                    """
                else:
                    sql = f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'onboarding_landingsession'
                                AND column_name = '{col_name}'
                            ) THEN
                                ALTER TABLE onboarding_landingsession
                                ADD COLUMN {col_name} {col_type} DEFAULT {default};
                                RAISE NOTICE 'Added column: {col_name}';
                            ELSE
                                RAISE NOTICE 'Column already exists: {col_name}';
                            END IF;
                        END $$;
                    """
                print(f"[fix_schema] Checking/adding column: {col_name}")
                cursor.execute(sql)
                print(f"[fix_schema] Processed column: {col_name}")
            except Exception as e:
                print(f"[fix_schema] Error with column {col_name}: {e}")
                traceback.print_exc()


def fix_projects_schema():
    """
    Fix projects_project.preferred_model column.
    This fixes: NOT NULL constraint failed: projects_project.preferred_model

    The problem: The column was added but is NOT NULL, and Django's model
    has the field commented out, so INSERTs don't include it.
    """
    with connection.cursor() as cursor:
        try:
            # Check if column exists and its nullability
            cursor.execute("""
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'projects_project' AND column_name = 'preferred_model'
            """)
            result = cursor.fetchone()

            if result is None:
                # Column doesn't exist - add it as nullable
                print("[fix_schema] Adding preferred_model column (nullable)")
                cursor.execute("""
                    ALTER TABLE projects_project
                    ADD COLUMN preferred_model VARCHAR(50) NULL DEFAULT 'claude-opus'
                """)
            else:
                # Column exists - check if it's nullable
                is_nullable = result[1]
                if is_nullable == 'NO':
                    print("[fix_schema] Making preferred_model column nullable")
                    cursor.execute("""
                        ALTER TABLE projects_project
                        ALTER COLUMN preferred_model DROP NOT NULL
                    """)
                    cursor.execute("""
                        ALTER TABLE projects_project
                        ALTER COLUMN preferred_model SET DEFAULT 'claude-opus'
                    """)
                else:
                    print("[fix_schema] preferred_model column is already nullable")

            print("[fix_schema] projects_project.preferred_model fix complete")
        except Exception as e:
            print(f"[fix_schema] Error fixing preferred_model: {e}")
            traceback.print_exc()




def fix_pending_modification():
    """Add pending_modification column to projects_project if missing."""
    with connection.cursor() as cursor:
        try:
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'projects_project'
                        AND column_name = 'pending_modification'
                    ) THEN
                        ALTER TABLE projects_project
                        ADD COLUMN pending_modification TEXT NULL;
                        RAISE NOTICE 'Added column: pending_modification';
                    ELSE
                        RAISE NOTICE 'Column already exists: pending_modification';
                    END IF;
                END $$;
            """)
            print("[fix_schema] projects_project.pending_modification fix complete")
        except Exception as e:
            print(f"[fix_schema] Error fixing pending_modification: {e}")
            traceback.print_exc()


if __name__ == '__main__':
    print("[fix_schema] Running pre-migration schema fixes...")
    print(f"[fix_schema] DATABASE_URL: {os.environ.get('DATABASE_URL', 'NOT SET')[:50]}...")
    try:
        fix_onboarding_schema()
        fix_projects_schema()
        fix_pending_modification()
        print("[fix_schema] Schema fixes complete.")
    except Exception as e:
        print(f"[fix_schema] Error: {e}")
        traceback.print_exc()
        # Don't fail the startup - just warn
        sys.exit(0)
