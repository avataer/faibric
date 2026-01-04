# Generated manually - add connector system fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('code_library', '0004_add_admin_feedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='libraryitem',
            name='interface',
            field=models.JSONField(blank=True, help_text='ComponentInterface definition for this building block', null=True),
        ),
        migrations.AddField(
            model_name='libraryitem',
            name='validated_connections',
            field=models.JSONField(blank=True, default=list, help_text='List of validated connections to other components'),
        ),
        migrations.AddField(
            model_name='libraryitem',
            name='wiring_hints',
            field=models.JSONField(blank=True, default=dict, help_text='Hints for automatic wiring (prop mappings, handlers)'),
        ),
    ]



