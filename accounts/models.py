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
    version_note = models.CharField(max_length=1000, blank=True, verbose_name="バージョンメモ")
    session_count = models.PositiveIntegerField(default=0, verbose_name="セッション数")
    is_active = models.BooleanField(default=True, verbose_name="アクティブ")
    
    # Cocoholia連携
    cocoholia_sync_enabled = models.BooleanField(default=False, verbose_name="Cocoholia同期有効")
    cocoholia_character_id = models.CharField(max_length=100, blank=True, verbose_name="CocoholiaキャラクターID")
    
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
        from django.core.exceptions import ValidationError
        
        # 循環参照の防止
        if self.parent_sheet:
            current = self.parent_sheet
            while current:
                if current == self:
                    raise ValidationError("循環参照は許可されていません")
                current = current.parent_sheet
        
        # バージョン番号の重複チェック
        if not self.pk:  # 新規作成時
            existing = CharacterSheet.objects.filter(
                user=self.user,
                name=self.name,
                version=self.version
            ).exists()
            if existing:
                raise ValidationError(f"バージョン{self.version}は既に存在します")
        
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
        from django.core.exceptions import ValidationError
        
        # バージョンメモの長さ制限
        if len(version_note) > 1000:
            raise ValidationError("バージョンメモは1000文字以内で入力してください")
        
        # 次のバージョン番号を取得
        latest_version = self.get_latest_version()
        next_version = latest_version.version + 1
        
        # 新しいキャラクターシートを作成
        new_character = CharacterSheet.objects.create(
            user=self.user,
            edition=self.edition,
            name=self.name,
            player_name=self.player_name,
            age=self.age,
            gender=self.gender,
            occupation=self.occupation,
            birthplace=self.birthplace,
            residence=self.residence,
            str_value=self.str_value,
            con_value=self.con_value,
            pow_value=self.pow_value,
            dex_value=self.dex_value,
            app_value=self.app_value,
            siz_value=self.siz_value,
            int_value=self.int_value,
            edu_value=self.edu_value,
            hit_points_max=self.hit_points_max,
            hit_points_current=self.hit_points_current,
            magic_points_max=self.magic_points_max,
            magic_points_current=self.magic_points_current,
            sanity_starting=self.sanity_starting,
            sanity_max=self.sanity_max,
            sanity_current=self.sanity_current,
            version=next_version,
            parent_sheet=self,
            character_image=self.character_image,
            notes=self.notes,
            version_note=version_note,
            session_count=session_count or (self.session_count + 1),
            is_active=True
        )
        
        # 6版固有データのコピー
        if self.edition == '6th' and hasattr(self, 'sixth_edition_data'):
            CharacterSheet6th.objects.create(
                character_sheet=new_character,
                mental_disorder=self.sixth_edition_data.mental_disorder
            )
        
        # 技能のコピー
        if copy_skills:
            for skill in self.skills.all():
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
    
    def get_version_history(self):
        """
        バージョン履歴を取得
        
        Returns:
            バージョンのリスト（古い順）
        """
        root = self.get_root_version()
        versions = [root]
        
        # 子バージョンを再帰的に取得
        def collect_versions(parent):
            children = parent.versions.all().order_by('version')
            for child in children:
                versions.append(child)
                collect_versions(child)
        
        collect_versions(root)
        return versions
    
    def get_latest_version(self):
        """
        最新バージョンを取得
        
        Returns:
            最新のCharacterSheetオブジェクト
        """
        history = self.get_version_history()
        return history[-1] if history else self
    
    def get_root_version(self):
        """
        ルートバージョンを取得
        
        Returns:
            ルートのCharacterSheetオブジェクト
        """
        current = self
        while current.parent_sheet:
            current = current.parent_sheet
        return current
    
    def get_child_versions(self):
        """
        直接の子バージョンを取得
        
        Returns:
            子バージョンのQuerySet
        """
        return self.versions.all()
    
    def compare_with_version(self, other_version):
        """
        他のバージョンとの比較
        
        Args:
            other_version: 比較対象のCharacterSheetオブジェクト
        
        Returns:
            差分の辞書
        """
        differences = {}
        
        # 能力値の比較
        ability_diffs = {}
        for ability in ['str_value', 'con_value', 'pow_value', 'dex_value', 
                       'app_value', 'siz_value', 'int_value', 'edu_value']:
            self_val = getattr(self, ability)
            other_val = getattr(other_version, ability)
            if self_val != other_val:
                ability_diffs[ability] = {
                    'old': self_val,
                    'new': other_val,
                    'change': other_val - self_val
                }
        
        if ability_diffs:
            differences['abilities'] = ability_diffs
        
        # 技能の比較
        skill_diffs = {}
        self_skills = {skill.skill_name: skill for skill in self.skills.all()}
        other_skills = {skill.skill_name: skill for skill in other_version.skills.all()}
        
        # 追加された技能
        added_skills = set(other_skills.keys()) - set(self_skills.keys())
        if added_skills:
            skill_diffs['added'] = list(added_skills)
        
        # 変更された技能
        changed_skills = {}
        for skill_name in set(self_skills.keys()) & set(other_skills.keys()):
            self_skill = self_skills[skill_name]
            other_skill = other_skills[skill_name]
            if self_skill.current_value != other_skill.current_value:
                changed_skills[skill_name] = {
                    'old': self_skill.current_value,
                    'new': other_skill.current_value,
                    'change': other_skill.current_value - self_skill.current_value
                }
        
        if changed_skills:
            skill_diffs['changed'] = changed_skills
        
        if skill_diffs:
            differences['skills'] = skill_diffs
        
        return differences
    
    def rollback_to_version(self, target_version):
        """
        指定バージョンにロールバック
        
        Args:
            target_version: ロールバック先のCharacterSheetオブジェクト
        
        Returns:
            新しいバージョンのCharacterSheetオブジェクト
        """
        # 現在のバージョンから新しいバージョンを作成
        next_version = self.get_latest_version().version + 1
        
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
            parent_sheet=self,  # 現在のバージョンを親にする
            character_image=target_version.character_image,
            notes=target_version.notes,
            version_note=f"バージョン{target_version.version}からのロールバック",
            session_count=self.session_count,
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
    
    def get_version_statistics(self):
        """
        バージョン統計を取得
        
        Returns:
            統計の辞書
        """
        history = self.get_version_history()
        return {
            'total_versions': len(history),
            'latest_version': history[-1].version if history else 1,
            'total_sessions': history[-1].session_count if history else 0
        }
    
    def export_version_data(self):
        """
        バージョンデータをエクスポート
        
        Returns:
            エクスポートデータの辞書
        """
        data = {
            'character_info': {
                'name': self.name,
                'edition': self.edition,
                'age': self.age,
                'occupation': self.occupation,
                'abilities': self.abilities
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
                for skill in self.skills.all()
            ],
            'version_info': {
                'version': self.version,
                'note': self.version_note,
                'session_count': self.session_count,
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat()
            }
        }
        
        # 6版固有データ
        if self.edition == '6th' and hasattr(self, 'sixth_edition_data'):
            data['sixth_edition'] = {
                'idea_roll': self.sixth_edition_data.idea_roll,
                'luck_roll': self.sixth_edition_data.luck_roll,
                'know_roll': self.sixth_edition_data.know_roll,
                'damage_bonus': self.sixth_edition_data.damage_bonus,
                'mental_disorder': self.sixth_edition_data.mental_disorder
            }
        
        return data
    
    def export_cocoholia_format(self):
        """
        Cocoholia形式でのデータエクスポート
        
        Returns:
            Cocoholia形式のデータ辞書
        """
        # 6版の能力値に変換（7版仕様から6版仕様へ）
        abilities_6th = {
            'STR': self.str_value // 5,
            'CON': self.con_value // 5,
            'POW': self.pow_value // 5,
            'DEX': self.dex_value // 5,
            'APP': self.app_value // 5,
            'SIZ': self.siz_value // 5,
            'INT': self.int_value // 5,
            'EDU': self.edu_value // 5,
        }
        
        # 副次ステータス
        hp = self.hit_points_max
        mp = self.magic_points_max
        san = self.sanity_current
        
        # アイデア・幸運・知識ロール（6版）
        idea = abilities_6th['INT'] * 5
        luck = abilities_6th['POW'] * 5
        know = abilities_6th['EDU'] * 5
        
        # 技能データをCocoholia形式に変換
        skills_data = []
        for skill in self.skills.all():
            skills_data.append({
                'name': skill.skill_name,
                'base': skill.base_value,
                'value': skill.current_value,
                'category': skill.category,
                'notes': skill.notes
            })
        
        # Cocoholia形式のデータ構造
        cocoholia_data = {
            'character_name': self.name,
            'pc_making_memo': self.notes or '',
            'age': self.age,
            'sex': self.gender or '',
            'pc_tags': [self.occupation] if self.occupation else [],
            'personal_data': {
                'occupation': self.occupation or '',
                'birthplace': self.birthplace or '',
                'residence': self.residence or '',
                'mental_disorder': getattr(self, 'sixth_edition_data', None) and 
                                 self.sixth_edition_data.mental_disorder or ''
            },
            'params': {
                'STR': abilities_6th['STR'],
                'CON': abilities_6th['CON'],
                'POW': abilities_6th['POW'],
                'DEX': abilities_6th['DEX'],
                'APP': abilities_6th['APP'],
                'SIZ': abilities_6th['SIZ'],
                'INT': abilities_6th['INT'],
                'EDU': abilities_6th['EDU'],
                'HP': hp,
                'MP': mp,
                'SAN': san,
                'アイデア': idea,
                '幸運': luck,
                '知識': know
            },
            'skills': skills_data,
            'items': [],  # 装備データは後で実装
            'version_info': {
                'version': self.version,
                'session_count': self.session_count,
                'last_updated': self.updated_at.isoformat()
            }
        }
        
        # 6版固有データの追加
        if self.edition == '6th' and hasattr(self, 'sixth_edition_data'):
            cocoholia_data['sixth_edition_data'] = {
                'damage_bonus': self.sixth_edition_data.damage_bonus,
                'idea_roll': self.sixth_edition_data.idea_roll,
                'luck_roll': self.sixth_edition_data.luck_roll,
                'know_roll': self.sixth_edition_data.know_roll
            }
        
        return cocoholia_data
    
    def sync_to_cocoholia(self):
        """
        Cocoholiaへの同期処理
        
        Returns:
            同期結果の辞書
        """
        if not self.cocoholia_sync_enabled:
            return {'status': 'disabled', 'message': '同期が無効です'}
        
        try:
            # Cocoholia形式のデータ取得
            data = self.export_cocoholia_format()
            
            # 実際のAPI呼び出しは後で実装
            # ここではダミーレスポンス
            sync_result = {
                'status': 'success',
                'character_id': self.cocoholia_character_id,
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
    
    def resolve_sync_conflict(self, conflict_data):
        """
        同期競合の解決
        
        Args:
            conflict_data: 競合データ
        
        Returns:
            解決方法の辞書
        """
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
    
    @classmethod
    def bulk_export_cocoholia(cls, character_ids):
        """
        複数キャラクターの一括Cocoholiaエクスポート
        
        Args:
            character_ids: キャラクターIDのリスト
        
        Returns:
            Cocoholia形式データのリスト
        """
        characters = cls.objects.filter(id__in=character_ids)
        export_data = []
        
        for character in characters:
            try:
                data = character.export_cocoholia_format()
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
    current_value = models.IntegerField(verbose_name="現在値")
    
    # 備考
    notes = models.TextField(blank=True, verbose_name="備考")
    
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
            self.bonus_points +
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


class CharacterDiceRollSetting(models.Model):
    """
    クトゥルフ神話TRPG 6版キャラクター作成用ダイスロール設定
    ユーザーごとに複数の設定を保存・管理可能
    """
    user = models.ForeignKey(
        CustomUser,
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
