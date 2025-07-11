# Generated by Django 5.2.3 on 2025-06-25 03:50

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0006_add_session_images'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionYouTubeLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('youtube_url', models.URLField(max_length=500)),
                ('video_id', models.CharField(db_index=True, max_length=50)),
                ('title', models.CharField(max_length=200)),
                ('duration_seconds', models.PositiveIntegerField(default=0)),
                ('channel_name', models.CharField(blank=True, max_length=100)),
                ('thumbnail_url', models.URLField(blank=True, max_length=500)),
                ('description', models.TextField(blank=True, help_text='この動画についての説明やメモ', verbose_name='備考')),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('added_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='added_youtube_links', to=settings.AUTH_USER_MODEL)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='youtube_links', to='schedules.trpgsession')),
            ],
            options={
                'ordering': ['order', 'created_at'],
                'indexes': [models.Index(fields=['session', 'order'], name='schedules_s_session_29437d_idx')],
                'unique_together': {('session', 'video_id')},
            },
        ),
    ]
