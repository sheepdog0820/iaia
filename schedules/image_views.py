from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny

from schedules.models import SessionImage
from schedules.session_permissions import can_view_session_basic


@method_decorator(never_cache, name="dispatch")
class SessionImageContentView(GenericAPIView):
    permission_classes = [AllowAny]
    queryset = SessionImage.objects.none()

    @extend_schema(
        responses={
            (200, "image/png"): OpenApiTypes.BINARY,
            (200, "image/jpeg"): OpenApiTypes.BINARY,
            (200, "image/gif"): OpenApiTypes.BINARY,
            (200, "image/webp"): OpenApiTypes.BINARY,
            (200, "application/octet-stream"): OpenApiTypes.BINARY,
        }
    )
    def get(self, request, pk=None, path=None):
        lookup = {"pk": pk} if pk is not None else {"image": f"session_images/{path}"}
        picture = get_object_or_404(SessionImage.objects.select_related("session"), **lookup)
        if not can_view_session_basic(request.user, picture.session) or not picture.image:
            raise Http404
        try:
            handle = picture.image.open("rb")
        except FileNotFoundError:
            raise Http404 from None
        response = FileResponse(handle)
        if response["Content-Type"] not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
            response["Content-Type"] = "application/octet-stream"
            response["Content-Disposition"] = "attachment"
        response["X-Content-Type-Options"] = "nosniff"
        patch_vary_headers(response, ("Cookie", "Authorization"))
        return response
