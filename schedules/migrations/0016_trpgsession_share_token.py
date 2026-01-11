import uuid

from django.db import migrations, models


def populate_share_tokens(apps, schema_editor):
    TRPGSession = apps.get_model("schedules", "TRPGSession")
    session_ids = TRPGSession.objects.filter(share_token__isnull=True).values_list("id", flat=True)
    for session_id in session_ids:
        TRPGSession.objects.filter(id=session_id).update(share_token=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0015_sessionyoutubelink_perspective_part"),
    ]

    operations = [
        migrations.AddField(
            model_name="trpgsession",
            name="share_token",
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True, db_index=True),
        ),
        migrations.RunPython(populate_share_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="trpgsession",
            name="share_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]

