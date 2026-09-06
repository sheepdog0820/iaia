"""
キャラクター画像管理ビュー
画像のアップロード・並び替え・削除などを提供
"""

import io
import logging
import math
import os
import re
import warnings
import zipfile
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import Http404, HttpResponse
from django.http.response import content_disposition_header
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from PIL import Image, UnidentifiedImageError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.background_removal_tasks import (
    clear_background_removal_source,
    fail_stale_background_removal_job,
    start_background_removal_task,
)
from accounts.models import BackgroundRemovalJob, CharacterSheet
from accounts.serializers import CharacterImageSerializer
from accounts.views.mixins import CharacterSheetAccessMixin

logger = logging.getLogger(__name__)

ZIP_IMAGE_ORDERING = ("order", "uploaded_at", "id")
ZIP_CONTENT_TYPE = "application/zip"
BACKGROUND_REMOVAL_MAX_DIMENSION = 4096
BACKGROUND_REMOVAL_MAX_PIXELS = 16_000_000
BACKGROUND_REMOVAL_ALLOWED_FORMATS = {"JPEG", "PNG", "GIF"}


def _validate_background_removal_image(image_bytes, *, allowed_formats):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as opened_image:
                opened_image.verify()
            with Image.open(io.BytesIO(image_bytes)) as opened_image:
                if opened_image.format not in allowed_formats:
                    return "Unsupported image format."
                if (
                    opened_image.width > BACKGROUND_REMOVAL_MAX_DIMENSION
                    or opened_image.height > BACKGROUND_REMOVAL_MAX_DIMENSION
                ):
                    return f"Image dimensions must not exceed {BACKGROUND_REMOVAL_MAX_DIMENSION}px."
                if opened_image.width * opened_image.height > BACKGROUND_REMOVAL_MAX_PIXELS:
                    return "Image contains too many pixels."
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError):
        return "A valid image file is required."

    return None


class CharacterImageBackgroundRemovalView(APIView):
    """Queue portrait background removal for premium users."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not getattr(request.user, "is_premium", False):
            raise PermissionDenied("Background removal is a premium feature.")

        image = request.FILES.get("image")
        if image is None:
            return Response({"error": "image is required"}, status=status.HTTP_400_BAD_REQUEST)
        if image.size > 5 * 1024 * 1024:
            return Response({"error": "Image size must be 5MB or less."}, status=status.HTTP_400_BAD_REQUEST)

        source = image.read()
        validation_error = _validate_background_removal_image(
            source,
            allowed_formats=BACKGROUND_REMOVAL_ALLOWED_FORMATS,
        )
        if validation_error:
            return Response({"error": validation_error}, status=status.HTTP_400_BAD_REQUEST)

        original_filename = _safe_original_filename(image)[:255]
        with transaction.atomic():
            get_user_model().objects.select_for_update().only("pk").get(pk=request.user.pk)
            now = timezone.now()
            local_now = timezone.localtime(now)
            usage_started_at = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            usage_resets_at = usage_started_at + timedelta(days=1)
            daily_limit = max(int(getattr(settings, "BACKGROUND_REMOVAL_DAILY_LIMIT", 10)), 1)
            used_count = BackgroundRemovalJob.objects.filter(
                user=request.user,
                created_at__gte=usage_started_at,
                created_at__lt=usage_resets_at,
            ).count()
            if used_count >= daily_limit:
                retry_after = max(math.ceil((usage_resets_at - local_now).total_seconds()), 1)
                return Response(
                    {
                        "error": (
                            f"本日の背景透過処理回数の上限（{daily_limit}回）に達しました。"
                            "翌日0時以降に再度お試しください。"
                        ),
                        "daily_limit": daily_limit,
                        "used_count": used_count,
                        "reset_at": usage_resets_at.isoformat(),
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(retry_after)},
                )
            active_jobs = list(
                BackgroundRemovalJob.objects.select_for_update().filter(
                    user=request.user,
                    status__in=(BackgroundRemovalJob.Status.PENDING, BackgroundRemovalJob.Status.RUNNING),
                )
            )
            active_jobs = [job for job in active_jobs if not fail_stale_background_removal_job(job)]
            if active_jobs:
                return Response(
                    {"error": "Another background removal job is already running."},
                    status=status.HTTP_409_CONFLICT,
                )
            job = BackgroundRemovalJob.objects.create(
                user=request.user,
                original_filename=original_filename,
                source_image=ContentFile(source, name=original_filename),
            )
        try:
            start_background_removal_task(job)
        except Exception:
            logger.exception("Character image background removal task could not start")
            job.status = BackgroundRemovalJob.Status.FAILED
            job.error_message = "Background removal could not be started."
            update_fields = ["status", "error_message", "updated_at"]
            if clear_background_removal_source(job):
                update_fields.append("source_image")
            job.save(update_fields=update_fields)
            return Response({"error": job.error_message}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(
            {
                "job_id": str(job.pk),
                "status": job.status,
                "status_url": reverse("character-image-background-removal-status", args=[job.pk]),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class CharacterImageBackgroundRemovalStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        with transaction.atomic():
            job = get_object_or_404(
                BackgroundRemovalJob.objects.select_for_update(),
                pk=job_id,
                user=request.user,
            )
            fail_stale_background_removal_job(job)
        if job.status == BackgroundRemovalJob.Status.COMPLETED:
            if not job.result_image:
                return Response(
                    {"error": "Background removal result is unavailable."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            with job.result_image.open("rb") as result_file:
                response = HttpResponse(result_file.read(), content_type="image/png")
            filename_root = os.path.splitext(_safe_original_filename(job.original_filename))[0] or "character"
            response["Content-Disposition"] = content_disposition_header(
                "attachment",
                filename=f"{filename_root}-transparent.png",
            )
            return response
        if job.status == BackgroundRemovalJob.Status.FAILED:
            return Response(
                {"error": job.error_message or "Background removal could not be completed."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"job_id": str(job.pk), "status": job.status}, status=status.HTTP_202_ACCEPTED)


def can_read_character_images(character_sheet, user):
    """Return whether a user can read images attached to a character sheet."""
    if CharacterSheetAccessMixin.is_publicly_readable(character_sheet):
        return True
    if user and user.is_authenticated:
        return CharacterSheetAccessMixin.can_read_character_sheet(character_sheet, user)
    return False


def _safe_original_filename(field_file):
    raw_name = field_file if isinstance(field_file, str) else getattr(field_file, "name", "")
    basename = os.path.basename(raw_name or "")
    basename = re.sub(r"^\d+_[0-9a-f]{8}_", "", basename)
    basename = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", basename).strip(" ._")
    return basename or "image"


def _unique_zip_name(filename, used_names):
    if filename not in used_names:
        used_names.add(filename)
        return filename

    base, ext = os.path.splitext(filename)
    suffix = 2
    while True:
        candidate = f"{base}_{suffix}{ext}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        suffix += 1


def _zip_entry_prefix(index, character_image):
    prefix = f"{index:02d}_"
    if character_image.is_main:
        prefix += "main_"
    return prefix


def _collect_zip_entries(character_sheet):
    detail = character_sheet.system_data
    images = list(detail.images.order_by(*ZIP_IMAGE_ORDERING))
    if images:
        return [
            (_zip_entry_prefix(index, character_image), character_image.image)
            for index, character_image in enumerate(images, start=1)
        ]

    if detail.character_image:
        return [("01_main_", detail.character_image)]

    return []


def _read_storage_file(field_file):
    if not field_file or not getattr(field_file, "name", ""):
        return None

    try:
        with field_file.storage.open(field_file.name, "rb") as image_file:
            return image_file.read()
    except Exception:
        logger.warning(
            "Failed to add character image to ZIP: %s",
            getattr(field_file, "name", ""),
            exc_info=True,
        )
        return None


def _write_zip_entries(archive, zip_entries):
    used_names = set()
    written_count = 0

    for prefix, field_file in zip_entries:
        content = _read_storage_file(field_file)
        if content is None:
            continue

        member_name = _unique_zip_name(
            f"{prefix}{_safe_original_filename(field_file)}",
            used_names,
        )
        archive.writestr(member_name, content)
        written_count += 1

    return written_count


def build_character_images_zip_response(character_sheet):
    zip_entries = _collect_zip_entries(character_sheet)
    output = io.BytesIO()

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        written_count = _write_zip_entries(archive, zip_entries)

    if written_count == 0:
        raise Http404("Character images not found")

    payload = output.getvalue()
    filename_root = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", character_sheet.system_data.name or "character")
    filename_root = filename_root.strip(" ._") or "character"
    filename = f"{filename_root}.zip"
    response = HttpResponse(payload, content_type=ZIP_CONTENT_TYPE)
    response["Content-Disposition"] = content_disposition_header("attachment", filename=filename)
    response["Content-Length"] = str(len(payload))
    return response


@method_decorator(never_cache, name="dispatch")
class CharacterImageViewSet(viewsets.ModelViewSet):
    """キャラクター画像の管理ViewSet"""

    serializer_class = CharacterImageSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ["GET", "HEAD", "OPTIONS"]:
            return [AllowAny()]
        return super().get_permissions()

    _character_sheet = None

    def _requires_owner(self):
        return self.request.method not in ["GET", "HEAD", "OPTIONS"]

    def _get_character_sheet(self, require_owner=False):
        """URLパラメータからキャラクターシートを取得（必要に応じて所有者チェック）"""
        if self._character_sheet is None:
            character_id = self.kwargs.get("character_sheet_id") or self.kwargs.get("character_id")
            self._character_sheet = get_object_or_404(CharacterSheet, pk=character_id)

        if require_owner and self._character_sheet.user != self.request.user:
            raise PermissionDenied("このキャラクターの画像にはアクセスできません。")
        if not require_owner and not can_read_character_images(self._character_sheet, self.request.user):
            raise Http404("Character sheet not found")

        return self._character_sheet

    def get_queryset(self):
        """キャラクターに紐づく画像のクエリセット（所有者のみ）"""
        character = self._get_character_sheet(require_owner=self._requires_owner())
        return character.system_data.images.all()

    def get_serializer_context(self):
        """シリアライザーのコンテキストにキャラクターシートを追加"""
        context = super().get_serializer_context()
        context["character_sheet"] = self._get_character_sheet(require_owner=self._requires_owner())
        return context

    def create(self, request, *args, **kwargs):
        """画像のアップロード"""
        character = self._get_character_sheet(require_owner=True)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image = serializer.save()

        # 最初の画像は自動でメインに設定
        if character.system_data.images.count() == 1:
            image.is_main = True
            image.save()

        response_serializer = self.get_serializer(image)
        logger.info(f"画像アップロード成功: character_id={character.id}, image_id={image.id}")

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """画像一覧の取得"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response({"count": queryset.count(), "results": serializer.data})

    @action(detail=False, methods=["get"], url_path="download")
    def download(self, request, **kwargs):
        """Download all readable character images as a ZIP archive."""
        character = self._get_character_sheet(require_owner=False)
        return build_character_images_zip_response(character)

    def destroy(self, request, *args, **kwargs):
        """画像の削除"""
        instance = self.get_object()
        character = instance.character_sheet

        # メイン画像を削除する場合は先にフラグを外し、他の画像をメインに
        if instance.is_main:
            instance.is_main = False
            instance.save(update_fields=["is_main"])
            other_images = character.images.exclude(pk=instance.pk).order_by("order")
            if other_images.exists():
                other = other_images.first()
                other.is_main = True
                other.save(update_fields=["is_main"])

        if instance.image:
            instance.image.delete()

        instance.delete()
        logger.info(f"画像削除成功: image_id={instance.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["patch"], url_path="reorder")
    def reorder(self, request, **kwargs):
        """画像の並び順変更"""
        character = self._get_character_sheet(require_owner=True)

        order_data = request.data.get("order", [])

        with transaction.atomic():
            for item in order_data:
                image_id = item.get("id")
                new_order = item.get("order")
                if image_id is None or new_order is None:
                    continue
                try:
                    image = character.system_data.images.get(pk=image_id)
                    image.order = new_order
                    image.save()
                except character.system_data.images.model.DoesNotExist:
                    logger.warning(f"画像が見つかりません: image_id={image_id}")

        images = character.system_data.images.all()
        serializer = self.get_serializer(images, many=True)
        return Response({"count": images.count(), "results": serializer.data})

    @action(detail=True, methods=["patch"], url_path="set-main")
    def set_main(self, request, pk=None, **kwargs):
        """メイン画像の設定"""
        character = self._get_character_sheet(require_owner=True)

        image = get_object_or_404(character.system_data.images.model, pk=pk, character_sheet=character.system_data)

        with transaction.atomic():
            character.system_data.images.filter(is_main=True).update(is_main=False)
            image.is_main = True
            image.save()

        serializer = self.get_serializer(image)
        return Response(serializer.data, status=status.HTTP_200_OK)
