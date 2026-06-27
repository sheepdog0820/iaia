from django.db import models
from django.utils import timezone
from accounts.models import CustomUser


SKILL_LEVEL_CHOICES = [
    ('required', 'Required'),
    ('recommended', 'Recommended'),
    ('semi_recommended', 'Semi recommended'),
    ('optional', 'Optional'),
]


class Scenario(models.Model):
    VISIBILITY_CHOICES = [
        ('private', 'Private'),
        ('group', 'Group'),
        ('link', 'Link'),
        ('public', 'Public'),
    ]

    GAME_SYSTEM_CHOICES = [
        ('coc6', 'クトゥルフ神話TRPG 6版'),
        ('coc7', 'クトゥルフ神話TRPG 7版'),
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
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    game_system = models.CharField(max_length=10, choices=GAME_SYSTEM_CHOICES, default='coc6')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='intermediate')
    estimated_duration = models.CharField(max_length=20, choices=DURATION_CHOICES, default='medium')
    summary = models.TextField(blank=True)
    public_info = models.TextField(blank=True, default='', help_text="PL向け公開情報")
    gm_notes = models.TextField(blank=True, default='', help_text="GM向け非公開メモ")
    investigator_requirements = models.TextField(blank=True, default='', help_text="推奨探索者条件")
    scenario_tags = models.CharField(max_length=255, blank=True, default='', help_text="タグ（カンマ区切り）")
    content_warnings = models.TextField(blank=True, default='', help_text="注意事項・地雷チェック")
    setting_era = models.CharField(max_length=100, blank=True, default='', help_text="時代")
    setting_location = models.CharField(max_length=100, blank=True, default='', help_text="舞台・地域")
    scenario_style = models.CharField(max_length=100, blank=True, default='', help_text="形式（クローズド/シティ等）")
    lost_rate = models.CharField(max_length=50, blank=True, default='', help_text="ロスト率")
    combat_level = models.CharField(max_length=50, blank=True, default='', help_text="戦闘有無・頻度")
    pvp_level = models.CharField(max_length=50, blank=True, default='', help_text="PvP有無")
    min_players = models.PositiveIntegerField(null=True, blank=True, help_text="最小人数")
    max_players = models.PositiveIntegerField(null=True, blank=True, help_text="最大人数")
    semi_recommended_skills = models.TextField(blank=True, default='', help_text="準推奨技能（カンマ区切り）")
    recommended_skills = models.TextField(blank=True, help_text="推奨技能（カンマ区切り）")
    url = models.URLField(blank=True, help_text="参照URL")
    recommended_players = models.CharField(max_length=50, blank=True, help_text="推奨人数（例: 3-4人）")
    player_count = models.PositiveIntegerField(help_text="推奨プレイヤー数", null=True, blank=True)
    estimated_time = models.PositiveIntegerField(help_text="推定プレイ時間（分）", null=True, blank=True)
    
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_scenarios')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if self.game_system in ('coc', 'cthulhu', '6', '6th'):
            self.game_system = 'coc6'
        elif self.game_system in ('7', '7th'):
            self.game_system = 'coc7'
        if self.recommended_skills is not None:
            self.recommended_skills = self.recommended_skills.strip()
        if self.semi_recommended_skills is not None:
            self.semi_recommended_skills = self.semi_recommended_skills.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['title']


class ScenarioRecommendedSkill(models.Model):
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='recommended_skill_items',
    )
    name = models.CharField(max_length=100)
    level = models.CharField(
        max_length=20,
        choices=SKILL_LEVEL_CHOICES,
        default='recommended',
    )
    description = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['scenario', 'order']),
        ]

    def __str__(self):
        return f"{self.scenario.title}: {self.name}"


class ScenarioHandout(models.Model):
    HANDOUT_NUMBER_CHOICES = [
        (1, 'HO1'),
        (2, 'HO2'),
        (3, 'HO3'),
        (4, 'HO4'),
    ]
    PLAYER_SLOT_CHOICES = [
        (1, 'プレイヤー1'),
        (2, 'プレイヤー2'),
        (3, 'プレイヤー3'),
        (4, 'プレイヤー4'),
    ]

    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='handout_templates',
    )
    code = models.CharField(max_length=50, blank=True, default='')
    name = models.CharField(max_length=100, blank=True, default='')
    title = models.CharField(max_length=100)
    content = models.TextField(blank=True, default='')
    recommended_skills = models.TextField(blank=True, default='')
    is_secret = models.BooleanField(default=True)
    handout_number = models.IntegerField(
        null=True,
        blank=True,
    )
    assigned_player_slot = models.IntegerField(
        choices=PLAYER_SLOT_CHOICES,
        null=True,
        blank=True,
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['scenario', 'order']),
            models.Index(fields=['scenario', 'code']),
        ]

    def __str__(self):
        label = self.code or (f"HO{self.handout_number}" if self.handout_number else "HO")
        return f"{self.scenario.title}: {label} {self.name or self.title}"

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.title
        if not self.title:
            self.title = self.name
        if not self.code and self.handout_number:
            self.code = f"HO{self.handout_number}"
        super().save(*args, **kwargs)


class ScenarioHandoutRecommendedSkill(models.Model):
    handout = models.ForeignKey(
        ScenarioHandout,
        on_delete=models.CASCADE,
        related_name='recommended_skill_items',
    )
    name = models.CharField(max_length=100)
    level = models.CharField(
        max_length=20,
        choices=SKILL_LEVEL_CHOICES,
        default='recommended',
    )
    description = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['handout', 'order']),
        ]

    def __str__(self):
        return f"{self.handout}: {self.name}"


class ScenarioImage(models.Model):
    """シナリオ添付画像モデル"""

    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(
        upload_to='scenario_images/%Y/%m/%d/',
        help_text='シナリオに関連する画像',
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text='画像のタイトル',
    )
    description = models.TextField(
        blank=True,
        help_text='画像の説明',
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text='表示順序',
    )
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_scenario_images',
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['scenario', 'order']),
        ]

    def __str__(self):
        return f"{self.scenario.title} - {self.title or f'画像{self.order + 1}'}"

    def save(self, *args, **kwargs):
        # 新規作成時、orderを自動設定
        if not self.pk and self.order == 0 and hasattr(self, 'scenario_id') and self.scenario_id:
            max_order = ScenarioImage.objects.filter(
                scenario_id=self.scenario_id,
            ).aggregate(
                max_order=models.Max('order'),
            )['max_order']
            self.order = (max_order or 0) + 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """削除時に画像ファイルも削除"""
        if self.image:
            try:
                if self.image.storage.exists(self.image.name):
                    self.image.delete(save=False)
            except Exception:
                pass
        super().delete(*args, **kwargs)


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
