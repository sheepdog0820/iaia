from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0038_sessioninvitation_invited_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="trpgsession",
            name="actual_duration_minutes",
            field=models.PositiveIntegerField(
                null=True,
                blank=True,
                help_text="実際にプレイした時間（分）。未入力時は予定時間を使用します。",
            ),
        ),
    ]
