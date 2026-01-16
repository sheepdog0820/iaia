# Generated manually for ISSUE-017: Advanced Scheduling Features

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('schedules', '0019_add_friend_notification_fields'),
        ('accounts', '0001_initial'),
        ('scenarios', '0001_initial'),
    ]

    operations = [
        # SessionSeries model
        migrations.CreateModel(
            name='SessionSeries',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='シリーズ/キャンペーン名', max_length=200)),
                ('description', models.TextField(blank=True, help_text='シリーズの説明')),
                ('recurrence', models.CharField(
                    choices=[
                        ('none', '単発'),
                        ('weekly', '毎週'),
                        ('biweekly', '隔週'),
                        ('monthly', '毎月'),
                        ('custom', 'カスタム'),
                    ],
                    default='none',
                    help_text='繰り返しパターン',
                    max_length=10,
                )),
                ('weekday', models.IntegerField(
                    blank=True,
                    choices=[
                        (0, '月曜日'),
                        (1, '火曜日'),
                        (2, '水曜日'),
                        (3, '木曜日'),
                        (4, '金曜日'),
                        (5, '土曜日'),
                        (6, '日曜日'),
                    ],
                    help_text='曜日（毎週/隔週の場合）',
                    null=True,
                )),
                ('day_of_month', models.IntegerField(blank=True, help_text='日（毎月の場合、1-31）', null=True)),
                ('start_time', models.TimeField(blank=True, help_text='開始時刻', null=True)),
                ('duration_minutes', models.PositiveIntegerField(default=180, help_text='予定時間（分）')),
                ('custom_interval_days', models.PositiveIntegerField(blank=True, help_text='カスタム間隔（日数）', null=True)),
                ('start_date', models.DateField(help_text='シリーズ開始日')),
                ('end_date', models.DateField(blank=True, help_text='シリーズ終了日（空の場合は無期限）', null=True)),
                ('auto_create_sessions', models.BooleanField(default=True, help_text='セッションを自動生成する')),
                ('auto_create_weeks_ahead', models.PositiveIntegerField(default=4, help_text='何週間先まで自動生成するか')),
                ('is_active', models.BooleanField(default=True, help_text='シリーズがアクティブか')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('gm', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='gm_session_series',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='session_series',
                    to='accounts.group',
                )),
                ('scenario', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='session_series',
                    to='scenarios.scenario',
                )),
            ],
            options={
                'verbose_name': 'セッションシリーズ',
                'verbose_name_plural': 'セッションシリーズ',
                'ordering': ['-created_at'],
            },
        ),

        # Add series field to TRPGSession
        migrations.AddField(
            model_name='trpgsession',
            name='series',
            field=models.ForeignKey(
                blank=True,
                help_text='所属するセッションシリーズ',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sessions',
                to='schedules.sessionseries',
            ),
        ),

        # DatePoll model
        migrations.CreateModel(
            name='DatePoll',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='投票タイトル', max_length=200)),
                ('description', models.TextField(blank=True, help_text='説明')),
                ('deadline', models.DateTimeField(blank=True, help_text='投票締め切り', null=True)),
                ('is_closed', models.BooleanField(default=False, help_text='投票が締め切られたか')),
                ('selected_date', models.DateTimeField(blank=True, help_text='確定日時', null=True)),
                ('create_session_on_confirm', models.BooleanField(default=True, help_text='確定時にセッションを作成')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='created_date_polls',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='date_polls',
                    to='accounts.group',
                )),
                ('session', models.ForeignKey(
                    blank=True,
                    help_text='作成されたセッション',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='date_polls',
                    to='schedules.trpgsession',
                )),
            ],
            options={
                'verbose_name': '日程調整',
                'verbose_name_plural': '日程調整',
                'ordering': ['-created_at'],
            },
        ),

        # DatePollOption model
        migrations.CreateModel(
            name='DatePollOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(help_text='候補日時')),
                ('note', models.CharField(blank=True, help_text='備考', max_length=100)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('poll', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='options',
                    to='schedules.datepoll',
                )),
            ],
            options={
                'ordering': ['datetime'],
            },
        ),

        # DatePollVote model
        migrations.CreateModel(
            name='DatePollVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('available', '◯ 参加可能'),
                        ('maybe', '△ 未定'),
                        ('unavailable', '✕ 参加不可'),
                    ],
                    default='available',
                    max_length=15,
                )),
                ('comment', models.CharField(blank=True, help_text='コメント', max_length=100)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('option', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='votes',
                    to='schedules.datepolloption',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='date_poll_votes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),

        # DatePollVote unique constraint
        migrations.AddConstraint(
            model_name='datepollvote',
            constraint=models.UniqueConstraint(fields=['option', 'user'], name='unique_poll_vote'),
        ),

        # SessionAvailability model
        migrations.CreateModel(
            name='SessionAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('proposed_date', models.DateTimeField(blank=True, help_text='候補日時（セッション/オカレンスが未確定の場合）', null=True)),
                ('status', models.CharField(
                    choices=[
                        ('available', '参加可能'),
                        ('maybe', '未定'),
                        ('unavailable', '参加不可'),
                    ],
                    default='available',
                    max_length=15,
                )),
                ('comment', models.CharField(blank=True, help_text='コメント（遅刻/早退など）', max_length=200)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('occurrence', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='availability_votes',
                    to='schedules.sessionoccurrence',
                )),
                ('session', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='availability_votes',
                    to='schedules.trpgsession',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='availability_votes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['proposed_date', 'created_at'],
            },
        ),

        # SessionAvailability indexes
        migrations.AddIndex(
            model_name='sessionavailability',
            index=models.Index(fields=['session', 'user'], name='schedules_s_session_avail_idx'),
        ),
        migrations.AddIndex(
            model_name='sessionavailability',
            index=models.Index(fields=['occurrence', 'user'], name='schedules_o_occur_avail_idx'),
        ),
        migrations.AddIndex(
            model_name='sessionavailability',
            index=models.Index(fields=['proposed_date'], name='schedules_p_proposed_idx'),
        ),
    ]
