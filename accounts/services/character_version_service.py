"""Single, transactional implementation of character-sheet version creation."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.forms.models import model_to_dict

from accounts.character_models import (
    CharacterBackground,
    CharacterSheet,
    CharacterSheet6th,
    CharacterSheet7th,
)


class CharacterVersionService:
    """Create versions with lineage and data stored in the edition table."""

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
            source_data = source_character.system_data
            data_model = CharacterSheet6th if source_character.edition == "6th" else CharacterSheet7th
            locked_data = list(data_model.objects.select_for_update().all())
            root_data = cls._root_data_for(source_data)
            latest_version = max(
                data.version for data in locked_data if cls._belongs_to_data_root(data, root_data.pk, locked_data)
            )

            detail_data = cls._system_data(source_data)
            # The registry receives only registry-owned values.  Character
            # values are copied into the edition record below.
            registry_field_names = {field.name for field in CharacterSheet._meta.fields}
            registry_data = {
                key: value for key, value in detail_data.items() if key in registry_field_names
            }
            registry_data.update(
                user=source_character.user,
                edition=source_character.edition,
                access_scope=source_character.access_scope,
            )
            new_sheet = CharacterSheet.objects.create(**registry_data)
            new_sheet.allowed_users.set(source_character.allowed_users.all())

            detail_data.update(
                {
                    "character_sheet": new_sheet,
                    "parent_data": cls._parent_data_for(parent_character or source_character),
                    "version": latest_version + 1,
                    "version_note": validated_data.get("version_note", ""),
                    "session_count": validated_data.get("session_count", source_data.session_count + 1),
                }
            )
            for field in ("hit_points_current", "magic_points_current", "sanity_current", "notes"):
                if field in validated_data:
                    detail_data[field] = validated_data[field]
            target_data = data_model.objects.create(**detail_data)

            if policy["copy_background"]:
                cls._copy_background(source_character, new_sheet)
            if policy["copy_skills"]:
                cls._copy_related(source_data.skills.all(), source_data.skills.model, target_data)
            if policy["copy_equipment"]:
                cls._copy_related(source_data.equipment.all(), source_data.equipment.model, target_data)
            if policy["copy_images"]:
                cls._copy_related(source_data.images.all(), source_data.images.model, target_data)
            return new_sheet

    @staticmethod
    def _root_data_for(data):
        while data.parent_data_id:
            data = data.__class__.objects.select_for_update().get(pk=data.parent_data_id)
        return data

    @staticmethod
    def _belongs_to_data_root(data, root_id, records):
        parents = {record.pk: record.parent_data_id for record in records}
        current_id = data.pk
        while parents[current_id] is not None:
            current_id = parents[current_id]
        return current_id == root_id

    @staticmethod
    def _system_data(data):
        excluded = {"id", "character_sheet", "parent_data"}
        return {
            field.name: getattr(data, field.name)
            for field in data._meta.fields
            if field.name not in excluded
        }

    @staticmethod
    def _parent_data_for(character):
        return character.system_data

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
            data = {
                field.name: getattr(obj, field.name)
                for field in obj._meta.fields
                if field.name not in {"id", "character_sheet"}
                and not field.name.startswith("legacy_")
            }
            model.objects.create(character_sheet=target, **data)


def create_character_version(*, source_character, actor, validated_data=None, copy_policy=None, parent_character=None):
    return CharacterVersionService.create_version(
        source_character=source_character,
        actor=actor,
        validated_data=validated_data,
        copy_policy=copy_policy,
        parent_character=parent_character,
    )
