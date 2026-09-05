import posixpath

from django.conf import settings
from django.http import Http404
from django.views.static import serve

from schedules.attachment_views import HandoutAttachmentDownloadView
from schedules.image_views import SessionImageContentView


def serve_media(request, path):
    # Normalize before checking the private prefix, just as static.serve does.
    # Otherwise paths such as other/../handouts/... bypass the private route.
    normalized = posixpath.normpath(path).lstrip("/")
    if normalized.startswith("handouts/"):
        return HandoutAttachmentDownloadView.as_view()(request, path=normalized[len("handouts/") :])
    if normalized.startswith("session_images/"):
        return SessionImageContentView.as_view()(request, path=normalized[len("session_images/") :])
    if not settings.DEBUG:
        raise Http404
    return serve(request, normalized, document_root=settings.MEDIA_ROOT)
