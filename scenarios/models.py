from django.db import models
from django.utils import timezone
from accounts.models import CustomUser


class Scenario(models.Model):
    GAME_SYSTEM_CHOICES = [
        ('coc', 'クトゥルフ神話TRPG'),
        ('dnd', 'D&D'),
        ('sw', 'ソード・ワールド'),
        ('insane', 'インセイン'),
        ('other', 'その他'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('beginner', '初心者向け'),
        ('intermediate', '中級者向け'),
        ('advanced', '上級者向け'),
        ('expert', 'エキスパート'),
    ]
    
    DURATION_CHOICES = [
        ('short', '短編（〜3時間）'),
        ('medium', '中編（3〜6時間）'),
        ('long', '長編（6時間〜）'),
        ('campaign', 'キャンペーン'),
    ]
    
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100, blank=True)
    game_system = models.CharField(max_length=10, choices=GAME_SYSTEM_CHOICES, default='coc')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='intermediate')
    estimated_duration = models.CharField(max_length=20, choices=DURATION_CHOICES, default='medium')
    summary = models.TextField(blank=True)
    url = models.URLField(blank=True, help_text="参照URL")
    recommended_players = models.CharField(max_length=50, blank=True, help_text="推奨人数（例: 3-4人）")
    player_count = models.PositiveIntegerField(help_text="推奨プレイヤー数", null=True, blank=True)
    estimated_time = models.PositiveIntegerField(help_text="推定プレイ時間（分）", null=True, blank=True)
    
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_scenarios')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['title']


class ScenarioNote(models.Model):
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.TextField()
    is_private = models.BooleanField(default=True, help_text="プライベートメモかどうか")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.scenario.title} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']


class PlayHistory(models.Model):
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='play_histories')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='play_histories')
    session = models.ForeignKey('schedules.TRPGSession', on_delete=models.CASCADE, null=True, blank=True)
    played_date = models.DateTimeField()
    role = models.CharField(max_length=10, choices=[('gm', 'GM'), ('player', 'PL')])
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.nickname} played {self.scenario.title} ({self.role})"
    
    class Meta:
        ordering = ['-played_date']
