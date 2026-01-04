"""
Fix missing columns in production database.
This migration safely adds columns that may be missing due to migration issues.
"""
from django.db import migrations


class Migration(migrations.Migration):
    """
    This migration uses raw SQL to add missing columns safely.
    It checks if columns exist before adding them (PostgreSQL only).
    """
    
    dependencies = [
        ('code_library', '0006_add_problem_record'),
    ]
    
    operations = [
        # Add is_approved column if missing
        migrations.RunSQL(
            sql="""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'code_library_libraryitem' 
                    AND column_name = 'is_approved'
                ) THEN 
                    ALTER TABLE code_library_libraryitem ADD COLUMN is_approved BOOLEAN DEFAULT FALSE;
                END IF;
            END $$;
            """,
            reverse_sql="SELECT 1;",  # No-op reverse
        ),
        
        # Add interface column if missing
        migrations.RunSQL(
            sql="""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'code_library_libraryitem' 
                    AND column_name = 'interface'
                ) THEN 
                    ALTER TABLE code_library_libraryitem ADD COLUMN interface JSONB NULL;
                END IF;
            END $$;
            """,
            reverse_sql="SELECT 1;",
        ),
        
        # Add validated_connections column if missing
        migrations.RunSQL(
            sql="""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'code_library_libraryitem' 
                    AND column_name = 'validated_connections'
                ) THEN 
                    ALTER TABLE code_library_libraryitem ADD COLUMN validated_connections JSONB NULL;
                END IF;
            END $$;
            """,
            reverse_sql="SELECT 1;",
        ),
        
        # Add admin_notes column if missing
        migrations.RunSQL(
            sql="""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'code_library_libraryitem' 
                    AND column_name = 'admin_notes'
                ) THEN 
                    ALTER TABLE code_library_libraryitem ADD COLUMN admin_notes TEXT DEFAULT '';
                END IF;
            END $$;
            """,
            reverse_sql="SELECT 1;",
        ),
        
        # Add improvement_notes column if missing
        migrations.RunSQL(
            sql="""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'code_library_libraryitem' 
                    AND column_name = 'improvement_notes'
                ) THEN 
                    ALTER TABLE code_library_libraryitem ADD COLUMN improvement_notes TEXT DEFAULT '';
                END IF;
            END $$;
            """,
            reverse_sql="SELECT 1;",
        ),
        
        # Add reviewed_at column if missing
        migrations.RunSQL(
            sql="""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'code_library_libraryitem' 
                    AND column_name = 'reviewed_at'
                ) THEN 
                    ALTER TABLE code_library_libraryitem ADD COLUMN reviewed_at TIMESTAMP NULL;
                END IF;
            END $$;
            """,
            reverse_sql="SELECT 1;",
        ),
        
        # Create AdminDesignRules table if missing
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS code_library_admindesignrules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) DEFAULT 'Default Rules',
                is_active BOOLEAN DEFAULT TRUE,
                font_rules TEXT DEFAULT '',
                color_rules TEXT DEFAULT '',
                layout_rules TEXT DEFAULT '',
                component_rules TEXT DEFAULT '',
                forbidden_patterns TEXT DEFAULT '',
                quality_standards TEXT DEFAULT '',
                custom_rules TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """,
            reverse_sql="SELECT 1;",
        ),
        
        # Create CustomerMessage table if missing
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS code_library_customermessage (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                operation_key VARCHAR(100) UNIQUE,
                customer_message TEXT DEFAULT '',
                message_variants JSONB DEFAULT '[]',
                min_display_seconds INTEGER DEFAULT 2,
                is_active BOOLEAN DEFAULT TRUE
            );
            """,
            reverse_sql="SELECT 1;",
        ),
        
        # Create Constraint table if missing
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS code_library_constraint (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(200) DEFAULT '',
                constraint_type VARCHAR(30) DEFAULT 'style',
                rule_text TEXT DEFAULT '',
                is_active BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """,
            reverse_sql="SELECT 1;",
        ),
    ]



