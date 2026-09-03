from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0054_sessionrecruitmentlink_sessionrecruitmentlinkuse_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="sessionparticipantrole",
            name="uniq_participant_single_role",
        ),
        migrations.AddConstraint(
            model_name="sessionparticipantrole",
            constraint=models.UniqueConstraint(
                fields=("participant", "role"),
                name="uniq_participant_role",
            ),
        ),
    ]
