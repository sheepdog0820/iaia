# Generated for ISSUE-017 follow-up: enforce unique availability votes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0020_advanced_scheduling'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='sessionavailability',
            constraint=models.UniqueConstraint(
                fields=['session', 'user'],
                name='unique_session_availability_vote',
            ),
        ),
        migrations.AddConstraint(
            model_name='sessionavailability',
            constraint=models.UniqueConstraint(
                fields=['occurrence', 'user'],
                name='unique_occurrence_availability_vote',
            ),
        ),
    ]

