"""Single, transactional implementation of character-sheet version creation."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.forms.models import model_to_dict

from accounts.character_models import (
    CharacterBackground,
    CharacterEquipment,
    CharacterImage,
    CharacterSheet,
    CharacterSheet6th,
    CharacterSkill,
)


class CharacterVersionService:
    """Create character versions consistently for API, model and rollback callers."""

    DEFAULT_COPY_POLICY = {
        "copy_skills": True,
        "copy_equipment": True,
        "copy_images": True,
        "copy_background": True,
    }

    @classmethod
    def create_version(cls, *, source_character, actor, validated_data=None, copy_policy=None, parent_character=None):
        validated_data = validated_data or {}
        policy = cls.DEFAULT_COPY_POLICY | (copy_policy or {})
        policy.update({key: validated_data[key] for key in policy if key in validated_data})

        if len(validated_data.get("version_note", "")) > 1000:
            raise ValidationError("Version notes must not exceed 1000 characters.")

        if actor is not None and actor.pk != source_character.user_id:
            raise PermissionDenied("Only the owner can create a character version.")

        with transaction.atomic():
            source_character = CharacterSheet.objects.select_for_update().get(pk=source_character.pk)
            root = cls._root_for(source_character)
            locked_sheets = list(CharacterSheet.objects.select_for_update().all())
            latest_version = max(
                sheet.version for sheet in locked_sheets if cls._belongs_to_root(sheet, root.pk, locked_sheets)
            )

            sheet_data = cls._sheet_data(source_character)
            sheet_data.update(
                {
                    "user": source_character.user,
                    "parent_sheet": parent_character or source_character,
                    "version": latest_version + 1,
                    "version_note": validated_data.get("version_note", ""),
                    "session_count": validated_data.get("session_count", source_character.session_count + 1),
                }
            )
            for field in ("hit_points_current", "magic_points_current", "sanity_current", "notes"):
                if field in validated_data:
                    sheet_data[field] = validated_data[field]
            new_sheet = CharacterSheet.objects.create(**sheet_data)
            new_sheet.allowed_users.set(source_character.allowed_users.all())

            cls._copy_sixth_data(source_character, new_sheet)
            if policy["copy_background"]:
                cls._copy_background(source_character, new_sheet)
            if policy["copy_skills"]:
                cls._copy_related(source_character.skills.all(), CharacterSkill, new_sheet)
            if policy["copy_equipment"]:
                cls._copy_related(source_character.equipment.all(), CharacterEquipment, new_sheet)
            if policy["copy_images"]:
                cls._copy_related(source_character.images.all(), CharacterImage, new_sheet)
            return new_sheet

    @staticmethod
    def _root_for(character):
        while character.parent_sheet_id:
            character = CharacterSheet.objects.select_for_update().get(pk=character.parent_sheet_id)
        return character

    @staticmethod
    def _belongs_to_root(character, root_id, sheets):
        parents = {sheet.pk: sheet.parent_sheet_id for sheet in sheets}
        current_id = character.pk
        while parents[current_id] is not None:
            current_id = parents[current_id]
        return current_id == root_id

    @staticmethod
    def _sheet_data(character):
        excluded = {"id", "parent_sheet", "version", "share_token", "created_at", "updated_at", "allowed_users"}
        return {key: value for key, value in model_to_dict(character).items() if key not in excluded}

    @staticmethod
    def _copy_sixth_data(source, target):
        try:
            source_data = source.sixth_edition_data
        except CharacterSheet6th.DoesNotExist:
            return
        data = model_to_dict(source_data, exclude=["id", "character_sheet"])
        CharacterSheet6th.objects.create(character_sheet=target, **data)

    @staticmethod
    def _copy_background(source, target):
        try:
            background = source.background_info
        except CharacterBackground.DoesNotExist:
            return
        data = model_to_dict(background, exclude=["id", "character_sheet"])
        CharacterBackground.objects.create(character_sheet=target, **data)

    @staticmethod
    def _copy_related(objects, model, target):
        for obj in objects:
            data = model_to_dict(obj, exclude=["id", "character_sheet"])
            model.objects.create(character_sheet=target, **data)


def create_character_version(*, source_character, actor, validated_data=None, copy_policy=None, parent_character=None):
    return CharacterVersionService.create_version(
        source_character=source_character,
        actor=actor,
        validated_data=validated_data,
        copy_policy=copy_policy,
        parent_character=parent_character,
    )
