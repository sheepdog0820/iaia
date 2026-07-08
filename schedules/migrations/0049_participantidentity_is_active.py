from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0048_alter_sessioninvitation_invited_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="participantidentity",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
    ]
