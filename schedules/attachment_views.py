"""
ハンドアウト添付ファイルAPI

エンドポイント:
- GET/POST /api/schedules/handouts/<handout_id>/attachments/
- DELETE   /api/schedules/attachments/<pk>/
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from schedules.attachment_service import HandoutAttachmentService
from schedules.models import HandoutAttachment, HandoutInfo, SessionParticipant
from schedules.serializers import HandoutAttachmentSerializer


def _user_can_view_handout(handout: HandoutInfo, user) -> bool:
    if handout.session.gm_id == user.id:
        return True
    return SessionParticipant.objects.filter(session_id=handout.session_id, user_id=user.id).exists()


class HandoutAttachmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, handout_id: int):
        handout = get_object_or_404(
            HandoutInfo.objects.select_related('session'),
            id=handout_id,
        )
        if not _user_can_view_handout(handout, request.user):
            return Response({'error': 'このハンドアウトにアクセスする権限がありません'}, status=status.HTTP_403_FORBIDDEN)

        attachments = HandoutAttachment.objects.filter(handout_id=handout.id).order_by('created_at')
        serializer = HandoutAttachmentSerializer(attachments, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, handout_id: int):
        handout = get_object_or_404(
            HandoutInfo.objects.select_related('session'),
            id=handout_id,
        )

        service = HandoutAttachmentService()
        try:
            attachment = service.upload_attachment(
                handout=handout,
                file=request.FILES.get('file'),
                uploaded_by=request.user,
                description=request.data.get('description', ''),
            )
        except PermissionError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            # ValidationError も含めて 400 で返す
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HandoutAttachmentSerializer(attachment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class HandoutAttachmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk: int):
        attachment = HandoutAttachment.objects.select_related('handout__session').filter(id=pk).first()
        if not attachment:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        service = HandoutAttachmentService()
        try:
            ok = service.delete_attachment(pk, request.user)
        except PermissionError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        if not ok:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

