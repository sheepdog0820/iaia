import logging

from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


class MediaDeletionUnavailable(APIException):
    status_code = 503
    default_detail = "添付ファイルを削除できませんでした。時間をおいて再試行してください。"
    default_code = "media_deletion_unavailable"


def delete_media_instance(instance):
    """Delete an already-authorized media model and expose only a retryable error."""
    object_id = instance.pk
    try:
        instance.delete()
    except Exception as exc:
        logger.warning(
            "Media deletion failed: model=%s id=%s error_type=%s",
            instance._meta.label_lower,
            object_id,
            type(exc).__name__,
        )
        raise MediaDeletionUnavailable() from None
