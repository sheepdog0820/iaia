# Generated by Django 5.2.3 on 2025-06-19 12:20

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_alter_characterskill_current_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='charactersheet',
            name='occupation_multiplier',
            field=models.IntegerField(default=20, validators=[django.core.validators.MinValueValidator(15), django.core.validators.MaxValueValidator(30)], verbose_name='職業技能ポイント倍率'),
        ),
    ]
