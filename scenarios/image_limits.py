from django.conf import settings

DEFAULT_SCENARIO_IMAGE_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_SCENARIO_IMAGE_MAX_FILES_PER_UPLOAD = 10


def _has_premium_access(user):
    return bool(getattr(user, "has_premium_access", False))


def get_scenario_image_max_bytes(user):
    setting_name = (
        "SCENARIO_IMAGE_PREMIUM_MAX_BYTES" if _has_premium_access(user) else "SCENARIO_IMAGE_NORMAL_MAX_BYTES"
    )
    return int(getattr(settings, setting_name, DEFAULT_SCENARIO_IMAGE_MAX_BYTES))


def get_scenario_image_max_files_per_upload(user):
    setting_name = (
        "SCENARIO_IMAGE_PREMIUM_MAX_FILES_PER_UPLOAD"
        if _has_premium_access(user)
        else "SCENARIO_IMAGE_NORMAL_MAX_FILES_PER_UPLOAD"
    )
    return int(
        getattr(
            settings,
            setting_name,
            DEFAULT_SCENARIO_IMAGE_MAX_FILES_PER_UPLOAD,
        )
    )
