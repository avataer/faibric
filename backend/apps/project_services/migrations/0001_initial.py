# Generated migration for project_services

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectDatabase',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('supabase_url', models.URLField(blank=True)),
                ('supabase_anon_key', models.CharField(blank=True, max_length=500)),
                ('supabase_service_key', models.CharField(blank=True, max_length=500)),
                ('tables', models.JSONField(default=list, help_text='List of table definitions')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('provisioning', 'Provisioning'), ('active', 'Active'), ('error', 'Error')], default='pending', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='database', to='projects.project')),
            ],
            options={
                'verbose_name': 'Project Database',
                'verbose_name_plural': 'Project Databases',
            },
        ),
        migrations.CreateModel(
            name='ProjectAuth',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email_password', models.BooleanField(default=True)),
                ('magic_link', models.BooleanField(default=True)),
                ('google_oauth', models.BooleanField(default=False)),
                ('github_oauth', models.BooleanField(default=False)),
                ('google_client_id', models.CharField(blank=True, max_length=500)),
                ('google_client_secret', models.CharField(blank=True, max_length=500)),
                ('github_client_id', models.CharField(blank=True, max_length=500)),
                ('github_client_secret', models.CharField(blank=True, max_length=500)),
                ('require_email_verification', models.BooleanField(default=True)),
                ('allow_signup', models.BooleanField(default=True)),
                ('session_duration_hours', models.IntegerField(default=168)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('active', 'Active'), ('error', 'Error')], default='pending', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='auth', to='projects.project')),
            ],
            options={
                'verbose_name': 'Project Auth',
                'verbose_name_plural': 'Project Auth Configs',
            },
        ),
        migrations.CreateModel(
            name='ProjectDomain',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('domain', models.CharField(db_index=True, max_length=255, unique=True)),
                ('is_primary', models.BooleanField(default=False)),
                ('verification_token', models.CharField(blank=True, max_length=100)),
                ('is_verified', models.BooleanField(default=False)),
                ('ssl_status', models.CharField(choices=[('pending', 'Pending'), ('provisioning', 'Provisioning'), ('active', 'Active'), ('error', 'Error')], default='pending', max_length=50)),
                ('dns_records', models.JSONField(default=list, help_text='DNS records to configure')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_domains', to='projects.project')),
            ],
            options={
                'verbose_name': 'Project Domain',
                'verbose_name_plural': 'Project Domains',
                'ordering': ['-is_primary', 'domain'],
            },
        ),
        migrations.CreateModel(
            name='ProjectPayments',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('stripe_account_id', models.CharField(blank=True, max_length=100)),
                ('stripe_account_status', models.CharField(choices=[('pending', 'Pending'), ('connected', 'Connected'), ('error', 'Error')], default='pending', max_length=50)),
                ('products', models.JSONField(default=list, help_text='Stripe product definitions')),
                ('webhook_secret', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='projects.project')),
            ],
            options={
                'verbose_name': 'Project Payments',
                'verbose_name_plural': 'Project Payment Configs',
            },
        ),
        migrations.CreateModel(
            name='ProjectStorage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('provider', models.CharField(choices=[('supabase', 'Supabase Storage'), ('cloudflare', 'Cloudflare R2'), ('s3', 'AWS S3')], default='supabase', max_length=50)),
                ('buckets', models.JSONField(default=list, help_text='Storage bucket definitions')),
                ('storage_used_bytes', models.BigIntegerField(default=0)),
                ('storage_limit_bytes', models.BigIntegerField(default=524288000)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('active', 'Active'), ('error', 'Error')], default='pending', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='storage', to='projects.project')),
            ],
            options={
                'verbose_name': 'Project Storage',
                'verbose_name_plural': 'Project Storage Configs',
            },
        ),
        migrations.CreateModel(
            name='ProjectVersion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version_number', models.IntegerField()),
                ('commit_hash', models.CharField(blank=True, max_length=40)),
                ('code_snapshot', models.TextField(help_text='Full App.tsx code at this version')),
                ('config_snapshot', models.JSONField(default=dict, help_text='Configuration at this version')),
                ('change_description', models.TextField(blank=True)),
                ('created_by', models.CharField(default='system', max_length=100)),
                ('is_deployed', models.BooleanField(default=False)),
                ('deployment_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_versions', to='projects.project')),
            ],
            options={
                'verbose_name': 'Project Version',
                'verbose_name_plural': 'Project Versions',
                'ordering': ['-version_number'],
                'unique_together': {('project', 'version_number')},
            },
        ),
        migrations.CreateModel(
            name='ProjectAnalytics',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('is_enabled', models.BooleanField(default=True)),
                ('total_pageviews', models.BigIntegerField(default=0)),
                ('total_visitors', models.BigIntegerField(default=0)),
                ('total_sessions', models.BigIntegerField(default=0)),
                ('pageviews_30d', models.IntegerField(default=0)),
                ('visitors_30d', models.IntegerField(default=0)),
                ('top_pages', models.JSONField(default=list)),
                ('traffic_sources', models.JSONField(default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analytics', to='projects.project')),
            ],
            options={
                'verbose_name': 'Project Analytics',
                'verbose_name_plural': 'Project Analytics',
            },
        ),
        migrations.CreateModel(
            name='AnalyticsEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(db_index=True, max_length=50)),
                ('path', models.CharField(max_length=500)),
                ('visitor_id', models.CharField(db_index=True, max_length=100)),
                ('session_id', models.CharField(max_length=100)),
                ('referrer', models.URLField(blank=True)),
                ('user_agent', models.CharField(blank=True, max_length=500)),
                ('country', models.CharField(blank=True, max_length=2)),
                ('event_data', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_events', to='projects.project')),
            ],
            options={
                'verbose_name': 'Analytics Event',
                'verbose_name_plural': 'Analytics Events',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='analyticsevent',
            index=models.Index(fields=['project', 'event_type', 'created_at'], name='project_ser_project_abc123_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsevent',
            index=models.Index(fields=['project', 'path', 'created_at'], name='project_ser_project_def456_idx'),
        ),
    ]

