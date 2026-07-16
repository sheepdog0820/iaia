"""
Character sheet management views
"""

import json
import logging
import math
import re
import time
from collections.abc import Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..character_detail_context import build_character_detail_context
from ..character_image_limits import (
    character_image_limit_error_message,
    collect_character_image_uploads,
    get_character_image_limit,
)
from ..character_models import CharacterEquipment6th, CharacterSkill6th, GrowthRecord
from ..serializers import CharacterSheetSerializer, CharacterVersionCreateSerializer, GrowthRecordSerializer
from ..services.character_version_service import CharacterVersionService
from .base_views import BaseViewSet, PermissionMixin
from .common_imports import *
from .mixins import CharacterNestedResourceMixin, CharacterSheetAccessMixin, ErrorHandlerMixin

logger = logging.getLogger(__name__)

COC6_BASIC_SKILL_NAMES = [
    "回避",
    "キック",
    "組み付き",
    "こぶし（パンチ）",
    "頭突き",
    "投擲",
    "マーシャルアーツ",
    "拳銃",
    "サブマシンガン",
    "ショットガン",
    "マシンガン",
    "ライフル",
    "応急手当",
    "鍵開け",
    "隠す",
    "隠れる",
    "聞き耳",
    "忍び歩き",
    "写真術",
    "精神分析",
    "追跡",
    "登攀",
    "図書館",
    "目星",
    "運転",
    "機械修理",
    "重機械操作",
    "乗馬",
    "水泳",
    "製作",
    "操縦",
    "跳躍",
    "電気修理",
    "ナビゲート",
    "変装",
    "言いくるめ",
    "信用",
    "説得",
    "値切り",
    "他の言語",
    "母国語",
    "医学",
    "オカルト",
    "化学",
    "クトゥルフ神話",
    "芸術",
    "経理",
    "考古学",
    "コンピューター",
    "心理学",
    "人類学",
    "生物学",
    "地質学",
    "電子工学",
    "天文学",
    "博物学",
    "物理学",
    "法律",
    "薬学",
    "歴史",
]

COC7_BASIC_SKILL_NAMES = [
    "回避",
    "近接戦闘（格闘）",
    "投擲",
    "射撃（拳銃）",
    "射撃（ライフル／ショットガン）",
    "応急手当",
    "鍵開け",
    "鑑定",
    "隠密",
    "聞き耳",
    "精神分析",
    "追跡",
    "登攀",
    "図書館",
    "目星",
    "手さばき",
    "運転（自動車）",
    "機械修理",
    "重機械操作",
    "乗馬",
    "水泳",
    "芸術／製作",
    "操縦",
    "跳躍",
    "電気修理",
    "電子工学",
    "ナビゲート",
    "サバイバル",
    "変装",
    "言いくるめ",
    "魅惑",
    "信用",
    "説得",
    "威圧",
    "ほかの言語",
    "母国語",
    "医学",
    "オカルト",
    "科学",
    "クトゥルフ神話",
    "経理",
    "考古学",
    "コンピューター",
    "心理学",
    "人類学",
    "自然",
    "法律",
    "歴史",
]


class CharacterSheetViewSet(CharacterSheetAccessMixin, PermissionMixin, viewsets.ModelViewSet):
    """Character sheet management ViewSet"""

    queryset = CharacterSheet.objects.none()
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"\d+"

    class OptionalPagination(PageNumberPagination):
        page_size = None
        page_size_query_param = "page_size"
        max_page_size = 100

    pagination_class = OptionalPagination

    def get_queryset(self):
        """Get user's character sheets only"""
        queryset = CharacterSheet.objects.select_related(
            "sixth_edition_data", "seventh_edition_data", "user"
        ).prefetch_related(
            "sixth_edition_data__skills", "sixth_edition_data__equipment",
            "seventh_edition_data__skills", "seventh_edition_data__equipment",
        ).order_by("-updated_at")

        if self.action in ["list", "active", "by_edition"]:
            return queryset.filter(user=self.request.user)

        return queryset

    def get_serializer_class(self):
        """Action-based serializer selection"""
        if self.action == "list":
            return CharacterSheetListSerializer
        elif self.action == "create":
            return CharacterSheetCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CharacterSheetUpdateSerializer
        else:
            return CharacterSheetSerializer

    # get_object is now handled by CharacterSheetAccessMixin

    @action(detail=False, methods=["get"])
    def by_edition(self, request):
        """Get character sheets by edition"""
        edition = request.query_params.get("edition")
        supported_editions = {"6th", "7th"}
        if not edition or edition not in supported_editions:
            return Response({"error": "edition parameter is required (6th or 7th)"}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset().filter(edition=edition)
        serializer = CharacterSheetListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get active character sheets"""
        queryset = self.get_queryset().filter(
            Q(sixth_edition_data__is_active=True) | Q(seventh_edition_data__is_active=True)
        )
        serializer = CharacterSheetListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def create_version(self, request, pk=None):
        """Create a new version through the single versioning service."""
        source_character = self.get_object()
        serializer = CharacterVersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_sheet = CharacterVersionService.create_version(
            source_character=source_character,
            actor=request.user,
            validated_data=serializer.validated_data,
        )
        response_serializer = CharacterSheetSerializer(new_sheet, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        """Get character sheet version history"""
        sheet = self.get_object()

        detail = sheet.system_data
        root = detail
        while root.parent_data_id:
            root = root.parent_data

        def belongs_to_root(candidate):
            while candidate.parent_data_id:
                candidate = candidate.parent_data
            return candidate.pk == root.pk

        all_versions = [
            candidate.character_sheet
            for candidate in detail.__class__.objects.select_related("character_sheet", "parent_data").order_by("version")
            if belongs_to_root(candidate)
        ]

        serializer = CharacterSheetListSerializer(all_versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle character sheet active status"""
        sheet = self.get_object()
        detail = sheet.system_data
        detail.is_active = not detail.is_active
        detail.save(update_fields=["is_active"])

        serializer = CharacterSheetSerializer(sheet)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="skill-points-summary", url_name="skill-points-summary")
    def skill_points_summary(self, request, pk=None):
        """Get skill points summary for a character"""
        sheet = self.get_object()

        occupation_total = sheet.system_data.calculate_occupation_points()
        hobby_total = sheet.system_data.calculate_hobby_points()

        # Calculate used points
        skills = sheet.system_data.skills.all()
        occupation_used = sum(skill.occupation_points for skill in skills)
        hobby_used = sum(skill.interest_points for skill in skills)

        summary = {
            "occupation_points": {
                "total": occupation_total,
                "used": occupation_used,
                "remaining": occupation_total - occupation_used,
            },
            "hobby_points": {"total": hobby_total, "used": hobby_used, "remaining": hobby_total - hobby_used},
            "total_occupation_points": occupation_total,
            "used_occupation_points": occupation_used,
            "remaining_occupation_points": occupation_total - occupation_used,
            "total_hobby_points": hobby_total,
            "used_hobby_points": hobby_used,
            "remaining_hobby_points": hobby_total - hobby_used,
            "skills": [
                {
                    "name": skill.skill_name,
                    "base_value": skill.base_value,
                    "occupation_points": skill.occupation_points,
                    "interest_points": skill.interest_points,
                    "other_points": skill.other_points,
                    "current_value": skill.current_value,
                }
                for skill in skills
            ],
        }

        return Response(summary)

    @action(detail=True, methods=["get"], url_path="ccfolia_json")
    def ccfolia_json(self, request, pk=None):
        """Export to CCFOLIA format JSON"""
        sheet = self.get_object()

        # Use model's export_ccfolia_format method
        ccfolia_data = sheet.export_ccfolia_format()

        return Response(ccfolia_data)

    @action(detail=False, methods=["post"], url_path="import_ccfolia_json")
    def import_ccfolia_json(self, request):
        """Import a character sheet from CCFOLIA format JSON"""
        if not getattr(request.user, "has_premium_access", False):
            return Response(
                {"detail": "CCFOLIAインポートはプレミアム機能です。"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            ccfolia_payload = self._extract_ccfolia_payload(request.data)
            parsed = self._parse_ccfolia_character(ccfolia_payload)
        except DRFValidationError:
            raise
        except Exception as exc:
            raise DRFValidationError({"ccfolia": f"Invalid payload: {exc}"}) from exc

        raw_age = request.data.get("age")
        if raw_age in (None, "", "null", "None"):
            age = None
        else:
            try:
                age = int(raw_age)
            except (TypeError, ValueError) as exc:
                raise DRFValidationError({"age": "age must be an integer"}) from exc
            if age < 15 or age > 90:
                raise DRFValidationError({"age": "age must be between 15 and 90"})

        user = request.user

        def optional_text(field_name):
            return str(request.data.get(field_name) or "").strip()

        external_url = parsed.get("external_url") or ""
        icon_url = parsed.get("icon_url") or ""
        import_notes = []
        if external_url:
            import_notes.append(f"外部URL: {external_url}")
        if icon_url:
            import_notes.append(f"アイコンURL: {icon_url}")
        notes = "\n".join(import_notes)

        name = parsed["name"]
        edition = self._parse_import_edition(request.data, ccfolia_payload)
        abilities = parsed["abilities"]
        status_values = parsed.get("status") or {}
        skill_totals = parsed.get("skills") or {}

        hp_value = status_values.get("HP", {}).get("value")
        hp_max = status_values.get("HP", {}).get("max")
        mp_value = status_values.get("MP", {}).get("value")
        mp_max = status_values.get("MP", {}).get("max")
        san_value = status_values.get("SAN", {}).get("value")
        san_start = status_values.get("SAN", {}).get("max")

        if edition == "7th":
            computed_hp_max = (abilities["CON"] + abilities["SIZ"]) // 10
            computed_mp_max = abilities["POW"] // 5
            computed_san_start = abilities["POW"]
        else:
            computed_hp_max = math.ceil((abilities["CON"] + abilities["SIZ"]) / 2)
            computed_mp_max = abilities["POW"]
            computed_san_start = abilities["POW"] * 5

        hit_points_max = int(hp_max) if hp_max is not None else computed_hp_max
        hit_points_current = int(hp_value) if hp_value is not None else hit_points_max
        magic_points_max = int(mp_max) if mp_max is not None else computed_mp_max
        magic_points_current = int(mp_value) if mp_value is not None else magic_points_max
        sanity_starting = int(san_start) if san_start is not None else computed_san_start
        sanity_current = int(san_value) if san_value is not None else sanity_starting

        mythos = int(skill_totals.get("クトゥルフ神話", 0) or 0)
        sanity_max = max(0, 99 - mythos)

        detail_model = CharacterSheet6th if edition == "6th" else CharacterSheet7th
        existing_details = [sheet.system_data for sheet in CharacterSheet.objects.by_system_name(name, user=user, edition=edition)]
        version = max((detail.version for detail in existing_details), default=0) + 1
        parent_data = min(existing_details, key=lambda detail: detail.version) if existing_details else None

        with transaction.atomic():
            character_sheet = CharacterSheet.objects.create(user=user, edition=edition)
            detail = detail_model.objects.create(
                character_sheet=character_sheet,
                name=name,
                player_name="",
                age=age,
                gender=optional_text("gender"),
                occupation=optional_text("occupation"),
                birthplace=optional_text("birthplace"),
                residence=optional_text("residence"),
                recommended_skills=[],
                str_value=abilities["STR"],
                con_value=abilities["CON"],
                pow_value=abilities["POW"],
                dex_value=abilities["DEX"],
                app_value=abilities["APP"],
                siz_value=abilities["SIZ"],
                int_value=abilities["INT"],
                edu_value=abilities["EDU"],
                hit_points_max=hit_points_max,
                hit_points_current=hit_points_current,
                magic_points_max=magic_points_max,
                magic_points_current=magic_points_current,
                sanity_starting=sanity_starting,
                sanity_max=sanity_max,
                sanity_current=sanity_current,
                notes=notes,
                version=version,
                parent_data=parent_data,
            )

            for skill_name, total_value in skill_totals.items():
                if not skill_name:
                    continue
                try:
                    total_value = int(total_value)
                except (TypeError, ValueError):
                    continue

                normalized = self._normalize_skill_name(skill_name)
                base_name = self._base_skill_name(normalized)

                if edition == "7th":
                    inferred_base = (detail.dex_value or 0) // 2 if base_name == "回避" else 0
                else:
                    inferred_base = min(25, total_value)
                if edition == "7th" and base_name in {"目星", "図書館"}:
                    inferred_base = 25 if base_name == "目星" else 20
                base_value = inferred_base if inferred_base <= total_value else total_value
                other_points = max(total_value - base_value, 0)

                category = detail.get_skill_category(base_name)
                skill = detail.skills.model(
                    character_sheet=detail,
                    skill_name=normalized,
                    category=category,
                    base_value=base_value,
                    occupation_points=0,
                    interest_points=0,
                    bonus_points=0,
                    other_points=other_points,
                )
                try:
                    skill.save(skip_point_validation=True)
                except IntegrityError:
                    continue

        response_serializer = CharacterSheetSerializer(character_sheet, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _extract_ccfolia_payload(request_data):
        # Prefer explicit "ccfolia" key
        payload = request_data.get("ccfolia") if isinstance(request_data, Mapping) else None
        if payload is None and isinstance(request_data, Mapping) and "ccfolia_json" in request_data:
            payload = request_data.get("ccfolia_json")
        if payload is None and isinstance(request_data, Mapping) and "kind" in request_data and "data" in request_data:
            payload = {key: request_data.get(key) for key in request_data.keys()}

        if payload is None:
            raise DRFValidationError({"ccfolia": "ccfolia is required"})

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise DRFValidationError({"ccfolia": "ccfolia must be valid JSON"}) from exc

        if not isinstance(payload, dict):
            raise DRFValidationError({"ccfolia": "ccfolia must be an object"})

        return payload

    @staticmethod
    def _parse_import_edition(request_data, payload):
        candidates = []
        if isinstance(request_data, Mapping):
            candidates.extend(
                [
                    request_data.get("edition"),
                    request_data.get("sourceVersion"),
                    request_data.get("source_version"),
                    request_data.get("gameSystem"),
                ]
            )
        if isinstance(payload, Mapping):
            candidates.extend(
                [
                    payload.get("edition"),
                    payload.get("sourceVersion"),
                    payload.get("source_version"),
                    payload.get("gameSystem"),
                ]
            )
            data = payload.get("data")
            if isinstance(data, Mapping):
                candidates.extend(
                    [
                        data.get("edition"),
                        data.get("sourceVersion"),
                        data.get("source_version"),
                        data.get("gameSystem"),
                    ]
                )

        for candidate in candidates:
            normalized = CharacterSheetViewSet._normalize_edition_value(candidate)
            if normalized:
                return normalized
        return "6th"

    @staticmethod
    def _normalize_edition_value(value):
        if value is None:
            return None
        text = str(value).strip().lower()
        if not text:
            return None
        text = text.replace("_", "").replace("-", "").replace(" ", "")
        if text in {"7", "7th", "coc7", "coc7th"} or "7版" in text:
            return "7th"
        if text in {"6", "6th", "coc6", "coc6th"} or "6版" in text:
            return "6th"
        return None

    @staticmethod
    def _parse_ccfolia_character(payload):
        if payload.get("kind") and payload.get("kind") != "character":
            raise DRFValidationError({"ccfolia": 'kind must be "character"'})

        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if not isinstance(data, dict):
            raise DRFValidationError({"ccfolia": "data must be an object"})

        name = (data.get("name") or "").strip()
        if not name:
            raise DRFValidationError({"ccfolia": "data.name is required"})

        params = data.get("params")
        if not isinstance(params, list):
            params = payload.get("params")
        abilities = CharacterSheetViewSet._parse_ccfolia_params(params)

        status_list = data.get("status")
        status_values = CharacterSheetViewSet._parse_ccfolia_status(status_list)

        skills = CharacterSheetViewSet._extract_skill_totals(payload, data)

        return {
            "name": name,
            "external_url": (data.get("externalUrl") or "").strip(),
            "icon_url": (data.get("iconUrl") or "").strip(),
            "abilities": abilities,
            "status": status_values,
            "skills": skills,
        }

    @staticmethod
    def _parse_ccfolia_params(params):
        if not isinstance(params, list):
            raise DRFValidationError({"ccfolia": "data.params is required"})

        wanted = {"STR", "CON", "POW", "DEX", "APP", "SIZ", "INT", "EDU"}
        values = {}

        for item in params:
            if not isinstance(item, dict):
                continue
            label = (item.get("label") or "").strip().upper()
            if label not in wanted:
                continue
            raw_value = item.get("value")
            try:
                parsed = int(raw_value)
            except (TypeError, ValueError):
                raise DRFValidationError({"ccfolia": f"Invalid ability value for {label}"}) from None
            if parsed < 1 or parsed > 999:
                raise DRFValidationError({"ccfolia": f"Ability {label} must be between 1 and 999"})
            values[label] = parsed

        missing = sorted(wanted - set(values.keys()))
        if missing:
            raise DRFValidationError({"ccfolia": f'Missing abilities: {", ".join(missing)}'})

        return values

    @staticmethod
    def _parse_ccfolia_status(status_list):
        if status_list is None:
            return {}
        if not isinstance(status_list, list):
            raise DRFValidationError({"ccfolia": "data.status must be an array"})

        allowed = {"HP", "MP", "SAN"}
        result = {}

        for item in status_list:
            if not isinstance(item, dict):
                continue
            label = (item.get("label") or "").strip().upper()
            if label not in allowed:
                continue
            raw_value = item.get("value")
            raw_max = item.get("max")

            entry = {}
            if raw_value is not None:
                try:
                    entry["value"] = int(raw_value)
                except (TypeError, ValueError):
                    raise DRFValidationError({"ccfolia": f"Invalid status value for {label}"}) from None
            if raw_max is not None:
                try:
                    entry["max"] = int(raw_max)
                except (TypeError, ValueError):
                    raise DRFValidationError({"ccfolia": f"Invalid status max for {label}"}) from None

            result[label] = entry

        return result

    @staticmethod
    def _extract_skill_totals(payload, data):
        # Prefer explicit skills list (Tableno export extension)
        skills = payload.get("skills")
        if isinstance(skills, list):
            totals = {}
            for skill in skills:
                if not isinstance(skill, dict):
                    continue
                name = (skill.get("name") or "").strip()
                if not name:
                    continue
                try:
                    totals[name] = int(skill.get("value"))
                except (TypeError, ValueError):
                    continue
            return totals

        commands = data.get("commands")
        if not isinstance(commands, str) or not commands.strip():
            return {}

        ccb_re = re.compile(r"^CCB?\s*<=\s*(\d+)\s*【(.+?)】", re.IGNORECASE)
        ignore = {"正気度ロール", "アイデア", "幸運", "知識"}
        ability_labels = {"STR", "CON", "POW", "DEX", "APP", "SIZ", "INT", "EDU"}
        totals = {}

        for raw_line in commands.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = ccb_re.match(line)
            if not match:
                continue
            value = int(match.group(1))
            label = match.group(2).strip()
            if not label or label in ignore:
                continue
            if label.upper() in ability_labels:
                continue
            if "×" in label or re.search(r"(?i)x\s*\d", label):
                continue

            existing = totals.get(label)
            if existing is None or value > existing:
                totals[label] = value

        return totals

    @staticmethod
    def _normalize_skill_name(skill_name):
        return (skill_name or "").strip()

    @staticmethod
    def _base_skill_name(skill_name):
        name = (skill_name or "").strip()
        if "（" in name and "）" in name:
            return name.split("（", 1)[0].strip()
        return name

    @action(detail=True, methods=["post"], url_path="allocate-skill-points")
    def allocate_skill_points(self, request, pk=None):
        """Allocate skill points to a single skill"""
        sheet = self.get_object()

        skill_name = request.data.get("skill_name")
        occupation_points = request.data.get("occupation_points", 0)
        interest_points = request.data.get("interest_points", 0)

        if not skill_name:
            return Response({"error": "skill_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create skill
        detail = sheet.system_data
        skill, created = detail.skills.get_or_create(
            skill_name=skill_name, defaults={"base_value": 0}
        )

        # Update points
        skill.occupation_points = occupation_points
        skill.interest_points = interest_points
        skill.save()

        return Response(
            {
                "skill": {
                    "name": skill.skill_name,
                    "base_value": skill.base_value,
                    "occupation_points": skill.occupation_points,
                    "interest_points": skill.interest_points,
                    "current_value": skill.current_value,
                }
            }
        )

    @action(detail=True, methods=["post"], url_path="batch-allocate-skill-points")
    def batch_allocate_skill_points(self, request, pk=None):
        """Batch allocate skill points to multiple skills"""
        sheet = self.get_object()

        skills_data = request.data.get("skills", [])
        if not skills_data:
            return Response({"error": "skills array is required"}, status=status.HTTP_400_BAD_REQUEST)

        updated_skills = []
        detail = sheet.system_data
        for skill_data in skills_data:
            skill_name = skill_data.get("skill_name")
            if not skill_name:
                continue

            skill, created = detail.skills.get_or_create(
                skill_name=skill_name, defaults={"base_value": skill_data.get("base_value", 0)}
            )

            # Update points
            skill.occupation_points = skill_data.get("occupation_points", 0)
            skill.interest_points = skill_data.get("interest_points", 0)
            skill.other_points = skill_data.get("other_points", 0)
            skill.save()

            updated_skills.append(
                {
                    "name": skill.skill_name,
                    "base_value": skill.base_value,
                    "occupation_points": skill.occupation_points,
                    "interest_points": skill.interest_points,
                    "other_points": skill.other_points,
                    "current_value": skill.current_value,
                }
            )

        return Response({"skills": updated_skills})

    @action(detail=True, methods=["get"], url_path="combat-summary")
    def combat_summary(self, request, pk=None):
        """Get combat summary including weapons and damage bonus"""
        sheet = self.get_object()

        # Get damage bonus
        damage_bonus = sheet.damage_bonus if hasattr(sheet, "damage_bonus") else "0"

        # Get weapons
        weapons = []
        for equipment in sheet.system_data.equipment.filter(item_type="weapon"):
            weapons.append(
                {
                    "name": equipment.name,
                    "skill_name": equipment.skill_name,
                    "damage": equipment.damage,
                    "base_range": equipment.base_range,
                    "attacks_per_round": equipment.attacks_per_round,
                    "ammo": equipment.ammo,
                    "malfunction_number": equipment.malfunction_number,
                }
            )

        # Get combat skills
        combat_skills = []
        for skill in sheet.system_data.skills.filter(
            skill_name__in=["拳銃", "ライフル", "ショットガン", "こぶし", "キック", "ナイフ", "回避"]
        ):
            combat_skills.append({"name": skill.skill_name, "current_value": skill.current_value})

        return Response(
            {
                "damage_bonus": damage_bonus,
                "weapons": weapons,
                "combat_skills": combat_skills,
                "hp": {
                    "current": sheet.system_data.hit_points_current,
                    "max": sheet.system_data.hit_points_max,
                },
            }
        )

    @action(detail=True, methods=["get"], url_path="growth-summary")
    def growth_summary(self, request, pk=None):
        """Get character growth summary"""
        sheet = self.get_object()

        # Get growth records
        growth_records = []
        if hasattr(sheet, "growth_records"):
            for record in sheet.growth_records.all().order_by("-session_date"):
                growth_records.append(
                    {
                        "session_date": record.session_date.isoformat(),
                        "session_name": record.session_name,
                        "changes": record.changes,
                        "notes": record.notes,
                    }
                )

        # Get version history
        versions = [
            {
                "version": version.system_data.version,
                "created_at": version.created_at.isoformat(),
                "session_count": version.system_data.session_count,
            }
            for version in sheet.get_version_history()
        ]

        return Response(
            {"session_count": sheet.system_data.session_count, "growth_records": growth_records, "version_history": versions}
        )

    @action(detail=True, methods=["post"])
    def background(self, request, pk=None):
        """Add or update character background"""
        sheet = self.get_object()

        # Get or create background
        background, created = CharacterBackground.objects.get_or_create(character_sheet=sheet)

        # Update fields
        for field in [
            "personal_description",
            "ideals_and_beliefs",
            "significant_people",
            "meaningful_locations",
            "treasured_possessions",
            "traits",
            "scars_injuries",
            "phobias_manias",
            "arcane_tomes_spells_artifacts",
            "encounters_with_strange_entities",
            "notes_memo",
        ]:
            if field in request.data:
                setattr(background, field, request.data[field])

        background.save()

        return Response(
            {
                "personal_description": background.personal_description,
                "ideals_and_beliefs": background.ideals_and_beliefs,
                "significant_people": background.significant_people,
                "meaningful_locations": background.meaningful_locations,
                "treasured_possessions": background.treasured_possessions,
                "traits": background.traits,
                "scars_injuries": background.scars_injuries,
                "phobias_manias": background.phobias_manias,
                "arcane_tomes_spells_artifacts": background.arcane_tomes_spells_artifacts,
                "encounters_with_strange_entities": background.encounters_with_strange_entities,
                "notes_memo": background.notes_memo,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def export_version_data(self, request, pk=None):
        """Export version data"""
        sheet = self.get_object()

        # Version data including history
        version_data = {
            "current_version": {
                "id": sheet.id,
                "version": sheet.system_data.version,
                "created_at": sheet.created_at.isoformat(),
                "updated_at": sheet.updated_at.isoformat(),
                "data": CharacterSheetSerializer(sheet).data,
            },
            "version_history": [],
        }

        for version in sheet.get_version_history():
            version_info = {
                "id": version.id,
                "version": version.system_data.version,
                "created_at": version.created_at.isoformat(),
                "updated_at": version.updated_at.isoformat(),
                "is_current": version.id == sheet.id,
            }
            version_data["version_history"].append(version_info)

        return Response(version_data)

    @staticmethod
    def _parse_occupation_point_method(request_data, edition):
        """リクエストの職業技能ポイント方式を版別に検証する"""
        occupation_point_method = (request_data.get("occupation_point_method") or "").strip()
        if occupation_point_method and occupation_point_method not in CharacterSheet.valid_occupation_point_methods_for_edition(
            edition
        ):
            raise ValueError("occupation_point_method is not valid for this edition")
        return occupation_point_method

    @action(detail=False, methods=["post"])
    def create_6th_edition(self, request):
        """6th edition character creation endpoint (Cthulhu Mythos TRPG exclusive)"""

        def parse_int(value, field_name, *, min_value=None, max_value=None, default=None):
            if value is None or value == "":
                if default is not None:
                    return default
                raise ValueError(f"{field_name} is required")

            try:
                int_value = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field_name} must be an integer") from exc

            if min_value is not None and int_value < min_value:
                raise ValueError(f"{field_name} must be between {min_value} and {max_value}")
            if max_value is not None and int_value > max_value:
                raise ValueError(f"{field_name} must be between {min_value} and {max_value}")

            return int_value

        def parse_json_list(value, field_name):
            if value is None or value == "":
                return []
            if isinstance(value, list):
                return value
            if not isinstance(value, str):
                raise ValueError(f"{field_name} must be valid JSON")
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{field_name} must be valid JSON") from exc
            if not isinstance(parsed, list):
                raise ValueError(f"{field_name} must be a JSON array")
            return parsed

        # Data validation
        required_fields = [
            "name",
            "str_value",
            "con_value",
            "pow_value",
            "dex_value",
            "app_value",
            "siz_value",
            "int_value",
            "edu_value",
        ]

        for field in required_fields:
            if field not in request.data:
                return Response({"error": f"{field} is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Remove ability value range restrictions as per specification
        # Users should be able to input any value (1-999)
        ability_fields = [
            "str_value",
            "con_value",
            "pow_value",
            "dex_value",
            "app_value",
            "siz_value",
            "int_value",
            "edu_value",
        ]
        parsed_abilities = {}
        for field in ability_fields:
            try:
                parsed_abilities[field] = parse_int(request.data.get(field), field, min_value=1, max_value=999)
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recommended_skills = parse_json_list(request.data.get("recommended_skills", []), "recommended_skills")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            occupation_skills = parse_json_list(request.data.get("occupation_skills", []), "occupation_skills")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            occupation_point_method = self._parse_occupation_point_method(request.data, "6th")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        scenario_id_raw = request.data.get("scenario_id")
        scenario_title = (request.data.get("scenario_title") or "").strip()
        scenario_game_system = (request.data.get("game_system") or "").strip()
        scenario_obj = None
        if scenario_id_raw not in (None, ""):
            try:
                scenario_id = int(scenario_id_raw)
            except (TypeError, ValueError):
                return Response({"error": "scenario_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
            if scenario_id <= 0:
                return Response({"error": "scenario_id must be a positive integer"}, status=status.HTTP_400_BAD_REQUEST)
            from scenarios.models import Scenario

            scenario_obj = Scenario.objects.filter(id=scenario_id).first()

        try:
            raw_skills_data = parse_json_list(request.data.get("skills", []), "skills")
            skills_data = []
            for skill_data in raw_skills_data:
                if not isinstance(skill_data, dict) or "skill_name" not in skill_data:
                    continue

                base_value = parse_int(
                    skill_data.get("base_value", 0), "base_value", min_value=0, max_value=999, default=0
                )
                occupation_points = parse_int(
                    skill_data.get("occupation_points", 0), "occupation_points", min_value=0, max_value=999, default=0
                )
                interest_points = parse_int(
                    skill_data.get("interest_points", 0), "interest_points", min_value=0, max_value=999, default=0
                )
                other_points = parse_int(
                    skill_data.get("other_points", 0), "other_points", min_value=0, max_value=999, default=0
                )
                current_value = parse_int(
                    skill_data.get("current_value", base_value + occupation_points + interest_points + other_points),
                    "current_value",
                    min_value=0,
                    max_value=999,
                    default=base_value + occupation_points + interest_points + other_points,
                )
                skills_data.append(
                    {
                        "skill_name": skill_data["skill_name"],
                        "base_value": base_value,
                        "occupation_points": occupation_points,
                        "interest_points": interest_points,
                        "other_points": other_points,
                        "current_value": current_value,
                    }
                )

            raw_equipment_data = parse_json_list(request.data.get("equipment", []), "equipment")
            equipment_data = []
            for equipment in raw_equipment_data:
                if not isinstance(equipment, dict) or "name" not in equipment:
                    continue
                equipment_data.append(equipment)

            image_files = collect_character_image_uploads(request.FILES)
            image_limit = get_character_image_limit(request.user)
            if len(image_files) > image_limit:
                return Response(
                    {"error": character_image_limit_error_message(image_limit)}, status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                character_data = {
                    "user": request.user,
                    "edition": "6th",
                    "name": request.data["name"],
                    "player_name": request.data.get("player_name", request.user.nickname or request.user.username),
                    "age": parse_int(request.data.get("age", 25), "age", min_value=0, max_value=999, default=25),
                    "gender": request.data.get("gender", ""),
                    "occupation": request.data.get("occupation", ""),
                    "occupation_point_method": occupation_point_method,
                    "birthplace": request.data.get("birthplace", ""),
                    "residence": request.data.get("residence", ""),
                    "recommended_skills": recommended_skills,
                    "occupation_skills": occupation_skills,
                    "str_value": parsed_abilities["str_value"],
                    "con_value": parsed_abilities["con_value"],
                    "pow_value": parsed_abilities["pow_value"],
                    "dex_value": parsed_abilities["dex_value"],
                    "app_value": parsed_abilities["app_value"],
                    "siz_value": parsed_abilities["siz_value"],
                    "int_value": parsed_abilities["int_value"],
                    "edu_value": parsed_abilities["edu_value"],
                    "notes": request.data.get("notes", ""),
                    "is_active": True,
                }
                if scenario_obj:
                    character_data["source_scenario"] = scenario_obj
                    character_data["source_scenario_title"] = scenario_obj.title
                    character_data["source_scenario_game_system"] = scenario_obj.game_system
                else:
                    if scenario_title:
                        character_data["source_scenario_title"] = scenario_title
                    if scenario_game_system:
                        character_data["source_scenario_game_system"] = scenario_game_system

                if "character_image" in request.FILES:
                    character_data["character_image"] = request.FILES["character_image"]

                character_data.pop("user")
                character_data.pop("edition")
                character_sheet = CharacterSheet.objects.create(user=request.user, edition="6th")
                character_data["mental_disorder"] = request.data.get("mental_disorder", "")
                detail = CharacterSheet6th(character_sheet=character_sheet, **character_data)
                stats = detail.calculate_derived_stats()
                detail.hit_points_max = detail.hit_points_current = stats["hit_points_max"]
                detail.magic_points_max = detail.magic_points_current = stats["magic_points_max"]
                detail.sanity_starting = detail.sanity_current = stats["sanity_starting"]
                detail.sanity_max = stats["sanity_max"]
                detail.save()

                for skill_data in skills_data:
                    detail.skills.model.objects.create(character_sheet=detail, **skill_data)

                for equipment in equipment_data:
                    detail.equipment.model.objects.create(
                        character_sheet=detail,
                        item_type=equipment.get("item_type", "item"),
                        name=equipment["name"],
                        skill_name=equipment.get("skill_name", ""),
                        damage=equipment.get("damage", ""),
                        base_range=equipment.get("base_range", ""),
                        attacks_per_round=equipment.get("attacks_per_round"),
                        ammo=equipment.get("ammo"),
                        malfunction_number=equipment.get("malfunction_number"),
                        armor_points=equipment.get("armor_points"),
                        description=equipment.get("description", ""),
                        quantity=equipment.get("quantity", 1),
                        weight=equipment.get("weight"),
                    )

                for index, image_file in enumerate(image_files):
                    detail.images.model.objects.create(
                        character_sheet=detail, image=image_file, is_main=(index == 0), order=index
                    )

            response_serializer = CharacterSheetSerializer(character_sheet)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except (ValueError, DjangoValidationError) as exc:
            if isinstance(exc, DjangoValidationError) and hasattr(exc, "message_dict"):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error while creating 6th edition character: user_id=%s", request.user.id)
            return Response(
                {"error": "キャラクターシートの保存中にシステムエラーが発生しました。時間をおいて再度お試しください。"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def create_7th_edition(self, request):
        """7th edition character creation endpoint (Cthulhu Mythos TRPG exclusive)"""

        def parse_int(value, field_name, *, min_value=None, max_value=None, default=None):
            if value is None or value == "":
                if default is not None:
                    return default
                raise ValueError(f"{field_name} is required")

            try:
                int_value = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field_name} must be an integer") from exc

            if min_value is not None and int_value < min_value:
                raise ValueError(f"{field_name} must be between {min_value} and {max_value}")
            if max_value is not None and int_value > max_value:
                raise ValueError(f"{field_name} must be between {min_value} and {max_value}")

            return int_value

        def parse_json_list(value, field_name):
            if value is None or value == "":
                return []
            if isinstance(value, list):
                return value
            if not isinstance(value, str):
                raise ValueError(f"{field_name} must be valid JSON")
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{field_name} must be valid JSON") from exc
            if not isinstance(parsed, list):
                raise ValueError(f"{field_name} must be a JSON array")
            return parsed

        required_fields = [
            "name",
            "str_value",
            "con_value",
            "pow_value",
            "dex_value",
            "app_value",
            "siz_value",
            "int_value",
            "edu_value",
        ]

        for field in required_fields:
            if field not in request.data:
                return Response({"error": f"{field} is required"}, status=status.HTTP_400_BAD_REQUEST)

        ability_fields = [
            "str_value",
            "con_value",
            "pow_value",
            "dex_value",
            "app_value",
            "siz_value",
            "int_value",
            "edu_value",
        ]
        parsed_abilities = {}
        for field in ability_fields:
            try:
                parsed_abilities[field] = parse_int(request.data.get(field), field, min_value=1, max_value=999)
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recommended_skills = parse_json_list(request.data.get("recommended_skills", []), "recommended_skills")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            occupation_skills = parse_json_list(request.data.get("occupation_skills", []), "occupation_skills")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            occupation_point_method = self._parse_occupation_point_method(request.data, "7th")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        scenario_id_raw = request.data.get("scenario_id")
        scenario_title = (request.data.get("scenario_title") or "").strip()
        scenario_game_system = (request.data.get("game_system") or "").strip()
        scenario_obj = None
        if scenario_id_raw not in (None, ""):
            try:
                scenario_id = int(scenario_id_raw)
            except (TypeError, ValueError):
                return Response({"error": "scenario_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
            if scenario_id <= 0:
                return Response({"error": "scenario_id must be a positive integer"}, status=status.HTTP_400_BAD_REQUEST)
            from scenarios.models import Scenario

            scenario_obj = Scenario.objects.filter(id=scenario_id).first()

        image_files = collect_character_image_uploads(request.FILES)
        image_limit = get_character_image_limit(request.user)
        if len(image_files) > image_limit:
            return Response(
                {"error": character_image_limit_error_message(image_limit)}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            character_data = {
                "user": request.user,
                "edition": "7th",
                "name": request.data["name"],
                "name_kana": request.data.get("name_kana", ""),
                "player_name": request.data.get("player_name", request.user.nickname or request.user.username),
                "age": parse_int(request.data.get("age"), "age", min_value=15, max_value=999, default=25),
                "gender": request.data.get("gender", ""),
                "occupation": request.data.get("occupation", ""),
                "occupation_point_method": occupation_point_method,
                "birthplace": request.data.get("birthplace", ""),
                "residence": request.data.get("residence", ""),
                "recommended_skills": recommended_skills,
                "occupation_skills": occupation_skills,
                "str_value": parsed_abilities["str_value"],
                "con_value": parsed_abilities["con_value"],
                "pow_value": parsed_abilities["pow_value"],
                "dex_value": parsed_abilities["dex_value"],
                "app_value": parsed_abilities["app_value"],
                "siz_value": parsed_abilities["siz_value"],
                "int_value": parsed_abilities["int_value"],
                "edu_value": parsed_abilities["edu_value"],
                "notes": request.data.get("notes", ""),
                "is_active": True,
            }
            if scenario_obj:
                character_data["source_scenario"] = scenario_obj
                character_data["source_scenario_title"] = scenario_obj.title
                character_data["source_scenario_game_system"] = scenario_obj.game_system
            else:
                if scenario_title:
                    character_data["source_scenario_title"] = scenario_title
                if scenario_game_system:
                    character_data["source_scenario_game_system"] = scenario_game_system

            if "character_image" in request.FILES:
                character_data["character_image"] = request.FILES["character_image"]

            character_data.pop("user")
            character_data.pop("edition")
            character_sheet = CharacterSheet.objects.create(user=request.user, edition="7th")
            detail = CharacterSheet7th(character_sheet=character_sheet, **character_data)
            stats = detail.calculate_derived_stats()
            detail.hit_points_max = detail.hit_points_current = stats["hit_points_max"]
            detail.magic_points_max = detail.magic_points_current = stats["magic_points_max"]
            detail.sanity_starting = detail.sanity_current = stats["sanity_starting"]
            detail.sanity_max = stats["sanity_max"]
            detail.save()

            try:
                skills_data = parse_json_list(request.data.get("skills", []), "skills")
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            for skill_data in skills_data:
                if not isinstance(skill_data, dict) or "skill_name" not in skill_data:
                    continue

                base_value = parse_int(
                    skill_data.get("base_value", 0), "base_value", min_value=0, max_value=999, default=0
                )
                occupation_points = parse_int(
                    skill_data.get("occupation_points", 0), "occupation_points", min_value=0, max_value=999, default=0
                )
                interest_points = parse_int(
                    skill_data.get("interest_points", 0), "interest_points", min_value=0, max_value=999, default=0
                )
                other_points = parse_int(
                    skill_data.get("other_points", 0), "other_points", min_value=0, max_value=999, default=0
                )
                current_value = parse_int(
                    skill_data.get("current_value", base_value + occupation_points + interest_points + other_points),
                    "current_value",
                    min_value=0,
                    max_value=999,
                    default=base_value + occupation_points + interest_points + other_points,
                )

                detail.skills.model.objects.create(
                    character_sheet=detail,
                    skill_name=skill_data["skill_name"],
                    base_value=base_value,
                    occupation_points=occupation_points,
                    interest_points=interest_points,
                    other_points=other_points,
                    current_value=current_value,
                )

            try:
                equipment_data = parse_json_list(request.data.get("equipment", []), "equipment")
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            for equipment in equipment_data:
                if not isinstance(equipment, dict) or "name" not in equipment:
                    continue
                detail.equipment.model.objects.create(
                    character_sheet=detail,
                    item_type=equipment.get("item_type", "item"),
                    name=equipment["name"],
                    skill_name=equipment.get("skill_name", ""),
                    damage=equipment.get("damage", ""),
                    base_range=equipment.get("base_range", ""),
                    attacks_per_round=equipment.get("attacks_per_round"),
                    ammo=equipment.get("ammo"),
                    malfunction_number=equipment.get("malfunction_number"),
                    armor_points=equipment.get("armor_points"),
                    description=equipment.get("description", ""),
                    quantity=equipment.get("quantity", 1),
                    weight=equipment.get("weight"),
                )

            for index, image_file in enumerate(image_files):
                detail.images.model.objects.create(
                    character_sheet=detail, image=image_file, is_main=(index == 0), order=index
                )

            response_serializer = CharacterSheetSerializer(character_sheet)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except DjangoValidationError as exc:
            error_data = exc.message_dict if hasattr(exc, "message_dict") else {"error": exc.messages}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error while creating 7th edition character: user_id=%s", request.user.id)
            return Response(
                {"error": "キャラクターシートの保存中にシステムエラーが発生しました。時間をおいて再度お試しください。"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_or_create_skill_with_retry(self, sheet, skill_name, base_value, skip_point_validation):
        detail = sheet.system_data
        skills = detail.skills
        """SQLiteのロックに備えて技能の作成をリトライする。"""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                skill = skills.filter(skill_name=skill_name).first()
                if skill:
                    return skill, False

                skill = skills.model(character_sheet=detail, skill_name=skill_name, base_value=base_value)
                if not skip_point_validation:
                    skill.full_clean()
                skill.save()
                return skill, True
            except IntegrityError:
                skill = skills.filter(skill_name=skill_name).first()
                if skill:
                    return skill, False
                raise
            except OperationalError:
                if attempt == max_attempts - 1:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def _save_skill_with_retry(self, skill, *, skip_point_validation):
        """SQLiteのロックに備えて技能の保存をリトライする。"""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if not skip_point_validation:
                    skill.full_clean()
                skill.save()
                return
            except OperationalError:
                if attempt == max_attempts - 1:
                    raise
                time.sleep(0.05 * (attempt + 1))

    @action(detail=True, methods=["post"])
    def allocate_skill_points(self, request, pk=None):
        """技能ポイント割り振りAPI"""
        sheet = self.get_object()

        skill_id = request.data.get("skill_id")
        skill_name = request.data.get("skill_name")
        base_value_present = "base_value" in request.data
        base_value = request.data.get("base_value", 0)
        occupation_points = request.data.get("occupation_points", 0)
        interest_points = request.data.get("interest_points", 0)

        def coerce_int(value, field_name):
            if value in [None, "", "null", "None"]:
                return 0
            try:
                return int(value)
            except (TypeError, ValueError):
                try:
                    return int(float(value))
                except (TypeError, ValueError):
                    raise DRFValidationError({field_name: "有効な数値を指定してください"})

        try:
            base_value = coerce_int(base_value, "base_value")
            occupation_points = coerce_int(occupation_points, "occupation_points")
            interest_points = coerce_int(interest_points, "interest_points")
        except DRFValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        if not skill_id and not skill_name:
            return Response({"error": "skill_id or skill_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        enforce_limits = True
        if skill_id:
            try:
                skill = sheet.system_data.skills.get(id=skill_id)
            except sheet.system_data.skills.model.DoesNotExist:
                return Response({"error": "技能が見つかりません"}, status=status.HTTP_404_NOT_FOUND)
        else:
            skill, _ = self._get_or_create_skill_with_retry(
                sheet=sheet,
                skill_name=skill_name,
                base_value=base_value if base_value_present else 0,
                skip_point_validation=True,
            )
            enforce_limits = False

        if base_value_present:
            skill.base_value = base_value

        if enforce_limits:
            # ポイント不足チェック
            if occupation_points > sheet.system_data.calculate_remaining_occupation_points() + skill.occupation_points:
                return Response({"error": "職業技能ポイントが不足しています"}, status=status.HTTP_400_BAD_REQUEST)

            if interest_points > sheet.system_data.calculate_remaining_hobby_points() + skill.interest_points:
                return Response({"error": "趣味技能ポイントが不足しています"}, status=status.HTTP_400_BAD_REQUEST)

        # ポイント更新
        skill.occupation_points = occupation_points
        skill.interest_points = interest_points
        self._save_skill_with_retry(skill, skip_point_validation=not enforce_limits)

        # 更新された技能データを返す
        serializer = CharacterSkillSerializer(skill)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def batch_allocate_skill_points(self, request, pk=None):
        """一括技能ポイント割り振りAPI"""
        sheet = self.get_object()
        allocations = request.data.get("allocations")
        skills_data = request.data.get("skills")

        if not allocations and skills_data:
            allocations = skills_data
            skip_point_validation = True
        else:
            skip_point_validation = False

        if not allocations:
            return Response({"error": "allocations or skills are required"}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        total_occupation_used = 0
        total_hobby_used = 0
        errors = []

        def coerce_int(value, field_name):
            if value in [None, "", "null", "None"]:
                return 0
            try:
                return int(value)
            except (TypeError, ValueError):
                try:
                    return int(float(value))
                except (TypeError, ValueError):
                    raise DRFValidationError({field_name: "有効な数値を指定してください"})

        for allocation in allocations:
            skill_id = allocation.get("skill_id")
            skill_name = allocation.get("skill_name")
            base_value_present = "base_value" in allocation
            base_value = allocation.get("base_value", 0)
            occupation_points = allocation.get("occupation_points", 0)
            interest_points = allocation.get("interest_points", 0)
            other_points = allocation.get("other_points", 0)

            try:
                base_value = coerce_int(base_value, "base_value")
                occupation_points = coerce_int(occupation_points, "occupation_points")
                interest_points = coerce_int(interest_points, "interest_points")
                other_points = coerce_int(other_points, "other_points")
            except DRFValidationError as exc:
                return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

            if skip_point_validation:
                interest_points = (interest_points // 10) * 10

            if not skill_id and not skill_name:
                continue

            if skill_id:
                try:
                    skill = sheet.system_data.skills.get(id=skill_id)
                except sheet.system_data.skills.model.DoesNotExist:
                    continue
            else:
                skill, _ = self._get_or_create_skill_with_retry(
                    sheet=sheet,
                    skill_name=skill_name,
                    base_value=base_value if base_value_present else 0,
                    skip_point_validation=skip_point_validation,
                )

            if base_value_present:
                skill.base_value = base_value

            skill.occupation_points = occupation_points
            skill.interest_points = interest_points
            skill.other_points = other_points
            try:
                self._save_skill_with_retry(skill, skip_point_validation=skip_point_validation)
            except ValidationError as exc:
                errors.append(str(exc))
                break

            updated_count += 1
            total_occupation_used += occupation_points
            total_hobby_used += interest_points

        if errors:
            return Response({"error": errors[0]}, status=status.HTTP_400_BAD_REQUEST)

        # 残りポイントを計算
        remaining_occupation = sheet.system_data.calculate_remaining_occupation_points()
        remaining_hobby = sheet.system_data.calculate_remaining_hobby_points()

        return Response(
            {
                "updated_count": updated_count,
                "remaining_occupation_points": remaining_occupation,
                "remaining_hobby_points": remaining_hobby,
            }
        )

    @action(detail=True, methods=["post"])
    def reset_skill_points(self, request, pk=None):
        """技能ポイントリセットAPI"""
        sheet = self.get_object()

        # 全技能のポイントをリセット（個別にsaveしてcurrent_valueを自動計算）
        skills = sheet.system_data.skills.all()
        for skill in skills:
            skill.occupation_points = 0
            skill.interest_points = 0
            skill.save()

        return Response({"message": "技能ポイントがリセットされました"})

    @action(detail=True, methods=["get"])
    def combat_summary(self, request, pk=None):
        """戦闘サマリー取得API"""
        sheet = self.get_object()

        # 武器・防具の取得
        equipment = sheet.system_data.equipment
        weapons = equipment.filter(item_type="weapon")
        armors = equipment.filter(item_type="armor")

        # ダメージボーナスの取得
        damage_bonus = sheet.system_data.damage_bonus

        # 総防護点の計算
        total_armor_points = sum(armor.armor_points or 0 for armor in armors)

        armor_items = [
            {"id": armor.id, "name": armor.name, "armor_points": armor.armor_points, "description": armor.description}
            for armor in armors
        ]

        summary = {
            "damage_bonus": damage_bonus,
            "total_armor_points": total_armor_points,
            "weapons_count": weapons.count(),
            "armor_count": armors.count(),
            "weapons": [
                {
                    "id": weapon.id,
                    "name": weapon.name,
                    "skill_name": weapon.skill_name,
                    "damage": weapon.damage,
                    "base_range": weapon.base_range,
                    "attacks_per_round": weapon.attacks_per_round,
                    "ammo": weapon.ammo,
                    "malfunction_number": weapon.malfunction_number,
                }
                for weapon in weapons
            ],
            "armors": armor_items,
            "armor": {"total_armor": total_armor_points, "items": armor_items},
        }

        return Response(summary)

    @action(detail=True, methods=["get"])
    def financial_summary(self, request, pk=None):
        """財務サマリー取得API"""
        sheet = self.get_object()

        # 6版データの取得
        if sheet.edition != "6th" or not hasattr(sheet, "sixth_edition_data"):
            return Response({"error": "6版キャラクターシートのみサポートします"}, status=status.HTTP_400_BAD_REQUEST)

        sixth_data = sheet.sixth_edition_data

        summary = {
            "cash": str(sixth_data.cash),
            "assets": str(sixth_data.assets),
            "annual_income": str(sixth_data.annual_income),
            "real_estate": sixth_data.real_estate,
            "total_wealth": str(sixth_data.calculate_total_wealth()),
        }

        return Response(summary)

    @action(detail=True, methods=["patch"])
    def update_financial_data(self, request, pk=None):
        """財務データ更新API"""
        from decimal import Decimal, InvalidOperation

        sheet = self.get_object()

        # 6版データの取得
        if sheet.edition != "6th" or not hasattr(sheet, "sixth_edition_data"):
            return Response({"error": "6版キャラクターシートのみサポートします"}, status=status.HTTP_400_BAD_REQUEST)

        sixth_data = sheet.sixth_edition_data

        try:
            # 各フィールドの更新
            if "cash" in request.data:
                sixth_data.cash = Decimal(str(request.data["cash"]))

            if "assets" in request.data:
                sixth_data.assets = Decimal(str(request.data["assets"]))

            if "annual_income" in request.data:
                sixth_data.annual_income = Decimal(str(request.data["annual_income"]))

            if "real_estate" in request.data:
                sixth_data.real_estate = request.data["real_estate"]

            # 保存（バリデーション含む）
            sixth_data.save()

            return Response(
                {
                    "message": "財務データが更新されました",
                    "cash": str(sixth_data.cash),
                    "assets": str(sixth_data.assets),
                    "annual_income": str(sixth_data.annual_income),
                    "real_estate": sixth_data.real_estate,
                    "total_wealth": str(sixth_data.calculate_total_wealth()),
                }
            )

        except (ValueError, InvalidOperation) as e:
            return Response({"error": f"数値変換エラー: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({"error": f"バリデーションエラー: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"財務データ更新に失敗しました: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def inventory_summary(self, request, pk=None):
        """インベントリサマリー取得API"""
        sheet = self.get_object()

        # アイテムの取得
        items = sheet.system_data.equipment.filter(item_type="item")

        # 総重量の計算
        total_weight = sum((item.weight or 0) * item.quantity for item in items)

        # 運搬能力の計算
        carry_capacity = sheet.system_data.calculate_carry_capacity()
        movement_penalty = sheet.system_data.calculate_movement_penalty(total_weight)

        summary = {
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "weight": item.weight,
                    "total_weight": (item.weight or 0) * item.quantity,
                    "description": item.description,
                }
                for item in items
            ],
            "total_items": len(items),
            "total_weight": total_weight,
            "carry_capacity": carry_capacity,
            "movement_penalty": movement_penalty,
            "is_overloaded": total_weight > carry_capacity,
        }

        return Response(summary)

    @action(detail=True, methods=["post"])
    def bulk_update_items(self, request, pk=None):
        """アイテム一括更新API"""
        sheet = self.get_object()

        items_data = request.data.get("items", [])
        if not items_data:
            return Response({"error": "items data is required"}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        errors = []

        for item_data in items_data:
            item_id = item_data.get("id")
            if not item_id:
                errors.append("item id is required")
                continue

            try:
                item = sheet.system_data.equipment.get(id=item_id)

                # 数量更新
                if "quantity" in item_data:
                    item.quantity = item_data["quantity"]

                # 重量更新
                if "weight" in item_data:
                    item.weight = item_data["weight"]

                item.save()
                updated_count += 1

            except sheet.system_data.equipment.model.DoesNotExist:
                errors.append(f"Item with id {item_id} not found")
            except Exception as e:
                errors.append(f"Failed to update item {item_id}: {str(e)}")

        response_data = {"updated_count": updated_count, "message": f"{updated_count}件のアイテムが更新されました"}

        if errors:
            response_data["errors"] = errors

        return Response(response_data)

    @action(detail=True, methods=["get"])
    def background_summary(self, request, pk=None):
        """背景情報サマリー取得API"""
        sheet = self.get_object()

        try:
            background = sheet.background_info
        except AttributeError:
            # 背景情報が存在しない場合は空のデータを返す
            return Response(
                {
                    "appearance_description": "",
                    "beliefs_ideology": "",
                    "significant_people": "",
                    "meaningful_locations": "",
                    "treasured_possessions": "",
                    "traits_mannerisms": "",
                    "personal_history": "",
                    "important_events": "",
                    "scars_injuries": "",
                    "phobias_manias": "",
                    "arcane_tomes_spells_artifacts": "",
                    "encounters_with_strange_entities": "",
                    "fellow_investigators": "",
                    "notes_memo": "",
                }
            )

        summary = {
            "appearance_description": background.appearance_description,
            "beliefs_ideology": background.beliefs_ideology,
            "significant_people": background.significant_people,
            "meaningful_locations": background.meaningful_locations,
            "treasured_possessions": background.treasured_possessions,
            "traits_mannerisms": background.traits_mannerisms,
            "personal_history": background.personal_history,
            "important_events": background.important_events,
            "scars_injuries": background.scars_injuries,
            "phobias_manias": background.phobias_manias,
            "arcane_tomes_spells_artifacts": background.arcane_tomes_spells_artifacts,
            "encounters_with_strange_entities": background.encounters_with_strange_entities,
            "fellow_investigators": background.fellow_investigators,
            "notes_memo": background.notes_memo,
        }

        return Response(summary)

    @action(detail=True, methods=["patch"])
    def update_background_data(self, request, pk=None):
        """背景情報更新API"""
        from ..character_models import CharacterBackground

        sheet = self.get_object()

        try:
            # 既存の背景情報を取得
            background = sheet.background_info
        except AttributeError:
            # 背景情報が存在しない場合は新規作成
            background = CharacterBackground.objects.create(character_sheet=sheet)

        try:
            # 各フィールドの更新
            update_fields = [
                "appearance_description",
                "beliefs_ideology",
                "significant_people",
                "meaningful_locations",
                "treasured_possessions",
                "traits_mannerisms",
                "personal_history",
                "important_events",
                "scars_injuries",
                "phobias_manias",
                "arcane_tomes_spells_artifacts",
                "encounters_with_strange_entities",
                "fellow_investigators",
                "notes_memo",
            ]

            for field in update_fields:
                if field in request.data:
                    setattr(background, field, request.data[field])

            # 保存（バリデーション含む）
            background.save()

            return Response(
                {
                    "message": "背景情報が更新されました",
                    "appearance_description": background.appearance_description,
                    "beliefs_ideology": background.beliefs_ideology,
                    "significant_people": background.significant_people,
                    "meaningful_locations": background.meaningful_locations,
                    "treasured_possessions": background.treasured_possessions,
                    "traits_mannerisms": background.traits_mannerisms,
                    "personal_history": background.personal_history,
                    "important_events": background.important_events,
                    "scars_injuries": background.scars_injuries,
                    "phobias_manias": background.phobias_manias,
                    "arcane_tomes_spells_artifacts": background.arcane_tomes_spells_artifacts,
                    "encounters_with_strange_entities": background.encounters_with_strange_entities,
                    "fellow_investigators": background.fellow_investigators,
                    "notes_memo": background.notes_memo,
                }
            )

        except ValidationError as e:
            return Response({"error": f"バリデーションエラー: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"背景情報更新に失敗しました: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get", "post"])
    def growth_records(self, request, pk=None):
        """成長記録の取得・作成API"""
        from ..character_models import GrowthRecord

        sheet = self.get_object()

        if request.method == "GET":
            # 成長記録一覧取得
            growth_records = GrowthRecord.objects.filter(character_sheet=sheet)

            records_data = []
            for record in growth_records:
                records_data.append(
                    {
                        "id": record.id,
                        "session_date": record.session_date,
                        "scenario_name": record.scenario_name,
                        "gm_name": record.gm_name,
                        "sanity_gained": record.sanity_gained,
                        "sanity_lost": record.sanity_lost,
                        "net_sanity_change": record.calculate_net_sanity_change(),
                        "experience_gained": record.experience_gained,
                        "special_rewards": record.special_rewards,
                        "notes": record.notes,
                        "skill_growths_count": record.skill_growths.count(),
                    }
                )

            return Response(records_data)

        elif request.method == "POST":
            # 成長記録作成
            try:
                growth_record = GrowthRecord.objects.create(
                    character_sheet=sheet,
                    session_date=request.data.get("session_date"),
                    scenario_name=request.data.get("scenario_name"),
                    gm_name=request.data.get("gm_name", ""),
                    sanity_gained=request.data.get("sanity_gained", 0),
                    sanity_lost=request.data.get("sanity_lost", 0),
                    experience_gained=request.data.get("experience_gained", 0),
                    special_rewards=request.data.get("special_rewards", ""),
                    notes=request.data.get("notes", ""),
                )

                return Response(
                    {
                        "id": growth_record.id,
                        "session_date": growth_record.session_date,
                        "scenario_name": growth_record.scenario_name,
                        "gm_name": growth_record.gm_name,
                        "sanity_gained": growth_record.sanity_gained,
                        "sanity_lost": growth_record.sanity_lost,
                        "net_sanity_change": growth_record.calculate_net_sanity_change(),
                        "experience_gained": growth_record.experience_gained,
                        "special_rewards": growth_record.special_rewards,
                        "notes": growth_record.notes,
                        "message": "成長記録が作成されました",
                    },
                    status=status.HTTP_201_CREATED,
                )

            except ValidationError as e:
                return Response({"error": f"バリデーションエラー: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response(
                    {"error": f"成長記録作成に失敗しました: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    @extend_schema(
        parameters=[
            OpenApiParameter("record_id", OpenApiTypes.INT, OpenApiParameter.PATH),
        ],
    )
    @action(detail=True, methods=["post"], url_path="growth-records/(?P<record_id>[^/.]+)/add-skill-growth")
    def add_skill_growth(self, request, pk=None, record_id=None):
        """技能成長記録追加API"""
        from ..character_models import GrowthRecord, SkillGrowthRecord

        sheet = self.get_object()

        try:
            growth_record = GrowthRecord.objects.get(id=record_id, character_sheet=sheet)
        except GrowthRecord.DoesNotExist:
            return Response({"error": "成長記録が見つかりません"}, status=status.HTTP_404_NOT_FOUND)

        try:
            skill_growth = SkillGrowthRecord.objects.create(
                growth_record=growth_record,
                skill_name=request.data.get("skill_name"),
                had_experience_check=request.data.get("had_experience_check", False),
                growth_roll_result=request.data.get("growth_roll_result"),
                old_value=request.data.get("old_value"),
                new_value=request.data.get("new_value"),
                growth_amount=request.data.get("growth_amount", 0),
                notes=request.data.get("notes", ""),
            )

            return Response(
                {
                    "id": skill_growth.id,
                    "skill_name": skill_growth.skill_name,
                    "had_experience_check": skill_growth.had_experience_check,
                    "growth_roll_result": skill_growth.growth_roll_result,
                    "old_value": skill_growth.old_value,
                    "new_value": skill_growth.new_value,
                    "growth_amount": skill_growth.growth_amount,
                    "is_growth_successful": skill_growth.is_growth_successful(),
                    "notes": skill_growth.notes,
                    "message": "技能成長記録が追加されました",
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response({"error": f"バリデーションエラー: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"技能成長記録追加に失敗しました: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def growth_summary(self, request, pk=None):
        """成長サマリー取得API"""
        from ..character_models import GrowthRecord

        sheet = self.get_object()

        growth_records = GrowthRecord.objects.filter(character_sheet=sheet).order_by("-session_date")

        # 基本統計
        record_count = growth_records.count()
        total_sessions = record_count
        if sheet.system_data.session_count:
            total_sessions = max(sheet.system_data.session_count, record_count)
        total_sanity_lost = sum(record.sanity_lost for record in growth_records)
        total_sanity_gained = sum(record.sanity_gained for record in growth_records)
        total_experience = sum(record.experience_gained for record in growth_records)

        # 最近のシナリオ
        recent_scenarios = []
        for record in growth_records[:5]:  # 最新5件
            recent_scenarios.append(
                {
                    "date": record.session_date,
                    "scenario": record.scenario_name,
                    "sanity_change": record.calculate_net_sanity_change(),
                }
            )

        # バージョン数
        version_count = len(sheet.get_version_history())

        growth_records_payload = []
        for record in growth_records:
            session_date = (
                record.session_date.isoformat()
                if hasattr(record.session_date, "isoformat")
                else str(record.session_date)
            )
            growth_records_payload.append(
                {
                    "session_date": session_date,
                    "session_title": record.session_title,
                    "changes": record.changes,
                    "notes": record.notes,
                }
            )

        summary = {
            "total_sessions": total_sessions,
            "total_sanity_lost": total_sanity_lost,
            "total_sanity_gained": total_sanity_gained,
            "net_sanity_change": total_sanity_gained - total_sanity_lost,
            "total_experience": total_experience,
            "recent_scenarios": recent_scenarios,
            "average_sanity_loss_per_session": total_sanity_lost / total_sessions if total_sessions > 0 else 0,
            "version_count": version_count,
            "growth_records": growth_records_payload,
        }

        return Response(summary)


class CharacterSkillViewSet(CharacterNestedResourceMixin, ErrorHandlerMixin, viewsets.ModelViewSet):
    """Character skill management ViewSet"""

    queryset = CharacterSkill6th.objects.none()
    serializer_class = CharacterSkillSerializer
    permission_classes = [IsAuthenticated]
    system_data_relation = "skills"

    # get_queryset and perform_create are now handled by CharacterNestedResourceMixin

    def perform_update(self, serializer):
        """Return model validation errors to the client instead of turning them into 500s."""
        skill = serializer.instance
        try:
            serializer.save()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
        except Exception:
            logger.exception(
                "Character skill update failed: character_sheet_id=%s skill_id=%s skill_name=%r user_id=%s fields=%s",
                skill.character_sheet_id,
                skill.id,
                skill.skill_name,
                self.request.user.id,
                sorted(serializer.validated_data.keys()),
            )
            raise

    @action(detail=False, methods=["post"])
    def create_custom_skill(self, request):
        """Create custom skill (specializations, languages, etc.)"""
        try:
            character_sheet = self.get_character_sheet()
        except (ValidationError, Http404):
            return self.handle_not_found("キャラクターシート")

        # Validate required fields
        skill_name = request.data.get("skill_name")
        if not skill_name or skill_name.strip() == "":
            return self.handle_validation_error("skill_name is required")

        try:
            # Use custom skill creation helper
            skill = character_sheet.system_data.skills.model.create_custom_skill(
                character_sheet=character_sheet.system_data,
                skill_name=skill_name,
                category=request.data.get("category", "特殊・その他"),
                base_value=request.data.get("base_value", 5),
                occupation_points=request.data.get("occupation_points", 0),
                interest_points=request.data.get("interest_points", 0),
                bonus_points=request.data.get("bonus_points", 0),
                other_points=request.data.get("other_points", 0),
                notes=request.data.get("notes", ""),
            )

            serializer = CharacterSkillSerializer(skill)
            return self.handle_creation_success(serializer.data, "カスタム技能が作成されました")

        except Exception as e:
            return self.handle_validation_error(f"Custom skill creation failed: {str(e)}")

    @action(detail=False, methods=["get"])
    def skill_categories(self, request):
        """Get available skill categories"""
        categories = [
            {"value": "explore", "label": "探索系"},
            {"value": "social", "label": "対人系"},
            {"value": "combat", "label": "戦闘系"},
            {"value": "knowledge", "label": "知識系"},
            {"value": "technical", "label": "技術系"},
            {"value": "action", "label": "行動系"},
            {"value": "language", "label": "言語系"},
            {"value": "special", "label": "特殊・その他"},
        ]
        return Response(categories)

    @action(detail=False, methods=["get"])
    def common_custom_skills(self, request):
        """Get list of common custom skill templates"""
        custom_skills = [
            {
                "name": "芸術（絵画）",
                "category": "特殊・その他",
                "base_value": 5,
                "description": "イラスト、油絵、水彩画などの絵画技術",
            },
            {
                "name": "芸術（音楽）",
                "category": "特殊・その他",
                "base_value": 5,
                "description": "楽器演奏、作曲、歌唱などの音楽技術",
            },
            {
                "name": "芸術（写真）",
                "category": "特殊・その他",
                "base_value": 5,
                "description": "写真撮影、現像、画像加工などの写真技術",
            },
            {
                "name": "制作（プログラミング）",
                "category": "技術系",
                "base_value": 5,
                "description": "ソフトウェア開発、システム設計",
            },
            {
                "name": "制作（料理）",
                "category": "技術系",
                "base_value": 5,
                "description": "調理技術、レシピ開発、食材知識",
            },
            {
                "name": "他の言語（英語）",
                "category": "言語系",
                "base_value": 1,
                "description": "英語の読み書き、会話能力",
            },
            {
                "name": "他の言語（中国語）",
                "category": "言語系",
                "base_value": 1,
                "description": "中国語の読み書き、会話能力",
            },
            {
                "name": "他の言語（フランス語）",
                "category": "言語系",
                "base_value": 1,
                "description": "フランス語の読み書き、会話能力",
            },
        ]
        return Response(custom_skills)

    @action(detail=False, methods=["patch"])
    def bulk_update(self, request, character_sheet_id=None):
        """Bulk update/create skills"""
        skills_data = request.data.get("skills", [])
        if not skills_data:
            return Response({"error": "skills data is required"}, status=status.HTTP_400_BAD_REQUEST)

        character_sheet_id = self.kwargs.get("character_sheet_id") or self.kwargs.get("character_sheet_pk")
        if not character_sheet_id:
            return Response({"error": "character_sheet_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            character_sheet = CharacterSheet.objects.get(id=character_sheet_id, user=self.request.user)
        except CharacterSheet.DoesNotExist:
            return Response({"error": "Character sheet not found"}, status=status.HTTP_404_NOT_FOUND)

        detail = character_sheet.system_data
        skill_model = detail.skills.model

        updated_skills = []
        created_skills = []

        for skill_data in skills_data:
            skill_id = skill_data.get("id")

            if skill_id:
                # Update existing skill
                try:
                    skill = skill_model.objects.get(id=skill_id, character_sheet=detail)

                    # Process updatable fields only
                    updatable_fields = [
                        "base_value",
                        "occupation_points",
                        "interest_points",
                        "bonus_points",
                        "other_points",
                    ]

                    for field in updatable_fields:
                        if field in skill_data:
                            setattr(skill, field, skill_data[field])

                    skill.save()
                    updated_skills.append(skill)

                except skill_model.DoesNotExist:
                    continue
            else:
                # Create new custom skill
                skill_name = skill_data.get("skill_name")
                if skill_name and skill_name.strip():
                    try:
                        skill = skill_model.create_custom_skill(
                            character_sheet=detail,
                            skill_name=skill_name,
                            category=skill_data.get("category", "特殊・その他"),
                            base_value=skill_data.get("base_value", 5),
                            occupation_points=skill_data.get("occupation_points", 0),
                            interest_points=skill_data.get("interest_points", 0),
                            bonus_points=skill_data.get("bonus_points", 0),
                            other_points=skill_data.get("other_points", 0),
                            notes=skill_data.get("notes", ""),
                        )
                        created_skills.append(skill)
                    except Exception:
                        continue

        all_skills = updated_skills + created_skills
        serializer = CharacterSkillSerializer(all_skills, many=True)
        return Response(serializer.data)


class CharacterEquipmentViewSet(CharacterNestedResourceMixin, viewsets.ModelViewSet):
    """Character equipment management ViewSet"""

    queryset = CharacterEquipment6th.objects.none()
    serializer_class = CharacterEquipmentSerializer
    permission_classes = [IsAuthenticated]
    system_data_relation = "equipment"

    # get_queryset and perform_create are now handled by CharacterNestedResourceMixin

    @action(detail=False, methods=["get"])
    def by_type(self, request):
        """Get equipment list by type"""
        item_type = request.query_params.get("type")
        if not item_type or item_type not in ["weapon", "armor", "item"]:
            return Response(
                {"error": "type parameter is required (weapon, armor, or item)"}, status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(item_type=item_type)
        serializer = CharacterEquipmentSerializer(queryset, many=True)
        return Response(serializer.data)


# Django Web Views for Character Management


@method_decorator(login_required, name="dispatch")
class CharacterListView(TemplateView):
    """Character sheet list view"""

    template_name = "accounts/character_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Edition-based filtering
        edition = self.request.GET.get("edition", "all")
        is_active = self.request.GET.get("active", "all")

        # Base queryset (show only user's character sheets)
        queryset = (
            CharacterSheet.objects.filter(user=user)
            .select_related("sixth_edition_data", "seventh_edition_data", "user")
            .prefetch_related(
                "sixth_edition_data__skills", "sixth_edition_data__equipment",
                "seventh_edition_data__skills", "seventh_edition_data__equipment",
            )
            .order_by("-updated_at")
        )

        # Apply filters
        if edition in ["6th", "7th"]:
            queryset = queryset.filter(edition=edition)

        if is_active == "active":
            queryset = queryset.filter(
                Q(edition="6th", sixth_edition_data__is_active=True)
                | Q(edition="7th", seventh_edition_data__is_active=True)
            )
        elif is_active == "inactive":
            queryset = queryset.filter(
                Q(edition="6th", sixth_edition_data__is_active=False)
                | Q(edition="7th", seventh_edition_data__is_active=False)
            )

        # Edition-based statistics (user's characters only)
        sixth_count = CharacterSheet.objects.filter(user=user, edition="6th").count()
        active_count = CharacterSheet.objects.filter(user=user).filter(
            Q(edition="6th", sixth_edition_data__is_active=True)
            | Q(edition="7th", seventh_edition_data__is_active=True)
        ).count()
        total_count = CharacterSheet.objects.filter(user=user).count()

        context.update(
            {
                "character_sheets": queryset,
                "sixth_count": sixth_count,
                "active_count": active_count,
                "total_count": total_count,
                "current_edition": edition,
                "current_active": is_active,
            }
        )

        return context


class CharacterDetailRedirectView(TemplateView):
    """Character sheet detail view dispatcher"""

    template_name = "accounts/character_detail.html"

    def get(self, request, *args, **kwargs):
        character_id = kwargs.get("character_id")

        try:
            character = CharacterSheet.objects.only("id", "edition").get(id=character_id)
        except CharacterSheet.DoesNotExist:
            raise Http404("キャラクターシートが見つかりません")

        if character.edition == "6th":
            return redirect("character_detail_6th", character_id=character.id)

        # Fallback: treat as 6th until other rule screens are implemented.
        return redirect("character_detail_6th", character_id=character.id)


class CharacterDetailView(TemplateView):
    """Character sheet detail view"""

    template_name = "accounts/character_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        character_id = kwargs.get("character_id")

        try:
            character = (
                CharacterSheet.objects.select_related("sixth_edition_data", "seventh_edition_data", "user")
                .prefetch_related(
                    "sixth_edition_data__skills", "sixth_edition_data__equipment",
                    "seventh_edition_data__skills", "seventh_edition_data__equipment",
                )
                .get(id=character_id)
            )

            if not CharacterSheetAccessMixin.can_read_character_sheet(character, self.request.user):
                raise Http404("Character sheet not found")

            context.update(
                build_character_detail_context(
                    self.request,
                    character,
                    can_edit_character=(
                        self.request.user.is_authenticated and character.user_id == self.request.user.id
                    ),
                    images_api_url=f"/api/accounts/character-sheets/{character.id}/images/",
                    images_zip_url=f"/api/accounts/character-sheets/{character.id}/images/download/",
                    ccfolia_json_url=f"/api/accounts/character-sheets/{character.id}/ccfolia_json/",
                    reference_url=f"/share/characters/{character.share_token}/view/",
                )
            )

        except CharacterSheet.DoesNotExist:
            raise Http404("キャラクターシートが見つかりません")

        return context


class Character6thDetailView(CharacterDetailView):
    """クトゥルフ神話TRPG 6版キャラクター詳細ビュー"""

    pass


@method_decorator(login_required, name="dispatch")
class Character6thCreateView(FormView):
    """Cthulhu Mythos TRPG 6th edition character creation view"""

    template_name = "accounts/character_6th_create.html"
    form_class = CharacterSheet6thForm
    success_url = "/accounts/character/list/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edition"] = "6th"
        context["default_player_name"] = self.request.user.nickname or self.request.user.username
        context["edition_name"] = "6版"

        context["available_skills"] = COC6_BASIC_SKILL_NAMES
        return context

    def form_valid(self, form):
        try:
            character_sheet = form.save()

            # 画像処理はフォームのsaveメソッドで既に実行されているため、ここでは何もしない

            messages.success(self.request, f"クトゥルフ神話TRPG 6版探索者「{character_sheet.system_data.name}」が作成されました！")

            # 作成したキャラクターの詳細画面にリダイレクト
            return redirect("character_detail_6th", character_id=character_sheet.id)

        except Exception:
            logger.exception("Error creating 6th edition character sheet")
            messages.error(self.request, "探索者の作成中にエラーが発生しました。")
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error("Character sheet form validation failed: fields=%s", list(form.errors.keys()))

        # エラーメッセージを詳細化
        error_messages = []
        for field, errors in form.errors.items():
            if field == "__all__":
                error_messages.extend(errors)
            else:
                field_label = form.fields.get(field, {}).label or field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")

        if error_messages:
            messages.error(
                self.request, f"探索者の作成に失敗しました。<br>" + "<br>".join(error_messages), extra_tags="safe"
            )
        else:
            messages.error(self.request, "探索者の作成に失敗しました。入力内容を確認してください。")
        return super().form_invalid(form)


@method_decorator(login_required, name="dispatch")
class Character7thCreateView(TemplateView):
    """Cthulhu Mythos TRPG 7th edition character creation view"""

    template_name = "accounts/character_7th_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edition"] = "7th"
        context["default_player_name"] = self.request.user.nickname or self.request.user.username
        context["edition_name"] = "7版"
        context["available_skills"] = COC7_BASIC_SKILL_NAMES
        return context


class GrowthRecordViewSet(CharacterNestedResourceMixin, viewsets.ModelViewSet):
    queryset = GrowthRecord.objects.none()
    """成長記録管理ViewSet"""
    permission_classes = [IsAuthenticated]

    def get_character_sheet(self):
        character_sheet_id = self.get_character_sheet_id()
        if not character_sheet_id:
            raise ValidationError("character_sheet_id is required")
        return get_object_or_404(
            CharacterSheet,
            id=character_sheet_id,
            user=self.request.user,
        )

    def get_serializer_class(self):
        """アクションベースのシリアライザー選択"""
        if self.action == "create":
            from ..serializers import GrowthRecordCreateSerializer

            return GrowthRecordCreateSerializer
        else:
            from ..serializers import GrowthRecordSerializer

            return GrowthRecordSerializer

    def get_queryset(self):
        """キャラクターシートに関連する成長記録を取得"""
        character_sheet = self.get_character_sheet()
        return (
            GrowthRecord.objects.filter(character_sheet=character_sheet)
            .prefetch_related("skill_growths")
            .order_by("-session_date", "-created_at")
        )

    def perform_create(self, serializer):
        """成長記録作成時の処理"""
        character_sheet = self.get_character_sheet()
        serializer.save(character_sheet=character_sheet)

    @action(detail=True, methods=["post"])
    def add_skill_growth(self, request, character_sheet_id=None, pk=None):
        """既存の成長記録にスキル成長を追加"""
        growth_record = self.get_object()

        from ..serializers import SkillGrowthRecordSerializer

        serializer = SkillGrowthRecordSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(growth_record=growth_record)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def summary(self, request, character_sheet_id=None):
        """成長記録のサマリーを取得"""
        character_sheet = self.get_character_sheet()
        growth_records = self.get_queryset()

        # 統計情報を計算
        total_sessions = growth_records.count()
        total_san_gained = sum(record.sanity_gained for record in growth_records)
        total_san_lost = sum(record.sanity_lost for record in growth_records)
        total_experience = sum(record.experience_gained for record in growth_records)

        # スキル成長の統計
        skill_growth_stats = {}
        for record in growth_records:
            for skill_growth in record.skill_growths.all():
                skill_name = skill_growth.skill_name
                if skill_name not in skill_growth_stats:
                    skill_growth_stats[skill_name] = {"total_growth": 0, "growth_count": 0, "successful_checks": 0}

                skill_growth_stats[skill_name]["total_growth"] += skill_growth.growth_amount
                skill_growth_stats[skill_name]["growth_count"] += 1
                if skill_growth.is_growth_successful():
                    skill_growth_stats[skill_name]["successful_checks"] += 1

        summary = {
            "total_sessions": total_sessions,
            "total_san_gained": total_san_gained,
            "total_san_lost": total_san_lost,
            "net_san_change": total_san_gained - total_san_lost,
            "total_experience": total_experience,
            "skill_growth_stats": skill_growth_stats,
            "recent_sessions": GrowthRecordSerializer(growth_records[:5], many=True).data,
        }

        return Response(summary)
