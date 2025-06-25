"""
キャラクターシート関連モデル
クトゥルフ神話TRPG 6版専用のモデル定義
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json

# Circular import回避のため、文字列参照を使用


class CharacterSheet(models.Model):
    """
    クトゥルフ神話TRPG キャラクターシート基底モデル
    6版・7版共通の基本データを管理
    """
    EDITION_CHOICES = [
        ('6th', '6版'),
    ]
    
    STATUS_CHOICES = [
        ('alive', '生存'),
        ('dead', '死亡'),
        ('insane', '発狂'),
        ('injured', '重傷'),
        ('missing', '行方不明'),
        ('retired', '引退'),
    ]
    
    # 基本情報
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='character_sheets')
    edition = models.CharField(max_length=3, choices=EDITION_CHOICES)
    name = models.CharField(max_length=100, verbose_name="探索者名")
    player_name = models.CharField(max_length=100, blank=True, verbose_name="プレイヤー名")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='alive', verbose_name="状態")
    
    # 個人情報
    age = models.IntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name="年齢"
    )
    gender = models.CharField(max_length=50, blank=True, verbose_name="性別")
    occupation = models.CharField(max_length=100, blank=True, verbose_name="職業")
    birthplace = models.CharField(max_length=100, blank=True, verbose_name="出身地")
    residence = models.CharField(max_length=100, blank=True, verbose_name="居住地")
    
    # 能力値 (範囲制限なし - ユーザーの自由度を最大化)
    str_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        verbose_name="筋力(STR)"
    )
    con_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        verbose_name="体力(CON)"
    )
    pow_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        verbose_name="意志力(POW)"
    )
    dex_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        verbose_name="敏捷性(DEX)"
    )
    app_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        verbose_name="外見(APP)"
    )
    siz_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        verbose_name="体格(SIZ)"
    )
    int_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        verbose_name="知識(INT)"
    )
    edu_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        verbose_name="教育(EDU)"
    )
    
    # 職業技能ポイント倍率（デフォルトは20）
    occupation_multiplier = models.IntegerField(
        default=20,
        validators=[MinValueValidator(15), MaxValueValidator(30)],
        verbose_name="職業技能ポイント倍率"
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
    version_note = models.CharField(max_length=1000, blank=True, verbose_name="バージョンメモ")
    session_count = models.PositiveIntegerField(default=0, verbose_name="セッション数")
    is_active = models.BooleanField(default=True, verbose_name="アクティブ")
    
    # CCFOLIA連携
    ccfolia_sync_enabled = models.BooleanField(default=False, verbose_name="CCFOLIA同期有効")
    ccfolia_character_id = models.CharField(max_length=100, blank=True, verbose_name="CCFOLIAキャラクターID")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # バージョン管理用の制約のみ（同一ユーザーの同一キャラクターでバージョンが重複しないよう）
        # 同名キャラクターは作成可能
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
    
    # リアルタイムステータスのエイリアス（テスト互換性のため）
    @property
    def hp_current(self):
        """現在HPのエイリアス"""
        return self.hit_points_current
    
    @hp_current.setter
    def hp_current(self, value):
        """現在HPのセッター"""
        self.hit_points_current = value
    
    @property
    def mp_current(self):
        """現在MPのエイリアス"""
        return self.magic_points_current
    
    @mp_current.setter
    def mp_current(self, value):
        """現在MPのセッター"""
        self.magic_points_current = value
    
    @property
    def san_current(self):
        """現在正気度のエイリアス"""
        return self.sanity_current
    
    @san_current.setter
    def san_current(self, value):
        """現在正気度のセッター"""
        self.sanity_current = value
    
    @property
    def mp_max(self):
        """最大MPのエイリアス"""
        return self.magic_points_max
    
    def calculate_derived_stats(self):
        """派生ステータスを計算"""
        # 6版と7版で計算式が異なる
        if self.edition == '6th':
            # 6版
            # HP = (CON + SIZ) / 2
            hp_max = (self.con_value + self.siz_value) // 2
            # MP = POW
            mp_max = self.pow_value
            # SAN = POW × 5 (最大99)
            san_start = self.pow_value * 5
            san_max = min(99, self.pow_value * 5)
        else:
            # 7版
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
        from django.core.exceptions import ValidationError
        
        # 循環参照の防止
        if self.parent_sheet:
            current = self.parent_sheet
            while current:
                if current == self:
                    raise ValidationError("循環参照は許可されていません")
                current = current.parent_sheet
        
        # バージョン番号の重複チェック（バージョンアップ時のみ）
        if not self.pk and self.parent_sheet:  # 新しいバージョン作成時のみ
            existing = CharacterSheet.objects.filter(
                parent_sheet=self.parent_sheet,
                version=self.version
            ).exclude(pk=self.pk).exists()
            if existing:
                raise ValidationError(f"バージョン{self.version}は既に存在します")
        
        # saveメソッドでの自動計算を無効化
        # フォームで全ての値を設定するため、モデルでの自動計算は行わない
        
        super().save(*args, **kwargs)
    
    def create_new_version(self, version_note="", session_count=None, copy_skills=False):
        """
        新しいバージョンを作成
        
        Args:
            version_note: バージョンメモ
            session_count: セッション数
            copy_skills: 技能をコピーするか
        
        Returns:
            新しいバージョンのCharacterSheetオブジェクト
        """
        return CharacterVersionManager.create_new_version(
            self, version_note, session_count, copy_skills
        )
    
    def get_version_history(self):
        """バージョン履歴を取得"""
        return CharacterVersionManager.get_version_history(self)
    
    def get_latest_version(self):
        """最新バージョンを取得"""
        return CharacterVersionManager.get_latest_version(self)
    
    def get_root_version(self):
        """ルートバージョンを取得"""
        return CharacterVersionManager.get_root_version(self)
    
    def get_child_versions(self):
        """直接の子バージョンを取得"""
        return self.versions.all()
    
    def compare_with_version(self, other_version):
        """他のバージョンとの比較"""
        return CharacterVersionManager.compare_versions(self, other_version)
    
    def rollback_to_version(self, target_version):
        """指定バージョンにロールバック"""
        return CharacterVersionManager.rollback_to_version(self, target_version)
    
    def get_version_statistics(self):
        """バージョン統計を取得"""
        return CharacterVersionManager.get_version_statistics(self)
    
    def export_version_data(self):
        """バージョンデータをエクスポート"""
        return CharacterExportManager.export_version_data(self)
    
    def export_ccfolia_format(self):
        """CCFOLIA形式でのデータエクスポート"""
        return CharacterExportManager.export_ccfolia_format(self)
    
    def sync_to_ccfolia(self):
        """CCFOLIAへの同期処理"""
        return CharacterSyncManager.sync_to_ccfolia(self)
    
    def resolve_sync_conflict(self, conflict_data):
        """同期競合の解決"""
        return CharacterSyncManager.resolve_sync_conflict(self, conflict_data)
    
    # 技能ポイント管理メソッド
    def calculate_occupation_points(self):
        """職業技能ポイントを計算"""
        if hasattr(self, 'occupation_multiplier') and self.occupation_multiplier:
            return self.edu_value * self.occupation_multiplier
        return self.edu_value * 20  # デフォルトはEDU×20
    
    def calculate_hobby_points(self):
        """趣味技能ポイントを計算"""
        return self.int_value * 10  # INT×10
    
    def calculate_used_occupation_points(self):
        """使用済み職業技能ポイントを計算"""
        from django.db.models import Sum
        total = self.skills.aggregate(
            total=Sum('occupation_points')
        )['total'] or 0
        return total
    
    def calculate_used_hobby_points(self):
        """使用済み趣味技能ポイントを計算"""
        from django.db.models import Sum
        total = self.skills.aggregate(
            total=Sum('interest_points')
        )['total'] or 0
        return total
    
    def calculate_remaining_occupation_points(self):
        """残り職業技能ポイントを計算"""
        return self.calculate_occupation_points() - self.calculate_used_occupation_points()
    
    def calculate_remaining_hobby_points(self):
        """残り趣味技能ポイントを計算"""
        return self.calculate_hobby_points() - self.calculate_used_hobby_points()
    
    def get_occupation_recommended_skills(self):
        """職業別推奨技能リストを取得"""
        occupation_skills = {
            '医師': [
                '医学', '応急手当', '生物学', '薬学',
                '心理学', '精神分析', '信用', '言いくるめ'
            ],
            '教授': [
                '図書館', '母国語', '他の言語', '教育',
                '心理学', '歴史', '人類学', '説得'
            ],
            '警察官': [
                '拳銃', '格闘技', '心理学', '聞き耳',
                '目星', '運転', '法律', '威圧'
            ],
            '探偵': [
                '目星', '聞き耳', '隠れる', '忍び歩き',
                '心理学', '図書館', '法律', '説得'
            ],
            '記者': [
                '目星', '聞き耳', '図書館', '心理学',
                '説得', '信用', '写真術', '運転'
            ],
            '考古学者': [
                '考古学', '歴史', '図書館', '目星',
                '他の言語', '登攀', '機械修理', 'ナビゲート'
            ]
        }
        
        return occupation_skills.get(self.occupation, [])
    
    def apply_occupation_template(self):
        """職業テンプレートを適用して推奨技能を作成"""
        recommended_skills = self.get_occupation_recommended_skills()
        
        # 教授の場合は倍率を25に設定
        if self.occupation == '教授':
            self.occupation_multiplier = 25
            self.save()
        
        # 推奨技能を作成
        for skill_name in recommended_skills:
            skill, created = CharacterSkill.objects.get_or_create(
                character_sheet=self,
                skill_name=skill_name,
                defaults={
                    'base_value': self._get_skill_base_value(skill_name),
                    'category': self._get_skill_category(skill_name)
                }
            )
        
        return len(recommended_skills)
    
    def _get_skill_base_value(self, skill_name):
        """技能の基本値を取得"""
        # 技能別基本値の定義
        base_values = {
            '医学': 5, '応急手当': 30, '生物学': 1, '薬学': 1,
            '心理学': 5, '精神分析': 1, '信用': 15, '言いくるめ': 5,
            '図書館': 25, '母国語': self.edu_value * 5, '他の言語': 1,
            '教育': 20, '歴史': 20, '人類学': 1, '説得': 15,
            '拳銃': 20, '格闘技': 25, '聞き耳': 25, '目星': 25,
            '運転': 20, '法律': 5, '威圧': 15, '隠れる': 10,
            '忍び歩き': 10, '写真術': 10, '考古学': 1,
            '登攀': 40, '機械修理': 20, 'ナビゲート': 10
        }
        
        return base_values.get(skill_name, 5)
    
    def _get_skill_category(self, skill_name):
        """技能のカテゴリを取得"""
        categories = {
            '医学': '知識系', '応急手当': '探索系', '生物学': '知識系', '薬学': '知識系',
            '心理学': '対人系', '精神分析': '対人系', '信用': '対人系', '言いくるめ': '対人系',
            '図書館': '探索系', '母国語': '対人系', '他の言語': '対人系',
            '教育': '対人系', '歴史': '知識系', '人類学': '知識系', '説得': '対人系',
            '拳銃': '戦闘系', '格闘技': '戦闘系', '聞き耳': '探索系', '目星': '探索系',
            '運転': '行動系', '法律': '知識系', '威圧': '対人系', '隠れる': '探索系',
            '忍び歩き': '探索系', '写真術': '技術系', '考古学': '知識系',
            '登攀': '行動系', '機械修理': '技術系', 'ナビゲート': '行動系'
        }
        
        return categories.get(skill_name, '特殊・その他')
    
    def export_ccfolia_format(self):
        """CCFOLIA形式でのデータエクスポート"""
        return CharacterExportManager.export_ccfolia_format(self)
    
    def calculate_carry_capacity(self):
        """運搬能力を計算（STRベース）"""
        # 基本運搬能力 = STR * 3kg （簡易ルール）
        return self.str_value * 3
    
    def calculate_movement_penalty(self, total_weight):
        """移動ペナルティを計算"""
        carry_capacity = self.calculate_carry_capacity()
        
        if total_weight <= carry_capacity:
            return 0  # ペナルティなし
        elif total_weight <= carry_capacity * 1.5:
            return 10  # 軽度のペナルティ
        elif total_weight <= carry_capacity * 2:
            return 20  # 中度のペナルティ
        else:
            return 30  # 重度のペナルティ


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
    idea_roll = models.IntegerField(default=0, verbose_name="アイデアロール")
    luck_roll = models.IntegerField(default=0, verbose_name="幸運ロール") 
    know_roll = models.IntegerField(default=0, verbose_name="知識ロール")
    damage_bonus = models.CharField(max_length=10, default="+0", verbose_name="ダメージボーナス")
    
    # 財務データ
    cash = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="現金・資産"
    )
    assets = models.DecimalField(
        max_digits=12,
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="その他資産"
    )
    annual_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="年収"
    )
    real_estate = models.TextField(blank=True, verbose_name="不動産")
    
    def clean(self):
        """財務データのバリデーション"""
        from django.core.exceptions import ValidationError
        
        # 負の値チェック
        if self.cash < 0:
            raise ValidationError({'cash': '現金は0以上の値を入力してください。'})
        
        if self.assets < 0:
            raise ValidationError({'assets': '資産は0以上の値を入力してください。'})
            
        if self.annual_income < 0:
            raise ValidationError({'annual_income': '年収は0以上の値を入力してください。'})
        
        # 上限チェック（10億円）
        max_value = 1000000000
        if self.cash >= max_value:
            raise ValidationError({'cash': f'現金は{max_value:,}円未満で入力してください。'})
            
        if self.assets >= max_value:
            raise ValidationError({'assets': f'資産は{max_value:,}円未満で入力してください。'})
            
        if self.annual_income >= max_value:
            raise ValidationError({'annual_income': f'年収は{max_value:,}円未満で入力してください。'})
    
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
        
        # 計算後にバリデーション実行
        self.full_clean()
        
        super().save(*args, **kwargs)
    
    def calculate_damage_bonus_6th(self):
        """6版ダメージボーナス計算"""
        total = self.character_sheet.str_value + self.character_sheet.siz_value
        
        if total <= 12:
            return "-1D6"
        elif total <= 16:
            return "-1D4"
        elif total <= 24:
            return "+0"
        elif total <= 32:
            return "+1D4"
        elif total <= 40:
            return "+1D6"
        elif total <= 56:
            return "+2D6"
        elif total <= 72:
            return "+3D6"
        elif total <= 88:
            return "+4D6"
        else:
            return "+5D6"
    
    def calculate_total_wealth(self):
        """総資産を計算"""
        return self.cash + self.assets


class CharacterSkill(models.Model):
    """キャラクタースキル"""
    
    CATEGORY_CHOICES = [
        ('探索系', '探索系'),
        ('対人系', '対人系'),
        ('戦闘系', '戦闘系'),
        ('知識系', '知識系'),
        ('技術系', '技術系'),
        ('行動系', '行動系'),
        ('言語系', '言語系'),
        ('特殊・その他', '特殊・その他'),
    ]
    
    character_sheet = models.ForeignKey(
        CharacterSheet,
        on_delete=models.CASCADE,
        related_name='skills'
    )
    skill_name = models.CharField(max_length=100, verbose_name="技能名")
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='特殊・その他',
        verbose_name="カテゴリ"
    )
    
    # ポイント配分
    base_value = models.IntegerField(default=0, verbose_name="基本値")
    occupation_points = models.IntegerField(default=0, verbose_name="職業技能ポイント")
    interest_points = models.IntegerField(default=0, verbose_name="興味技能ポイント")
    bonus_points = models.IntegerField(default=0, verbose_name="ボーナスポイント")
    other_points = models.IntegerField(default=0, verbose_name="その他ポイント")
    
    # 現在値（自動計算）
    current_value = models.IntegerField(default=0, verbose_name="現在値")
    
    # 備考
    notes = models.TextField(blank=True, verbose_name="備考")
    
    class Meta:
        unique_together = ['character_sheet', 'skill_name']
        ordering = ['skill_name']
        verbose_name = "キャラクタースキル"
        verbose_name_plural = "キャラクタースキル"
    
    def clean(self):
        """カスタム技能のバリデーション"""
        from django.core.exceptions import ValidationError
        
        # 技能名の必須チェック
        if not self.skill_name or self.skill_name.strip() == '':
            raise ValidationError('技能名は必須です。')
        
        # 技能名の長さチェック
        if len(self.skill_name) > 100:
            raise ValidationError('技能名は100文字以内で入力してください。')
        
        # ポイント値の範囲チェック
        point_fields = [
            ('base_value', '基本値'),
            ('occupation_points', '職業技能ポイント'),
            ('interest_points', '興味技能ポイント'),
            ('bonus_points', 'ボーナスポイント'),
            ('other_points', 'その他ポイント')
        ]
        
        for field_name, field_label in point_fields:
            value = getattr(self, field_name, 0)
            if value < 0:
                raise ValidationError({field_name: f'{field_label}は0以上の値を入力してください。'})
            if value > 100:
                raise ValidationError({field_name: f'{field_label}は100以下の値を入力してください。'})
        
        # 技能値の合計チェック（6版は99%、7版は90%）
        total_value = (
            self.base_value + 
            self.occupation_points + 
            self.interest_points + 
            self.bonus_points +
            self.other_points
        )
        
        # 6版かどうかを確認
        is_6th_edition = self.character_sheet and self.character_sheet.edition == '6th'
        max_skill_value = 99 if is_6th_edition else 90
        
        if total_value > max_skill_value:
            raise ValidationError(f'技能値の合計は{max_skill_value}%を超えることはできません。')
        
        # 技能ポイント過剰割り振りチェック
        if self.character_sheet:
            # 職業技能ポイントのチェック
            total_occupation_points = self.character_sheet.calculate_occupation_points()
            used_occupation_points = self.character_sheet.skills.exclude(
                pk=self.pk
            ).aggregate(total=models.Sum('occupation_points'))['total'] or 0
            
            if (used_occupation_points + self.occupation_points) > total_occupation_points:
                raise ValidationError({
                    'occupation_points': f'職業技能ポイントが不足しています。残り: {total_occupation_points - used_occupation_points}ポイント'
                })
            
            # 趣味技能ポイントのチェック
            total_hobby_points = self.character_sheet.calculate_hobby_points()
            used_hobby_points = self.character_sheet.skills.exclude(
                pk=self.pk
            ).aggregate(total=models.Sum('interest_points'))['total'] or 0
            
            if (used_hobby_points + self.interest_points) > total_hobby_points:
                raise ValidationError({
                    'interest_points': f'趣味技能ポイントが不足しています。残り: {total_hobby_points - used_hobby_points}ポイント'
                })
    
    def save(self, *args, **kwargs):
        """保存時に値を自動計算"""
        # バリデーション実行
        self.full_clean()
        
        # 現在値計算（6版は99、7版は90の上限）
        total = (
            self.base_value + 
            self.occupation_points + 
            self.interest_points + 
            self.bonus_points +
            self.other_points
        )
        
        # 6版かどうかを確認
        is_6th_edition = self.character_sheet and self.character_sheet.edition == '6th'
        max_skill_value = 99 if is_6th_edition else 90
        
        self.current_value = min(total, max_skill_value)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def create_custom_skill(cls, character_sheet, skill_name, category='特殊・その他', **kwargs):
        """カスタム技能作成のヘルパーメソッド"""
        # 専門分野の抽出
        specialization = None
        if '（' in skill_name and '）' in skill_name:
            specialization = skill_name[skill_name.find('（')+1:skill_name.find('）')]
        
        # カスタム技能作成
        skill = cls.objects.create(
            character_sheet=character_sheet,
            skill_name=skill_name,
            category=category,
            notes=kwargs.get('notes', specialization or ''),
            **{k: v for k, v in kwargs.items() if k != 'notes'}
        )
        
        return skill
    
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
    weight = models.FloatField(null=True, blank=True, verbose_name="重量(kg)")
    
    class Meta:
        ordering = ['item_type', 'name']
        verbose_name = "キャラクター装備"
        verbose_name_plural = "キャラクター装備"
    
    def clean(self):
        """装備データのバリデーション"""
        from django.core.exceptions import ValidationError
        
        # 名前の必須チェック
        if not self.name or self.name.strip() == '':
            raise ValidationError('装備名は必須です。')
        
        # 攻撃回数の範囲チェック
        if self.attacks_per_round is not None and self.attacks_per_round < 0:
            raise ValidationError({'attacks_per_round': '攻撃回数は0以上の値を入力してください。'})
        
        # 装弾数の範囲チェック
        if self.ammo is not None and self.ammo < 0:
            raise ValidationError({'ammo': '装弾数は0以上の値を入力してください。'})
        
        # 故障ナンバーの範囲チェック
        if self.malfunction_number is not None and (self.malfunction_number < 1 or self.malfunction_number > 100):
            raise ValidationError({'malfunction_number': '故障ナンバーは1-100の範囲で入力してください。'})
        
        # 防護点の範囲チェック
        if self.armor_points is not None and self.armor_points < 0:
            raise ValidationError({'armor_points': '防護点は0以上の値を入力してください。'})
        
        # 数量の範囲チェック
        if self.quantity < 1:
            raise ValidationError({'quantity': '数量は1以上の値を入力してください。'})
        
        # 重量の範囲チェック
        if self.weight is not None and self.weight < 0:
            raise ValidationError({'weight': '重量は0以上の値を入力してください。'})
    
    def save(self, *args, **kwargs):
        """保存時にバリデーション実行"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.character_sheet.name} - {self.name}"


class CharacterBackground(models.Model):
    """キャラクター背景情報"""
    character_sheet = models.OneToOneField(
        CharacterSheet,
        on_delete=models.CASCADE,
        related_name='background_info'
    )
    
    # パーソナルデータ
    appearance_description = models.TextField(
        max_length=1000, 
        blank=True, 
        verbose_name="容姿・特徴"
    )
    beliefs_ideology = models.TextField(
        max_length=1000, 
        blank=True, 
        verbose_name="信念・信条"
    )
    significant_people = models.TextField(
        max_length=1000, 
        blank=True, 
        verbose_name="大切な人物"
    )
    meaningful_locations = models.TextField(
        max_length=1000, 
        blank=True, 
        verbose_name="意味のある場所"
    )
    treasured_possessions = models.TextField(
        max_length=1000, 
        blank=True, 
        verbose_name="愛用の品"
    )
    traits_mannerisms = models.TextField(
        max_length=1000, 
        blank=True, 
        verbose_name="特徴・癖"
    )
    
    # 経歴
    personal_history = models.TextField(
        max_length=2000, 
        blank=True, 
        verbose_name="生い立ち"
    )
    important_events = models.TextField(
        max_length=2000, 
        blank=True, 
        verbose_name="重要な出来事"
    )
    scars_injuries = models.TextField(
        max_length=1000, 
        blank=True, 
        verbose_name="傷・傷跡"
    )
    phobias_manias = models.TextField(
        max_length=1000, 
        blank=True, 
        verbose_name="恐怖症・マニア"
    )
    
    # 仲間の探索者
    fellow_investigators = models.TextField(
        max_length=2000, 
        blank=True, 
        verbose_name="仲間の探索者"
    )
    
    # その他
    notes_memo = models.TextField(
        max_length=3000, 
        blank=True, 
        verbose_name="メモ欄"
    )
    
    # メタデータ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = "キャラクター背景情報"
        verbose_name_plural = "キャラクター背景情報"
    
    def clean(self):
        """背景情報のバリデーション"""
        from django.core.exceptions import ValidationError
        
        # 各フィールドの文字数制限チェック
        text_fields = [
            ('appearance_description', '容姿・特徴', 1000),
            ('beliefs_ideology', '信念・信条', 1000),
            ('significant_people', '大切な人物', 1000),
            ('meaningful_locations', '意味のある場所', 1000),
            ('treasured_possessions', '愛用の品', 1000),
            ('traits_mannerisms', '特徴・癖', 1000),
            ('personal_history', '生い立ち', 2000),
            ('important_events', '重要な出来事', 2000),
            ('scars_injuries', '傷・傷跡', 1000),
            ('phobias_manias', '恐怖症・マニア', 1000),
            ('fellow_investigators', '仲間の探索者', 2000),
            ('notes_memo', 'メモ欄', 3000)
        ]
        
        for field_name, field_label, max_length in text_fields:
            value = getattr(self, field_name, '')
            if value and len(value) > max_length:
                raise ValidationError({
                    field_name: f'{field_label}は{max_length}文字以内で入力してください。'
                })
    
    def save(self, *args, **kwargs):
        """保存時にバリデーション実行"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.character_sheet.name} - 背景情報"


class GrowthRecord(models.Model):
    """成長記録（セッション記録）"""
    character_sheet = models.ForeignKey(
        CharacterSheet,
        on_delete=models.CASCADE,
        related_name='growth_records'
    )
    
    # セッション情報
    session_date = models.DateField(verbose_name="セッション日付")
    scenario_name = models.CharField(max_length=200, verbose_name="シナリオ名")
    gm_name = models.CharField(max_length=100, blank=True, verbose_name="GM名")
    
    # 正気度の増減
    sanity_gained = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(99)],
        verbose_name="正気度獲得"
    )
    sanity_lost = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(99)],
        verbose_name="正気度喪失"
    )
    
    # 経験値・報酬
    experience_gained = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="獲得経験値"
    )
    special_rewards = models.TextField(
        max_length=1000,
        blank=True,
        verbose_name="特別報酬"
    )
    
    # 備考
    notes = models.TextField(
        max_length=2000,
        blank=True,
        verbose_name="セッション備考"
    )
    
    # メタデータ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-session_date', '-created_at']
        verbose_name = "成長記録"
        verbose_name_plural = "成長記録"
    
    def clean(self):
        """成長記録のバリデーション"""
        from django.core.exceptions import ValidationError
        
        # シナリオ名必須チェック
        if not self.scenario_name or self.scenario_name.strip() == '':
            raise ValidationError({'scenario_name': 'シナリオ名は必須です。'})
        
        # 正気度の範囲チェック
        if self.sanity_gained < 0 or self.sanity_gained > 99:
            raise ValidationError({'sanity_gained': '正気度獲得は0-99の範囲で入力してください。'})
        
        if self.sanity_lost < 0 or self.sanity_lost > 99:
            raise ValidationError({'sanity_lost': '正気度喪失は0-99の範囲で入力してください。'})
        
        # 経験値の範囲チェック
        if self.experience_gained < 0:
            raise ValidationError({'experience_gained': '経験値は0以上の値を入力してください。'})
    
    def save(self, *args, **kwargs):
        """保存時にバリデーション実行"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def calculate_net_sanity_change(self):
        """正気度の増減を計算"""
        return self.sanity_gained - self.sanity_lost
    
    def __str__(self):
        return f"{self.character_sheet.name} - {self.scenario_name} ({self.session_date})"


class SkillGrowthRecord(models.Model):
    """技能成長記録"""
    growth_record = models.ForeignKey(
        GrowthRecord,
        on_delete=models.CASCADE,
        related_name='skill_growths'
    )
    
    # 技能情報
    skill_name = models.CharField(max_length=100, verbose_name="技能名")
    
    # 経験チェック
    had_experience_check = models.BooleanField(default=False, verbose_name="経験チェック有無")
    
    # 成長ロール
    growth_roll_result = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="成長ロール結果"
    )
    
    # 技能値の変化
    old_value = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(90)],
        verbose_name="成長前技能値"
    )
    new_value = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(90)],
        verbose_name="成長後技能値"
    )
    growth_amount = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(90)],
        verbose_name="成長量"
    )
    
    # 備考
    notes = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="成長備考"
    )
    
    class Meta:
        ordering = ['skill_name']
        verbose_name = "技能成長記録"
        verbose_name_plural = "技能成長記録"
    
    def clean(self):
        """技能成長記録のバリデーション"""
        from django.core.exceptions import ValidationError
        
        # 技能名必須チェック
        if not self.skill_name or self.skill_name.strip() == '':
            raise ValidationError({'skill_name': '技能名は必須です。'})
        
        # 技能値の範囲チェック
        if self.old_value < 0 or self.old_value > 90:
            raise ValidationError({'old_value': '成長前技能値は0-90の範囲で入力してください。'})
        
        if self.new_value < 0 or self.new_value > 90:
            raise ValidationError({'new_value': '成長後技能値は0-90の範囲で入力してください。'})
        
        # 成長量の整合性チェック
        expected_growth = self.new_value - self.old_value
        if self.growth_amount != expected_growth:
            raise ValidationError({
                'growth_amount': f'成長量が一致しません。期待値: {expected_growth}, 実際: {self.growth_amount}'
            })
        
        # 成長ロール結果の妥当性チェック
        if self.had_experience_check and self.growth_roll_result is not None:
            # 6版では現在値より大きいロールで成長成功
            if self.growth_roll_result <= self.old_value and self.growth_amount > 0:
                raise ValidationError({
                    'growth_roll_result': '成長ロール結果が現在値以下なのに成長しています。'
                })
    
    def save(self, *args, **kwargs):
        """保存時にバリデーション実行"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_growth_successful(self):
        """成長が成功したかを判定"""
        if not self.had_experience_check or self.growth_roll_result is None:
            return False
        return self.growth_roll_result > self.old_value
    
    def __str__(self):
        growth_text = f"+{self.growth_amount}" if self.growth_amount > 0 else "変化なし"
        return f"{self.growth_record.character_sheet.name} - {self.skill_name}: {self.old_value} → {self.new_value} ({growth_text})"


class CharacterDiceRollSetting(models.Model):
    """
    クトゥルフ神話TRPG 6版キャラクター作成用ダイスロール設定
    ユーザーごとに複数の設定を保存・管理可能
    """
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='dice_roll_settings'
    )
    setting_name = models.CharField(max_length=100, verbose_name="設定名")
    description = models.TextField(blank=True, verbose_name="説明")
    is_default = models.BooleanField(default=False, verbose_name="デフォルト設定")
    
    # STR設定
    str_dice_count = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="STRダイス数"
    )
    str_dice_sides = models.IntegerField(
        default=6,
        validators=[MinValueValidator(2), MaxValueValidator(100)],
        verbose_name="STRダイス面数"
    )
    str_bonus = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        verbose_name="STRボーナス"
    )
    
    # CON設定
    con_dice_count = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="CONダイス数"
    )
    con_dice_sides = models.IntegerField(
        default=6,
        validators=[MinValueValidator(2), MaxValueValidator(100)],
        verbose_name="CONダイス面数"
    )
    con_bonus = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        verbose_name="CONボーナス"
    )
    
    # POW設定
    pow_dice_count = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="POWダイス数"
    )
    pow_dice_sides = models.IntegerField(
        default=6,
        validators=[MinValueValidator(2), MaxValueValidator(100)],
        verbose_name="POWダイス面数"
    )
    pow_bonus = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        verbose_name="POWボーナス"
    )
    
    # DEX設定
    dex_dice_count = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="DEXダイス数"
    )
    dex_dice_sides = models.IntegerField(
        default=6,
        validators=[MinValueValidator(2), MaxValueValidator(100)],
        verbose_name="DEXダイス面数"
    )
    dex_bonus = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        verbose_name="DEXボーナス"
    )
    
    # APP設定
    app_dice_count = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="APPダイス数"
    )
    app_dice_sides = models.IntegerField(
        default=6,
        validators=[MinValueValidator(2), MaxValueValidator(100)],
        verbose_name="APPダイス面数"
    )
    app_bonus = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        verbose_name="APPボーナス"
    )
    
    # SIZ設定
    siz_dice_count = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="SIZダイス数"
    )
    siz_dice_sides = models.IntegerField(
        default=6,
        validators=[MinValueValidator(2), MaxValueValidator(100)],
        verbose_name="SIZダイス面数"
    )
    siz_bonus = models.IntegerField(
        default=6,
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        verbose_name="SIZボーナス"
    )
    
    # INT設定
    int_dice_count = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="INTダイス数"
    )
    int_dice_sides = models.IntegerField(
        default=6,
        validators=[MinValueValidator(2), MaxValueValidator(100)],
        verbose_name="INTダイス面数"
    )
    int_bonus = models.IntegerField(
        default=6,
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        verbose_name="INTボーナス"
    )
    
    # EDU設定
    edu_dice_count = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="EDUダイス数"
    )
    edu_dice_sides = models.IntegerField(
        default=6,
        validators=[MinValueValidator(2), MaxValueValidator(100)],
        verbose_name="EDUダイス面数"
    )
    edu_bonus = models.IntegerField(
        default=3,
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        verbose_name="EDUボーナス"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'setting_name']
        ordering = ['-is_default', 'setting_name']
        verbose_name = "ダイスロール設定"
        verbose_name_plural = "ダイスロール設定"
    
    def __str__(self):
        return f"{self.user.username} - {self.setting_name}"
    
    def save(self, *args, **kwargs):
        """保存時にデフォルト設定の管理"""
        if self.is_default:
            # 他のデフォルト設定を解除
            CharacterDiceRollSetting.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        else:
            # ユーザーの最初の設定の場合、自動的にデフォルトにする
            if not CharacterDiceRollSetting.objects.filter(user=self.user).exists():
                self.is_default = True
        
        super().save(*args, **kwargs)
    
    def set_as_default(self):
        """この設定をデフォルトに設定"""
        CharacterDiceRollSetting.objects.filter(
            user=self.user,
            is_default=True
        ).update(is_default=False)
        
        self.is_default = True
        self.save()
    
    # ダイス式取得メソッド
    def get_str_formula(self):
        """STRのダイス式を取得"""
        return self._format_dice_formula(self.str_dice_count, self.str_dice_sides, self.str_bonus)
    
    def get_con_formula(self):
        """CONのダイス式を取得"""
        return self._format_dice_formula(self.con_dice_count, self.con_dice_sides, self.con_bonus)
    
    def get_pow_formula(self):
        """POWのダイス式を取得"""
        return self._format_dice_formula(self.pow_dice_count, self.pow_dice_sides, self.pow_bonus)
    
    def get_dex_formula(self):
        """DEXのダイス式を取得"""
        return self._format_dice_formula(self.dex_dice_count, self.dex_dice_sides, self.dex_bonus)
    
    def get_app_formula(self):
        """APPのダイス式を取得"""
        return self._format_dice_formula(self.app_dice_count, self.app_dice_sides, self.app_bonus)
    
    def get_siz_formula(self):
        """SIZのダイス式を取得"""
        return self._format_dice_formula(self.siz_dice_count, self.siz_dice_sides, self.siz_bonus)
    
    def get_int_formula(self):
        """INTのダイス式を取得"""
        return self._format_dice_formula(self.int_dice_count, self.int_dice_sides, self.int_bonus)
    
    def get_edu_formula(self):
        """EDUのダイス式を取得"""
        return self._format_dice_formula(self.edu_dice_count, self.edu_dice_sides, self.edu_bonus)
    
    def _format_dice_formula(self, dice_count, dice_sides, bonus):
        """ダイス式の文字列をフォーマット"""
        formula = f"{dice_count}D{dice_sides}"
        if bonus > 0:
            formula += f"+{bonus}"
        elif bonus < 0:
            formula += str(bonus)  # 負の場合は自動的に-がつく
        return formula
    
    # ダイスロールメソッド
    def roll_str(self):
        """STRをロール"""
        return self._roll_dice(self.str_dice_count, self.str_dice_sides, self.str_bonus)
    
    def roll_con(self):
        """CONをロール"""
        return self._roll_dice(self.con_dice_count, self.con_dice_sides, self.con_bonus)
    
    def roll_pow(self):
        """POWをロール"""
        return self._roll_dice(self.pow_dice_count, self.pow_dice_sides, self.pow_bonus)
    
    def roll_dex(self):
        """DEXをロール"""
        return self._roll_dice(self.dex_dice_count, self.dex_dice_sides, self.dex_bonus)
    
    def roll_app(self):
        """APPをロール"""
        return self._roll_dice(self.app_dice_count, self.app_dice_sides, self.app_bonus)
    
    def roll_siz(self):
        """SIZをロール"""
        return self._roll_dice(self.siz_dice_count, self.siz_dice_sides, self.siz_bonus)
    
    def roll_int(self):
        """INTをロール"""
        return self._roll_dice(self.int_dice_count, self.int_dice_sides, self.int_bonus)
    
    def roll_edu(self):
        """EDUをロール"""
        return self._roll_dice(self.edu_dice_count, self.edu_dice_sides, self.edu_bonus)
    
    def _roll_dice(self, dice_count, dice_sides, bonus):
        """ダイスロール実行"""
        import random
        total = sum(random.randint(1, dice_sides) for _ in range(dice_count))
        return total + bonus
    
    def roll_all_abilities(self):
        """全能力値を一括ロール"""
        return {
            'str': self.roll_str(),
            'con': self.roll_con(),
            'pow': self.roll_pow(),
            'dex': self.roll_dex(),
            'app': self.roll_app(),
            'siz': self.roll_siz(),
            'int': self.roll_int(),
            'edu': self.roll_edu()
        }
    
    # プリセット作成メソッド
    @classmethod
    def create_standard_6th_preset(cls, user):
        """標準6版プリセットを作成"""
        return cls.objects.create(
            user=user,
            setting_name="標準6版設定",
            description="クトゥルフ神話TRPG 6版の標準的なダイス設定",
            is_default=True,
            str_dice_count=3, str_dice_sides=6, str_bonus=0,
            con_dice_count=3, con_dice_sides=6, con_bonus=0,
            pow_dice_count=3, pow_dice_sides=6, pow_bonus=0,
            dex_dice_count=3, dex_dice_sides=6, dex_bonus=0,
            app_dice_count=3, app_dice_sides=6, app_bonus=0,
            siz_dice_count=2, siz_dice_sides=6, siz_bonus=6,
            int_dice_count=2, int_dice_sides=6, int_bonus=6,
            edu_dice_count=3, edu_dice_sides=6, edu_bonus=3
        )
    
    @classmethod
    def create_high_stats_6th_preset(cls, user):
        """高能力値6版プリセットを作成"""
        return cls.objects.create(
            user=user,
            setting_name="高能力値6版設定",
            description="能力値が高めになるダイス設定（4D6のベスト3など）",
            is_default=False,
            str_dice_count=4, str_dice_sides=6, str_bonus=-3,
            con_dice_count=4, con_dice_sides=6, con_bonus=-3,
            pow_dice_count=4, pow_dice_sides=6, pow_bonus=-3,
            dex_dice_count=4, dex_dice_sides=6, dex_bonus=-3,
            app_dice_count=4, app_dice_sides=6, app_bonus=-3,
            siz_dice_count=3, siz_dice_sides=6, siz_bonus=3,
            int_dice_count=3, int_dice_sides=6, int_bonus=3,
            edu_dice_count=4, edu_dice_sides=6, edu_bonus=0
        )
    
    # ユーティリティメソッド
    @classmethod
    def get_user_settings(cls, user):
        """ユーザーの設定一覧を取得"""
        return cls.objects.filter(user=user).order_by('-is_default', 'setting_name')
    
    @classmethod
    def get_default_setting(cls, user):
        """ユーザーのデフォルト設定を取得"""
        try:
            return cls.objects.get(user=user, is_default=True)
        except cls.DoesNotExist:
            return None
    
    def duplicate(self, new_name):
        """設定を複製"""
        new_setting = CharacterDiceRollSetting(
            user=self.user,
            setting_name=new_name,
            description=self.description,
            is_default=False,
            str_dice_count=self.str_dice_count,
            str_dice_sides=self.str_dice_sides,
            str_bonus=self.str_bonus,
            con_dice_count=self.con_dice_count,
            con_dice_sides=self.con_dice_sides,
            con_bonus=self.con_bonus,
            pow_dice_count=self.pow_dice_count,
            pow_dice_sides=self.pow_dice_sides,
            pow_bonus=self.pow_bonus,
            dex_dice_count=self.dex_dice_count,
            dex_dice_sides=self.dex_dice_sides,
            dex_bonus=self.dex_bonus,
            app_dice_count=self.app_dice_count,
            app_dice_sides=self.app_dice_sides,
            app_bonus=self.app_bonus,
            siz_dice_count=self.siz_dice_count,
            siz_dice_sides=self.siz_dice_sides,
            siz_bonus=self.siz_bonus,
            int_dice_count=self.int_dice_count,
            int_dice_sides=self.int_dice_sides,
            int_bonus=self.int_bonus,
            edu_dice_count=self.edu_dice_count,
            edu_dice_sides=self.edu_dice_sides,
            edu_bonus=self.edu_bonus
        )
        new_setting.save()
        return new_setting
    
    def export_to_json(self):
        """JSON形式でエクスポート"""
        data = {
            'setting_name': self.setting_name,
            'description': self.description,
            'str_dice_count': self.str_dice_count,
            'str_dice_sides': self.str_dice_sides,
            'str_bonus': self.str_bonus,
            'con_dice_count': self.con_dice_count,
            'con_dice_sides': self.con_dice_sides,
            'con_bonus': self.con_bonus,
            'pow_dice_count': self.pow_dice_count,
            'pow_dice_sides': self.pow_dice_sides,
            'pow_bonus': self.pow_bonus,
            'dex_dice_count': self.dex_dice_count,
            'dex_dice_sides': self.dex_dice_sides,
            'dex_bonus': self.dex_bonus,
            'app_dice_count': self.app_dice_count,
            'app_dice_sides': self.app_dice_sides,
            'app_bonus': self.app_bonus,
            'siz_dice_count': self.siz_dice_count,
            'siz_dice_sides': self.siz_dice_sides,
            'siz_bonus': self.siz_bonus,
            'int_dice_count': self.int_dice_count,
            'int_dice_sides': self.int_dice_sides,
            'int_bonus': self.int_bonus,
            'edu_dice_count': self.edu_dice_count,
            'edu_dice_sides': self.edu_dice_sides,
            'edu_bonus': self.edu_bonus,
            'export_version': '1.0',
            'export_timestamp': timezone.now().isoformat()
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @classmethod
    def import_from_json(cls, user, json_data, new_name=None):
        """JSON形式からインポート"""
        data = json.loads(json_data)
        
        setting_name = new_name or data.get('setting_name', 'インポート設定')
        
        return cls.objects.create(
            user=user,
            setting_name=setting_name,
            description=data.get('description', ''),
            is_default=False,
            str_dice_count=data.get('str_dice_count', 3),
            str_dice_sides=data.get('str_dice_sides', 6),
            str_bonus=data.get('str_bonus', 0),
            con_dice_count=data.get('con_dice_count', 3),
            con_dice_sides=data.get('con_dice_sides', 6),
            con_bonus=data.get('con_bonus', 0),
            pow_dice_count=data.get('pow_dice_count', 3),
            pow_dice_sides=data.get('pow_dice_sides', 6),
            pow_bonus=data.get('pow_bonus', 0),
            dex_dice_count=data.get('dex_dice_count', 3),
            dex_dice_sides=data.get('dex_dice_sides', 6),
            dex_bonus=data.get('dex_bonus', 0),
            app_dice_count=data.get('app_dice_count', 3),
            app_dice_sides=data.get('app_dice_sides', 6),
            app_bonus=data.get('app_bonus', 0),
            siz_dice_count=data.get('siz_dice_count', 2),
            siz_dice_sides=data.get('siz_dice_sides', 6),
            siz_bonus=data.get('siz_bonus', 6),
            int_dice_count=data.get('int_dice_count', 2),
            int_dice_sides=data.get('int_dice_sides', 6),
            int_bonus=data.get('int_bonus', 6),
            edu_dice_count=data.get('edu_dice_count', 3),
            edu_dice_sides=data.get('edu_dice_sides', 6),
            edu_bonus=data.get('edu_bonus', 3)
        )


class CharacterImage(models.Model):
    """
    キャラクター画像モデル
    1キャラクターに複数の画像を添付可能
    """
    character_sheet = models.ForeignKey(
        CharacterSheet,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="キャラクターシート"
    )
    def upload_to(instance, filename):
        """一意なファイル名を生成"""
        import os
        from django.utils import timezone
        import uuid
        
        # ファイル拡張子を取得
        ext = os.path.splitext(filename)[1]
        # 一意なファイル名を生成
        unique_filename = f"{instance.character_sheet.id}_{uuid.uuid4().hex[:8]}{ext}"
        # 日付ベースのパスに保存
        return f"character_images/{timezone.now().year}/{timezone.now().month:02d}/{unique_filename}"
    
    image = models.ImageField(
        upload_to=upload_to,
        verbose_name="画像"
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name="メイン画像"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="表示順序"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="アップロード日時"
    )
    
    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = "キャラクター画像"
        verbose_name_plural = "キャラクター画像"
        constraints = [
            models.UniqueConstraint(
                fields=['character_sheet'],
                condition=models.Q(is_main=True),
                name='unique_main_image_per_character'
            )
        ]
    
    def __str__(self):
        return f"{self.character_sheet.name} - 画像{self.order + 1}"


# ユーティリティクラス（長いメソッドを分離）

class CharacterVersionManager:
    """キャラクターバージョン管理ユーティリティ"""
    
    @staticmethod
    def create_new_version(character, version_note="", session_count=None, copy_skills=False):
        """新しいバージョンを作成"""
        from django.core.exceptions import ValidationError
        
        # バージョンメモの長さ制限
        if len(version_note) > 1000:
            raise ValidationError("バージョンメモは1000文字以内で入力してください")
        
        # 次のバージョン番号を取得
        latest_version = CharacterVersionManager.get_latest_version(character)
        next_version = latest_version.version + 1
        
        # 新しいキャラクターシートを作成
        new_character = CharacterSheet.objects.create(
            user=character.user,
            edition=character.edition,
            name=character.name,
            player_name=character.player_name,
            age=character.age,
            gender=character.gender,
            occupation=character.occupation,
            birthplace=character.birthplace,
            residence=character.residence,
            str_value=character.str_value,
            con_value=character.con_value,
            pow_value=character.pow_value,
            dex_value=character.dex_value,
            app_value=character.app_value,
            siz_value=character.siz_value,
            int_value=character.int_value,
            edu_value=character.edu_value,
            hit_points_max=character.hit_points_max,
            hit_points_current=character.hit_points_current,
            magic_points_max=character.magic_points_max,
            magic_points_current=character.magic_points_current,
            sanity_starting=character.sanity_starting,
            sanity_max=character.sanity_max,
            sanity_current=character.sanity_current,
            version=next_version,
            parent_sheet=character,
            character_image=character.character_image,
            notes=character.notes,
            version_note=version_note,
            session_count=session_count or (character.session_count + 1),
            is_active=True
        )
        
        # 6版固有データのコピー
        if character.edition == '6th' and hasattr(character, 'sixth_edition_data'):
            CharacterSheet6th.objects.create(
                character_sheet=new_character,
                mental_disorder=character.sixth_edition_data.mental_disorder
            )
        
        # 技能のコピー
        if copy_skills:
            for skill in character.skills.all():
                CharacterSkill.objects.create(
                    character_sheet=new_character,
                    skill_name=skill.skill_name,
                    category=skill.category,
                    base_value=skill.base_value,
                    occupation_points=skill.occupation_points,
                    interest_points=skill.interest_points,
                    bonus_points=skill.bonus_points,
                    other_points=skill.other_points,
                    notes=skill.notes
                )
        
        return new_character
    
    @staticmethod
    def get_version_history(character):
        """バージョン履歴を取得"""
        root = CharacterVersionManager.get_root_version(character)
        versions = [root]
        
        # 子バージョンを再帰的に取得
        def collect_versions(parent):
            children = parent.versions.all().order_by('version')
            for child in children:
                versions.append(child)
                collect_versions(child)
        
        collect_versions(root)
        return versions
    
    @staticmethod
    def get_latest_version(character):
        """最新バージョンを取得"""
        history = CharacterVersionManager.get_version_history(character)
        return history[-1] if history else character
    
    @staticmethod
    def get_root_version(character):
        """ルートバージョンを取得"""
        current = character
        while current.parent_sheet:
            current = current.parent_sheet
        return current
    
    @staticmethod
    def compare_versions(character1, character2):
        """バージョン間の比較"""
        differences = {}
        
        # 能力値の比較
        ability_diffs = {}
        for ability in ['str_value', 'con_value', 'pow_value', 'dex_value', 
                       'app_value', 'siz_value', 'int_value', 'edu_value']:
            val1 = getattr(character1, ability)
            val2 = getattr(character2, ability)
            if val1 != val2:
                ability_diffs[ability] = {
                    'old': val1,
                    'new': val2,
                    'change': val2 - val1
                }
        
        if ability_diffs:
            differences['abilities'] = ability_diffs
        
        # 技能の比較
        skill_diffs = {}
        skills1 = {skill.skill_name: skill for skill in character1.skills.all()}
        skills2 = {skill.skill_name: skill for skill in character2.skills.all()}
        
        # 追加された技能
        added_skills = set(skills2.keys()) - set(skills1.keys())
        if added_skills:
            skill_diffs['added'] = list(added_skills)
        
        # 変更された技能
        changed_skills = {}
        for skill_name in set(skills1.keys()) & set(skills2.keys()):
            skill1 = skills1[skill_name]
            skill2 = skills2[skill_name]
            if skill1.current_value != skill2.current_value:
                changed_skills[skill_name] = {
                    'old': skill1.current_value,
                    'new': skill2.current_value,
                    'change': skill2.current_value - skill1.current_value
                }
        
        if changed_skills:
            skill_diffs['changed'] = changed_skills
        
        if skill_diffs:
            differences['skills'] = skill_diffs
        
        return differences
    
    @staticmethod
    def rollback_to_version(current_character, target_version):
        """指定バージョンにロールバック"""
        # 現在のバージョンから新しいバージョンを作成
        next_version = CharacterVersionManager.get_latest_version(current_character).version + 1
        
        # ロールバック先のデータを使って新バージョンを作成
        rolled_back = CharacterSheet.objects.create(
            user=target_version.user,
            edition=target_version.edition,
            name=target_version.name,
            player_name=target_version.player_name,
            age=target_version.age,
            gender=target_version.gender,
            occupation=target_version.occupation,
            birthplace=target_version.birthplace,
            residence=target_version.residence,
            str_value=target_version.str_value,
            con_value=target_version.con_value,
            pow_value=target_version.pow_value,
            dex_value=target_version.dex_value,
            app_value=target_version.app_value,
            siz_value=target_version.siz_value,
            int_value=target_version.int_value,
            edu_value=target_version.edu_value,
            hit_points_max=target_version.hit_points_max,
            hit_points_current=target_version.hit_points_current,
            magic_points_max=target_version.magic_points_max,
            magic_points_current=target_version.magic_points_current,
            sanity_starting=target_version.sanity_starting,
            sanity_max=target_version.sanity_max,
            sanity_current=target_version.sanity_current,
            version=next_version,
            parent_sheet=current_character,  # 現在のバージョンを親にする
            character_image=target_version.character_image,
            notes=target_version.notes,
            version_note=f"バージョン{target_version.version}からのロールバック",
            session_count=current_character.session_count,
            is_active=True
        )
        
        # 6版固有データのコピー
        if target_version.edition == '6th' and hasattr(target_version, 'sixth_edition_data'):
            CharacterSheet6th.objects.create(
                character_sheet=rolled_back,
                mental_disorder=target_version.sixth_edition_data.mental_disorder
            )
        
        # 技能のコピー
        for skill in target_version.skills.all():
            CharacterSkill.objects.create(
                character_sheet=rolled_back,
                skill_name=skill.skill_name,
                category=skill.category,
                base_value=skill.base_value,
                occupation_points=skill.occupation_points,
                interest_points=skill.interest_points,
                bonus_points=skill.bonus_points,
                other_points=skill.other_points,
                notes=skill.notes
            )
        
        return rolled_back
    
    @staticmethod
    def get_version_statistics(character):
        """バージョン統計を取得"""
        history = CharacterVersionManager.get_version_history(character)
        return {
            'total_versions': len(history),
            'latest_version': history[-1].version if history else 1,
            'total_sessions': history[-1].session_count if history else 0
        }


class CharacterExportManager:
    """キャラクター エクスポート管理ユーティリティ"""
    
    @staticmethod
    def export_version_data(character):
        """バージョンデータをエクスポート"""
        data = {
            'character_info': {
                'name': character.name,
                'edition': character.edition,
                'age': character.age,
                'occupation': character.occupation,
                'abilities': character.abilities
            },
            'skills': [
                {
                    'name': skill.skill_name,
                    'category': skill.category,
                    'value': skill.current_value,
                    'base': skill.base_value,
                    'occupation': skill.occupation_points,
                    'interest': skill.interest_points,
                    'bonus': skill.bonus_points,
                    'notes': skill.notes
                }
                for skill in character.skills.all()
            ],
            'version_info': {
                'version': character.version,
                'note': character.version_note,
                'session_count': character.session_count,
                'created_at': character.created_at.isoformat(),
                'updated_at': character.updated_at.isoformat()
            }
        }
        
        # 6版固有データ
        if character.edition == '6th' and hasattr(character, 'sixth_edition_data'):
            data['sixth_edition'] = {
                'idea_roll': character.sixth_edition_data.idea_roll,
                'luck_roll': character.sixth_edition_data.luck_roll,
                'know_roll': character.sixth_edition_data.know_roll,
                'damage_bonus': character.sixth_edition_data.damage_bonus,
                'mental_disorder': character.sixth_edition_data.mental_disorder
            }
        
        return data
    
    @staticmethod
    def export_ccfolia_format(character):
        """CCFOLIA形式でのデータエクスポート"""
        # 技能値からコマンド文字列を生成
        commands = []
        
        # 正気度ロール
        commands.append(f"1d100<={{SAN}} 【正気度ロール】")
        
        # 基本判定
        commands.append(f"CCB<={character.int_value * 5} 【アイデア】")
        commands.append(f"CCB<={character.pow_value * 5} 【幸運】") 
        commands.append(f"CCB<={character.edu_value * 5} 【知識】")
        
        # 技能ロール
        for skill in character.skills.all():
            total_value = (skill.base_value + skill.occupation_points + 
                          skill.interest_points + skill.bonus_points + skill.other_points)
            commands.append(f"CCB<={total_value} 【{skill.skill_name}】")
        
        # ダメージ判定
        commands.append("1d3+0 【ダメージ判定】")
        commands.append("1d4+0 【ダメージ判定】")
        commands.append("1d6+0 【ダメージ判定】")
        
        # 能力値ロール
        for ability, value in [
            ('STR', character.str_value), ('CON', character.con_value), 
            ('POW', character.pow_value), ('DEX', character.dex_value),
            ('APP', character.app_value), ('SIZ', character.siz_value),
            ('INT', character.int_value), ('EDU', character.edu_value)
        ]:
            commands.append(f"CCB<={{{ability}}}*5 【{ability} × 5】")
        
        # CCFOLIA標準形式
        ccfolia_data = {
            "kind": "character",
            "data": {
                "name": character.name,
                "initiative": character.dex_value,  # DEXを行動力として使用
                "externalUrl": "",  # 外部URLは空
                "iconUrl": "",  # アイコンURLは空
                "commands": "\n".join(commands),
                "status": [
                    {
                        "label": "HP",
                        "value": character.hit_points_current,
                        "max": character.hit_points_max
                    },
                    {
                        "label": "MP", 
                        "value": character.magic_points_current,
                        "max": character.magic_points_max
                    },
                    {
                        "label": "SAN",
                        "value": character.sanity_current,
                        "max": character.sanity_max
                    }
                ],
                "params": [
                    {"label": "STR", "value": str(character.str_value)},
                    {"label": "CON", "value": str(character.con_value)},
                    {"label": "POW", "value": str(character.pow_value)},
                    {"label": "DEX", "value": str(character.dex_value)},
                    {"label": "APP", "value": str(character.app_value)},
                    {"label": "SIZ", "value": str(character.siz_value)},
                    {"label": "INT", "value": str(character.int_value)},
                    {"label": "EDU", "value": str(character.edu_value)}
                ]
            }
        }
        
        return ccfolia_data
    
    @staticmethod
    def bulk_export_ccfolia(character_ids):
        """複数キャラクターの一括CCFOLIAエクスポート"""
        characters = CharacterSheet.objects.filter(id__in=character_ids)
        export_data = []
        
        for character in characters:
            try:
                data = CharacterExportManager.export_ccfolia_format(character)
                export_data.append(data)
            except Exception as e:
                # エラーが発生したキャラクターはスキップ
                export_data.append({
                    'error': True,
                    'character_id': character.id,
                    'character_name': character.name,
                    'error_message': str(e)
                })
        
        return export_data


class CharacterSyncManager:
    """キャラクター同期管理ユーティリティ"""
    
    @staticmethod
    def sync_to_ccfolia(character):
        """CCFOLIAへの同期処理"""
        if not character.ccfolia_sync_enabled:
            return {'status': 'disabled', 'message': '同期が無効です'}
        
        try:
            # CCFOLIA形式のデータ取得
            data = CharacterExportManager.export_ccfolia_format(character)
            
            # 実際のAPI呼び出しは後で実装
            # ここではダミーレスポンス
            sync_result = {
                'status': 'success',
                'character_id': character.ccfolia_character_id,
                'data_sent': data,
                'timestamp': timezone.now().isoformat()
            }
            
            return sync_result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    @staticmethod
    def resolve_sync_conflict(character, conflict_data):
        """同期競合の解決"""
        # 基本的な競合解決戦略
        strategies = {
            'local_wins': 'ローカルデータを優先',
            'remote_wins': 'リモートデータを優先',
            'manual_merge': '手動マージが必要',
            'create_branch': '新しいブランチを作成'
        }
        
        # 競合フィールドに基づく解決方法の決定
        conflict_fields = conflict_data.get('conflict_fields', [])
        
        if 'abilities' in conflict_fields:
            strategy = 'manual_merge'
        elif 'skills' in conflict_fields:
            strategy = 'local_wins'  # 技能成長はローカル優先
        else:
            strategy = 'remote_wins'
        
        return {
            'resolution_strategy': strategy,
            'strategy_description': strategies.get(strategy, '不明'),
            'conflict_fields': conflict_fields,
            'recommended_action': f"{strategy}を実行してください"
        }