from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0011_rename_schedules_s_session_07710f_idx_schedules_s_session_628b50_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='handoutinfo',
            name='recommended_skills',
            field=models.TextField(
                blank=True,
                default='',
                help_text='推奨技能（カンマ/改行区切り）',
            ),
        ),
    ]
