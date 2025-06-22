from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.db import models
from PIL import Image
import os
from .models import (
    CustomUser, Friend, Group, GroupMembership, GroupInvitation
)
from .character_models import (
    CharacterSheet, CharacterSheet6th,
    CharacterSkill, CharacterEquipment, CharacterImage
)


def validate_character_image(image):
    """キャラクター画像のバリデーション"""
    if not image:
        return image
    
    # ファイルサイズチェック（5MB以下）
    max_size = 5 * 1024 * 1024  # 5MB
    if image.size > max_size:
        raise ValidationError("画像ファイルのサイズは5MB以下にしてください。")
    
    # ファイル形式チェック
    allowed_formats = ['JPEG', 'PNG', 'GIF']
    try:
        with Image.open(image) as img:
            if img.format not in allowed_formats:
                raise ValidationError(
                    f"サポートされていない画像形式です。{', '.join(allowed_formats)}形式を使用してください。"
                )
            
            # 画像サイズチェック（最大3000x4000px）
            max_width, max_height = 3000, 4000
            if img.width > max_width or img.height > max_height:
                raise ValidationError(
                    f"画像サイズが大きすぎます。最大{max_width}x{max_height}ピクセルにしてください。"
                )
                
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError("画像ファイルが破損しているか、サポートされていない形式です。")
    
    return image


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'nickname', 'trpg_history', 
                 'profile_image', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'username', 'date_joined']


class FriendSerializer(serializers.ModelSerializer):
    friend_username = serializers.CharField(source='friend.username', read_only=True)
    friend_nickname = serializers.CharField(source='friend.nickname', read_only=True)
    
    class Meta:
        model = Friend
        fields = ['id', 'friend', 'friend_username', 'friend_nickname', 'created_at']
        read_only_fields = ['id', 'created_at']


class GroupMembershipSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    
    class Meta:
        model = GroupMembership
        fields = ['id', 'user', 'user_detail', 'user_username', 'user_nickname', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class GroupSerializer(serializers.ModelSerializer):
    members_detail = GroupMembershipSerializer(
        source='groupmembership_set', 
        many=True, 
        read_only=True
    )
    member_count = serializers.SerializerMethodField()
    session_count = serializers.SerializerMethodField()
    total_play_hours = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.nickname', read_only=True)
    is_member = serializers.SerializerMethodField()
    member_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'visibility', 'created_by', 'created_by_name',
                 'created_at', 'members_detail', 'member_count', 'session_count', 'total_play_hours',
                 'is_member', 'member_role']
        read_only_fields = ['id', 'created_by', 'created_at']
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_session_count(self, obj):
        return obj.sessions.count()
    
    def get_total_play_hours(self, obj):
        from django.db.models import Sum
        total_minutes = obj.sessions.filter(status='completed').aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0
        return round(total_minutes / 60, 1)
    
    def get_is_member(self, obj):
        """ユーザーがこのグループのメンバーかどうか"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # ViewSetから設定された場合
        if hasattr(obj, 'is_member'):
            return obj.is_member
        
        # 直接チェック
        return GroupMembership.objects.filter(
            group=obj, user=request.user
        ).exists()
    
    def get_member_role(self, obj):
        """ユーザーのグループでの役割"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        # ViewSetから設定された場合
        if hasattr(obj, 'member_role'):
            return obj.member_role
        
        # 直接チェック
        membership = GroupMembership.objects.filter(
            group=obj, user=request.user
        ).first()
        return membership.role if membership else None


class GroupInvitationSerializer(serializers.ModelSerializer):
    inviter_detail = UserSerializer(source='inviter', read_only=True)
    invitee_detail = UserSerializer(source='invitee', read_only=True)
    group_detail = GroupSerializer(source='group', read_only=True)
    
    class Meta:
        model = GroupInvitation
        fields = ['id', 'group', 'group_detail', 'inviter', 'inviter_detail', 
                 'invitee', 'invitee_detail', 'status', 'message', 'created_at', 'responded_at']
        read_only_fields = ['id', 'inviter', 'created_at', 'responded_at']


class FriendDetailSerializer(serializers.ModelSerializer):
    friend_detail = UserSerializer(source='friend', read_only=True)
    
    class Meta:
        model = Friend
        fields = ['id', 'friend', 'friend_detail', 'created_at']
        read_only_fields = ['id', 'created_at']


# キャラクターシート関連のシリアライザー

class CharacterSkillSerializer(serializers.ModelSerializer):
    """キャラクタースキルシリアライザー"""
    class Meta:
        model = CharacterSkill
        fields = [
            'id', 'skill_name', 'base_value', 'occupation_points', 
            'interest_points', 'other_points', 'current_value'
        ]
        read_only_fields = ['id', 'current_value']


class CharacterEquipmentSerializer(serializers.ModelSerializer):
    """キャラクター装備シリアライザー"""
    class Meta:
        model = CharacterEquipment
        fields = [
            'id', 'item_type', 'name', 'skill_name', 'damage', 'base_range',
            'attacks_per_round', 'ammo', 'malfunction_number', 'armor_points',
            'description', 'quantity'
        ]
        read_only_fields = ['id']


class CharacterSheet6thSerializer(serializers.ModelSerializer):
    """6版固有データシリアライザー"""
    class Meta:
        model = CharacterSheet6th
        fields = [
            'mental_disorder', 'idea_roll', 'luck_roll', 'know_roll', 'damage_bonus'
        ]
        read_only_fields = ['idea_roll', 'luck_roll', 'know_roll', 'damage_bonus']




class CharacterSheetSerializer(serializers.ModelSerializer):
    """キャラクターシートメインシリアライザー"""
    # 関連データ
    skills = CharacterSkillSerializer(many=True, read_only=True)
    equipment = CharacterEquipmentSerializer(many=True, read_only=True)
    
    # 版別データ
    sixth_edition_data = CharacterSheet6thSerializer(read_only=True)
    
    # 計算済みフィールド
    abilities = serializers.ReadOnlyField()
    
    # バージョン関連
    versions = serializers.SerializerMethodField()
    parent_sheet_name = serializers.CharField(source='parent_sheet.name', read_only=True)
    
    # ユーザー情報
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    
    class Meta:
        model = CharacterSheet
        fields = [
            'id', 'edition', 'name', 'player_name', 'age', 'gender', 'occupation',
            'birthplace', 'residence', 'str_value', 'con_value', 'pow_value',
            'dex_value', 'app_value', 'siz_value', 'int_value', 'edu_value',
            'hit_points_max', 'hit_points_current', 'magic_points_max',
            'magic_points_current', 'sanity_starting', 'sanity_max', 'sanity_current',
            'version', 'parent_sheet', 'parent_sheet_name', 'character_image',
            'notes', 'is_active', 'created_at', 'updated_at',
            'skills', 'equipment', 'sixth_edition_data',
            'abilities', 'versions', 'user_nickname'
        ]
        read_only_fields = [
            'id', 'user', 'hit_points_max', 'magic_points_max', 'sanity_starting',
            'sanity_max', 'created_at', 'updated_at', 'abilities', 'versions',
            'user_nickname'
        ]
    
    def get_versions(self, obj):
        """このキャラクターのバージョン一覧を返す"""
        if obj.parent_sheet:
            # 子バージョンの場合、親のバージョン一覧を返す
            base_sheet = obj.parent_sheet
        else:
            # 親バージョンの場合、自分のバージョン一覧を返す
            base_sheet = obj
        
        versions = CharacterSheet.objects.filter(
            parent_sheet=base_sheet
        ).order_by('version')
        
        # 親バージョンも含める
        all_versions = [base_sheet] + list(versions)
        
        return [
            {
                'id': v.id,
                'version': v.version,
                'name': v.name,
                'updated_at': v.updated_at,
                'is_current': v.id == obj.id
            }
            for v in all_versions
        ]
    
    def validate_age(self, value):
        """年齢のバリデーション"""
        if value < 15 or value > 90:
            raise serializers.ValidationError("年齢は15歳から90歳の間で設定してください。")
        return value
    
    def validate(self, data):
        """能力値の総合バリデーション"""
        # 能力値の合計チェック（新規作成時のみ）
        if not self.instance:  # 新規作成時
            ability_sum = (
                data.get('str_value', 0) + data.get('con_value', 0) +
                data.get('pow_value', 0) + data.get('dex_value', 0) +
                data.get('app_value', 0) + data.get('siz_value', 0) +
                data.get('int_value', 0) + data.get('edu_value', 0)
            )
            
            # 一般的な3d6×5の合計値チェック（420±50程度）
            if ability_sum < 320 or ability_sum > 520:
                raise serializers.ValidationError(
                    "能力値の合計が異常です。適切な値を設定してください。"
                )
        
        return data
    
    def create(self, validated_data):
        """キャラクターシート作成"""
        # 現在のユーザーを設定
        validated_data['user'] = self.context['request'].user
        
        # 同名キャラクター対応 - ユニークIDで管理、名前の重複は許可
        # バージョン番号は常に1から開始（独立したキャラクターとして扱う）
        validated_data['version'] = 1
        validated_data['parent_sheet'] = None
        
        return super().create(validated_data)
    
    def to_representation(self, instance):
        """表示時に6版の場合は値を変換"""
        data = super().to_representation(instance)
        
        # 6版の場合、能力値を6版表示用に変換（15-90 → 3-18）
        if instance.edition == '6th':
            ability_fields = ['str_value', 'con_value', 'pow_value', 'dex_value', 
                            'app_value', 'siz_value', 'int_value', 'edu_value']
            for field in ability_fields:
                if field in data and data[field] is not None:
                    # 7版互換の値を6版の値に変換（÷5）
                    data[field] = data[field] // 5
        
        return data


class CharacterSheetCreateSerializer(serializers.ModelSerializer):
    """キャラクターシート作成専用シリアライザー"""
    # 版別データ
    sixth_edition_data = CharacterSheet6thSerializer(required=False)
    
    # スキルデータ
    skills = CharacterSkillSerializer(many=True, required=False)
    
    # 装備データ
    equipment = CharacterEquipmentSerializer(many=True, required=False)
    
    # 現在値フィールドをオプショナルに
    hit_points_current = serializers.IntegerField(required=False)
    magic_points_current = serializers.IntegerField(required=False)
    sanity_current = serializers.IntegerField(required=False)
    
    # 能力値フィールドをカスタムバリデーションに
    str_value = serializers.IntegerField()
    con_value = serializers.IntegerField()
    pow_value = serializers.IntegerField()
    dex_value = serializers.IntegerField()
    app_value = serializers.IntegerField()
    siz_value = serializers.IntegerField()
    int_value = serializers.IntegerField()
    edu_value = serializers.IntegerField()
    
    class Meta:
        model = CharacterSheet
        fields = [
            'id', 'edition', 'name', 'player_name', 'age', 'gender', 'occupation',
            'birthplace', 'residence', 'str_value', 'con_value', 'pow_value',
            'dex_value', 'app_value', 'siz_value', 'int_value', 'edu_value',
            'hit_points_current', 'magic_points_current', 'sanity_current',
            'character_image', 'notes', 'sixth_edition_data',
            'skills', 'equipment'
        ]
        read_only_fields = ['id']
    
    def validate_character_image(self, value):
        """キャラクター画像のバリデーション"""
        return validate_character_image(value)
    
    def validate(self, data):
        """版別のバリデーション"""
        edition = data.get('edition')
        
        # 能力値制限を削除 - ユーザーの自由度を最大化
        # 6版・7版問わず、1-999の範囲で自由に設定可能
        
        # 基本的な妥当性チェックのみ実施
        for field in ['str_value', 'con_value', 'pow_value', 'dex_value', 'app_value', 'siz_value', 'int_value', 'edu_value']:
            value = data.get(field)
            if value is not None:
                if value < 1 or value > 999:
                    raise serializers.ValidationError({
                        field: "能力値は1から999の間で設定してください。"
                    })
        
        return data
    
    def create(self, validated_data):
        """キャラクターシート作成（関連データも含む）"""
        import logging
        logger = logging.getLogger(__name__)
        
        # 関連データを分離
        sixth_data = validated_data.pop('sixth_edition_data', None)
        skills_data = validated_data.pop('skills', [])
        equipment_data = validated_data.pop('equipment', [])
        
        # リクエストオブジェクトから追加データを取得
        request = self.context.get('request')
        
        # デバッグ情報
        logger.info(f"受信した能力値データ: str={validated_data.get('str_value')}, con={validated_data.get('con_value')}")
        logger.info(f"validated_data keys: {list(validated_data.keys())}")
        if request:
            logger.info(f"request.data keys: {list(request.data.keys())}")
            logger.info(f"skills_data in request: {'skills_data' in request.data}")
        
        # 6版固有データ処理
        if validated_data.get('edition') == '6th':
            if not sixth_data:
                sixth_data = {}
            # mental_disorder を直接リクエストから取得
            mental_disorder = request.data.get('mental_disorder', '') if request else ''
            sixth_data['mental_disorder'] = mental_disorder
        
        # フロントエンドからのスキルデータを処理
        if request and 'skills_data' in request.data:
            import json
            try:
                skills_json = request.data.get('skills_data')
                if skills_json:
                    skills_data = json.loads(skills_json)
                    logger.info(f"パースしたスキルデータ数: {len(skills_data)}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"スキルデータのパースエラー: {e}")
                pass  # JSONデコードエラーの場合はスキップ
        
        # 6版の場合、能力値を内部保存用に変換（3-18 → 15-90）
        if validated_data.get('edition') == '6th':
            ability_fields = ['str_value', 'con_value', 'pow_value', 'dex_value', 
                            'app_value', 'siz_value', 'int_value', 'edu_value']
            for field in ability_fields:
                if field in validated_data:
                    original_value = validated_data[field]
                    # 6版の値を7版互換の値に変換（×5）
                    validated_data[field] = validated_data[field] * 5
                    logger.info(f"{field}: {original_value} → {validated_data[field]}")
        
        # 現在のユーザーを設定
        validated_data['user'] = self.context['request'].user
        
        # 同名キャラクターが存在する場合、バージョン番号を調整
        existing_chars = CharacterSheet.objects.filter(
            user=validated_data['user'],
            name=validated_data['name']
        )
        
        if existing_chars.exists():
            latest_version = existing_chars.order_by('-version').first().version
            validated_data['version'] = latest_version + 1
            validated_data['parent_sheet'] = existing_chars.order_by('version').first()
        
        # キャラクターシート作成
        try:
            character_sheet = CharacterSheet.objects.create(**validated_data)
            logger.info(f"キャラクターシート作成成功: ID={character_sheet.id}")
        except Exception as e:
            logger.error(f"キャラクターシート作成エラー: {e}")
            logger.error(f"作成時のvalidated_data: {validated_data}")
            raise
        
        # 版別データ作成
        if character_sheet.edition == '6th' and sixth_data:
            CharacterSheet6th.objects.create(
                character_sheet=character_sheet,
                **sixth_data
            )
        
        # スキルデータ作成
        created_skills = []
        for skill_data in skills_data:
            try:
                skill = CharacterSkill.objects.create(
                    character_sheet=character_sheet,
                    **skill_data
                )
                created_skills.append(skill)
            except Exception as e:
                logger.error(f"スキル作成エラー: {e}, データ: {skill_data}")
        
        logger.info(f"作成されたスキル数: {len(created_skills)}")
        
        # 装備データ作成
        for equipment_data_item in equipment_data:
            CharacterEquipment.objects.create(
                character_sheet=character_sheet,
                **equipment_data_item
            )
        
        return character_sheet
    
    def to_representation(self, instance):
        """表示時に6版の場合は値を変換"""
        data = super().to_representation(instance)
        
        # 6版の場合、能力値を6版表示用に変換（15-90 → 3-18）
        if instance.edition == '6th':
            ability_fields = ['str_value', 'con_value', 'pow_value', 'dex_value', 
                            'app_value', 'siz_value', 'int_value', 'edu_value']
            for field in ability_fields:
                if field in data and data[field] is not None:
                    # 7版互換の値を6版の値に変換（÷5）
                    data[field] = data[field] // 5
        
        return data


class CharacterSheetListSerializer(serializers.ModelSerializer):
    """キャラクターシート一覧表示用シリアライザー"""
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    skill_count = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()
    latest_version = serializers.SerializerMethodField()
    
    class Meta:
        model = CharacterSheet
        fields = [
            'id', 'edition', 'name', 'player_name', 'age', 'occupation',
            'version', 'character_image', 'is_active', 'created_at', 'updated_at',
            'user_nickname', 'skill_count', 'equipment_count', 'latest_version'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_skill_count(self, obj):
        """スキル数を返す"""
        return obj.skills.count()
    
    def get_equipment_count(self, obj):
        """装備数を返す"""
        return obj.equipment.count()
    
    def get_latest_version(self, obj):
        """最新バージョン番号を返す"""
        if obj.parent_sheet:
            base_sheet = obj.parent_sheet
        else:
            base_sheet = obj
        
        latest = CharacterSheet.objects.filter(
            parent_sheet=base_sheet
        ).order_by('-version').first()
        
        if latest:
            return latest.version
        return base_sheet.version


class CharacterSheetUpdateSerializer(serializers.ModelSerializer):
    """キャラクターシート更新用シリアライザー"""
    class Meta:
        model = CharacterSheet
        fields = [
            'name', 'player_name', 'age', 'gender', 'occupation',
            'birthplace', 'residence', 'str_value', 'con_value', 'pow_value',
            'dex_value', 'app_value', 'siz_value', 'int_value', 'edu_value',
            'hit_points_current', 'magic_points_current', 'sanity_current',
            'character_image', 'notes', 'is_active'
        ]
    
    def validate_character_image(self, value):
        """キャラクター画像のバリデーション"""
        return validate_character_image(value)
    
    def validate_name(self, value):
        """名前の重複チェック（同一ユーザー内）"""
        if self.instance and self.instance.name != value:
            existing = CharacterSheet.objects.filter(
                user=self.instance.user,
                name=value
            ).exclude(id=self.instance.id)
            
            if existing.exists():
                raise serializers.ValidationError(
                    "同じ名前のキャラクターが既に存在します。"
                )
        return value
    
    def update(self, instance, validated_data):
        """更新処理（画像削除対応）"""
        # リクエストから削除フラグをチェック
        request = self.context.get('request')
        delete_image = request.data.get('delete_image') == 'true' if request else False
        
        # 画像削除フラグが設定されている場合
        if delete_image:
            if instance.character_image:
                instance.character_image.delete(save=False)
            validated_data['character_image'] = None
        elif 'character_image' in validated_data:
            # 通常の画像更新処理
            new_image = validated_data['character_image']
            # 空文字列が渡された場合は画像を削除
            if new_image == '' or new_image is None:
                if instance.character_image:
                    instance.character_image.delete(save=False)
                validated_data['character_image'] = None
        
        return super().update(instance, validated_data)


class CharacterImageSerializer(serializers.ModelSerializer):
    """キャラクター画像シリアライザー"""
    image_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CharacterImage
        fields = [
            'id', 'image', 'image_url', 'thumbnail_url', 
            'is_main', 'order', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at', 'image_url', 'thumbnail_url']
    
    def get_image_url(self, obj):
        """画像のフルURLを返す"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_thumbnail_url(self, obj):
        """サムネイルURLを返す（現時点では元画像と同じ）"""
        # TODO: 実際のサムネイル生成機能を実装
        return self.get_image_url(obj)
    
    def validate_image(self, value):
        """画像ファイルのバリデーション"""
        if not value:
            raise serializers.ValidationError("画像ファイルは必須です。")
        
        # 既存のバリデーション関数を使用
        return validate_character_image(value)
    
    def validate(self, attrs):
        """追加バリデーション"""
        character_sheet = self.context.get('character_sheet')
        if not character_sheet:
            raise serializers.ValidationError("キャラクターシートが指定されていません。")
        
        # 画像数制限チェック（10枚まで）
        existing_count = CharacterImage.objects.filter(
            character_sheet=character_sheet
        ).count()
        
        if self.instance:
            # 更新の場合は現在の画像を除外
            existing_count -= 1
        
        if existing_count >= 10:
            raise serializers.ValidationError(
                "1キャラクターにつき最大10枚まで画像をアップロードできます。"
            )
        
        # 総容量制限チェック（30MB）
        total_size = 0
        for img in CharacterImage.objects.filter(character_sheet=character_sheet):
            if img.image and img != self.instance:
                total_size += img.image.size
        
        new_image = attrs.get('image')
        if new_image:
            total_size += new_image.size
        
        max_total_size = 30 * 1024 * 1024  # 30MB
        if total_size > max_total_size:
            raise serializers.ValidationError(
                f"総容量が30MBを超えています。現在: {total_size / 1024 / 1024:.1f}MB"
            )
        
        # メイン画像の一意性チェック
        if attrs.get('is_main', False):
            existing_main = CharacterImage.objects.filter(
                character_sheet=character_sheet,
                is_main=True
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_main.exists():
                # 既存のメイン画像をFalseに更新
                existing_main.update(is_main=False)
        
        return attrs
    
    def create(self, validated_data):
        """画像作成時の処理"""
        character_sheet = self.context.get('character_sheet')
        validated_data['character_sheet'] = character_sheet
        
        # 順序番号の自動設定
        if 'order' not in validated_data:
            max_order = CharacterImage.objects.filter(
                character_sheet=character_sheet
            ).aggregate(max_order=models.Max('order'))['max_order']
            validated_data['order'] = (max_order or -1) + 1
        
        return super().create(validated_data)