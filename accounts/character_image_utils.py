"""Helpers for resolving character sheet image URLs."""

from django.core.exceptions import ObjectDoesNotExist


def _image_url(image_field):
    if not image_field:
        return ""
    try:
        return image_field.url
    except ValueError:
        return ""


def get_character_preview_image_field(character):
    """Return the image field that should represent a character in previews."""
    if not character:
        return None

    try:
        detail = character.system_data
    except (AttributeError, ValueError, ObjectDoesNotExist):
        detail = character

    image_field = None
    images = getattr(detail, "images", None)
    if images is not None:
        main_image = images.filter(is_main=True).order_by("order", "uploaded_at", "id").first()
        if main_image and main_image.image:
            image_field = main_image.image
        else:
            first_image = images.order_by("order", "uploaded_at", "id").first()
            if first_image and first_image.image:
                image_field = first_image.image

    if not image_field:
        image_field = getattr(detail, "character_image", None)

    return image_field


def get_character_preview_image_url(character, request=None):
    """Return the image URL that should represent a character in previews."""
    image_field = get_character_preview_image_field(character)
    url = _image_url(image_field)
    if url and request:
        return request.build_absolute_uri(url)
    return url
