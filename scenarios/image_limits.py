from django.conf import settings

DEFAULT_SCENARIO_IMAGE_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_SCENARIO_IMAGE_MAX_FILES_PER_UPLOAD = 10


def get_scenario_image_max_bytes(user):
    """Use the existing normal-plan setting as the shared limit for every user."""
    return int(getattr(settings, "SCENARIO_IMAGE_NORMAL_MAX_BYTES", DEFAULT_SCENARIO_IMAGE_MAX_BYTES))


def get_scenario_image_max_files_per_upload(user):
    return int(
        getattr(
            settings,
            "SCENARIO_IMAGE_NORMAL_MAX_FILES_PER_UPLOAD",
            DEFAULT_SCENARIO_IMAGE_MAX_FILES_PER_UPLOAD,
        )
    )
