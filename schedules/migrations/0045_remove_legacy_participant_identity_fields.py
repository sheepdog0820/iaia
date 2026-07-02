from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0044_allow_identity_gm_participants"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="participantidentity",
            name="schedules_p_normali_fd260a_idx",
        ),
        migrations.RemoveField(
            model_name="participantidentity",
            name="legacy_key",
        ),
        migrations.RemoveField(
            model_name="participantidentity",
            name="legacy_source",
        ),
        migrations.RemoveIndex(
            model_name="participantidentityalias",
            name="schedules_p_normali_860b37_idx",
        ),
        migrations.RemoveField(
            model_name="participantidentityalias",
            name="source",
        ),
    ]
