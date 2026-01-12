"""
ハンドアウト添付ファイルのサービス層。

モデル/バリデーションを直接扱う処理をまとめ、API/ビューから利用する。
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass

from django.core.exceptions import ValidationError

from schedules.models import HandoutAttachment, HandoutInfo, SessionParticipant


@dataclass(frozen=True)
class UploadResult:
    attachment: HandoutAttachment


class HandoutAttachmentService:
    """ハンドアウト添付ファイルの操作を提供するサービス"""

    def _require_access(self, handout: HandoutInfo, user) -> None:
        session = handout.session
        if session.gm_id == getattr(user, 'id', None):
            return
        if SessionParticipant.objects.filter(session_id=session.id, user_id=getattr(user, 'id', None)).exists():
            return
        raise PermissionError("この添付ファイルにアクセスする権限がありません。")

    def _require_gm(self, handout: HandoutInfo, user) -> None:
        if handout.session.gm_id != getattr(user, 'id', None):
            raise PermissionError("GMのみが添付ファイルを操作できます。")

    def _detect_file_type(self, content_type: str) -> str:
        for file_type, supported in HandoutAttachment.SUPPORTED_CONTENT_TYPES.items():
            if content_type in supported:
                return file_type
        raise ValidationError(f"サポートされていないファイル形式です: {content_type}")

    def upload_attachment(self, *, handout: HandoutInfo, file, uploaded_by, description: str = "") -> HandoutAttachment:
        self._require_gm(handout, uploaded_by)

        content_type = getattr(file, 'content_type', None) or mimetypes.guess_type(getattr(file, 'name', '') or '')[0] or ''
        file_type = self._detect_file_type(content_type)

        file_size = getattr(file, 'size', None) or 0
        max_size = HandoutAttachment.MAX_FILE_SIZE.get(file_type)
        if max_size and file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise ValidationError(
                f"{dict(HandoutAttachment.FILE_TYPE_CHOICES).get(file_type, file_type)}ファイルのサイズは{max_size_mb}MB以下である必要があります"
            )

        attachment = HandoutAttachment(
            handout=handout,
            file=file,
            original_filename=getattr(file, 'name', '') or 'upload',
            file_type=file_type,
            file_size=file_size,
            content_type=content_type,
            description=description or '',
            uploaded_by=uploaded_by,
        )
        attachment.full_clean()
        attachment.save()
        return attachment

    def delete_attachment(self, attachment_id: int, user) -> bool:
        attachment = HandoutAttachment.objects.select_related('handout__session').filter(id=attachment_id).first()
        if not attachment:
            return False

        # 削除はGMまたはアップロード者に限定
        if attachment.handout.session.gm_id != getattr(user, 'id', None) and attachment.uploaded_by_id != getattr(user, 'id', None):
            raise PermissionError("この添付ファイルを削除する権限がありません。")

        if attachment.file:
            try:
                attachment.file.delete(save=False)
            except Exception:
                pass
        attachment.delete()
        return True

    def get_attachment_url(self, attachment: HandoutAttachment, user) -> str:
        self._require_access(attachment.handout, user)
        return attachment.get_download_url()

