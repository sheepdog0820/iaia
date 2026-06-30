NORMAL_CHARACTER_IMAGE_LIMIT = 2
PREMIUM_CHARACTER_IMAGE_LIMIT = 10


def get_character_image_limit(user):
    """Return the maximum number of character images for a user."""
    return PREMIUM_CHARACTER_IMAGE_LIMIT if getattr(user, "is_premium", False) else NORMAL_CHARACTER_IMAGE_LIMIT


def get_character_image_limit_for_sheet(character_sheet):
    return get_character_image_limit(getattr(character_sheet, "user", None))


def character_image_limit_error_message(limit):
    return f"1キャラクターにつき最大{limit}枚まで画像をアップロードできます。"


def collect_character_image_uploads(files):
    """Collect legacy and multiple character image uploads from a MultiValueDict."""
    image_files = []
    for key in ("character_image", "character_images", "images"):
        if key in files:
            image_files.extend(files.getlist(key))
    return [image_file for image_file in image_files if image_file]
