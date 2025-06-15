from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class CustomUser(AbstractUser):
    nickname = models.CharField(max_length=50, blank=True)
    trpg_history = models.TextField(blank=True, help_text="過去のTRPG参加履歴")
    profile_image = models.ImageField(upload_to='profiles/', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nickname or self.username


class Friend(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friends')
    friend = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friend_of')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'friend')
        
    def __str__(self):
        return f"{self.user.nickname} -> {self.friend.nickname}"


class Group(models.Model):
    VISIBILITY_CHOICES = [
        ('private', 'プライベート'),
        ('public', '公開'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='private')
    members = models.ManyToManyField(CustomUser, through='GroupMembership')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'group')
        
    def __str__(self):
        return f"{self.user.nickname} in {self.group.name} ({self.role})"


class GroupInvitation(models.Model):
    STATUS_CHOICES = [
        ('pending', '保留中'),
        ('accepted', '承認済み'),
        ('declined', '拒否'),
        ('expired', '期限切れ'),
    ]
    
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, help_text="招待メッセージ")
    
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('group', 'invitee')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.inviter.nickname} invited {self.invitee.nickname} to {self.group.name}"


class CharacterSheet(models.Model):
    """
    クトゥルフ神話TRPG キャラクターシート基底モデル
    6版・7版共通の基本データを管理
    """
    EDITION_CHOICES = [
        ('6th', '6版'),
        ('7th', '7版'),
    ]
    
    # 基本情報
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='character_sheets')
    edition = models.CharField(max_length=3, choices=EDITION_CHOICES)
    name = models.CharField(max_length=100, verbose_name="探索者名")
    player_name = models.CharField(max_length=100, blank=True, verbose_name="プレイヤー名")
    
    # 個人情報
    age = models.IntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name="年齢"
    )
    gender = models.CharField(max_length=50, blank=True, verbose_name="性別")
    occupation = models.CharField(max_length=100, blank=True, verbose_name="職業")
    birthplace = models.CharField(max_length=100, blank=True, verbose_name="出身地")
    residence = models.CharField(max_length=100, blank=True, verbose_name="居住地")
    
    # 能力値 (3D6×5で15-90、一部例外あり)
    str_value = models.IntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name="筋力(STR)"
    )
    con_value = models.IntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name="体力(CON)"
    )
    pow_value = models.IntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name="意志力(POW)"
    )
    dex_value = models.IntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name="敏捷性(DEX)"
    )
    app_value = models.IntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name="外見(APP)"
    )
    siz_value = models.IntegerField(
        validators=[MinValueValidator(30), MaxValueValidator(90)],
        verbose_name="体格(SIZ)"
    )
    int_value = models.IntegerField(
        validators=[MinValueValidator(40), MaxValueValidator(90)],
        verbose_name="知識(INT)"
    )
    edu_value = models.IntegerField(
        validators=[MinValueValidator(30), MaxValueValidator(90)],
        verbose_name="教育(EDU)"
    )
    
    # 副次ステータス
    hit_points_max = models.IntegerField(verbose_name="最大HP")
    hit_points_current = models.IntegerField(verbose_name="現在HP")
    magic_points_max = models.IntegerField(verbose_name="最大MP")
    magic_points_current = models.IntegerField(verbose_name="現在MP")
    sanity_starting = models.IntegerField(verbose_name="初期正気度")
    sanity_max = models.IntegerField(verbose_name="最大正気度")
    sanity_current = models.IntegerField(verbose_name="現在正気度")
    
    # バージョン管理
    version = models.PositiveIntegerField(default=1, verbose_name="バージョン")
    parent_sheet = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='versions',
        verbose_name="元キャラクター"
    )
    
    # 画像
    character_image = models.ImageField(
        upload_to='character_sheets/',
        blank=True,
        verbose_name="キャラクター画像"
    )
    
    # メタデータ
    notes = models.TextField(blank=True, verbose_name="メモ")
    is_active = models.BooleanField(default=True, verbose_name="アクティブ")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name', 'version']
        ordering = ['-updated_at']
        verbose_name = "キャラクターシート"
        verbose_name_plural = "キャラクターシート"
    
    def __str__(self):
        return f"{self.name} ({self.edition}) v{self.version}"
    
    @property
    def abilities(self):
        """能力値辞書を返す"""
        return {
            'str': self.str_value,
            'con': self.con_value,
            'pow': self.pow_value,
            'dex': self.dex_value,
            'app': self.app_value,
            'siz': self.siz_value,
            'int': self.int_value,
            'edu': self.edu_value,
        }
    
    def calculate_derived_stats(self):
        """派生ステータスを計算"""
        # HP = (CON + SIZ) / 10
        hp_max = (self.con_value + self.siz_value) // 10
        
        # MP = POW / 5
        mp_max = self.pow_value // 5
        
        # SAN = POW (最大99)
        san_start = self.pow_value
        san_max = min(99, self.pow_value)
        
        return {
            'hit_points_max': hp_max,
            'magic_points_max': mp_max,
            'sanity_starting': san_start,
            'sanity_max': san_max,
        }
    
    def save(self, *args, **kwargs):
        """保存時に派生ステータスを自動計算"""
        if not self.pk:  # 新規作成時
            derived = self.calculate_derived_stats()
            self.hit_points_max = derived['hit_points_max']
            self.hit_points_current = derived['hit_points_max']
            self.magic_points_max = derived['magic_points_max']
            self.magic_points_current = derived['magic_points_max']
            self.sanity_starting = derived['sanity_starting']
            self.sanity_max = derived['sanity_max']
            self.sanity_current = derived['sanity_starting']
        
        super().save(*args, **kwargs)


class CharacterSheet6th(models.Model):
    """6版固有データ"""
    character_sheet = models.OneToOneField(
        CharacterSheet, 
        on_delete=models.CASCADE,
        related_name='sixth_edition_data'
    )
    
    # 6版固有フィールド
    mental_disorder = models.TextField(blank=True, verbose_name="精神的障害")
    
    # 6版では自動計算される値
    idea_roll = models.IntegerField(verbose_name="アイデアロール")
    luck_roll = models.IntegerField(verbose_name="幸運ロール") 
    know_roll = models.IntegerField(verbose_name="知識ロール")
    damage_bonus = models.CharField(max_length=10, verbose_name="ダメージボーナス")
    
    def save(self, *args, **kwargs):
        """6版固有の計算を実行"""
        if self.character_sheet:
            # アイデア = INT × 5
            self.idea_roll = self.character_sheet.int_value * 5
            
            # 幸運 = POW × 5
            self.luck_roll = self.character_sheet.pow_value * 5
            
            # 知識 = EDU × 5
            self.know_roll = self.character_sheet.edu_value * 5
            
            # ダメージボーナス計算
            self.damage_bonus = self.calculate_damage_bonus_6th()
        
        super().save(*args, **kwargs)
    
    def calculate_damage_bonus_6th(self):
        """6版ダメージボーナス計算"""
        total = self.character_sheet.str_value + self.character_sheet.siz_value
        
        if total <= 64:
            return "-1d4"
        elif total <= 84:
            return "-1d2"
        elif total <= 124:
            return "+0"
        elif total <= 164:
            return "+1d4"
        elif total <= 204:
            return "+1d6"
        elif total <= 284:
            return "+2d6"
        elif total <= 364:
            return "+3d6"
        elif total <= 444:
            return "+4d6"
        else:
            return "+5d6"


class CharacterSheet7th(models.Model):
    """7版固有データ"""
    character_sheet = models.OneToOneField(
        CharacterSheet,
        on_delete=models.CASCADE,
        related_name='seventh_edition_data'
    )
    
    # 7版固有能力値
    luck_points = models.IntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name="幸運"
    )
    
    # 7版固有計算値
    build_value = models.IntegerField(verbose_name="ビルド")
    move_rate = models.IntegerField(verbose_name="移動力")
    dodge_value = models.IntegerField(verbose_name="回避")
    damage_bonus = models.CharField(max_length=10, verbose_name="ダメージボーナス")
    
    # 7版背景情報
    personal_description = models.TextField(blank=True, verbose_name="個人的な記述")
    ideology_beliefs = models.TextField(blank=True, verbose_name="イデオロギー・信念")
    significant_people = models.TextField(blank=True, verbose_name="重要な人々")
    meaningful_locations = models.TextField(blank=True, verbose_name="思い出の品・場所")
    treasured_possessions = models.TextField(blank=True, verbose_name="宝物")
    traits = models.TextField(blank=True, verbose_name="特徴")
    injuries_scars = models.TextField(blank=True, verbose_name="傷・傷跡")
    phobias_manias = models.TextField(blank=True, verbose_name="恐怖症・躁病")
    
    def save(self, *args, **kwargs):
        """7版固有の計算を実行"""
        if self.character_sheet:
            # ビルド計算
            self.build_value = self.calculate_build_7th()
            
            # 移動力計算
            self.move_rate = self.calculate_move_rate_7th()
            
            # 回避 = DEX / 2
            self.dodge_value = self.character_sheet.dex_value // 2
            
            # ダメージボーナス計算
            self.damage_bonus = self.get_damage_bonus_from_build()
        
        super().save(*args, **kwargs)
    
    def calculate_build_7th(self):
        """7版ビルド計算"""
        total = self.character_sheet.str_value + self.character_sheet.siz_value
        
        if total <= 64:
            return -2
        elif total <= 84:
            return -1
        elif total <= 124:
            return 0
        elif total <= 164:
            return 1
        elif total <= 204:
            return 2
        elif total <= 284:
            return 3
        else:
            return 4
    
    def calculate_move_rate_7th(self):
        """7版移動力計算"""
        base_move = 8
        age = self.character_sheet.age
        
        # 年齢修正
        if age >= 80:
            base_move -= 5
        elif age >= 70:
            base_move -= 4
        elif age >= 60:
            base_move -= 3
        elif age >= 50:
            base_move -= 2
        elif age >= 40:
            base_move -= 1
        
        # 能力値修正
        str_val = self.character_sheet.str_value
        dex_val = self.character_sheet.dex_value
        siz_val = self.character_sheet.siz_value
        
        if str_val < siz_val and dex_val < siz_val:
            base_move -= 1
        elif str_val > siz_val or dex_val > siz_val:
            base_move += 1
        
        return max(base_move, 1)
    
    def get_damage_bonus_from_build(self):
        """ビルドからダメージボーナスを取得"""
        build_to_damage = {
            -2: "-2",
            -1: "-1",
            0: "+0",
            1: "+1d4",
            2: "+1d6",
            3: "+2d6",
            4: "+3d6"
        }
        return build_to_damage.get(self.build_value, "+0")


class CharacterSkill(models.Model):
    """キャラクタースキル"""
    character_sheet = models.ForeignKey(
        CharacterSheet,
        on_delete=models.CASCADE,
        related_name='skills'
    )
    skill_name = models.CharField(max_length=100, verbose_name="技能名")
    
    # ポイント配分
    base_value = models.IntegerField(default=0, verbose_name="基本値")
    occupation_points = models.IntegerField(default=0, verbose_name="職業技能ポイント")
    interest_points = models.IntegerField(default=0, verbose_name="興味技能ポイント")
    other_points = models.IntegerField(default=0, verbose_name="その他ポイント")
    
    # 現在値（自動計算）
    current_value = models.IntegerField(verbose_name="現在値")
    
    # 7版用
    half_value = models.IntegerField(default=0, verbose_name="1/2値")
    fifth_value = models.IntegerField(default=0, verbose_name="1/5値")
    
    class Meta:
        unique_together = ['character_sheet', 'skill_name']
        ordering = ['skill_name']
        verbose_name = "キャラクタースキル"
        verbose_name_plural = "キャラクタースキル"
    
    def save(self, *args, **kwargs):
        """保存時に値を自動計算"""
        # 現在値計算
        self.current_value = (
            self.base_value + 
            self.occupation_points + 
            self.interest_points + 
            self.other_points
        )
        
        # 7版の場合、半分値・1/5値を計算
        if self.character_sheet.edition == '7th':
            self.half_value = self.current_value // 2
            self.fifth_value = self.current_value // 5
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.character_sheet.name} - {self.skill_name}: {self.current_value}"


class CharacterEquipment(models.Model):
    """キャラクター装備・所持品"""
    ITEM_TYPE_CHOICES = [
        ('weapon', '武器'),
        ('armor', '防具'),
        ('item', 'アイテム'),
    ]
    
    character_sheet = models.ForeignKey(
        CharacterSheet,
        on_delete=models.CASCADE,
        related_name='equipment'
    )
    item_type = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES)
    name = models.CharField(max_length=100, verbose_name="名前")
    
    # 武器用フィールド
    skill_name = models.CharField(max_length=100, blank=True, verbose_name="使用技能")
    damage = models.CharField(max_length=20, blank=True, verbose_name="ダメージ")
    base_range = models.CharField(max_length=20, blank=True, verbose_name="射程")
    attacks_per_round = models.IntegerField(null=True, blank=True, verbose_name="攻撃回数/R")
    ammo = models.IntegerField(null=True, blank=True, verbose_name="装弾数")
    malfunction_number = models.IntegerField(null=True, blank=True, verbose_name="故障ナンバー")
    
    # 防具用フィールド
    armor_points = models.IntegerField(null=True, blank=True, verbose_name="防護点")
    
    # 一般情報
    description = models.TextField(blank=True, verbose_name="説明")
    quantity = models.IntegerField(default=1, verbose_name="数量")
    
    class Meta:
        ordering = ['item_type', 'name']
        verbose_name = "キャラクター装備"
        verbose_name_plural = "キャラクター装備"
    
    def __str__(self):
        return f"{self.character_sheet.name} - {self.name}"
