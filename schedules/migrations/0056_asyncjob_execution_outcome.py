from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("schedules", "0055_allow_multiple_participant_roles")]

    operations = [
        migrations.AddField(
            model_name="asyncjob",
            name="execution_token",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="asyncjob",
            name="execution_deadline",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="asyncjob",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("succeeded", "Succeeded"),
                    ("failed", "Failed"),
                    ("uncertain", "結果不明"),
                ],
                db_index=True,
                default="queued",
                max_length=16,
            ),
        ),
    ]
