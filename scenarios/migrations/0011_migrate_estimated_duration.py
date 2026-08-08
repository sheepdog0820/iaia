from django.db import migrations

DEFAULT_MINUTES_BY_DURATION = {
    "short": 180,
    "medium": 270,
    "long": 420,
    "campaign": 480,
}


def migrate_estimated_duration(apps, schema_editor):
    Scenario = apps.get_model("scenarios", "Scenario")
    for duration, minutes in DEFAULT_MINUTES_BY_DURATION.items():
        Scenario.objects.filter(estimated_time__isnull=True, estimated_duration=duration).update(estimated_time=minutes)


class Migration(migrations.Migration):
    dependencies = [("scenarios", "0010_scenario_share_token")]

    operations = [
        migrations.RunPython(migrate_estimated_duration, migrations.RunPython.noop),
        migrations.RemoveField(model_name="scenario", name="estimated_duration"),
    ]
