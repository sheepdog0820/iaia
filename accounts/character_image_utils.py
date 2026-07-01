"""Helpers for resolving character sheet image URLs."""


def _image_url(image_field):
    if not image_field:
        return ''
    try:
        return image_field.url
    except ValueError:
        return ''


def get_character_preview_image_url(character, request=None):
    """Return the image URL that should represent a character in previews."""
    if not character:
        return ''

    image_field = None
    images = getattr(character, 'images', None)
    if images is not None:
        main_image = images.filter(is_main=True).order_by('order', 'uploaded_at', 'id').first()
        if main_image and main_image.image:
            image_field = main_image.image
        else:
            first_image = images.order_by('order', 'uploaded_at', 'id').first()
            if first_image and first_image.image:
                image_field = first_image.image

    if not image_field and character.character_image:
        image_field = character.character_image

    url = _image_url(image_field)
    if url and request:
        return request.build_absolute_uri(url)
    return url
