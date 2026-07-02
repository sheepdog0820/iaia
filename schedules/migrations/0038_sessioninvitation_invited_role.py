from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0037_trpgsession_created_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessioninvitation",
            name="invited_role",
            field=models.CharField(
                choices=[("player", "PL"), ("gm", "GM")],
                default="player",
                help_text="Session role assigned when the invitation is accepted",
                max_length=10,
            ),
        ),
    ]
