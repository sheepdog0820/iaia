from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scenarios', '0003_scenario_difficulty_scenario_estimated_duration_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='scenario',
            name='recommended_skills',
            field=models.TextField(blank=True, help_text='推奨技能（カンマ区切り）'),
        ),
    ]
