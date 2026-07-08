from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0046_session_permission_model"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sessionparticipant",
            name="role",
        ),
    ]
