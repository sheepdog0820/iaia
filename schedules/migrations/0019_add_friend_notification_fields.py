# Generated manually for ISSUE-013 friend request notifications

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0018_backfill_session_occurrences'),
    ]

    operations = [
        # Add friend_notifications_enabled field to UserNotificationPreferences
        migrations.AddField(
            model_name='usernotificationpreferences',
            name='friend_notifications_enabled',
            field=models.BooleanField(default=True, help_text='フレンド通知を有効にする'),
        ),
        # Update notification_type choices in HandoutNotification
        # (This is handled by altering the field)
        migrations.AlterField(
            model_name='handoutnotification',
            name='notification_type',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('handout_created', 'ハンドアウト作成'),
                    ('handout_published', 'ハンドアウト公開'),
                    ('handout_updated', 'ハンドアウト更新'),
                    ('session_invitation', 'セッション招待'),
                    ('schedule_change', 'スケジュール変更'),
                    ('session_cancelled', 'セッションキャンセル'),
                    ('session_reminder', 'セッションリマインダー'),
                    ('group_invitation', 'グループ招待'),
                    ('friend_request', 'フレンドリクエスト'),
                    ('friend_request_accepted', 'フレンドリクエスト承認'),
                ],
            ),
        ),
    ]
