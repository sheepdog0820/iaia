import os

from django.db import models as django_models

from .character_image_utils import get_character_preview_image_url


def build_character_detail_context(
    request,
    character,
    *,
    is_public_view=False,
    is_shared_view=False,
    can_edit_character=False,
    shared_api_url="",
    images_api_url="",
    images_zip_url="",
    ccfolia_json_url="",
    reference_url="",
    preview_image_url=None,
):
    system_data = character.system_data
    assigned_skills = system_data.skills.filter(current_value__gt=django_models.F("base_value")).order_by("skill_name")
    weapons = system_data.equipment.filter(item_type="weapon")
    armor = system_data.equipment.filter(item_type="armor")
    items = system_data.equipment.filter(item_type="item")

    versions = []
    if not is_public_view:
        versions = character.get_version_history()

    if preview_image_url is None:
        preview_image_url = get_character_preview_image_url(character, request)

    character_image_file_names = []
    if can_edit_character:
        character_image_file_names = [
            os.path.basename(image.image.name) for image in system_data.images.order_by("order", "id") if image.image
        ]

    context = {
        "character": character,
        "character_system_data": system_data,
        "character_id": character.id,
        "is_public_view": is_public_view,
        "is_shared_view": is_shared_view,
        "can_edit_character": can_edit_character,
        "character_og_image_url": preview_image_url,
        "assigned_skills": assigned_skills,
        "weapons": weapons,
        "armor": armor,
        "items": items,
        "versions": versions,
        "character_image_file_names": character_image_file_names,
    }

    optional_urls = {
        "character_shared_api_url": shared_api_url,
        "character_images_api_url": images_api_url,
        "character_images_zip_url": images_zip_url,
        "character_ccfolia_json_url": ccfolia_json_url,
        "character_reference_url": reference_url,
    }
    context.update({key: value for key, value in optional_urls.items() if value})
    return context
