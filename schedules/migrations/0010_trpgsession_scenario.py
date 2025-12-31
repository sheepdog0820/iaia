from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('schedules', '0009_sessionnote_sessionlog'),
        ('scenarios', '0004_scenario_recommended_skills'),
    ]

    operations = [
        migrations.AddField(
            model_name='trpgsession',
            name='scenario',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sessions',
                to='scenarios.scenario'
            ),
        ),
    ]
