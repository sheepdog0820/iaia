"""
共通の mixin クラス - コード重複の共通化
"""
from django.http import Http404
from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status


class UserOwnershipMixin:
    """ユーザー所有リソースのアクセス制御 mixin"""
    
    def get_object(self):
        """リソース所有者のみアクセス可能"""
        obj = super().get_object()
        if hasattr(obj, 'user') and obj.user != self.request.user:
            raise PermissionDenied("この操作には権限が必要です。")
        return obj


class CharacterSheetAccessMixin:
    """キャラクターシート特化のアクセス制御 mixin"""
    
    def get_object(self):
        """キャラクターシートのアクセス制御"""
        obj = super().get_object()
        
        # 自分のキャラクターの場合は常にアクセス可能
        if hasattr(obj, 'user') and obj.user == self.request.user:
            return obj
        
        # 他人のキャラクターの場合
        if self.action in ['retrieve', 'list']:
            # 参照系アクション（GET）は公開設定されていればOK
            if hasattr(obj, 'is_public') and obj.is_public:
                return obj
            else:
                raise PermissionDenied("このキャラクターシートは非公開です。")
        else:
            # 更新・削除系アクション（PUT, PATCH, DELETE）は所有者のみ
            raise PermissionDenied("このキャラクターシートを編集する権限がありません。")
        
        return obj


class CharacterNestedResourceMixin:
    """キャラクターシート関連リソース用の mixin"""
    
    def get_character_sheet_id(self):
        """URLまたはリクエストデータからキャラクターシートIDを取得"""
        # URLパラメータから取得
        character_sheet_id = self.kwargs.get('character_sheet_id') or self.kwargs.get('character_sheet_pk')
        
        # URLパラメータにない場合は、リクエストデータから取得
        if not character_sheet_id and hasattr(self, 'request'):
            if self.request.method in ['POST', 'PUT', 'PATCH']:
                character_sheet_id = self.request.data.get('character_sheet_id')
            elif self.request.method == 'GET':
                character_sheet_id = self.request.query_params.get('character_sheet_id')
        
        return character_sheet_id
    
    def get_character_sheet(self):
        """認証済みユーザーのキャラクターシートを取得"""
        from ..character_models import CharacterSheet
        
        character_sheet_id = self.get_character_sheet_id()
        if not character_sheet_id:
            # IDが見つからない場合は、パラメータから直接取得を試みる
            if hasattr(self, 'kwargs') and 'pk' in self.kwargs:
                # 直接キャラクターシートを参照している場合
                character_sheet_id = self.kwargs['pk']
            else:
                raise ValidationError("character_sheet_id is required")
        
        try:
            return CharacterSheet.objects.get(
                id=character_sheet_id,
                user=self.request.user
            )
        except CharacterSheet.DoesNotExist:
            raise Http404("Character sheet not found")
    
    def get_queryset(self):
        """キャラクターシート関連リソースのクエリセット"""
        try:
            character_sheet = self.get_character_sheet()
            return self.get_model().objects.filter(character_sheet=character_sheet)
        except (ValidationError, Http404):
            return self.get_model().objects.none()
    
    def perform_create(self, serializer):
        """作成時にキャラクターシートを関連付け"""
        character_sheet = self.get_character_sheet()
        serializer.save(character_sheet=character_sheet)
    
    def get_model(self):
        """サブクラスで定義される対象モデルを取得"""
        if hasattr(self, 'model'):
            return self.model
        elif hasattr(self, 'queryset') and self.queryset is not None:
            return self.queryset.model
        elif hasattr(self, 'serializer_class'):
            return self.serializer_class.Meta.model
        else:
            raise NotImplementedError("Model must be defined")


class ErrorHandlerMixin:
    """エラーハンドリング用の共通メソッド"""
    
    @staticmethod
    def handle_not_found(resource_name="リソース"):
        """404エラーレスポンス生成"""
        return Response(
            {'error': f'{resource_name}が見つかりません'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def handle_already_exists(resource_name="リソース"):
        """400エラーレスポンス生成（既存エラー）"""
        return Response(
            {'error': f'{resource_name}は既に存在します'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @staticmethod
    def handle_permission_denied(message="この操作には権限が必要です"):
        """403エラーレスポンス生成"""
        return Response(
            {'error': message},
            status=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def handle_validation_error(message="入力データが無効です", details=None):
        """400エラーレスポンス生成（バリデーションエラー）"""
        error_data = {'error': message}
        if details:
            error_data['details'] = details
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def handle_creation_success(data, message="作成が完了しました"):
        """201成功レスポンス生成"""
        response_data = data.copy() if isinstance(data, dict) else {'data': data}
        response_data['message'] = message
        return Response(response_data, status=status.HTTP_201_CREATED)


class GroupAccessMixin:
    """グループアクセス制御用の mixin"""
    
    def check_group_access(self, group, user):
        """グループアクセス権をチェック"""
        # 公開グループまたは参加中のグループはアクセス可能
        return group.visibility == 'public' or group.members.filter(id=user.id).exists()
    
    def check_admin_permission(self, group, user):
        """グループ管理者権限をチェック"""
        from ..models import GroupMembership
        
        return GroupMembership.objects.filter(
            group=group, 
            user=user, 
            role='admin'
        ).exists()
    
    def get_object(self):
        """グループアクセス制御付きオブジェクト取得"""
        obj = super().get_object()
        
        # アクション別の権限チェック
        action = getattr(self, 'action', None)
        
        # 管理者のみアクセス可能なアクション
        admin_only_actions = ['update', 'partial_update', 'destroy', 'invite', 'remove_member']
        if action in admin_only_actions:
            if not self.check_admin_permission(obj, self.request.user):
                raise PermissionDenied("この操作には管理者権限が必要です")
        
        # グループアクセス権チェック
        elif not self.check_group_access(obj, self.request.user):
            raise Http404("Group not found")
        
        return obj


class CommonQuerysetMixin:
    """共通のクエリセット操作用 mixin"""
    
    def get_user_filtered_queryset(self, base_queryset=None):
        """ユーザーでフィルタリングしたクエリセット取得"""
        if base_queryset is None:
            base_queryset = self.get_queryset()
        
        if hasattr(base_queryset.model, 'user'):
            return base_queryset.filter(user=self.request.user)
        return base_queryset
    
    def get_active_only_queryset(self, base_queryset=None):
        """アクティブなもののみのクエリセット取得"""
        if base_queryset is None:
            base_queryset = self.get_queryset()
        
        if hasattr(base_queryset.model, 'is_active'):
            return base_queryset.filter(is_active=True)
        return base_queryset


class BulkOperationMixin:
    """一括操作用の共通 mixin"""
    
    def validate_bulk_data(self, data_list, required_fields=None):
        """一括操作データのバリデーション"""
        if not data_list:
            raise ValidationError("データが提供されていません")
        
        if required_fields:
            for i, data in enumerate(data_list):
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    raise ValidationError(
                        f"アイテム{i+1}: 必須フィールドが不足しています: {', '.join(missing_fields)}"
                    )
        
        return True
    
    def process_bulk_updates(self, data_list, update_fields):
        """一括更新処理"""
        updated_objects = []
        
        for data in data_list:
            obj_id = data.get('id')
            if not obj_id:
                continue
            
            try:
                obj = self.get_queryset().get(id=obj_id)
                
                for field in update_fields:
                    if field in data:
                        setattr(obj, field, data[field])
                
                obj.save()
                updated_objects.append(obj)
                
            except self.get_model().DoesNotExist:
                continue
        
        return updated_objects
    
    def get_model(self):
        """対象モデルを取得"""
        if hasattr(self, 'model'):
            return self.model
        elif hasattr(self, 'queryset') and self.queryset is not None:
            return self.queryset.model
        elif hasattr(self, 'serializer_class'):
            return self.serializer_class.Meta.model
        else:
            raise NotImplementedError("Model must be defined")