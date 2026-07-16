"""
キャラクターシート関連モデル
クトゥルフ神話TRPG 6版・7版のモデル定義
"""

import json
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

# Circular import回避のため、文字列参照を使用


class CharacterSheetManager(models.Manager):
    def by_system_name(self, name, *, user=None, edition=None):
        """Find registry rows by the name stored in their edition table."""
        queryset = self.get_queryset()
        if user is not None:
            queryset = queryset.filter(user=user)
        if edition == "6th":
            return queryset.filter(edition="6th", sixth_edition_data__name=name)
        if edition == "7th":
            return queryset.filter(edition="7th", seventh_edition_data__name=name)
        return queryset.filter(
            models.Q(edition="6th", sixth_edition_data__name=name)
            | models.Q(edition="7th", seventh_edition_data__name=name)
        )

    def bulk_create(self, objs, **kwargs):
        # The registry has no derived character values.
        return super().bulk_create(objs, **kwargs)


class CharacterSheet(models.Model):
    """
    クトゥルフ神話TRPG キャラクターシート基底モデル
    6版・7版共通の基本データを管理
    """

    EDITION_CHOICES = [
        ("6th", "6版"),
        ("7th", "7版"),
    ]

    STATUS_CHOICES = [
        ("alive", "生存"),
        ("dead", "死亡"),
        ("insane", "発狂"),
        ("injured", "重傷"),
        ("missing", "行方不明"),
        ("retired", "引退"),
    ]

    OCCUPATION_POINT_METHODS_6TH = frozenset(
        [
            "edu20",
            "edu10app10",
            "edu10dex10",
            "edu10pow10",
            "edu10str10",
            "edu10con10",
            "edu10siz10",
        ]
    )
    OCCUPATION_POINT_METHODS_7TH = frozenset(
        [
            "edu4",
            "edu2app2",
            "edu2dex2",
            "edu2pow2",
            "edu2str2",
            "edu2con2",
            "edu2siz2",
        ]
    )
    OCCUPATION_POINT_METHOD_CHOICES = [
        ("", "未指定"),
        ("edu20", "EDU×20"),
        ("edu10app10", "EDU×10＋APP×10"),
        ("edu10dex10", "EDU×10＋DEX×10"),
        ("edu10pow10", "EDU×10＋POW×10"),
        ("edu10str10", "EDU×10＋STR×10"),
        ("edu10con10", "EDU×10＋CON×10"),
        ("edu10siz10", "EDU×10＋SIZ×10"),
        ("edu4", "EDU×4"),
        ("edu2app2", "EDU×2＋APP×2"),
        ("edu2dex2", "EDU×2＋DEX×2"),
        ("edu2pow2", "EDU×2＋POW×2"),
        ("edu2str2", "EDU×2＋STR×2"),
        ("edu2con2", "EDU×2＋CON×2"),
        ("edu2siz2", "EDU×2＋SIZ×2"),
    ]

    # 基本情報
    ACCESS_SCOPE_CHOICES = [
        ("private", "Private"),
        ("group", "Group"),
        ("link", "Link"),
        ("public", "Public"),
    ]

    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="character_sheets")
    edition = models.CharField(max_length=3, choices=EDITION_CHOICES)

    # 個人情報

    # 能力値 (範囲制限なし - ユーザーの自由度を最大化)

    # 職業技能ポイント倍率（デフォルトは20）

    # 副次ステータス

    # バージョン管理

    # 画像

    # メタデータ
    access_scope = models.CharField(
        max_length=10,
        choices=ACCESS_SCOPE_CHOICES,
        default="group",
        verbose_name="Access scope",
    )
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    allowed_users = models.ManyToManyField(
        "accounts.CustomUser",
        blank=True,
        related_name="readable_character_sheets",
        verbose_name="Allowed users",
    )

    # CCFOLIA連携

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CharacterSheetManager()

    class Meta:
        # バージョン管理用の制約のみ（同一ユーザーの同一キャラクターでバージョンが重複しないよう）
        # 同名キャラクターは作成可能
        ordering = ["-updated_at"]
        verbose_name = "キャラクターシート"
        verbose_name_plural = "キャラクターシート"

    def __str__(self):
        try:
            name = self.system_data.name
        except (CharacterSheet6th.DoesNotExist, CharacterSheet7th.DoesNotExist):
            name = "(detail missing)"
        try:
            version = self.system_data.version
        except (CharacterSheet6th.DoesNotExist, CharacterSheet7th.DoesNotExist):
            version = 0
        return f"{name} ({self.edition}) v{version}"

    @property
    def system_data(self):
        """Return the edition-specific record for this registry entry."""
        if self.edition == "6th":
            return self.sixth_edition_data
        if self.edition == "7th":
            return self.seventh_edition_data
        raise ValueError(f"Unsupported character system: {self.edition}")

    def calculate_derived_stats(self):
        """派生ステータスを計算"""
        return self.system_data.calculate_derived_stats()

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
        from .services.character_version_service import CharacterVersionService

        return CharacterVersionService.create_version(
            source_character=self,
            actor=self.user,
            validated_data={
                "version_note": version_note,
                "session_count": session_count or (self.system_data.session_count + 1),
            },
            copy_policy={"copy_skills": copy_skills},
        )

    def create_version(self, version_note="", session_count=None, copy_skills=False):
        """create_version 互換メソッド"""
        return self.create_new_version(version_note, session_count, copy_skills)

    def get_all_versions(self):
        """get_all_versions 互換メソッド"""
        return self.get_version_history()

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
        detail_model = CharacterSheet6th if self.edition == "6th" else CharacterSheet7th
        child_ids = detail_model.objects.filter(parent_data=self.system_data).values("character_sheet_id")
        return CharacterSheet.objects.filter(pk__in=child_ids)

    def compare_with_version(self, other_version):
        """他のバージョンとの比較"""
        return CharacterVersionManager.compare_versions(self, other_version)

    def rollback_to_version(self, target_version):
        """指定バージョンにロールバック"""
        return CharacterVersionManager.rollback_to_version(self, target_version)

    def get_version_statistics(self):
        """バージョン統計を取得"""
        return CharacterVersionManager.get_version_statistics(self)

    def delete(self, *args, **kwargs):
        """子バージョンの参照を付け替えてから削除"""
        return super().delete(*args, **kwargs)

    def calculate_max_sanity(self):
        return self.system_data.calculate_max_sanity()

    def update_max_sanity(self):
        """最大SAN値を更新"""
        detail = self.system_data
        try:
            cthulhu_skill = detail.skills.get(skill_name="クトゥルフ神話")
            cthulhu_value = cthulhu_skill.current_value
        except detail.skills.model.DoesNotExist:
            cthulhu_value = 0
        detail.sanity_max = 99 - cthulhu_value
        detail.save(update_fields=["sanity_max"])

    def export_version_data(self):
        """バージョンデータをエクスポート"""
        return CharacterExportManager.export_version_data(self)

    def export_ccfolia_format(self):
        """CCFOLIA形式でのデータエクスポート"""
        return CharacterExportManager.export_ccfolia_format(self)

    @staticmethod
    def bulk_export_ccfolia(character_ids):
        """複数キャラクターの一括CCFOLIAエクスポート"""
        return CharacterExportManager.bulk_export_ccfolia(character_ids)

    def sync_to_ccfolia(self):
        """CCFOLIAへの同期処理"""
        return CharacterSyncManager.sync_to_ccfolia(self)

    def resolve_sync_conflict(self, conflict_data):
        """同期競合の解決"""
        return CharacterSyncManager.resolve_sync_conflict(self, conflict_data)

    # 技能ポイント管理メソッド
    @classmethod
    def valid_occupation_point_methods_for_edition(cls, edition):
        """版別に利用可能な職業技能ポイント計算方式を返す"""
        if edition == "7th":
            return cls.OCCUPATION_POINT_METHODS_7TH
        return cls.OCCUPATION_POINT_METHODS_6TH

    def get_occupation_point_method(self):
        return self.system_data.get_occupation_point_method()

    def calculate_occupation_points(self):
        return self.system_data.calculate_occupation_points()

    def calculate_hobby_points(self):
        return self.system_data.calculate_hobby_points()

    def get_7th_skill_base_value(self, skill_name):
        if isinstance(self, CharacterSheet):
            detail = self.system_data
            if skill_name == "母国語":
                return detail.edu_value or 0
            if skill_name == "回避":
                return (detail.dex_value or 0) // 2
            return 0
        if isinstance(self, CharacterSheet):
            detail = self.system_data
            if skill_name:
                return (detail.dex_value or 0) // 2
        """7版の代表的な技能初期値を返す"""
        if skill_name == "回避":
            return self.dex_value // 2
        if skill_name == "母国語":
            return self.edu_value

        base_values = {
            "信用": 0,
            "目星": 25,
            "聞き耳": 20,
            "図書館": 20,
            "応急手当": 30,
            "鍵開け": 1,
            "鑑定": 5,
            "隠密": 20,
            "隠れる": 20,
            "忍び歩き": 20,
            "隠す": 10,
            "手さばき": 10,
            "追跡": 10,
            "登攀": 20,
            "心理学": 10,
            "説得": 10,
            "魅惑": 15,
            "威圧": 15,
            "言いくるめ": 5,
            "ほかの言語": 1,
            "他の言語": 1,
            "射撃（拳銃）": 20,
            "拳銃": 20,
            "射撃（ライフル／ショットガン）": 25,
            "ショットガン": 25,
            "ライフル": 25,
            "投擲": 20,
            "近接戦闘（格闘）": 25,
            "近接戦闘": 25,
            "格闘技": 25,
            "キック": 25,
            "組み付き": 25,
            "こぶし（パンチ）": 25,
            "頭突き": 25,
            "マーシャルアーツ": 25,
            "クトゥルフ神話": 0,
            "医学": 1,
            "オカルト": 5,
            "科学": 1,
            "化学": 1,
            "生物学": 1,
            "地質学": 1,
            "天文学": 1,
            "物理学": 1,
            "薬学": 1,
            "経理": 5,
            "考古学": 1,
            "コンピューター": 5,
            "人類学": 1,
            "自然": 10,
            "博物学": 10,
            "法律": 5,
            "歴史": 5,
            "運転（自動車）": 20,
            "運転": 20,
            "機械修理": 10,
            "重機械操作": 1,
            "乗馬": 5,
            "水泳": 20,
            "芸術／製作": 5,
            "芸術": 5,
            "製作": 5,
            "操縦": 1,
            "跳躍": 20,
            "電気修理": 10,
            "電子工学": 1,
            "ナビゲート": 10,
            "サバイバル": 10,
            "変装": 5,
        }
        return base_values.get(skill_name, 1)

    def calculate_used_occupation_points(self):
        """使用済み職業技能ポイントを計算"""
        from django.db.models import Sum

        total = self.skills.aggregate(total=Sum("occupation_points"))["total"] or 0
        return total

    def calculate_used_hobby_points(self):
        """使用済み趣味技能ポイントを計算"""
        from django.db.models import Sum

        total = self.skills.aggregate(total=Sum("interest_points"))["total"] or 0
        return total

    def calculate_remaining_occupation_points(self):
        """残り職業技能ポイントを計算"""
        return self.calculate_occupation_points() - self.calculate_used_occupation_points()

    def calculate_remaining_hobby_points(self):
        """残り趣味技能ポイントを計算"""
        return self.calculate_hobby_points() - self.calculate_used_hobby_points()

    def get_occupation_recommended_skills(self):
        """互換用。職業ルールは版別データから取得する。"""
        return self.system_data.get_occupation_recommended_skills()

    def apply_occupation_template(self):
        """職業テンプレートを適用して推奨技能を作成"""
        recommended_skills = self.get_occupation_recommended_skills()

        # 教授の場合は倍率を25に設定
        if self.occupation == "教授":
            self.occupation_multiplier = 25
            self.save()

        # 推奨技能を作成
        for skill_name in recommended_skills:
            skill, created = self.system_data.skills.get_or_create(
                character_sheet=self,
                skill_name=skill_name,
                defaults={
                    "base_value": self._get_skill_base_value(skill_name),
                    "category": self._get_skill_category(skill_name),
                },
            )

        return len(recommended_skills)

    def _get_skill_base_value(self, skill_name):
        """技能の基本値を取得"""
        if self.edition == "7th":
            return self.get_7th_skill_base_value(skill_name)

        # 技能別基本値の定義
        base_values = {
            "医学": 5,
            "応急手当": 30,
            "生物学": 1,
            "薬学": 1,
            "心理学": 5,
            "精神分析": 1,
            "信用": 15,
            "言いくるめ": 5,
            "図書館": 25,
            "母国語": self.edu_value * 5,
            "他の言語": 1,
            "教育": 20,
            "歴史": 20,
            "人類学": 1,
            "説得": 15,
            "拳銃": 20,
            "格闘技": 25,
            "聞き耳": 25,
            "目星": 25,
            "運転": 20,
            "法律": 5,
            "威圧": 15,
            "隠れる": 10,
            "忍び歩き": 10,
            "写真術": 10,
            "考古学": 1,
            "鍵開け": 1,
            "登攀": 40,
            "機械修理": 20,
            "ナビゲート": 10,
        }

        return base_values.get(skill_name, 5)

    def _get_skill_category(self, skill_name):
        """技能のカテゴリを取得"""
        if self.edition == "7th":
            categories_7th = {
                "回避": "戦闘系",
                "近接戦闘（格闘）": "戦闘系",
                "投擲": "戦闘系",
                "射撃（拳銃）": "戦闘系",
                "射撃（ライフル／ショットガン）": "戦闘系",
                "応急手当": "探索系",
                "鍵開け": "探索系",
                "鑑定": "探索系",
                "隠密": "探索系",
                "聞き耳": "探索系",
                "精神分析": "探索系",
                "追跡": "探索系",
                "登攀": "探索系",
                "図書館": "探索系",
                "目星": "探索系",
                "手さばき": "探索系",
                "運転（自動車）": "行動系",
                "機械修理": "行動系",
                "重機械操作": "行動系",
                "乗馬": "行動系",
                "水泳": "行動系",
                "芸術／製作": "行動系",
                "操縦": "行動系",
                "跳躍": "行動系",
                "電気修理": "行動系",
                "電子工学": "行動系",
                "ナビゲート": "行動系",
                "サバイバル": "行動系",
                "変装": "行動系",
                "言いくるめ": "対人系",
                "魅惑": "対人系",
                "信用": "対人系",
                "説得": "対人系",
                "威圧": "対人系",
                "ほかの言語": "対人系",
                "他の言語": "対人系",
                "母国語": "対人系",
                "医学": "知識系",
                "オカルト": "知識系",
                "科学": "知識系",
                "クトゥルフ神話": "知識系",
                "経理": "知識系",
                "考古学": "知識系",
                "コンピューター": "知識系",
                "心理学": "知識系",
                "人類学": "知識系",
                "自然": "知識系",
                "法律": "知識系",
                "歴史": "知識系",
            }
            return categories_7th.get(skill_name, "特殊・その他")

        categories = {
            "医学": "知識系",
            "応急手当": "探索系",
            "生物学": "知識系",
            "薬学": "知識系",
            "心理学": "対人系",
            "精神分析": "対人系",
            "信用": "対人系",
            "言いくるめ": "対人系",
            "図書館": "探索系",
            "母国語": "対人系",
            "他の言語": "対人系",
            "教育": "対人系",
            "歴史": "知識系",
            "人類学": "知識系",
            "説得": "対人系",
            "拳銃": "戦闘系",
            "格闘技": "戦闘系",
            "聞き耳": "探索系",
            "目星": "探索系",
            "運転": "行動系",
            "法律": "知識系",
            "威圧": "対人系",
            "隠れる": "探索系",
            "忍び歩き": "探索系",
            "写真術": "技術系",
            "考古学": "知識系",
            "鍵開け": "探索系",
            "登攀": "行動系",
            "機械修理": "技術系",
            "ナビゲート": "行動系",
        }

        return categories.get(skill_name, "特殊・その他")

    def export_ccfolia_format(self):
        """CCFOLIA形式でのデータエクスポート"""
        return CharacterExportManager.export_ccfolia_format(self)

    def calculate_carry_capacity(self):
        return (self.system_data.str_value or 0) * 3

    def calculate_movement_penalty(self, total_weight):
        return self.system_data.calculate_movement_penalty(total_weight)


class CharacterSheetSystemData(models.Model):
    """Edition-specific character data stored outside the registry table."""

    name_kana = models.CharField(max_length=100, blank=True)
    # Existing parent-table data is copied by migration.  These remain nullable
    # during the compatibility transition so that already persisted 6th data
    # can be upgraded without synthetic values.
    name = models.CharField(max_length=100, null=True, blank=True)
    player_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=CharacterSheet.STATUS_CHOICES, default="alive")
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=50, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    birthplace = models.CharField(max_length=100, blank=True)
    residence = models.CharField(max_length=100, blank=True)
    recommended_skills = models.JSONField(default=list, blank=True)
    occupation_skills = models.JSONField(default=list, blank=True)
    source_scenario = models.ForeignKey("scenarios.Scenario", on_delete=models.SET_NULL, null=True, blank=True)
    source_scenario_title = models.CharField(max_length=200, blank=True)
    source_scenario_game_system = models.CharField(max_length=10, blank=True)
    str_value = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(999)])
    con_value = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(999)])
    pow_value = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(999)])
    dex_value = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(999)])
    app_value = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(999)])
    siz_value = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(999)])
    int_value = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(999)])
    edu_value = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(999)])
    occupation_multiplier = models.IntegerField(default=20)
    occupation_point_method = models.CharField(max_length=20, blank=True, default="")
    hit_points_max = models.IntegerField(null=True, blank=True)
    hit_points_current = models.IntegerField(null=True, blank=True)
    magic_points_max = models.IntegerField(null=True, blank=True)
    magic_points_current = models.IntegerField(null=True, blank=True)
    sanity_starting = models.IntegerField(null=True, blank=True)
    sanity_max = models.IntegerField(null=True, blank=True)
    sanity_current = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    secret_ho_info = models.TextField(blank=True, default="")
    character_image = models.ImageField(upload_to="character_sheets/", blank=True)
    is_active = models.BooleanField(default=True)
    session_count = models.PositiveIntegerField(default=0)
    ccfolia_sync_enabled = models.BooleanField(default=False)
    ccfolia_character_id = models.CharField(max_length=100, blank=True)
    version = models.PositiveIntegerField(default=1)
    version_note = models.CharField(max_length=1000, blank=True)

    class Meta:
        abstract = True

    @property
    def edition(self):
        """Edition is owned by the registry but read through the detail API."""
        return self.character_sheet.edition

    @property
    def abilities(self):
        return {
            "str": self.str_value,
            "con": self.con_value,
            "pow": self.pow_value,
            "dex": self.dex_value,
            "app": self.app_value,
            "siz": self.siz_value,
            "int": self.int_value,
            "edu": self.edu_value,
        }

    def calculate_derived_stats(self):
        """Calculate derived values from this edition's own ability values."""
        import math

        if self.character_sheet.edition == "6th":
            return {
                "hit_points_max": math.ceil(((self.con_value or 0) + (self.siz_value or 0)) / 2),
                "magic_points_max": self.pow_value or 0,
                "sanity_starting": (self.pow_value or 0) * 5,
                "sanity_max": 99,
            }
        return {
            "hit_points_max": ((self.con_value or 0) + (self.siz_value or 0)) // 10,
            "magic_points_max": (self.pow_value or 0) // 5,
            "sanity_starting": self.pow_value or 0,
            "sanity_max": 99,
        }

    def save(self, *args, **kwargs):
        """Initialize derived values on the edition-specific record itself."""
        stats = self.calculate_derived_stats()
        if self.hit_points_max is None:
            self.hit_points_max = stats["hit_points_max"]
        if self.hit_points_current is None:
            self.hit_points_current = self.hit_points_max
        if self.magic_points_max is None:
            self.magic_points_max = stats["magic_points_max"]
        if self.magic_points_current is None:
            self.magic_points_current = self.magic_points_max
        if self.sanity_starting is None:
            self.sanity_starting = stats["sanity_starting"]
        if self.sanity_max is None:
            self.sanity_max = stats["sanity_max"]
        if self.sanity_current is None:
            self.sanity_current = self.sanity_starting
        return super().save(*args, **kwargs)

    def clean(self):
        """Keep version lineage inside one edition and prevent cycles."""
        from django.core.exceptions import ValidationError

        if self.age is not None and not 15 <= self.age <= 90:
            raise ValidationError({"age": "年齢は15から90の範囲で入力してください。"})

        parent_data = getattr(self, "parent_data", None)
        if parent_data is None:
            return
        if parent_data.character_sheet.edition != self.character_sheet.edition:
            raise ValidationError({"parent_data": "親バージョンは同じ版でなければなりません。"})
        if self.version <= parent_data.version:
            raise ValidationError({"version": "バージョン番号は親より大きくしてください。"})
        root = parent_data
        while root.parent_data_id:
            root = root.parent_data
        if self.__class__.objects.filter(parent_data=root, version=self.version).exclude(pk=self.pk).exists():
            raise ValidationError({"version": "同じ履歴内でバージョン番号は重複できません。"})
        seen = {self.pk} if self.pk else set()
        current = parent_data
        while current is not None:
            if current.pk in seen:
                raise ValidationError({"parent_data": "バージョン履歴に循環参照は作成できません。"})
            seen.add(current.pk)
            current = current.parent_data

    def calculate_occupation_points(self):
        method = (self.occupation_point_method or "").strip()
        if self.character_sheet.edition == "7th":
            values = {
                "edu4": (self.edu_value or 0) * 4,
                "edu2app2": (self.edu_value or 0) * 2 + (self.app_value or 0) * 2,
                "edu2dex2": (self.edu_value or 0) * 2 + (self.dex_value or 0) * 2,
                "edu2pow2": (self.edu_value or 0) * 2 + (self.pow_value or 0) * 2,
                "edu2str2": (self.edu_value or 0) * 2 + (self.str_value or 0) * 2,
                "edu2con2": (self.edu_value or 0) * 2 + (self.con_value or 0) * 2,
                "edu2siz2": (self.edu_value or 0) * 2 + (self.siz_value or 0) * 2,
            }
            return values.get(method, (self.edu_value or 0) * 4)
        values = {
            "edu20": (self.edu_value or 0) * 20,
            "edu10app10": (self.edu_value or 0) * 10 + (self.app_value or 0) * 10,
            "edu10dex10": (self.edu_value or 0) * 10 + (self.dex_value or 0) * 10,
            "edu10pow10": (self.edu_value or 0) * 10 + (self.pow_value or 0) * 10,
            "edu10str10": (self.edu_value or 0) * 10 + (self.str_value or 0) * 10,
            "edu10con10": (self.edu_value or 0) * 10 + (self.con_value or 0) * 10,
            "edu10siz10": (self.edu_value or 0) * 10 + (self.siz_value or 0) * 10,
        }
        return values.get(method, (self.edu_value or 0) * (self.occupation_multiplier or 20))

    def calculate_hobby_points(self):
        return (self.int_value or 0) * (2 if self.character_sheet.edition == "7th" else 10)

    def get_occupation_point_method(self):
        method = (self.occupation_point_method or "").strip()
        valid = CharacterSheet.valid_occupation_point_methods_for_edition(self.edition)
        if method in valid:
            return method
        return "edu4" if self.edition == "7th" else ""

    def calculate_max_sanity(self):
        skill = self.skills.filter(skill_name="クトゥルフ神話").only("current_value").first()
        return 99 - (skill.current_value if skill else 0)

    def update_max_sanity(self):
        self.sanity_max = self.calculate_max_sanity()
        self.save(update_fields=["sanity_max"])
        return self.sanity_max

    # Skill rules are invoked on an edition record.  The registry retains
    # compatibility wrappers only; it no longer owns the underlying values.
    def get_7th_skill_base_value(self, skill_name):
        return CharacterSheet.get_7th_skill_base_value(self, skill_name)

    def get_skill_base_value(self, skill_name):
        return CharacterSheet._get_skill_base_value(self, skill_name)

    def get_skill_category(self, skill_name):
        return CharacterSheet._get_skill_category(self, skill_name)

    def get_occupation_recommended_skills(self):
        if self.edition == "7th":
            skills = {
                "医師": ["医学", "応急手当", "科学", "心理学", "信用", "説得", "ほかの言語", "図書館"],
                "教授": ["図書館", "母国語", "ほかの言語", "科学", "心理学", "歴史", "人類学", "説得"],
                "警察官": ["射撃（拳銃）", "近接戦闘（格闘）", "心理学", "聞き耳", "目星", "運転（自動車）", "法律", "威圧"],
                "探偵": ["目星", "聞き耳", "隠密", "手さばき", "心理学", "図書館", "法律", "説得"],
                "記者": ["目星", "聞き耳", "図書館", "心理学", "説得", "信用", "コンピューター", "運転（自動車）"],
                "考古学者": ["考古学", "歴史", "図書館", "目星", "ほかの言語", "登攀", "科学", "ナビゲート"],
            }
        else:
            skills = {
                "医師": ["医学", "応急手当", "生物学", "薬学", "心理学", "精神分析", "信用", "言いくるめ"],
                "教授": ["図書館", "母国語", "他の言語", "教育", "心理学", "歴史", "人類学", "説得"],
                "警察官": ["拳銃", "格闘技", "心理学", "聞き耳", "目星", "運転", "法律", "威圧"],
                "探偵": ["目星", "聞き耳", "隠れる", "忍び歩き", "心理学", "図書館", "法律", "説得"],
                "記者": ["目星", "聞き耳", "図書館", "心理学", "説得", "信用", "写真術", "運転"],
                "考古学者": ["考古学", "歴史", "図書館", "目星", "他の言語", "登攀", "機械修理", "ナビゲート"],
            }
        return skills.get(self.occupation, [])

    def apply_occupation_template(self):
        recommended_skills = self.get_occupation_recommended_skills()
        if self.occupation == "医師":
            self.occupation_multiplier = 25
            self.save(update_fields=["occupation_multiplier"])
        for skill_name in recommended_skills:
            self.skills.get_or_create(
                skill_name=skill_name,
                defaults={
                    "base_value": self.get_skill_base_value(skill_name),
                    "category": self.get_skill_category(skill_name),
                },
            )
        return len(recommended_skills)

    def calculate_used_occupation_points(self):
        from django.db.models import Sum

        return self.skills.aggregate(total=Sum("occupation_points"))["total"] or 0

    def calculate_used_hobby_points(self):
        from django.db.models import Sum

        return self.skills.aggregate(total=Sum("interest_points"))["total"] or 0

    def calculate_remaining_occupation_points(self):
        return self.calculate_occupation_points() - self.calculate_used_occupation_points()

    def calculate_remaining_hobby_points(self):
        return self.calculate_hobby_points() - self.calculate_used_hobby_points()

    def calculate_carry_capacity(self):
        return (self.str_value or 0) * 3

    def calculate_movement_penalty(self, total_weight):
        carry_capacity = (self.str_value or 0) * 3
        if total_weight <= carry_capacity:
            return 0
        if total_weight <= carry_capacity * 1.5:
            return 10
        if total_weight <= carry_capacity * 2:
            return 20
        return 30

    def calculate_damage_bonus_7th(self):
        total = (self.str_value or 0) + (self.siz_value or 0)
        if total <= 64: return "-2"
        if total <= 84: return "-1"
        if total <= 124: return "+0"
        if total <= 164: return "+1D4"
        if total <= 204: return "+1D6"
        return "+2D6"

    def calculate_build_7th(self):
        total = (self.str_value or 0) + (self.siz_value or 0)
        if total <= 64: return -2
        if total <= 84: return -1
        if total <= 124: return 0
        if total <= 164: return 1
        if total <= 204: return 2
        return 3

    def calculate_move_rate_7th(self):
        strength, size, dexterity = self.str_value or 0, self.siz_value or 0, self.dex_value or 0
        move = 7 if strength < size and dexterity < size else 9 if strength > size and dexterity > size else 8
        for threshold, penalty in ((80, 5), (70, 4), (60, 3), (50, 2), (40, 1)):
            if (self.age or 0) >= threshold:
                return max(1, move - penalty)
        return move

    @classmethod
    def sync_from_registry(cls, character_sheet, **overrides):
        # Registry data deliberately contains no character attributes.
        return cls.objects.update_or_create(character_sheet=character_sheet, defaults=overrides)[0]


class CharacterSheet6th(CharacterSheetSystemData):
    """6版固有データ"""

    character_sheet = models.OneToOneField(CharacterSheet, on_delete=models.CASCADE, related_name="sixth_edition_data")
    parent_data = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="versions")

    # 6版固有フィールド
    mental_disorder = models.TextField(blank=True, verbose_name="精神的障害")

    # 6版では自動計算される値
    idea_roll = models.IntegerField(default=0, verbose_name="アイデアロール")
    luck_roll = models.IntegerField(default=0, verbose_name="幸運ロール")
    know_roll = models.IntegerField(default=0, verbose_name="知識ロール")
    damage_bonus = models.CharField(max_length=10, default="+0", verbose_name="ダメージボーナス")

    # 財務データ
    cash = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, validators=[MinValueValidator(0)], verbose_name="現金・資産"
    )
    assets = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, validators=[MinValueValidator(0)], verbose_name="その他資産"
    )
    annual_income = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, validators=[MinValueValidator(0)], verbose_name="年収"
    )
    real_estate = models.TextField(blank=True, verbose_name="不動産")

    def clean(self):
        """財務データのバリデーション"""
        from django.core.exceptions import ValidationError

        super().clean()

        # 負の値チェック
        if self.cash < 0:
            raise ValidationError({"cash": "現金は0以上の値を入力してください。"})

        if self.assets < 0:
            raise ValidationError({"assets": "資産は0以上の値を入力してください。"})

        if self.annual_income < 0:
            raise ValidationError({"annual_income": "年収は0以上の値を入力してください。"})

        # 上限チェック（10億円）
        max_value = 1000000000
        if self.cash >= max_value:
            raise ValidationError({"cash": f"現金は{max_value:,}円未満で入力してください。"})

        if self.assets >= max_value:
            raise ValidationError({"assets": f"資産は{max_value:,}円未満で入力してください。"})

        if self.annual_income >= max_value:
            raise ValidationError({"annual_income": f"年収は{max_value:,}円未満で入力してください。"})

    def save(self, *args, **kwargs):
        """6版固有の計算を実行"""
        if self.character_sheet_id and not getattr(self, "_skip_point_validation", False):
            # アイデア = INT × 5
            self.idea_roll = (self.int_value or 0) * 5

            # 幸運 = POW × 5
            self.luck_roll = (self.pow_value or 0) * 5

            # 知識 = EDU × 5
            self.know_roll = (self.edu_value or 0) * 5

            # ダメージボーナス計算
            self.damage_bonus = self.calculate_damage_bonus_6th()

        # 計算後にバリデーション実行
        self.full_clean()

        super().save(*args, **kwargs)


    def calculate_damage_bonus_6th(self):
        """6版ダメージボーナス計算"""
        total = (self.str_value or 0) + (self.siz_value or 0)

        # クトゥルフ神話TRPG 6版の正式なダメージボーナス表
        if 2 <= total <= 12:
            return "-1D6"
        elif 13 <= total <= 16:
            return "-1D4"
        elif 17 <= total <= 24:
            return "+0"
        elif 25 <= total <= 32:
            return "+1D4"
        elif 33 <= total <= 40:
            return "+1D6"
        elif 41 <= total <= 56:
            return "+2D6"
        elif 57 <= total <= 72:
            return "+3D6"
        elif total <= 88:
            return "+4D6"
        else:
            return "+5D6"

    def calculate_total_wealth(self):
        """総資産を計算"""
        return self.cash + self.assets


class CharacterSheet7th(CharacterSheetSystemData):
    """クトゥルフ神話TRPG 7版の専用データテーブル。"""

    character_sheet = models.OneToOneField(CharacterSheet, on_delete=models.CASCADE, related_name="seventh_edition_data")
    parent_data = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="versions")

    class Meta:
        verbose_name = "7版キャラクターシートデータ"
        verbose_name_plural = "7版キャラクターシートデータ"


class _LegacyCharacterSkill(models.Model):
    """Historical pre-0059 schema; abstract and never used at runtime."""

    CATEGORY_CHOICES = [
        ("探索系", "探索系"),
        ("対人系", "対人系"),
        ("戦闘系", "戦闘系"),
        ("知識系", "知識系"),
        ("技術系", "技術系"),
        ("行動系", "行動系"),
        ("言語系", "言語系"),
        ("特殊・その他", "特殊・その他"),
    ]

    character_sheet = models.ForeignKey(CharacterSheet, on_delete=models.CASCADE, related_name="skills")
    skill_name = models.CharField(max_length=100, verbose_name="技能名")
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="特殊・その他", verbose_name="カテゴリ"
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
        abstract = True
        unique_together = ["character_sheet", "skill_name"]
        ordering = ["skill_name"]
        verbose_name = "キャラクタースキル"
        verbose_name_plural = "キャラクタースキル"

    def clean(self):
        """カスタム技能のバリデーション"""
        from django.core.exceptions import ValidationError
        from django.db import DatabaseError, OperationalError

        # 技能名の必須チェック
        if not self.skill_name or self.skill_name.strip() == "":
            raise ValidationError("技能名は必須です。")

        # 技能名の長さチェック
        if len(self.skill_name) > 100:
            raise ValidationError("技能名は100文字以内で入力してください。")

        # ポイント値の範囲チェック
        point_fields = [
            ("base_value", "基本値"),
            ("occupation_points", "職業技能ポイント"),
            ("interest_points", "興味技能ポイント"),
            ("bonus_points", "ボーナスポイント"),
            ("other_points", "その他ポイント"),
        ]

        for field_name, field_label in point_fields:
            value = getattr(self, field_name, 0)
            if value < 0:
                raise ValidationError({field_name: f"{field_label}は0以上の値を入力してください。"})
            if value > 999:
                raise ValidationError({field_name: f"{field_label}は999以下の値を入力してください。"})

        # 技能値の合計チェック（最大999）
        total_value = (
            self.base_value + self.occupation_points + self.interest_points + self.bonus_points + self.other_points
        )

        max_skill_value = 999

        if total_value > max_skill_value:
            raise ValidationError(f"技能値の合計は{max_skill_value}を超えることはできません。")

        # 技能ポイント過剰割り振りチェック
        if self.character_sheet and not getattr(self, "_skip_point_validation", False):
            try:
                # 職業技能ポイントのチェック
                system_data = (
                    self.character_sheet.system_data
                    if isinstance(self.character_sheet, CharacterSheet)
                    else self.character_sheet
                )
                total_occupation_points = system_data.calculate_occupation_points()
                used_occupation_points = (
                    self.character_sheet.skills.exclude(pk=self.pk).aggregate(total=models.Sum("occupation_points"))[
                        "total"
                    ]
                    or 0
                )

                if (used_occupation_points + self.occupation_points) > total_occupation_points:
                    raise ValidationError(
                        {
                            "occupation_points": f"職業技能ポイントが不足しています。残り: {total_occupation_points - used_occupation_points}ポイント"
                        }
                    )

                # 趣味技能ポイントのチェック
                total_hobby_points = (system_data.int_value or 0) * (2 if system_data.edition == "7th" else 10)
                used_hobby_points = (
                    self.character_sheet.skills.exclude(pk=self.pk).aggregate(total=models.Sum("interest_points"))[
                        "total"
                    ]
                    or 0
                )

                if (used_hobby_points + self.interest_points) > total_hobby_points:
                    raise ValidationError(
                        {
                            "interest_points": f"趣味技能ポイントが不足しています。残り: {total_hobby_points - used_hobby_points}ポイント"
                        }
                    )
            except (OperationalError, DatabaseError):
                # SQLite並行実行時のロックはポイント検証をスキップ
                return

    def save(self, *args, **kwargs):
        """保存時に値を自動計算"""
        # バリデーション実行
        skip_point_validation = kwargs.pop("skip_point_validation", False)
        if skip_point_validation:
            self._skip_point_validation = True
        try:
            self.full_clean()
        finally:
            if skip_point_validation and hasattr(self, "_skip_point_validation"):
                delattr(self, "_skip_point_validation")

        # 現在値計算（最大999）
        total = self.base_value + self.occupation_points + self.interest_points + self.bonus_points + self.other_points

        max_skill_value = 999

        self.current_value = min(total, max_skill_value)

        super().save(*args, **kwargs)
        sync_edition_related_data(self)

        # クトゥルフ神話技能の場合、最大SAN値を更新
        if self.skill_name == "クトゥルフ神話" and self.character_sheet:
            self.character_sheet.update_max_sanity()

    def delete(self, *args, **kwargs):
        delete_edition_related_data(self)
        return super().delete(*args, **kwargs)

    @classmethod
    def create_custom_skill(cls, character_sheet, skill_name, category="特殊・その他", **kwargs):
        """カスタム技能作成のヘルパーメソッド"""
        # 専門分野の抽出
        specialization = None
        if "（" in skill_name and "）" in skill_name:
            specialization = skill_name[skill_name.find("（") + 1 : skill_name.find("）")]

        # カスタム技能作成
        skill = cls.objects.create(
            character_sheet=character_sheet,
            skill_name=skill_name,
            category=category,
            notes=kwargs.get("notes", specialization or ""),
            **{k: v for k, v in kwargs.items() if k != "notes"},
        )

        return skill

    def __str__(self):
        return f"{self.character_sheet.system_data.name} - {self.skill_name}: {self.current_value}"


class _LegacyCharacterEquipment(models.Model):
    """Historical pre-0059 schema; abstract and never used at runtime."""

    ITEM_TYPE_CHOICES = [
        ("weapon", "武器"),
        ("armor", "防具"),
        ("item", "アイテム"),
    ]

    character_sheet = models.ForeignKey(CharacterSheet, on_delete=models.CASCADE, related_name="equipment")
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

    def __init__(self, *args, **kwargs):
        if "equipment_type" in kwargs and "item_type" not in kwargs:
            kwargs["item_type"] = kwargs.pop("equipment_type")
        if "armor_value" in kwargs and "armor_points" not in kwargs:
            kwargs["armor_points"] = kwargs.pop("armor_value")
        super().__init__(*args, **kwargs)

    class Meta:
        abstract = True
        ordering = ["item_type", "name"]
        verbose_name = "キャラクター装備"
        verbose_name_plural = "キャラクター装備"

    def clean(self):
        """装備データのバリデーション"""
        from django.core.exceptions import ValidationError

        # 名前の必須チェック
        if not self.name or self.name.strip() == "":
            raise ValidationError("装備名は必須です。")

        # 攻撃回数の範囲チェック
        if self.attacks_per_round is not None and self.attacks_per_round < 0:
            raise ValidationError({"attacks_per_round": "攻撃回数は0以上の値を入力してください。"})

        # 装弾数の範囲チェック
        if self.ammo is not None and self.ammo < 0:
            raise ValidationError({"ammo": "装弾数は0以上の値を入力してください。"})

        # 故障ナンバーの範囲チェック
        if self.malfunction_number is not None and (self.malfunction_number < 1 or self.malfunction_number > 100):
            raise ValidationError({"malfunction_number": "故障ナンバーは1-100の範囲で入力してください。"})

        # 防護点の範囲チェック
        if self.armor_points is not None and self.armor_points < 0:
            raise ValidationError({"armor_points": "防護点は0以上の値を入力してください。"})

        # 数量の範囲チェック
        if self.quantity < 1:
            raise ValidationError({"quantity": "数量は1以上の値を入力してください。"})

        # 重量の範囲チェック
        if self.weight is not None and self.weight < 0:
            raise ValidationError({"weight": "重量は0以上の値を入力してください。"})

    def save(self, *args, **kwargs):
        """保存時にバリデーション実行"""
        self.full_clean()
        super().save(*args, **kwargs)
        sync_edition_related_data(self)

    def delete(self, *args, **kwargs):
        delete_edition_related_data(self)
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.character_sheet.system_data.name} - {self.name}"

    @property
    def equipment_type(self):
        return self.item_type

    @equipment_type.setter
    def equipment_type(self, value):
        self.item_type = value

    @property
    def armor_value(self):
        return self.armor_points

    @armor_value.setter
    def armor_value(self, value):
        self.armor_points = value


class CharacterBackground(models.Model):
    """キャラクター背景情報"""

    character_sheet = models.OneToOneField(CharacterSheet, on_delete=models.CASCADE, related_name="background_info")

    # パーソナルデータ
    appearance_description = models.TextField(max_length=1000, blank=True, verbose_name="容姿・特徴")
    beliefs_ideology = models.TextField(max_length=1000, blank=True, verbose_name="信念・信条")
    significant_people = models.TextField(max_length=1000, blank=True, verbose_name="大切な人物")
    meaningful_locations = models.TextField(max_length=1000, blank=True, verbose_name="意味のある場所")
    treasured_possessions = models.TextField(max_length=1000, blank=True, verbose_name="愛用の品")
    traits_mannerisms = models.TextField(max_length=1000, blank=True, verbose_name="特徴・癖")

    # 経歴
    personal_history = models.TextField(max_length=2000, blank=True, verbose_name="生い立ち")
    important_events = models.TextField(max_length=2000, blank=True, verbose_name="重要な出来事")
    scars_injuries = models.TextField(max_length=1000, blank=True, verbose_name="傷・傷跡")
    phobias_manias = models.TextField(max_length=1000, blank=True, verbose_name="恐怖症・マニア")
    arcane_tomes_spells_artifacts = models.TextField(
        max_length=2000, blank=True, default="", verbose_name="魔道書・呪文・アーティファクト"
    )
    encounters_with_strange_entities = models.TextField(
        max_length=2000, blank=True, default="", verbose_name="遭遇した超自然の存在"
    )

    # 仲間の探索者
    fellow_investigators = models.TextField(max_length=2000, blank=True, verbose_name="仲間の探索者")

    # その他
    notes_memo = models.TextField(max_length=3000, blank=True, verbose_name="メモ欄")

    # メタデータ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        alias_map = {
            "description": "personal_history",
            "personal_data": "personal_history",
            "personal_description": "appearance_description",
            "ideals_and_beliefs": "beliefs_ideology",
            "ideology_beliefs": "beliefs_ideology",
            "important_people": "significant_people",
            "traits": "traits_mannerisms",
            "arcane_tomes": "arcane_tomes_spells_artifacts",
            "spells_artifacts": "arcane_tomes_spells_artifacts",
            "encounters": "encounters_with_strange_entities",
        }
        for alias, target in alias_map.items():
            if alias in kwargs:
                if target not in kwargs:
                    kwargs[target] = kwargs.pop(alias)
                else:
                    kwargs.pop(alias)
        super().__init__(*args, **kwargs)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "キャラクター背景情報"
        verbose_name_plural = "キャラクター背景情報"

    def clean(self):
        """背景情報のバリデーション"""
        from django.core.exceptions import ValidationError

        # 各フィールドの文字数制限チェック
        text_fields = [
            ("appearance_description", "容姿・特徴", 1000),
            ("beliefs_ideology", "信念・信条", 1000),
            ("significant_people", "大切な人物", 1000),
            ("meaningful_locations", "意味のある場所", 1000),
            ("treasured_possessions", "愛用の品", 1000),
            ("traits_mannerisms", "特徴・癖", 1000),
            ("personal_history", "生い立ち", 2000),
            ("important_events", "重要な出来事", 2000),
            ("scars_injuries", "傷・傷跡", 1000),
            ("phobias_manias", "恐怖症・マニア", 1000),
            ("arcane_tomes_spells_artifacts", "魔道書・呪文・アーティファクト", 2000),
            ("encounters_with_strange_entities", "遭遇した超自然の存在", 2000),
            ("fellow_investigators", "仲間の探索者", 2000),
            ("notes_memo", "メモ欄", 3000),
        ]

        for field_name, field_label, max_length in text_fields:
            value = getattr(self, field_name, "")
            if value and len(value) > max_length:
                raise ValidationError({field_name: f"{field_label}は{max_length}文字以内で入力してください。"})

    def save(self, *args, **kwargs):
        """保存時にバリデーション実行"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.character_sheet.system_data.name} - 背景情報"

    @property
    def description(self):
        return self.personal_history

    @description.setter
    def description(self, value):
        self.personal_history = value

    @property
    def personal_data(self):
        return self.personal_history

    @personal_data.setter
    def personal_data(self, value):
        self.personal_history = value

    @property
    def personal_description(self):
        return self.appearance_description

    @personal_description.setter
    def personal_description(self, value):
        self.appearance_description = value

    @property
    def ideals_and_beliefs(self):
        return self.beliefs_ideology

    @ideals_and_beliefs.setter
    def ideals_and_beliefs(self, value):
        self.beliefs_ideology = value

    @property
    def ideology_beliefs(self):
        return self.beliefs_ideology

    @ideology_beliefs.setter
    def ideology_beliefs(self, value):
        self.beliefs_ideology = value

    @property
    def important_people(self):
        return self.significant_people

    @important_people.setter
    def important_people(self, value):
        self.significant_people = value

    @property
    def traits(self):
        return self.traits_mannerisms

    @traits.setter
    def traits(self, value):
        self.traits_mannerisms = value


class GrowthRecord(models.Model):
    """成長記録（セッション記録）"""

    character_sheet = models.ForeignKey(CharacterSheet, on_delete=models.CASCADE, related_name="growth_records")

    # セッション情報
    session_date = models.DateField(verbose_name="セッション日付")
    scenario_name = models.CharField(max_length=200, verbose_name="シナリオ名")
    gm_name = models.CharField(max_length=100, blank=True, verbose_name="GM名")

    # 正気度の増減
    sanity_gained = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(99)], verbose_name="正気度獲得"
    )
    sanity_lost = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(99)], verbose_name="正気度喪失"
    )

    # 経験値・報酬
    experience_gained = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="獲得経験値")
    special_rewards = models.TextField(max_length=1000, blank=True, verbose_name="特別報酬")

    # 備考
    notes = models.TextField(max_length=2000, blank=True, verbose_name="セッション備考")

    # メタデータ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        session_title = kwargs.pop("session_title", None)
        session_id = kwargs.pop("session_id", None)
        changes = kwargs.pop("changes", None)

        if session_title and "scenario_name" not in kwargs:
            kwargs["scenario_name"] = session_title
        if changes is not None and "notes" not in kwargs:
            kwargs["notes"] = json.dumps(changes, ensure_ascii=False)
        if session_id is not None and "notes" not in kwargs:
            kwargs["notes"] = f"session_id:{session_id}"

        super().__init__(*args, **kwargs)
        self._changes_cache = changes

    class Meta:
        ordering = ["-session_date", "-created_at"]
        verbose_name = "成長記録"
        verbose_name_plural = "成長記録"

    def clean(self):
        """成長記録のバリデーション"""
        from django.core.exceptions import ValidationError

        # シナリオ名必須チェック
        if not self.scenario_name or self.scenario_name.strip() == "":
            raise ValidationError({"scenario_name": "シナリオ名は必須です。"})

        # 正気度の範囲チェック
        if self.sanity_gained < 0 or self.sanity_gained > 99:
            raise ValidationError({"sanity_gained": "正気度獲得は0-99の範囲で入力してください。"})

        if self.sanity_lost < 0 or self.sanity_lost > 99:
            raise ValidationError({"sanity_lost": "正気度喪失は0-99の範囲で入力してください。"})

        # 経験値の範囲チェック
        if self.experience_gained < 0:
            raise ValidationError({"experience_gained": "経験値は0以上の値を入力してください。"})

    def save(self, *args, **kwargs):
        """保存時にバリデーション実行"""
        self.full_clean()
        super().save(*args, **kwargs)

    def calculate_net_sanity_change(self):
        """正気度の増減を計算"""
        return self.sanity_gained - self.sanity_lost

    @property
    def session_title(self):
        return self.scenario_name

    @session_title.setter
    def session_title(self, value):
        self.scenario_name = value

    @property
    def session_name(self):
        return self.scenario_name

    @session_name.setter
    def session_name(self, value):
        self.scenario_name = value

    @property
    def changes(self):
        if self._changes_cache is not None:
            return self._changes_cache
        if not self.notes:
            return None
        try:
            return json.loads(self.notes)
        except (TypeError, json.JSONDecodeError):
            return None

    @changes.setter
    def changes(self, value):
        self._changes_cache = value
        if value is not None:
            self.notes = json.dumps(value, ensure_ascii=False)

    def __str__(self):
        return f"{self.character_sheet.system_data.name} - {self.scenario_name} ({self.session_date})"


class SkillGrowthRecord(models.Model):
    """技能成長記録"""

    growth_record = models.ForeignKey(GrowthRecord, on_delete=models.CASCADE, related_name="skill_growths")

    # 技能情報
    skill_name = models.CharField(max_length=100, verbose_name="技能名")

    # 経験チェック
    had_experience_check = models.BooleanField(default=False, verbose_name="経験チェック有無")

    # 成長ロール
    growth_roll_result = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(100)], verbose_name="成長ロール結果"
    )

    # 技能値の変化
    old_value = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(999)], verbose_name="成長前技能値"
    )
    new_value = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(999)], verbose_name="成長後技能値"
    )
    growth_amount = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(999)], verbose_name="成長量"
    )

    # 備考
    notes = models.TextField(max_length=500, blank=True, verbose_name="成長備考")

    class Meta:
        ordering = ["skill_name"]
        verbose_name = "技能成長記録"
        verbose_name_plural = "技能成長記録"

    def clean(self):
        """技能成長記録のバリデーション"""
        from django.core.exceptions import ValidationError

        # 技能名必須チェック
        if not self.skill_name or self.skill_name.strip() == "":
            raise ValidationError({"skill_name": "技能名は必須です。"})

        # 技能値の範囲チェック
        if self.old_value < 0 or self.old_value > 999:
            raise ValidationError({"old_value": "成長前技能値は0-999の範囲で入力してください。"})

        if self.new_value < 0 or self.new_value > 999:
            raise ValidationError({"new_value": "成長後技能値は0-999の範囲で入力してください。"})

        # 成長量の整合性チェック
        expected_growth = self.new_value - self.old_value
        if self.growth_amount != expected_growth:
            raise ValidationError(
                {"growth_amount": f"成長量が一致しません。期待値: {expected_growth}, 実際: {self.growth_amount}"}
            )

        # 成長ロール結果の妥当性チェック
        if self.had_experience_check and self.growth_roll_result is not None:
            # 6版では現在値より大きいロールで成長成功
            if self.growth_roll_result <= self.old_value and self.growth_amount > 0:
                raise ValidationError({"growth_roll_result": "成長ロール結果が現在値以下なのに成長しています。"})

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
        return f"{self.growth_record.character_sheet.system_data.name} - {self.skill_name}: {self.old_value} → {self.new_value} ({growth_text})"


class CharacterDiceRollSetting(models.Model):
    """
    クトゥルフ神話TRPG 6版キャラクター作成用ダイスロール設定
    ユーザーごとに複数の設定を保存・管理可能
    """

    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="dice_roll_settings")
    character_sheet = models.ForeignKey(
        "accounts.CharacterSheet",
        on_delete=models.CASCADE,
        related_name="character_dice_roll_settings",
        null=True,
        blank=True,
    )
    setting_name = models.CharField(max_length=100, verbose_name="設定名")
    description = models.TextField(blank=True, verbose_name="説明")
    is_default = models.BooleanField(default=False, verbose_name="デフォルト設定")

    # STR設定
    str_dice_count = models.IntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="STRダイス数"
    )
    str_dice_sides = models.IntegerField(
        default=6, validators=[MinValueValidator(2), MaxValueValidator(100)], verbose_name="STRダイス面数"
    )
    str_bonus = models.IntegerField(
        default=0, validators=[MinValueValidator(-50), MaxValueValidator(50)], verbose_name="STRボーナス"
    )

    # CON設定
    con_dice_count = models.IntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="CONダイス数"
    )
    con_dice_sides = models.IntegerField(
        default=6, validators=[MinValueValidator(2), MaxValueValidator(100)], verbose_name="CONダイス面数"
    )
    con_bonus = models.IntegerField(
        default=0, validators=[MinValueValidator(-50), MaxValueValidator(50)], verbose_name="CONボーナス"
    )

    # POW設定
    pow_dice_count = models.IntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="POWダイス数"
    )
    pow_dice_sides = models.IntegerField(
        default=6, validators=[MinValueValidator(2), MaxValueValidator(100)], verbose_name="POWダイス面数"
    )
    pow_bonus = models.IntegerField(
        default=0, validators=[MinValueValidator(-50), MaxValueValidator(50)], verbose_name="POWボーナス"
    )

    # DEX設定
    dex_dice_count = models.IntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="DEXダイス数"
    )
    dex_dice_sides = models.IntegerField(
        default=6, validators=[MinValueValidator(2), MaxValueValidator(100)], verbose_name="DEXダイス面数"
    )
    dex_bonus = models.IntegerField(
        default=0, validators=[MinValueValidator(-50), MaxValueValidator(50)], verbose_name="DEXボーナス"
    )

    # APP設定
    app_dice_count = models.IntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="APPダイス数"
    )
    app_dice_sides = models.IntegerField(
        default=6, validators=[MinValueValidator(2), MaxValueValidator(100)], verbose_name="APPダイス面数"
    )
    app_bonus = models.IntegerField(
        default=0, validators=[MinValueValidator(-50), MaxValueValidator(50)], verbose_name="APPボーナス"
    )

    # SIZ設定
    siz_dice_count = models.IntegerField(
        default=2, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="SIZダイス数"
    )
    siz_dice_sides = models.IntegerField(
        default=6, validators=[MinValueValidator(2), MaxValueValidator(100)], verbose_name="SIZダイス面数"
    )
    siz_bonus = models.IntegerField(
        default=6, validators=[MinValueValidator(-50), MaxValueValidator(50)], verbose_name="SIZボーナス"
    )

    # INT設定
    int_dice_count = models.IntegerField(
        default=2, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="INTダイス数"
    )
    int_dice_sides = models.IntegerField(
        default=6, validators=[MinValueValidator(2), MaxValueValidator(100)], verbose_name="INTダイス面数"
    )
    int_bonus = models.IntegerField(
        default=6, validators=[MinValueValidator(-50), MaxValueValidator(50)], verbose_name="INTボーナス"
    )

    # EDU設定
    edu_dice_count = models.IntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="EDUダイス数"
    )
    edu_dice_sides = models.IntegerField(
        default=6, validators=[MinValueValidator(2), MaxValueValidator(100)], verbose_name="EDUダイス面数"
    )
    edu_bonus = models.IntegerField(
        default=3, validators=[MinValueValidator(-50), MaxValueValidator(50)], verbose_name="EDUボーナス"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "setting_name"]
        ordering = ["-is_default", "setting_name"]
        verbose_name = "ダイスロール設定"
        verbose_name_plural = "ダイスロール設定"

    def __init__(self, *args, **kwargs):
        name = kwargs.pop("name", None)
        dice_count = kwargs.pop("dice_count", None)
        dice_sides = kwargs.pop("dice_sides", None)
        provided_fields = set(kwargs.keys())
        super().__init__(*args, **kwargs)

        if name and not self.setting_name:
            self.setting_name = name

        if dice_count is not None:
            for field in (
                "str_dice_count",
                "con_dice_count",
                "pow_dice_count",
                "dex_dice_count",
                "app_dice_count",
                "siz_dice_count",
                "int_dice_count",
                "edu_dice_count",
            ):
                if field not in provided_fields:
                    setattr(self, field, dice_count)

        if dice_sides is not None:
            for field in (
                "str_dice_sides",
                "con_dice_sides",
                "pow_dice_sides",
                "dex_dice_sides",
                "app_dice_sides",
                "siz_dice_sides",
                "int_dice_sides",
                "edu_dice_sides",
            ):
                if field not in provided_fields:
                    setattr(self, field, dice_sides)

    def __str__(self):
        return f"{self.user.username} - {self.setting_name}"

    @property
    def name(self):
        return self.setting_name

    @name.setter
    def name(self, value):
        self.setting_name = value

    @property
    def dice_count(self):
        return self.str_dice_count

    @dice_count.setter
    def dice_count(self, value):
        for field in (
            "str_dice_count",
            "con_dice_count",
            "pow_dice_count",
            "dex_dice_count",
            "app_dice_count",
            "siz_dice_count",
            "int_dice_count",
            "edu_dice_count",
        ):
            setattr(self, field, value)

    @property
    def dice_sides(self):
        return self.str_dice_sides

    @dice_sides.setter
    def dice_sides(self, value):
        for field in (
            "str_dice_sides",
            "con_dice_sides",
            "pow_dice_sides",
            "dex_dice_sides",
            "app_dice_sides",
            "siz_dice_sides",
            "int_dice_sides",
            "edu_dice_sides",
        ):
            setattr(self, field, value)

    def save(self, *args, **kwargs):
        """保存時にデフォルト設定の管理"""
        if self.character_sheet and not self.user_id:
            self.user = self.character_sheet.user

        if self.is_default:
            # 他のデフォルト設定を解除
            CharacterDiceRollSetting.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        else:
            # ユーザーの最初の設定の場合、自動的にデフォルトにする
            if not CharacterDiceRollSetting.objects.filter(user=self.user).exists():
                self.is_default = True

        super().save(*args, **kwargs)

    def set_as_default(self):
        """この設定をデフォルトに設定"""
        CharacterDiceRollSetting.objects.filter(user=self.user, is_default=True).update(is_default=False)

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
            "str": self.roll_str(),
            "con": self.roll_con(),
            "pow": self.roll_pow(),
            "dex": self.roll_dex(),
            "app": self.roll_app(),
            "siz": self.roll_siz(),
            "int": self.roll_int(),
            "edu": self.roll_edu(),
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
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0,
            con_dice_count=3,
            con_dice_sides=6,
            con_bonus=0,
            pow_dice_count=3,
            pow_dice_sides=6,
            pow_bonus=0,
            dex_dice_count=3,
            dex_dice_sides=6,
            dex_bonus=0,
            app_dice_count=3,
            app_dice_sides=6,
            app_bonus=0,
            siz_dice_count=2,
            siz_dice_sides=6,
            siz_bonus=6,
            int_dice_count=2,
            int_dice_sides=6,
            int_bonus=6,
            edu_dice_count=3,
            edu_dice_sides=6,
            edu_bonus=3,
        )

    @classmethod
    def create_high_stats_6th_preset(cls, user):
        """高能力値6版プリセットを作成"""
        return cls.objects.create(
            user=user,
            setting_name="高能力値6版設定",
            description="能力値が高めになるダイス設定（4D6のベスト3など）",
            is_default=False,
            str_dice_count=4,
            str_dice_sides=6,
            str_bonus=-3,
            con_dice_count=4,
            con_dice_sides=6,
            con_bonus=-3,
            pow_dice_count=4,
            pow_dice_sides=6,
            pow_bonus=-3,
            dex_dice_count=4,
            dex_dice_sides=6,
            dex_bonus=-3,
            app_dice_count=4,
            app_dice_sides=6,
            app_bonus=-3,
            siz_dice_count=3,
            siz_dice_sides=6,
            siz_bonus=3,
            int_dice_count=3,
            int_dice_sides=6,
            int_bonus=3,
            edu_dice_count=4,
            edu_dice_sides=6,
            edu_bonus=0,
        )

    # ユーティリティメソッド
    @classmethod
    def get_user_settings(cls, user):
        """ユーザーの設定一覧を取得"""
        return cls.objects.filter(user=user).order_by("-is_default", "setting_name")

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
            edu_bonus=self.edu_bonus,
        )
        new_setting.save()
        return new_setting

    def export_to_json(self):
        """JSON形式でエクスポート"""
        data = {
            "setting_name": self.setting_name,
            "description": self.description,
            "str_dice_count": self.str_dice_count,
            "str_dice_sides": self.str_dice_sides,
            "str_bonus": self.str_bonus,
            "con_dice_count": self.con_dice_count,
            "con_dice_sides": self.con_dice_sides,
            "con_bonus": self.con_bonus,
            "pow_dice_count": self.pow_dice_count,
            "pow_dice_sides": self.pow_dice_sides,
            "pow_bonus": self.pow_bonus,
            "dex_dice_count": self.dex_dice_count,
            "dex_dice_sides": self.dex_dice_sides,
            "dex_bonus": self.dex_bonus,
            "app_dice_count": self.app_dice_count,
            "app_dice_sides": self.app_dice_sides,
            "app_bonus": self.app_bonus,
            "siz_dice_count": self.siz_dice_count,
            "siz_dice_sides": self.siz_dice_sides,
            "siz_bonus": self.siz_bonus,
            "int_dice_count": self.int_dice_count,
            "int_dice_sides": self.int_dice_sides,
            "int_bonus": self.int_bonus,
            "edu_dice_count": self.edu_dice_count,
            "edu_dice_sides": self.edu_dice_sides,
            "edu_bonus": self.edu_bonus,
            "export_version": "1.0",
            "export_timestamp": timezone.now().isoformat(),
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def import_from_json(cls, user, json_data, new_name=None):
        """JSON形式からインポート"""
        data = json.loads(json_data)

        setting_name = new_name or data.get("setting_name", "インポート設定")

        return cls.objects.create(
            user=user,
            setting_name=setting_name,
            description=data.get("description", ""),
            is_default=False,
            str_dice_count=data.get("str_dice_count", 3),
            str_dice_sides=data.get("str_dice_sides", 6),
            str_bonus=data.get("str_bonus", 0),
            con_dice_count=data.get("con_dice_count", 3),
            con_dice_sides=data.get("con_dice_sides", 6),
            con_bonus=data.get("con_bonus", 0),
            pow_dice_count=data.get("pow_dice_count", 3),
            pow_dice_sides=data.get("pow_dice_sides", 6),
            pow_bonus=data.get("pow_bonus", 0),
            dex_dice_count=data.get("dex_dice_count", 3),
            dex_dice_sides=data.get("dex_dice_sides", 6),
            dex_bonus=data.get("dex_bonus", 0),
            app_dice_count=data.get("app_dice_count", 3),
            app_dice_sides=data.get("app_dice_sides", 6),
            app_bonus=data.get("app_bonus", 0),
            siz_dice_count=data.get("siz_dice_count", 2),
            siz_dice_sides=data.get("siz_dice_sides", 6),
            siz_bonus=data.get("siz_bonus", 6),
            int_dice_count=data.get("int_dice_count", 2),
            int_dice_sides=data.get("int_dice_sides", 6),
            int_bonus=data.get("int_bonus", 6),
            edu_dice_count=data.get("edu_dice_count", 3),
            edu_dice_sides=data.get("edu_dice_sides", 6),
            edu_bonus=data.get("edu_bonus", 3),
        )


class _LegacyCharacterImage(models.Model):
    """Historical pre-0059 schema; abstract and never used at runtime."""

    character_sheet = models.ForeignKey(
        CharacterSheet, on_delete=models.CASCADE, related_name="images", verbose_name="キャラクターシート"
    )

    def upload_to(instance, filename):
        """一意なファイル名を生成"""
        import os
        import uuid

        from django.utils import timezone

        # ファイル拡張子を取得
        base_name = os.path.basename(filename)
        ext = os.path.splitext(base_name)[1]
        # 一意なファイル名を生成
        unique_filename = f"{instance.character_sheet.id}_{uuid.uuid4().hex[:8]}_{base_name}"
        # 日付ベースのパスに保存
        return f"character_images/{timezone.now().year}/{timezone.now().month:02d}/{unique_filename}"

    image = models.ImageField(upload_to=upload_to, verbose_name="画像")
    is_main = models.BooleanField(default=False, verbose_name="メイン画像")
    order = models.PositiveIntegerField(default=0, verbose_name="表示順序")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="アップロード日時")

    class Meta:
        abstract = True
        ordering = ["order", "uploaded_at"]
        verbose_name = "キャラクター画像"
        verbose_name_plural = "キャラクター画像"
        constraints = [
            models.UniqueConstraint(
                fields=["character_sheet"], condition=models.Q(is_main=True), name="unique_main_image_per_character"
            )
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        sync_edition_related_data(self)

    def delete(self, *args, **kwargs):
        delete_edition_related_data(self)
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.character_sheet.system_data.name} - 画像{self.order + 1}"


# ユーティリティクラス（長いメソッドを分離）


class CharacterSkillSystemData(models.Model):
    """Shared schema for skills stored in an edition-specific table."""

    legacy_skill_id = models.BigIntegerField(null=True, blank=True, unique=True)
    skill_name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, default="その他・独自")
    base_value = models.IntegerField(default=0)
    occupation_points = models.IntegerField(default=0)
    interest_points = models.IntegerField(default=0)
    bonus_points = models.IntegerField(default=0)
    other_points = models.IntegerField(default=0)
    current_value = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        abstract = True

    def clean(self):
        from django.core.exceptions import ValidationError

        point_fields = ("base_value", "occupation_points", "interest_points", "bonus_points", "other_points")
        errors = {field: "0以上で指定してください。" for field in point_fields if getattr(self, field) < 0}
        total = sum(getattr(self, field) for field in point_fields)
        if total > 999:
            errors["current_value"] = "技能値の合計は999を超えることはできません。"
        if self.character_sheet_id and not getattr(self, "_skip_point_validation", False):
            if self.occupation_points > self.character_sheet.calculate_occupation_points():
                errors["occupation_points"] = "職業技能ポイントが上限を超えています。"
            if self.interest_points > self.character_sheet.calculate_hobby_points():
                errors["interest_points"] = "趣味技能ポイントが上限を超えています。"
        if self.character_sheet_id:
            used_points = self.character_sheet.skills.exclude(pk=self.pk).aggregate(
                occupation=models.Sum("occupation_points"),
                interest=models.Sum("interest_points"),
            )
            if (used_points["occupation"] or 0) + self.occupation_points > self.character_sheet.calculate_occupation_points():
                errors["occupation_points"] = "職業技能ポイントの合計が上限を超えています。"
            if (used_points["interest"] or 0) + self.interest_points > self.character_sheet.calculate_hobby_points():
                errors["interest_points"] = "趣味技能ポイントの合計が上限を超えています。"
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        skip_point_validation = kwargs.pop("skip_point_validation", False)
        if skip_point_validation:
            self._skip_point_validation = True
        try:
            self.full_clean()
        finally:
            if skip_point_validation:
                delattr(self, "_skip_point_validation")
        self.current_value = sum(
            getattr(self, field) for field in ("base_value", "occupation_points", "interest_points", "bonus_points", "other_points")
        )
        result = super().save(*args, **kwargs)
        if self.skill_name == "\u30af\u30c8\u30a5\u30eb\u30d5\u795e\u8a71" and self.character_sheet_id:
            self.character_sheet.update_max_sanity()
        return result

    @classmethod
    def create_custom_skill(cls, character_sheet, skill_name, category="特殊・その他", **kwargs):
        """Create a custom skill on an edition-specific character record."""
        specialization = None
        if "（" in skill_name and "）" in skill_name:
            specialization = skill_name[skill_name.find("（") + 1 : skill_name.find("）")]
        return cls.objects.create(
            character_sheet=character_sheet,
            skill_name=skill_name,
            category=category,
            notes=kwargs.get("notes", specialization or ""),
            **{key: value for key, value in kwargs.items() if key != "notes"},
        )

    def get_occupation_recommended_skills(self):
        if self.edition == "7th":
            occupation_skills = {
                "医師": ["医学", "応急手当", "科学", "心理学", "信用", "説得", "ほかの言語", "図書館"],
                "教授": ["図書館", "母国語", "ほかの言語", "科学", "心理学", "歴史", "人類学", "説得"],
                "警察官": ["射撃（拳銃）", "近接戦闘（格闘）", "心理学", "聞き耳", "目星", "運転（自動車）", "法律", "威圧"],
                "探偵": ["目星", "聞き耳", "隠密", "手さばき", "心理学", "図書館", "法律", "説得"],
                "記者": ["目星", "聞き耳", "図書館", "心理学", "説得", "信用", "コンピューター", "運転（自動車）"],
                "考古学者": ["考古学", "歴史", "図書館", "目星", "ほかの言語", "登攀", "科学", "ナビゲート"],
            }
        else:
            occupation_skills = {
                "医師": ["医学", "応急手当", "生物学", "薬学", "心理学", "精神分析", "信用", "言いくるめ"],
                "教授": ["図書館", "母国語", "他の言語", "教育", "心理学", "歴史", "人類学", "説得"],
                "警察官": ["拳銃", "格闘技", "心理学", "聞き耳", "目星", "運転", "法律", "威圧"],
                "探偵": ["目星", "聞き耳", "隠れる", "忍び歩き", "心理学", "図書館", "法律", "説得"],
                "記者": ["目星", "聞き耳", "図書館", "心理学", "説得", "信用", "写真術", "運転"],
                "考古学者": ["考古学", "歴史", "図書館", "目星", "他の言語", "登攀", "機械修理", "ナビゲート"],
            }
        return occupation_skills.get(self.occupation, [])

    def apply_occupation_template(self):
        recommended_skills = self.get_occupation_recommended_skills()
        if self.occupation == "医師":
            self.occupation_multiplier = 25
            self.save(update_fields=["occupation_multiplier"])
        for skill_name in recommended_skills:
            self.skills.get_or_create(
                skill_name=skill_name,
                defaults={
                    "base_value": self.character_sheet.system_data.get_skill_base_value(skill_name),
                    "category": self.character_sheet.system_data.get_skill_category(skill_name),
                },
            )
        return len(recommended_skills)


class CharacterSkill6th(CharacterSkillSystemData):
    character_sheet = models.ForeignKey(CharacterSheet6th, on_delete=models.CASCADE, related_name="skills")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["character_sheet", "skill_name"], name="unique_6th_skill_name")]
        ordering = ["skill_name"]


class CharacterSkill7th(CharacterSkillSystemData):
    character_sheet = models.ForeignKey(CharacterSheet7th, on_delete=models.CASCADE, related_name="skills")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["character_sheet", "skill_name"], name="unique_7th_skill_name")]
        ordering = ["skill_name"]


class CharacterEquipmentSystemData(models.Model):
    """Shared schema for equipment stored in an edition-specific table."""

    legacy_equipment_id = models.BigIntegerField(null=True, blank=True, unique=True)
    item_type = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    skill_name = models.CharField(max_length=100, blank=True)
    damage = models.CharField(max_length=20, blank=True)
    base_range = models.CharField(max_length=20, blank=True)
    attacks_per_round = models.IntegerField(null=True, blank=True)
    ammo = models.IntegerField(null=True, blank=True)
    malfunction_number = models.IntegerField(null=True, blank=True)
    armor_points = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    quantity = models.IntegerField(default=1)
    weight = models.FloatField(null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if not self.name or not self.name.strip():
            errors["name"] = "装備名を入力してください。"
        if self.attacks_per_round is not None and self.attacks_per_round < 0:
            errors["attacks_per_round"] = "攻撃回数は0以上で入力してください。"
        if self.ammo is not None and self.ammo < 0:
            errors["ammo"] = "弾薬数は0以上で入力してください。"
        if self.malfunction_number is not None and not 1 <= self.malfunction_number <= 100:
            errors["malfunction_number"] = "故障ナンバーは1から100で入力してください。"
        if self.armor_points is not None and self.armor_points < 0:
            errors["armor_points"] = "防護点は0以上で入力してください。"
        if self.quantity is not None and self.quantity < 1:
            errors["quantity"] = "数量は0以上で指定してください。"
        if self.weight is not None and self.weight < 0:
            errors["weight"] = "重量は0以上で指定してください。"
        if errors:
            raise ValidationError(errors)


class CharacterEquipment6th(CharacterEquipmentSystemData):
    character_sheet = models.ForeignKey(CharacterSheet6th, on_delete=models.CASCADE, related_name="equipment")

    class Meta:
        ordering = ["item_type", "name"]


class CharacterEquipment7th(CharacterEquipmentSystemData):
    character_sheet = models.ForeignKey(CharacterSheet7th, on_delete=models.CASCADE, related_name="equipment")

    class Meta:
        ordering = ["item_type", "name"]


class CharacterImageSystemData(models.Model):
    """Edition-specific image metadata; the file itself remains in shared media storage."""

    legacy_image_id = models.BigIntegerField(null=True, blank=True, unique=True)
    image = models.ImageField(upload_to="character_images/")
    is_main = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class CharacterImage6th(CharacterImageSystemData):
    character_sheet = models.ForeignKey(CharacterSheet6th, on_delete=models.CASCADE, related_name="images")

    class Meta:
        ordering = ["order", "uploaded_at"]
        constraints = [models.UniqueConstraint(fields=["character_sheet"], condition=models.Q(is_main=True), name="unique_main_6th_image")]


class CharacterImage7th(CharacterImageSystemData):
    character_sheet = models.ForeignKey(CharacterSheet7th, on_delete=models.CASCADE, related_name="images")

    class Meta:
        ordering = ["order", "uploaded_at"]
        constraints = [models.UniqueConstraint(fields=["character_sheet"], condition=models.Q(is_main=True), name="unique_main_7th_image")]


def sync_edition_related_data(instance):
    """Mirror legacy related rows into the edition table during the transition."""
    registry = instance.character_sheet
    if registry.edition == "6th":
        try:
            system_data = registry.sixth_edition_data
        except CharacterSheet6th.DoesNotExist:
            system_data = CharacterSheet6th.objects.create(character_sheet=registry)
        skill_model, equipment_model, image_model = CharacterSkill6th, CharacterEquipment6th, CharacterImage6th
    elif registry.edition == "7th":
        try:
            system_data = registry.seventh_edition_data
        except CharacterSheet7th.DoesNotExist:
            system_data = CharacterSheet7th.objects.create(character_sheet=registry)
        skill_model, equipment_model, image_model = CharacterSkill7th, CharacterEquipment7th, CharacterImage7th
    else:
        return

    if isinstance(instance, _LegacyCharacterSkill):
        skill_model.objects.update_or_create(
            legacy_skill_id=instance.id,
            defaults={
                "character_sheet": system_data,
                "skill_name": instance.skill_name,
                "category": instance.category,
                "base_value": instance.base_value,
                "occupation_points": instance.occupation_points,
                "interest_points": instance.interest_points,
                "bonus_points": instance.bonus_points,
                "other_points": instance.other_points,
                "current_value": instance.current_value,
                "notes": instance.notes,
            },
        )
    elif isinstance(instance, _LegacyCharacterEquipment):
        equipment_model.objects.update_or_create(
            legacy_equipment_id=instance.id,
            defaults={
                "character_sheet": system_data,
                "item_type": instance.item_type,
                "name": instance.name,
                "skill_name": instance.skill_name,
                "damage": instance.damage,
                "base_range": instance.base_range,
                "attacks_per_round": instance.attacks_per_round,
                "ammo": instance.ammo,
                "malfunction_number": instance.malfunction_number,
                "armor_points": instance.armor_points,
                "description": instance.description,
                "quantity": instance.quantity,
                "weight": instance.weight,
            },
        )
    elif isinstance(instance, _LegacyCharacterImage):
        image_model.objects.update_or_create(
            legacy_image_id=instance.id,
            defaults={
                "character_sheet": system_data,
                "image": instance.image.name,
                "is_main": instance.is_main,
                "order": instance.order,
            },
        )


def delete_edition_related_data(instance):
    """Remove the edition copy when a compatibility row is deleted."""
    registry = instance.character_sheet
    if registry.edition == "6th":
        skill_model, equipment_model, image_model = CharacterSkill6th, CharacterEquipment6th, CharacterImage6th
    elif registry.edition == "7th":
        skill_model, equipment_model, image_model = CharacterSkill7th, CharacterEquipment7th, CharacterImage7th
    else:
        return

    if isinstance(instance, _LegacyCharacterSkill):
        skill_model.objects.filter(legacy_skill_id=instance.id).delete()
    elif isinstance(instance, _LegacyCharacterEquipment):
        equipment_model.objects.filter(legacy_equipment_id=instance.id).delete()
    elif isinstance(instance, _LegacyCharacterImage):
        image_model.objects.filter(legacy_image_id=instance.id).delete()


class CharacterVersionManager:
    """キャラクターバージョン管理ユーティリティ"""

    @staticmethod
    def create_new_version(character, version_note="", session_count=None, copy_skills=False):
        from .services.character_version_service import CharacterVersionService

        return CharacterVersionService.create_version(
            source_character=character,
            actor=character.user,
            validated_data={
                "version_note": version_note,
                "session_count": session_count or (character.system_data.session_count + 1),
            },
            copy_policy={"copy_skills": copy_skills},
        )

    @staticmethod
    def get_version_history(character):
        """バージョン履歴を取得"""
        root_data = character.system_data
        while root_data.parent_data_id:
            root_data = root_data.parent_data
        versions = [root_data.character_sheet]

        # 子バージョンを再帰的に取得
        def collect_versions(parent_data):
            children = parent_data.versions.select_related("character_sheet").order_by("version")
            for child in children:
                versions.append(child.character_sheet)
                collect_versions(child)

        collect_versions(root_data)
        return versions

    @staticmethod
    def get_latest_version(character):
        """最新バージョンを取得"""
        history = CharacterVersionManager.get_version_history(character)
        return history[-1] if history else character

    @staticmethod
    def get_root_version(character):
        """ルートバージョンを取得"""
        current = character.system_data
        while current.parent_data_id:
            current = current.parent_data
        return current.character_sheet

    @staticmethod
    def compare_versions(character1, character2):
        """バージョン間の比較"""
        differences = {}

        # 能力値の比較
        ability_diffs = {}
        for ability in [
            "str_value",
            "con_value",
            "pow_value",
            "dex_value",
            "app_value",
            "siz_value",
            "int_value",
            "edu_value",
        ]:
            val1 = getattr(character1.system_data, ability)
            val2 = getattr(character2.system_data, ability)
            if val1 != val2:
                ability_diffs[ability] = {"old": val1, "new": val2, "change": val2 - val1}

        if ability_diffs:
            differences["abilities"] = ability_diffs

        # 技能の比較
        skill_diffs = {}
        skills1 = {skill.skill_name: skill for skill in character1.system_data.skills.all()}
        skills2 = {skill.skill_name: skill for skill in character2.system_data.skills.all()}

        # 追加された技能
        added_skills = set(skills2.keys()) - set(skills1.keys())
        if added_skills:
            skill_diffs["added"] = list(added_skills)

        # 変更された技能
        changed_skills = {}
        for skill_name in set(skills1.keys()) & set(skills2.keys()):
            skill1 = skills1[skill_name]
            skill2 = skills2[skill_name]
            if skill1.current_value != skill2.current_value:
                changed_skills[skill_name] = {
                    "old": skill1.current_value,
                    "new": skill2.current_value,
                    "change": skill2.current_value - skill1.current_value,
                }

        if changed_skills:
            skill_diffs["changed"] = changed_skills

        if skill_diffs:
            differences["skills"] = skill_diffs

        return differences

    @staticmethod
    def rollback_to_version(current_character, target_version):
        from .services.character_version_service import CharacterVersionService

        return CharacterVersionService.create_version(
            source_character=target_version,
            actor=current_character.user,
            validated_data={
                "version_note": f"Rollback from version {target_version.system_data.version}",
                "session_count": current_character.system_data.session_count,
            },
            parent_character=current_character,
        )

    @staticmethod
    def get_version_statistics(character):
        """バージョン統計を取得"""
        history = CharacterVersionManager.get_version_history(character)
        return {
            "total_versions": len(history),
            "latest_version": history[-1].system_data.version if history else 1,
            "total_sessions": history[-1].system_data.session_count if history else 0,
        }


class CharacterExportManager:
    """キャラクター エクスポート管理ユーティリティ"""

    @staticmethod
    def export_version_data(character):
        registry = character
        character = registry.system_data
        """バージョンデータをエクスポート"""
        data = {
            "character_info": {
                "name": character.name,
                "edition": registry.edition,
                "age": character.age,
                "occupation": character.occupation,
                "occupation_point_method": character.occupation_point_method,
                "abilities": character.abilities,
            },
            "skills": [
                {
                    "name": skill.skill_name,
                    "category": skill.category,
                    "value": skill.current_value,
                    "base": skill.base_value,
                    "occupation": skill.occupation_points,
                    "interest": skill.interest_points,
                    "bonus": skill.bonus_points,
                    "notes": skill.notes,
                }
                for skill in character.skills.all()
            ],
            "version_info": {
                "version": character.version,
                "note": character.version_note,
                "session_count": character.session_count,
                "created_at": registry.created_at.isoformat(),
                "updated_at": registry.updated_at.isoformat(),
            },
        }

        # 6版固有データ
        if registry.edition == "6th":
            data["sixth_edition"] = {
                "idea_roll": character.idea_roll,
                "luck_roll": character.luck_roll,
                "know_roll": character.know_roll,
                "damage_bonus": character.damage_bonus,
                "mental_disorder": character.mental_disorder,
            }

        return data

    @staticmethod
    def export_ccfolia_format(character):
        registry = character
        character = registry.system_data
        """CCFOLIA形式でのデータエクスポート"""
        # 技能値からコマンド文字列を生成
        commands = []
        skills = []

        # 正気度ロール
        commands.append(f"1d100<={{SAN}} 【正気度ロール】")

        # 基本判定
        commands.append(f"CCB<={character.int_value * 5} 【アイデア】")
        commands.append(f"CCB<={character.pow_value * 5} 【幸運】")
        commands.append(f"CCB<={character.edu_value * 5} 【知識】")

        # 技能ロール
        for skill in character.skills.all():
            total_value = (
                skill.base_value
                + skill.occupation_points
                + skill.interest_points
                + skill.bonus_points
                + skill.other_points
            )
            commands.append(f"CCB<={total_value} 【{skill.skill_name}】")
            skills.append({"name": skill.skill_name, "value": total_value})

        # ダメージ判定
        commands.append("1d3+0 【ダメージ判定】")
        commands.append("1d4+0 【ダメージ判定】")
        commands.append("1d6+0 【ダメージ判定】")

        # 能力値ロール
        for ability, value in [
            ("STR", character.str_value),
            ("CON", character.con_value),
            ("POW", character.pow_value),
            ("DEX", character.dex_value),
            ("APP", character.app_value),
            ("SIZ", character.siz_value),
            ("INT", character.int_value),
            ("EDU", character.edu_value),
        ]:
            commands.append(f"CCB<={{{ability}}}*5 【{ability} × 5】")

        # CCFOLIA標準形式
        memo = f"読み仮名: {character.name_kana}" if character.name_kana else ""

        ccfolia_data = {
            "kind": "character",
            "data": {
                "name": character.name,
                "memo": memo,
                "initiative": character.dex_value,  # DEXを行動力として使用
                "externalUrl": "",  # 外部URLは空
                "iconUrl": "",  # アイコンURLは空
                "commands": "\n".join(commands),
                "status": [
                    {"label": "HP", "value": character.hit_points_current, "max": character.hit_points_max},
                    {"label": "MP", "value": character.magic_points_current, "max": character.magic_points_max},
                    {"label": "SAN", "value": character.sanity_current, "max": character.sanity_max},
                ],
                "params": [
                    {"label": "STR", "value": str(character.str_value)},
                    {"label": "CON", "value": str(character.con_value)},
                    {"label": "POW", "value": str(character.pow_value)},
                    {"label": "DEX", "value": str(character.dex_value)},
                    {"label": "APP", "value": str(character.app_value)},
                    {"label": "SIZ", "value": str(character.siz_value)},
                    {"label": "INT", "value": str(character.int_value)},
                    {"label": "EDU", "value": str(character.edu_value)},
                ],
            },
        }

        ccfolia_data.update(
            {
                "name": character.name,
                "params": [
                    {"label": "STR", "value": character.str_value},
                    {"label": "CON", "value": character.con_value},
                    {"label": "POW", "value": character.pow_value},
                    {"label": "DEX", "value": character.dex_value},
                    {"label": "APP", "value": character.app_value},
                    {"label": "SIZ", "value": character.siz_value},
                    {"label": "INT", "value": character.int_value},
                    {"label": "EDU", "value": character.edu_value},
                ],
                "skills": skills,
            }
        )

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
                export_data.append(
                    {
                        "error": True,
                        "character_id": character.id,
                        "character_name": character.system_data.name,
                        "error_message": str(e),
                    }
                )

        return export_data


class CharacterSyncManager:
    """キャラクター同期管理ユーティリティ"""

    @staticmethod
    def sync_to_ccfolia(character):
        """CCFOLIAへの同期処理"""
        system_data = character.system_data
        if not system_data.ccfolia_sync_enabled:
            return {"status": "disabled", "message": "同期が無効です"}

        try:
            # CCFOLIA形式のデータ取得
            data = CharacterExportManager.export_ccfolia_format(character)

            # 実際のAPI呼び出しは後で実装
            # ここではダミーレスポンス
            sync_result = {
                "status": "success",
                "character_id": system_data.ccfolia_character_id,
                "data_sent": data,
                "timestamp": timezone.now().isoformat(),
            }

            return sync_result

        except Exception as e:
            return {"status": "error", "message": str(e), "timestamp": timezone.now().isoformat()}

    @staticmethod
    def resolve_sync_conflict(character, conflict_data):
        """同期競合の解決"""
        # 基本的な競合解決戦略
        strategies = {
            "local_wins": "ローカルデータを優先",
            "remote_wins": "リモートデータを優先",
            "manual_merge": "手動マージが必要",
            "create_branch": "新しいブランチを作成",
        }

        # 競合フィールドに基づく解決方法の決定
        conflict_fields = conflict_data.get("conflict_fields", [])

        if "abilities" in conflict_fields:
            strategy = "manual_merge"
        elif "skills" in conflict_fields:
            strategy = "local_wins"  # 技能成長はローカル優先
        else:
            strategy = "remote_wins"

        return {
            "resolution_strategy": strategy,
            "strategy_description": strategies.get(strategy, "不明"),
            "conflict_fields": conflict_fields,
            "recommended_action": f"{strategy}を実行してください",
        }
