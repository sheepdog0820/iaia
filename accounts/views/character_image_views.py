"""
キャラクター画像管理ビュー
画像のアップロード・並び替え・削除などを提供
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db import transaction
from accounts.models import CharacterSheet, CharacterImage
from accounts.serializers import CharacterImageSerializer
import logging

logger = logging.getLogger(__name__)


class CharacterImageViewSet(viewsets.ModelViewSet):
    """キャラクター画像の管理ViewSet"""
    serializer_class = CharacterImageSerializer
    permission_classes = [IsAuthenticated]

    _character_sheet = None

    def _get_character_sheet(self, require_owner=False):
        """URLパラメータからキャラクターシートを取得（必要に応じて所有者チェック）"""
        if self._character_sheet is None:
            character_id = self.kwargs.get("character_sheet_id") or self.kwargs.get("character_id")
            self._character_sheet = get_object_or_404(CharacterSheet, pk=character_id)

        if require_owner and self._character_sheet.user != self.request.user:
            raise PermissionDenied("このキャラクターの画像にはアクセスできません。")

        return self._character_sheet

    def get_queryset(self):
        """キャラクターに紐づく画像のクエリセット（所有者のみ）"""
        character = self._get_character_sheet(require_owner=True)
        return CharacterImage.objects.filter(character_sheet=character)

    def get_serializer_context(self):
        """シリアライザーのコンテキストにキャラクターシートを追加"""
        context = super().get_serializer_context()
        context["character_sheet"] = self._get_character_sheet(require_owner=True)
        return context

    def create(self, request, *args, **kwargs):
        """画像のアップロード"""
        character = self._get_character_sheet(require_owner=True)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image = serializer.save()

        # 最初の画像は自動でメインに設定
        if character.images.count() == 1:
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
                    image = CharacterImage.objects.get(pk=image_id, character_sheet=character)
                    image.order = new_order
                    image.save()
                except CharacterImage.DoesNotExist:
                    logger.warning(f"画像が見つかりません: image_id={image_id}")

        images = character.images.all()
        serializer = self.get_serializer(images, many=True)
        return Response({"count": images.count(), "results": serializer.data})

    @action(detail=True, methods=["patch"], url_path="set-main")
    def set_main(self, request, pk=None, **kwargs):
        """メイン画像の設定"""
        character = self._get_character_sheet(require_owner=True)

        image = get_object_or_404(CharacterImage, pk=pk, character_sheet=character)

        with transaction.atomic():
            CharacterImage.objects.filter(character_sheet=character, is_main=True).update(is_main=False)
            image.is_main = True
            image.save()

        serializer = self.get_serializer(image)
        return Response(serializer.data, status=status.HTTP_200_OK)
