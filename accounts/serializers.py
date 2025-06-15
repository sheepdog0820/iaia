from rest_framework import serializers
from .models import (
    CustomUser, Friend, Group, GroupMembership, GroupInvitation,
    CharacterSheet, CharacterSheet6th, CharacterSheet7th,
    CharacterSkill, CharacterEquipment
)


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
            'interest_points', 'other_points', 'current_value',
            'half_value', 'fifth_value'
        ]
        read_only_fields = ['id', 'current_value', 'half_value', 'fifth_value']


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


class CharacterSheet7thSerializer(serializers.ModelSerializer):
    """7版固有データシリアライザー"""
    class Meta:
        model = CharacterSheet7th
        fields = [
            'luck_points', 'build_value', 'move_rate', 'dodge_value', 'damage_bonus',
            'personal_description', 'ideology_beliefs', 'significant_people',
            'meaningful_locations', 'treasured_possessions', 'traits',
            'injuries_scars', 'phobias_manias'
        ]
        read_only_fields = ['build_value', 'move_rate', 'dodge_value', 'damage_bonus']


class CharacterSheetSerializer(serializers.ModelSerializer):
    """キャラクターシートメインシリアライザー"""
    # 関連データ
    skills = CharacterSkillSerializer(many=True, read_only=True)
    equipment = CharacterEquipmentSerializer(many=True, read_only=True)
    
    # 版別データ
    sixth_edition_data = CharacterSheet6thSerializer(read_only=True)
    seventh_edition_data = CharacterSheet7thSerializer(read_only=True)
    
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
            'skills', 'equipment', 'sixth_edition_data', 'seventh_edition_data',
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
        
        # 同名キャラクターが存在する場合、バージョン番号を調整
        existing_chars = CharacterSheet.objects.filter(
            user=validated_data['user'],
            name=validated_data['name']
        )
        
        if existing_chars.exists():
            # 最新バージョン番号を取得
            latest_version = existing_chars.order_by('-version').first().version
            validated_data['version'] = latest_version + 1
            
            # 最初のキャラクターを親として設定
            validated_data['parent_sheet'] = existing_chars.order_by('version').first()
        
        return super().create(validated_data)


class CharacterSheetCreateSerializer(serializers.ModelSerializer):
    """キャラクターシート作成専用シリアライザー"""
    # 版別データ
    sixth_edition_data = CharacterSheet6thSerializer(required=False)
    seventh_edition_data = CharacterSheet7thSerializer(required=False)
    
    # スキルデータ
    skills = CharacterSkillSerializer(many=True, required=False)
    
    # 装備データ
    equipment = CharacterEquipmentSerializer(many=True, required=False)
    
    class Meta:
        model = CharacterSheet
        fields = [
            'id', 'edition', 'name', 'player_name', 'age', 'gender', 'occupation',
            'birthplace', 'residence', 'str_value', 'con_value', 'pow_value',
            'dex_value', 'app_value', 'siz_value', 'int_value', 'edu_value',
            'hit_points_current', 'magic_points_current', 'sanity_current',
            'character_image', 'notes', 'sixth_edition_data', 'seventh_edition_data',
            'skills', 'equipment'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """キャラクターシート作成（関連データも含む）"""
        # 関連データを分離
        sixth_data = validated_data.pop('sixth_edition_data', None)
        seventh_data = validated_data.pop('seventh_edition_data', None)
        skills_data = validated_data.pop('skills', [])
        equipment_data = validated_data.pop('equipment', [])
        
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
        character_sheet = CharacterSheet.objects.create(**validated_data)
        
        # 版別データ作成
        if character_sheet.edition == '6th' and sixth_data:
            CharacterSheet6th.objects.create(
                character_sheet=character_sheet,
                **sixth_data
            )
        elif character_sheet.edition == '7th' and seventh_data:
            CharacterSheet7th.objects.create(
                character_sheet=character_sheet,
                **seventh_data
            )
        
        # スキルデータ作成
        for skill_data in skills_data:
            CharacterSkill.objects.create(
                character_sheet=character_sheet,
                **skill_data
            )
        
        # 装備データ作成
        for equipment_data_item in equipment_data:
            CharacterEquipment.objects.create(
                character_sheet=character_sheet,
                **equipment_data_item
            )
        
        return character_sheet


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