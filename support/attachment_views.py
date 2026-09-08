from pathlib import PurePosixPath

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_vary_headers
from django.views.decorators.cache import never_cache

from support.models import SupportMessage


@never_cache
def download_attachment(request, pk=None, path=None):
    user = request.user
    if not user.is_authenticated or not user.is_active or not user.is_staff:
        raise Http404
    for model in ("supportticket", "supportmessage"):
        if not (user.has_perm(f"support.view_{model}") or user.has_perm(f"support.change_{model}")):
            raise Http404
    lookup = {"pk": pk} if pk is not None else {"attachment": f"support/line/{path}"}
    message = get_object_or_404(SupportMessage, **lookup)
    if not message.attachment:
        raise Http404
    try:
        handle = message.attachment.open("rb")
    except FileNotFoundError:
        raise Http404 from None
    response = FileResponse(
        handle,
        as_attachment=True,
        filename=PurePosixPath(message.attachment.name).name,
        content_type="application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    patch_vary_headers(response, ("Cookie",))
    return response
