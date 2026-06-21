from django.conf import settings
from django.db import migrations, models


def backfill_created_by(apps, schema_editor):
    TRPGSession = apps.get_model('schedules', 'TRPGSession')
    TRPGSession.objects.filter(created_by__isnull=True).update(created_by_id=models.F('gm_id'))


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('schedules', '0036_japaneseholiday'),
    ]

    operations = [
        migrations.AddField(
            model_name='trpgsession',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='created_sessions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_created_by, migrations.RunPython.noop),
    ]
