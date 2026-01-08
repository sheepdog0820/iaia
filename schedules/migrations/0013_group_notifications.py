from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0012_handoutinfo_recommended_skills'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotificationpreferences',
            name='group_notifications_enabled',
            field=models.BooleanField(default=True, help_text='グループ通知を有効にする'),
        ),
        migrations.AlterField(
            model_name='handoutnotification',
            name='notification_type',
            field=models.CharField(choices=[('handout_created', 'ハンドアウト作成'), ('handout_published', 'ハンドアウト公開'), ('handout_updated', 'ハンドアウト更新'), ('session_invitation', 'セッション招待'), ('schedule_change', 'スケジュール変更'), ('session_cancelled', 'セッションキャンセル'), ('session_reminder', 'セッションリマインダー'), ('group_invitation', 'グループ招待')], max_length=30),
        ),
    ]
