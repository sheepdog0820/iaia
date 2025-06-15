from django.db import models
from django.utils import timezone
from accounts.models import CustomUser, Group


class TRPGSession(models.Model):
    STATUS_CHOICES = [
        ('planned', '予定'),
        ('ongoing', '進行中'),
        ('completed', '完了'),
        ('cancelled', 'キャンセル'),
    ]
    
    VISIBILITY_CHOICES = [
        ('private', 'プライベート'),
        ('group', 'グループ内'),
        ('public', '公開'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    youtube_url = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='planned')
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='group')
    
    gm = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='gm_sessions')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='sessions')
    participants = models.ManyToManyField(CustomUser, through='SessionParticipant', related_name='sessions')
    
    duration_minutes = models.PositiveIntegerField(default=0, help_text="セッション時間（分）")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} ({self.date.strftime('%Y-%m-%d')})"
    
    class Meta:
        ordering = ['-date']


class SessionParticipant(models.Model):
    ROLE_CHOICES = [
        ('gm', 'GM'),
        ('player', 'PL'),
    ]
    
    session = models.ForeignKey(TRPGSession, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='player')
    character_name = models.CharField(max_length=100, blank=True)
    character_sheet_url = models.URLField(blank=True)
    
    class Meta:
        unique_together = ('session', 'user')
        
    def __str__(self):
        return f"{self.user.nickname} in {self.session.title} ({self.role})"


class HandoutInfo(models.Model):
    session = models.ForeignKey(TRPGSession, on_delete=models.CASCADE, related_name='handouts')
    participant = models.ForeignKey(SessionParticipant, on_delete=models.CASCADE, related_name='handouts')
    title = models.CharField(max_length=100)
    content = models.TextField()
    is_secret = models.BooleanField(default=True, help_text="秘匿ハンドアウトかどうか")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.participant.user.nickname}"
    
    class Meta:
        ordering = ['title']
