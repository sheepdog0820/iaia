# Generated by Django 5.2.3 on 2025-06-14 00:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scenarios', '0001_initial'),
        ('schedules', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='playhistory',
            name='session',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='schedules.trpgsession'),
        ),
    ]
