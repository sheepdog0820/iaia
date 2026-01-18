# Generated for ISSUE-017 follow-up: Date poll chat comments

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('schedules', '0022_trpgsession_date_nullable'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatePollComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(help_text='コメント本文')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='schedules.datepoll')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='date_poll_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at', 'id'],
                'indexes': [
                    models.Index(fields=['poll', 'created_at'], name='date_poll_comment_poll_created'),
                    models.Index(fields=['user', 'created_at'], name='date_poll_comment_user_created'),
                ],
            },
        ),
    ]

