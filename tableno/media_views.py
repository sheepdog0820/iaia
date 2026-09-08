import posixpath

from django.conf import settings
from django.http import Http404
from django.views.static import serve

from scenarios.image_views import ScenarioImageContentView
from schedules.attachment_views import HandoutAttachmentDownloadView
from schedules.image_views import SessionImageContentView
from support.attachment_views import download_attachment


def serve_media(request, path):
    # Normalize before checking the private prefix, just as static.serve does.
    # Otherwise paths such as other/../handouts/... bypass the private route.
    normalized = posixpath.normpath(path).lstrip("/")
    # Work files use the owner-checked job API; retired template files have no public route.
    if normalized.startswith(("background_removal/", "session_template_images/")):
        raise Http404
    if normalized.startswith("support/line/"):
        return download_attachment(request, path=normalized[len("support/line/") :])
    if normalized.startswith("handouts/"):
        return HandoutAttachmentDownloadView.as_view()(request, path=normalized[len("handouts/") :])
    if normalized.startswith("session_images/"):
        return SessionImageContentView.as_view()(request, path=normalized[len("session_images/") :])
    if normalized.startswith("scenario_images/"):
        return ScenarioImageContentView.as_view()(request, path=normalized[len("scenario_images/") :])
    if not settings.DEBUG:
        raise Http404
    return serve(request, normalized, document_root=settings.MEDIA_ROOT)
