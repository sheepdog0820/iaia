"""
ハンドアウト添付ファイルAPI

エンドポイント:
- GET/POST /api/schedules/handouts/<handout_id>/attachments/
- DELETE   /api/schedules/attachments/<pk>/
"""

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from schedules.attachment_service import HandoutAttachmentService
from schedules.handout_access import can_view_handout
from schedules.models import HandoutAttachment, HandoutInfo
from schedules.serializers import HandoutAttachmentSerializer


def _user_can_view_handout(handout: HandoutInfo, user) -> bool:
    return can_view_handout(handout, user)


@method_decorator(never_cache, name="dispatch")
class HandoutAttachmentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None, path=None):
        lookup = {"pk": pk} if pk is not None else {"file": f"handouts/{path}"}
        attachment = get_object_or_404(
            HandoutAttachment.objects.select_related("handout__session", "handout__participant"), **lookup
        )
        if not can_view_handout(attachment.handout, request.user) or not attachment.file:
            raise Http404
        try:
            handle = attachment.file.open("rb")
        except FileNotFoundError:
            raise Http404 from None
        response = FileResponse(
            handle,
            as_attachment=True,
            filename=attachment.original_filename,
            content_type="application/octet-stream",
        )
        response["X-Content-Type-Options"] = "nosniff"
        patch_vary_headers(response, ("Cookie", "Authorization"))
        return response


class HandoutAttachmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, handout_id: int):
        handout = get_object_or_404(
            HandoutInfo.objects.select_related("session"),
            id=handout_id,
        )
        if not _user_can_view_handout(handout, request.user):
            return Response(
                {"error": "このハンドアウトにアクセスする権限がありません"}, status=status.HTTP_403_FORBIDDEN
            )

        attachments = HandoutAttachment.objects.filter(handout_id=handout.id).order_by("created_at")
        serializer = HandoutAttachmentSerializer(attachments, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, handout_id: int):
        handout = get_object_or_404(
            HandoutInfo.objects.select_related("session"),
            id=handout_id,
        )

        service = HandoutAttachmentService()
        try:
            attachment = service.upload_attachment(
                handout=handout,
                file=request.FILES.get("file"),
                uploaded_by=request.user,
                description=request.data.get("description", ""),
            )
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            # ValidationError も含めて 400 で返す
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HandoutAttachmentSerializer(attachment, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class HandoutAttachmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk: int):
        attachment = HandoutAttachment.objects.select_related("handout__session").filter(id=pk).first()
        if not attachment:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        if not _user_can_view_handout(attachment.handout, request.user):
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        service = HandoutAttachmentService()
        try:
            ok = service.delete_attachment(pk, request.user)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        if not ok:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
