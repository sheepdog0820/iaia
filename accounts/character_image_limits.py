NORMAL_CHARACTER_IMAGE_LIMIT = 5
PREMIUM_CHARACTER_IMAGE_LIMIT = NORMAL_CHARACTER_IMAGE_LIMIT


def get_character_image_limit(user):
    """All plans share the same character image limit."""
    return NORMAL_CHARACTER_IMAGE_LIMIT


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
