# Generated by Django 5.2.3 on 2025-06-19 04:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_friend_updated_at_group_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='characterskill',
            name='current_value',
            field=models.IntegerField(default=0, verbose_name='現在値'),
        ),
    ]
