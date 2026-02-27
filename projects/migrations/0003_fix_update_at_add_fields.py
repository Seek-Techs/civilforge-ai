from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_project_boq_generated_at_project_boq_result'),
    ]

    operations = [
        # Rename the typo field
        migrations.RenameField(
            model_name='project',
            old_name='update_at',
            new_name='updated_at',
        ),
        # Add status field
        migrations.AddField(
            model_name='project',
            name='status',
            field=models.CharField(
                choices=[
                    ('planning', 'Planning'),
                    ('active', 'Active'),
                    ('on_hold', 'On Hold'),
                    ('completed', 'Completed'),
                ],
                default='planning',
                max_length=20,
            ),
        ),
        # Add location field
        migrations.AddField(
            model_name='project',
            name='location',
            field=models.CharField(
                blank=True,
                help_text='Site location (city/state)',
                max_length=255,
            ),
        ),
        # Add notes field
        migrations.AddField(
            model_name='project',
            name='notes',
            field=models.TextField(blank=True, help_text='Internal notes or comments'),
        ),
    ]
