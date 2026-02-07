# Fix preferred_model column NULL constraint in SQLite
# SQLite doesn't support ALTER COLUMN to change NULL constraints
# We need to recreate the table

from django.db import migrations


def fix_sqlite_preferred_model(apps, schema_editor):
    """
    SQLite workaround: Recreate projects_project table with preferred_model as nullable.

    SQLite does not support:
    - ALTER TABLE ... ALTER COLUMN ... DROP NOT NULL
    - ALTER TABLE ... MODIFY COLUMN ...

    The only solution is to:
    1. Create a new table with the correct schema
    2. Copy data from old table
    3. Drop old table
    4. Rename new table
    """
    from django.db import connection

    if connection.vendor != 'sqlite':
        # PostgreSQL can just alter the column
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE projects_project
                ALTER COLUMN preferred_model DROP NOT NULL
            """)
            cursor.execute("""
                ALTER TABLE projects_project
                ALTER COLUMN preferred_model SET DEFAULT 'claude-opus'
            """)
        print("PostgreSQL: Made preferred_model nullable")
        return

    # SQLite: Need to recreate table
    print("SQLite: Recreating table to fix NULL constraint...")

    with connection.cursor() as cursor:
        # 1. Create new table with correct schema (preferred_model nullable)
        cursor.execute("""
            CREATE TABLE projects_project_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name varchar(200) NOT NULL,
                description TEXT NOT NULL,
                status varchar(20) NOT NULL,
                user_prompt TEXT NOT NULL,
                ai_analysis TEXT,
                database_schema TEXT,
                api_code TEXT NOT NULL,
                frontend_code TEXT NOT NULL,
                subdomain varchar(100) UNIQUE,
                deployment_url varchar(200) NOT NULL,
                container_id varchar(200) NOT NULL,
                created_at datetime NOT NULL,
                updated_at datetime NOT NULL,
                deployed_at datetime,
                template_id bigint REFERENCES templates_template(id),
                user_id bigint NOT NULL REFERENCES users_user(id),
                tenant_id char(32) REFERENCES tenants_tenant(id),
                preferred_model varchar(50) DEFAULT 'claude-opus',
                github_repo varchar(255) NOT NULL DEFAULT '',
                last_github_sha varchar(40) NOT NULL DEFAULT ''
            )
        """)

        # 2. Copy data from old table
        cursor.execute("""
            INSERT INTO projects_project_new
            SELECT
                id, name, description, status, user_prompt, ai_analysis,
                database_schema, api_code, frontend_code, subdomain,
                deployment_url, container_id, created_at, updated_at,
                deployed_at, template_id, user_id, tenant_id,
                COALESCE(preferred_model, 'claude-opus'),
                COALESCE(github_repo, ''),
                COALESCE(last_github_sha, '')
            FROM projects_project
        """)

        # 3. Drop old table
        cursor.execute("DROP TABLE projects_project")

        # 4. Rename new table
        cursor.execute("ALTER TABLE projects_project_new RENAME TO projects_project")

        # 5. Recreate indexes
        cursor.execute("""
            CREATE INDEX projects_project_tenant_status
            ON projects_project(tenant_id, status)
        """)
        cursor.execute("""
            CREATE INDEX projects_project_tenant_user
            ON projects_project(tenant_id, user_id)
        """)

        print("SQLite: Table recreated with preferred_model as nullable")


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0009_fix_preferred_model_nullable'),
    ]

    operations = [
        migrations.RunPython(fix_sqlite_preferred_model, migrations.RunPython.noop),
    ]
