"""Factories for tests that exercise the split character-sheet schema."""

from .character_models import CharacterSheet, CharacterSheet6th, CharacterSheet7th


def create_character_with_system_data(*, user, edition="6th", **values):
    """Create a registry and its edition record without parent-field shortcuts."""
    edition = values.pop("edition", edition)
    registry_fields = {key: values.pop(key) for key in ("access_scope",) if key in values}
    registry = CharacterSheet.objects.create(user=user, edition=edition, **registry_fields)
    detail_model = CharacterSheet6th if edition == "6th" else CharacterSheet7th
    detail = detail_model.objects.create(character_sheet=registry, **values)
    return registry, detail


def create_6th_character(*, user, **values):
    values.pop("edition", None)
    return create_character_with_system_data(user=user, edition="6th", **values)


def create_7th_character(*, user, **values):
    values.pop("edition", None)
    return create_character_with_system_data(user=user, edition="7th", **values)
