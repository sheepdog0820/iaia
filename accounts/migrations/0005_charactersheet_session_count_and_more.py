# Generated by Django 5.2.3 on 2025-06-16 11:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_characterskill_bonus_points_characterskill_category_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='charactersheet',
            name='session_count',
            field=models.PositiveIntegerField(default=0, verbose_name='セッション数'),
        ),
        migrations.AddField(
            model_name='charactersheet',
            name='version_note',
            field=models.CharField(blank=True, max_length=1000, verbose_name='バージョンメモ'),
        ),
    ]
