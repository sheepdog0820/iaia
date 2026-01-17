# Generated for allowing sessions without a fixed calendar date.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0021_session_availability_constraints'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trpgsession',
            name='date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

