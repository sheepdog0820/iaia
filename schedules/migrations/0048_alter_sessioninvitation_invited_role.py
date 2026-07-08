from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0047_remove_sessionparticipant_role"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sessioninvitation",
            name="invited_role",
            field=models.CharField(
                choices=[("player", "PL"), ("gm", "GM"), ("observer", "Observer")],
                default="player",
                help_text="Session role assigned when the invitation is accepted",
                max_length=10,
            ),
        ),
    ]
