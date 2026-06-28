import uuid

from django.db import migrations, models


def populate_scenario_share_tokens(apps, schema_editor):
    Scenario = apps.get_model('scenarios', 'Scenario')
    for scenario in Scenario.objects.filter(share_token__isnull=True).only('id'):
        Scenario.objects.filter(pk=scenario.pk).update(share_token=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ('scenarios', '0009_scenario_visibility'),
    ]

    operations = [
        migrations.AddField(
            model_name='scenario',
            name='share_token',
            field=models.UUIDField(blank=True, db_index=True, editable=False, null=True),
        ),
        migrations.RunPython(populate_scenario_share_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='scenario',
            name='share_token',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
