"""
キャラクター画像管理ビュー
複数画像のアップロード・管理機能を提供
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from accounts.models import CharacterSheet, CharacterImage
from accounts.serializers import CharacterImageSerializer
import logging

logger = logging.getLogger(__name__)


class CharacterImageViewSet(viewsets.ModelViewSet):
    """キャラクター画像の管理ViewSet"""
    serializer_class = CharacterImageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """キャラクターに紐づく画像のクエリセット"""
        character_id = self.kwargs.get('character_id')
        character = get_object_or_404(
            CharacterSheet,
            pk=character_id,
            user=self.request.user
        )
        return CharacterImage.objects.filter(character_sheet=character)
    
    def get_serializer_context(self):
        """シリアライザーのコンテキストにキャラクターシートを追加"""
        context = super().get_serializer_context()
        character_id = self.kwargs.get('character_id')
        if character_id:
            character = get_object_or_404(
                CharacterSheet,
                pk=character_id,
                user=self.request.user
            )
            context['character_sheet'] = character
        return context
    
    def create(self, request, *args, **kwargs):
        """画像のアップロード"""
        character_id = self.kwargs.get('character_id')
        character = get_object_or_404(
            CharacterSheet,
            pk=character_id,
            user=request.user
        )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 画像を保存
        image = serializer.save()
        
        # 最初の画像の場合、自動的にメイン画像に設定
        if character.images.count() == 1:
            image.is_main = True
            image.save()
        
        # レスポンス用のシリアライザーを作成
        response_serializer = self.get_serializer(image)
        
        logger.info(f"画像アップロード成功: character_id={character_id}, image_id={image.id}")
        
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def list(self, request, *args, **kwargs):
        """画像一覧の取得"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """画像の削除"""
        instance = self.get_object()
        character = instance.character_sheet
        
        # メイン画像を削除する場合、他の画像をメインに設定
        if instance.is_main:
            other_images = character.images.exclude(pk=instance.pk).order_by('order')
            if other_images.exists():
                other_images.first().is_main = True
                other_images.first().save()
        
        # 画像ファイルも削除
        if instance.image:
            instance.image.delete()
        
        instance.delete()
        
        logger.info(f"画像削除成功: image_id={instance.id}")
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['patch'], url_path='reorder')
    def reorder(self, request, character_id=None):
        """画像の順序変更"""
        character = get_object_or_404(
            CharacterSheet,
            pk=character_id,
            user=request.user
        )
        
        order_data = request.data.get('order', [])
        
        with transaction.atomic():
            for item in order_data:
                image_id = item.get('id')
                new_order = item.get('order')
                
                if image_id is None or new_order is None:
                    continue
                
                try:
                    image = CharacterImage.objects.get(
                        pk=image_id,
                        character_sheet=character
                    )
                    image.order = new_order
                    image.save()
                except CharacterImage.DoesNotExist:
                    logger.warning(f"画像が見つかりません: image_id={image_id}")
        
        # 更新後の画像一覧を返す
        images = character.images.all()
        serializer = self.get_serializer(images, many=True)
        
        return Response({
            'count': images.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='set-main')
    def set_main(self, request, character_id=None, pk=None):
        """メイン画像の設定"""
        character = get_object_or_404(
            CharacterSheet,
            pk=character_id,
            user=request.user
        )
        
        image = get_object_or_404(
            CharacterImage,
            pk=pk,
            character_sheet=character
        )
        
        with transaction.atomic():
            # 既存のメイン画像を解除
            CharacterImage.objects.filter(
                character_sheet=character,
                is_main=True
            ).update(is_main=False)
            
            # 新しいメイン画像を設定
            image.is_main = True
            image.save()
        
        serializer = self.get_serializer(image)
        
        logger.info(f"メイン画像設定成功: image_id={image.id}")
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request, character_id=None):
        """複数画像の一括アップロード"""
        character = get_object_or_404(
            CharacterSheet,
            pk=character_id,
            user=request.user
        )
        
        files = request.FILES.getlist('images')
        if not files:
            return Response(
                {'error': '画像ファイルが選択されていません。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 現在の画像数をチェック
        current_count = character.images.count()
        if current_count + len(files) > 10:
            return Response(
                {'error': f'画像は最大10枚までです。現在{current_count}枚、追加可能: {10 - current_count}枚'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_images = []
        errors = []
        
        with transaction.atomic():
            for index, file in enumerate(files):
                try:
                    # 各ファイルに対してシリアライザーを作成
                    data = {
                        'image': file,
                        'order': current_count + index,
                        'is_main': current_count == 0 and index == 0  # 最初の画像のみメイン
                    }
                    
                    serializer = self.get_serializer(data=data)
                    if serializer.is_valid():
                        image = serializer.save()
                        uploaded_images.append(serializer.data)
                    else:
                        errors.append({
                            'file': file.name,
                            'errors': serializer.errors
                        })
                except Exception as e:
                    errors.append({
                        'file': file.name,
                        'errors': str(e)
                    })
        
        response_data = {
            'uploaded': uploaded_images,
            'uploaded_count': len(uploaded_images),
            'errors': errors,
            'error_count': len(errors)
        }
        
        if errors:
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
        
        return Response(response_data, status=status.HTTP_201_CREATED)