from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, FormView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import (
    CustomUser, Friend, Group, GroupMembership, GroupInvitation,
    CharacterSheet, CharacterSheet6th, CharacterSheet7th,
    CharacterSkill, CharacterEquipment
)
from .serializers import (
    UserSerializer, FriendSerializer, GroupSerializer, GroupMembershipSerializer,
    GroupInvitationSerializer, FriendDetailSerializer,
    CharacterSheetSerializer, CharacterSheetCreateSerializer,
    CharacterSheetListSerializer, CharacterSheetUpdateSerializer,
    CharacterSkillSerializer, CharacterEquipmentSerializer,
    CharacterSheet6thSerializer, CharacterSheet7thSerializer
)
from .forms import CustomLoginForm, CustomSignUpForm, ProfileEditForm, CharacterSheet6thForm
from allauth.socialaccount.models import SocialAccount

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.action == 'list':
            return CustomUser.objects.filter(id=self.request.user.id)
        return CustomUser.objects.all()
    
    @action(detail=True, methods=['get'])
    def friends(self, request, pk=None):
        user = self.get_object()
        friends = Friend.objects.filter(user=user)
        serializer = FriendSerializer(friends, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def groups(self, request, pk=None):
        user = self.get_object()
        memberships = GroupMembership.objects.filter(user=user)
        serializer = GroupMembershipSerializer(memberships, many=True)
        return Response(serializer.data)


class FriendViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return FriendDetailSerializer
        return FriendSerializer
    
    def get_queryset(self):
        return Friend.objects.filter(user=self.request.user).select_related('friend')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # 参加中のグループ + 公開グループ（重複除去）
        from django.db.models import Q
        return Group.objects.filter(
            Q(members=self.request.user) | Q(visibility='public')
        ).distinct()
    
    def get_object(self):
        """オブジェクト取得時の権限チェック"""
        obj = super().get_object()
        
        # アクション別の権限チェック
        action = getattr(self, 'action', None)
        
        # 管理者のみアクセス可能なアクション
        admin_only_actions = ['update', 'partial_update', 'destroy', 'invite', 'remove_member']
        if action in admin_only_actions:
            membership = GroupMembership.objects.filter(
                group=obj, user=self.request.user, role='admin'
            ).first()
            if not membership:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("この操作には管理者権限が必要です")
        
        # 参加者のみアクセス可能なアクション
        member_only_actions = ['leave']
        if action in member_only_actions:
            if not obj.members.filter(id=self.request.user.id).exists():
                from django.http import Http404
                raise Http404("Group not found")
        
        # 公開グループまたは参加中のグループはアクセス可能
        elif obj.visibility == 'public' or obj.members.filter(id=self.request.user.id).exists():
            return obj
        
        # プライベートグループで非メンバーの場合は404を返す
        else:
            from django.http import Http404
            raise Http404("Group not found")
        
        return obj
    
    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user)
        GroupMembership.objects.create(
            user=self.request.user,
            group=group,
            role='admin'
        )
    
    @action(detail=False, methods=['get'])
    def public(self, request):
        """公開グループ一覧取得"""
        groups = Group.objects.filter(visibility='public').order_by('-created_at')
        
        # 既に参加しているかの情報を追加
        for group in groups:
            group.is_member = GroupMembership.objects.filter(
                group=group, user=request.user
            ).exists()
        
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def private(self, request):
        """プライベートグループ一覧取得（参加中のみ）"""
        groups = Group.objects.filter(
            members=request.user, 
            visibility='private'
        ).distinct().order_by('-created_at')
        
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """グループ参加API"""
        group = self.get_object()
        
        # 公開グループかチェック
        if group.visibility != 'public':
            return Response({'error': 'このグループは公開されていません'}, status=status.HTTP_403_FORBIDDEN)
        
        # 既に参加しているかチェック
        if GroupMembership.objects.filter(user=request.user, group=group).exists():
            return Response(
                {'error': '既にこのグループのメンバーです'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # グループ参加を作成
        membership = GroupMembership.objects.create(
            user=request.user,
            group=group,
            role='member'
        )
        
        return Response({'message': f'{group.name}に参加しました'}, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def all_groups(self, request):
        """すべてのグループ一覧（参加中 + 公開）"""
        from django.db.models import Q
        
        # 参加中のグループ + 公開グループ（重複除去）
        groups = Group.objects.filter(
            Q(members=request.user) | Q(visibility='public')
        ).distinct().order_by('-created_at')
        
        # 各グループに参加状況を追加
        for group in groups:
            group.is_member = GroupMembership.objects.filter(
                group=group, user=request.user
            ).exists()
            group.member_role = None
            if group.is_member:
                membership = GroupMembership.objects.filter(
                    group=group, user=request.user
                ).first()
                if membership:
                    group.member_role = membership.role
        
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """グループメンバー一覧取得"""
        try:
            group = self.get_object()
            memberships = GroupMembership.objects.filter(group=group).select_related('user')
            serializer = GroupMembershipSerializer(memberships, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """メンバー招待"""
        group = self.get_object()
        
        # 管理者権限チェック
        membership = GroupMembership.objects.filter(
            group=group, user=request.user, role='admin'
        ).first()
        if not membership:
            return Response({'error': '管理者権限が必要です'}, status=status.HTTP_403_FORBIDDEN)
        
        invitee_ids = request.data.get('invitee_ids', [])
        message = request.data.get('message', '')
        
        if not invitee_ids:
            return Response({'error': '招待するユーザーを選択してください'}, status=status.HTTP_400_BAD_REQUEST)
        
        invitations = []
        for invitee_id in invitee_ids:
            try:
                invitee = CustomUser.objects.get(id=invitee_id)
                
                # 既にメンバーかチェック
                if GroupMembership.objects.filter(group=group, user=invitee).exists():
                    continue
                
                # 既に招待済みかチェック
                if GroupInvitation.objects.filter(
                    group=group, invitee=invitee, status='pending'
                ).exists():
                    continue
                
                invitation = GroupInvitation.objects.create(
                    group=group,
                    inviter=request.user,
                    invitee=invitee,
                    message=message
                )
                invitations.append(invitation)
                
            except CustomUser.DoesNotExist:
                continue
        
        serializer = GroupInvitationSerializer(invitations, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """グループ退出"""
        group = self.get_object()
        
        try:
            membership = GroupMembership.objects.get(group=group, user=request.user)
            
            # 管理者が最後の一人の場合は退出できない
            if membership.role == 'admin':
                admin_count = GroupMembership.objects.filter(group=group, role='admin').count()
                if admin_count == 1:
                    return Response(
                        {'error': '管理者が最後の一人のため退出できません'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            membership.delete()
            return Response({'message': 'グループから退出しました'}, status=status.HTTP_200_OK)
            
        except GroupMembership.DoesNotExist:
            return Response({'error': 'グループに参加していません'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """メンバー除名（管理者のみ）"""
        group = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({'error': 'user_idが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 管理者権限チェック
        admin_membership = GroupMembership.objects.filter(
            group=group, user=request.user, role='admin'
        ).first()
        if not admin_membership:
            return Response({'error': '管理者権限が必要です'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            target_membership = GroupMembership.objects.get(group=group, user_id=user_id)
            
            # 自分自身は除名できない
            if target_membership.user == request.user:
                return Response({'error': '自分自身を除名することはできません'}, status=status.HTTP_400_BAD_REQUEST)
            
            target_membership.delete()
            return Response({'message': 'メンバーを除名しました'}, status=status.HTTP_200_OK)
            
        except GroupMembership.DoesNotExist:
            return Response({'error': 'メンバーが見つかりません'}, status=status.HTTP_404_NOT_FOUND)


class GroupInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = GroupInvitationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return GroupInvitation.objects.filter(invitee=self.request.user)
    
    def perform_create(self, serializer):
        """招待作成時にinviterを自動設定"""
        serializer.save(inviter=self.request.user)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """招待を受諾"""
        invitation = self.get_object()
        
        if invitation.status != 'pending':
            return Response({'error': '既に処理済みの招待です'}, status=status.HTTP_400_BAD_REQUEST)
        
        # グループメンバーに追加
        GroupMembership.objects.create(
            user=invitation.invitee,
            group=invitation.group,
            role='member'
        )
        
        # 招待ステータス更新
        invitation.status = 'accepted'
        invitation.responded_at = timezone.now()
        invitation.save()
        
        return Response({'message': 'グループに参加しました'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """招待を拒否"""
        invitation = self.get_object()
        
        if invitation.status != 'pending':
            return Response({'error': '既に処理済みの招待です'}, status=status.HTTP_400_BAD_REQUEST)
        
        invitation.status = 'declined'
        invitation.responded_at = timezone.now()
        invitation.save()
        
        return Response({'message': '招待を拒否しました'}, status=status.HTTP_200_OK)


class CharacterSheetViewSet(viewsets.ModelViewSet):
    """キャラクターシートViewSet"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """全ユーザーのキャラクターシートを取得（参照権限は全ユーザに開放）"""
        return CharacterSheet.objects.all().select_related(
            'parent_sheet', 'sixth_edition_data', 'seventh_edition_data', 'user'
        ).prefetch_related(
            'skills', 'equipment'
        ).order_by('-updated_at')
    
    def get_serializer_class(self):
        """アクション別のシリアライザー選択"""
        if self.action == 'list':
            return CharacterSheetListSerializer
        elif self.action == 'create':
            return CharacterSheetCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CharacterSheetUpdateSerializer
        else:
            return CharacterSheetSerializer
    
    def get_object(self):
        """キャラクターシート取得（参照は全ユーザ可能、編集は作成者のみ）"""
        obj = super().get_object()
        # 参照系のアクション（retrieve）は全ユーザに許可
        if self.action in ['retrieve']:
            return obj
        # 編集系のアクションは作成者のみ許可
        if obj.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("このキャラクターシートを編集する権限がありません。")
        return obj
    
    @action(detail=False, methods=['get'])
    def by_edition(self, request):
        """版別のキャラクターシート一覧"""
        edition = request.query_params.get('edition')
        if not edition or edition not in ['6th', '7th']:
            return Response(
                {'error': 'edition parameter is required (6th or 7th)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(edition=edition)
        serializer = CharacterSheetListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """アクティブなキャラクターシート一覧"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = CharacterSheetListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """キャラクターシートの新バージョン作成"""
        original_sheet = self.get_object()
        
        # 親シートの設定
        if original_sheet.parent_sheet:
            parent_sheet = original_sheet.parent_sheet
        else:
            parent_sheet = original_sheet
        
        # 新しいバージョン番号を設定
        latest_version = CharacterSheet.objects.filter(
            parent_sheet=parent_sheet
        ).order_by('-version').first()
        
        if latest_version:
            new_version = latest_version.version + 1
        else:
            new_version = parent_sheet.version + 1
        
        # 元のデータをコピー
        new_data = {
            'user': request.user,
            'edition': original_sheet.edition,
            'name': original_sheet.name,
            'player_name': original_sheet.player_name,
            'age': original_sheet.age,
            'gender': original_sheet.gender,
            'occupation': original_sheet.occupation,
            'birthplace': original_sheet.birthplace,
            'residence': original_sheet.residence,
            'str_value': original_sheet.str_value,
            'con_value': original_sheet.con_value,
            'pow_value': original_sheet.pow_value,
            'dex_value': original_sheet.dex_value,
            'app_value': original_sheet.app_value,
            'siz_value': original_sheet.siz_value,
            'int_value': original_sheet.int_value,
            'edu_value': original_sheet.edu_value,
            'hit_points_max': original_sheet.hit_points_max,
            'hit_points_current': original_sheet.hit_points_current,
            'magic_points_max': original_sheet.magic_points_max,
            'magic_points_current': original_sheet.magic_points_current,
            'sanity_starting': original_sheet.sanity_starting,
            'sanity_max': original_sheet.sanity_max,
            'sanity_current': original_sheet.sanity_current,
            'version': new_version,
            'parent_sheet': parent_sheet,
            'notes': original_sheet.notes,
            'is_active': original_sheet.is_active,
        }
        
        # キャラクター画像をコピー（存在する場合のみ）
        if original_sheet.character_image:
            new_data['character_image'] = original_sheet.character_image
        
        # リクエストデータで上書き
        for key, value in request.data.items():
            if key not in ['id', 'version', 'created_at', 'updated_at', 'parent_sheet', 'user']:
                new_data[key] = value
        
        # 新しいキャラクターシート作成
        new_sheet = CharacterSheet.objects.create(**new_data)
        
        # リクエストデータで現在値を個別に更新（saveメソッドの自動計算を回避）
        update_fields = {}
        for key, value in request.data.items():
            if key in ['hit_points_current', 'magic_points_current', 'sanity_current']:
                update_fields[key] = value
        
        if update_fields:
            CharacterSheet.objects.filter(id=new_sheet.id).update(**update_fields)
            new_sheet.refresh_from_db()
        
        # 元のスキルをコピー
        for skill in original_sheet.skills.all():
            CharacterSkill.objects.create(
                character_sheet=new_sheet,
                skill_name=skill.skill_name,
                base_value=skill.base_value,
                occupation_points=skill.occupation_points,
                interest_points=skill.interest_points,
                other_points=skill.other_points
            )
        
        # 元の装備をコピー
        for equipment in original_sheet.equipment.all():
            CharacterEquipment.objects.create(
                character_sheet=new_sheet,
                item_type=equipment.item_type,
                name=equipment.name,
                skill_name=equipment.skill_name,
                damage=equipment.damage,
                base_range=equipment.base_range,
                attacks_per_round=equipment.attacks_per_round,
                ammo=equipment.ammo,
                malfunction_number=equipment.malfunction_number,
                armor_points=equipment.armor_points,
                description=equipment.description,
                quantity=equipment.quantity
            )
        
        # 版別データをコピー  
        if original_sheet.edition == '6th' and hasattr(original_sheet, 'sixth_edition_data'):
            sixth_data = original_sheet.sixth_edition_data
            CharacterSheet6th.objects.create(
                character_sheet=new_sheet,
                mental_disorder=sixth_data.mental_disorder
            )
        elif original_sheet.edition == '7th' and hasattr(original_sheet, 'seventh_edition_data'):
            seventh_data = original_sheet.seventh_edition_data
            CharacterSheet7th.objects.create(
                character_sheet=new_sheet,
                luck_points=seventh_data.luck_points,
                personal_description=seventh_data.personal_description,
                ideology_beliefs=seventh_data.ideology_beliefs,
                significant_people=seventh_data.significant_people,
                meaningful_locations=seventh_data.meaningful_locations,
                treasured_possessions=seventh_data.treasured_possessions,
                traits=seventh_data.traits,
                injuries_scars=seventh_data.injuries_scars,
                phobias_manias=seventh_data.phobias_manias
            )
        
        # 作成されたキャラクターシートを返す
        response_serializer = CharacterSheetSerializer(new_sheet)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """キャラクターシートのバージョン一覧"""
        sheet = self.get_object()
        
        if sheet.parent_sheet:
            base_sheet = sheet.parent_sheet
        else:
            base_sheet = sheet
        
        # すべてのバージョンを取得
        versions = CharacterSheet.objects.filter(
            parent_sheet=base_sheet
        ).order_by('version')
        
        # 親バージョンも含める
        all_versions = [base_sheet] + list(versions)
        
        serializer = CharacterSheetListSerializer(all_versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """キャラクターシートのアクティブ状態切り替え"""
        sheet = self.get_object()
        sheet.is_active = not sheet.is_active
        sheet.save()
        
        serializer = CharacterSheetSerializer(sheet)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def create_6th_edition(self, request):
        """6版探索者専用作成エンドポイント（クトゥルフ神話TRPG専用）"""
        # データ検証
        required_fields = ['name', 'str_value', 'con_value', 'pow_value', 'dex_value', 
                          'app_value', 'siz_value', 'int_value', 'edu_value']
        
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {'error': f'{field} is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 6版の能力値範囲チェック（3-18）
        ability_fields = ['str_value', 'con_value', 'pow_value', 'dex_value', 
                         'app_value', 'int_value', 'edu_value']
        for field in ability_fields:
            value = request.data.get(field)
            if not isinstance(value, int) or value < 3 or value > 18:
                return Response(
                    {'error': f'{field} must be between 3 and 18 for 6th edition'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # SIZの範囲チェック（8-18）
        siz_value = request.data.get('siz_value')
        if not isinstance(siz_value, int) or siz_value < 8 or siz_value > 18:
            return Response(
                {'error': 'siz_value must be between 8 and 18 for 6th edition'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 基本キャラクターシート作成
            character_data = {
                'user': request.user,
                'edition': '6th',
                'name': request.data['name'],
                'player_name': request.data.get('player_name', request.user.nickname or request.user.username),
                'age': request.data.get('age', 25),
                'gender': request.data.get('gender', ''),
                'occupation': request.data.get('occupation', ''),
                'birthplace': request.data.get('birthplace', ''),
                'residence': request.data.get('residence', ''),
                'str_value': request.data['str_value'],
                'con_value': request.data['con_value'],
                'pow_value': request.data['pow_value'],
                'dex_value': request.data['dex_value'],
                'app_value': request.data['app_value'],
                'siz_value': request.data['siz_value'],
                'int_value': request.data['int_value'],
                'edu_value': request.data['edu_value'],
                'notes': request.data.get('notes', ''),
                'is_active': True
            }
            
            # キャラクターシート作成（saveメソッドで副次ステータス自動計算）
            character_sheet = CharacterSheet.objects.create(**character_data)
            
            # 6版固有データ作成
            CharacterSheet6th.objects.create(
                character_sheet=character_sheet,
                mental_disorder=request.data.get('mental_disorder', '')
            )
            
            # スキルデータがある場合は作成
            skills_data = request.data.get('skills', [])
            for skill_data in skills_data:
                if 'skill_name' in skill_data:
                    CharacterSkill.objects.create(
                        character_sheet=character_sheet,
                        skill_name=skill_data['skill_name'],
                        base_value=skill_data.get('base_value', 0),
                        occupation_points=skill_data.get('occupation_points', 0),
                        interest_points=skill_data.get('interest_points', 0),
                        other_points=skill_data.get('other_points', 0)
                    )
            
            # 装備データがある場合は作成
            equipment_data = request.data.get('equipment', [])
            for equipment in equipment_data:
                if 'name' in equipment:
                    CharacterEquipment.objects.create(
                        character_sheet=character_sheet,
                        item_type=equipment.get('item_type', 'item'),
                        name=equipment['name'],
                        skill_name=equipment.get('skill_name', ''),
                        damage=equipment.get('damage', ''),
                        base_range=equipment.get('base_range', ''),
                        attacks_per_round=equipment.get('attacks_per_round'),
                        ammo=equipment.get('ammo'),
                        malfunction_number=equipment.get('malfunction_number'),
                        armor_points=equipment.get('armor_points'),
                        description=equipment.get('description', ''),
                        quantity=equipment.get('quantity', 1)
                    )
            
            # 作成されたキャラクターシートを返す
            response_serializer = CharacterSheetSerializer(character_sheet)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Character sheet creation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CharacterSkillViewSet(viewsets.ModelViewSet):
    """キャラクタースキルViewSet"""
    serializer_class = CharacterSkillSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """関連するキャラクターシートのスキルのみ取得"""
        character_sheet_id = self.kwargs.get('character_sheet_id') or self.kwargs.get('character_sheet_pk')
        if character_sheet_id:
            # ネストされたルート用
            return CharacterSkill.objects.filter(
                character_sheet_id=character_sheet_id,
                character_sheet__user=self.request.user
            )
        else:
            # 通常のルート用（全ユーザーのスキル）
            return CharacterSkill.objects.filter(
                character_sheet__user=self.request.user
            )
    
    def perform_create(self, serializer):
        """スキル作成時にキャラクターシートを関連付け"""
        character_sheet_id = self.kwargs.get('character_sheet_id') or self.kwargs.get('character_sheet_pk')
        if character_sheet_id:
            character_sheet = CharacterSheet.objects.get(
                id=character_sheet_id,
                user=self.request.user
            )
            serializer.save(character_sheet=character_sheet)
        else:
            # character_sheet_idが指定されていない場合はエラー
            from rest_framework.exceptions import ValidationError
            raise ValidationError("character_sheet_id is required")
    
    @action(detail=False, methods=['patch'])
    def bulk_update(self, request):
        """スキルの一括更新"""
        skills_data = request.data.get('skills', [])
        if not skills_data:
            return Response(
                {'error': 'skills data is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_skills = []
        for skill_data in skills_data:
            skill_id = skill_data.get('id')
            if not skill_id:
                continue
            
            try:
                skill = CharacterSkill.objects.get(
                    id=skill_id,
                    character_sheet__user=self.request.user
                )
                
                # 更新可能なフィールドのみ処理
                updatable_fields = [
                    'base_value', 'occupation_points', 
                    'interest_points', 'other_points'
                ]
                
                for field in updatable_fields:
                    if field in skill_data:
                        setattr(skill, field, skill_data[field])
                
                skill.save()
                updated_skills.append(skill)
                
            except CharacterSkill.DoesNotExist:
                continue
        
        serializer = CharacterSkillSerializer(updated_skills, many=True)
        return Response(serializer.data)


class CharacterEquipmentViewSet(viewsets.ModelViewSet):
    """キャラクター装備ViewSet"""
    serializer_class = CharacterEquipmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """関連するキャラクターシートの装備のみ取得"""
        character_sheet_id = self.kwargs.get('character_sheet_id') or self.kwargs.get('character_sheet_pk')
        if character_sheet_id:
            # ネストされたルート用
            return CharacterEquipment.objects.filter(
                character_sheet_id=character_sheet_id,
                character_sheet__user=self.request.user
            )
        else:
            # 通常のルート用（全ユーザーの装備）
            return CharacterEquipment.objects.filter(
                character_sheet__user=self.request.user
            )
    
    def perform_create(self, serializer):
        """装備作成時にキャラクターシートを関連付け"""
        character_sheet_id = self.kwargs.get('character_sheet_id') or self.kwargs.get('character_sheet_pk')
        if character_sheet_id:
            character_sheet = CharacterSheet.objects.get(
                id=character_sheet_id,
                user=self.request.user
            )
            serializer.save(character_sheet=character_sheet)
        else:
            # character_sheet_idが指定されていない場合はエラー
            from rest_framework.exceptions import ValidationError
            raise ValidationError("character_sheet_id is required")
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """装備タイプ別の一覧"""
        item_type = request.query_params.get('type')
        if not item_type or item_type not in ['weapon', 'armor', 'item']:
            return Response(
                {'error': 'type parameter is required (weapon, armor, or item)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(item_type=item_type)
        serializer = CharacterEquipmentSerializer(queryset, many=True)
        return Response(serializer.data)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddFriendView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            friend_user = CustomUser.objects.get(username=username)
            friend, created = Friend.objects.get_or_create(
                user=request.user,
                friend=friend_user
            )
            
            if created:
                serializer = FriendSerializer(friend)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Already friends'}, status=status.HTTP_400_BAD_REQUEST)
                
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


# Django Views for Web Interface

class CustomLoginView(FormView):
    """カスタムログインビュー"""
    template_name = 'account/login.html'
    form_class = CustomLoginForm
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        remember_me = form.cleaned_data.get('remember_me', False)
        
        user = authenticate(self.request, username=username, password=password)
        if user is not None:
            login(self.request, user)
            
            # Remember me機能
            if remember_me:
                self.request.session.set_expiry(60*60*24*30)  # 30日間
            else:
                self.request.session.set_expiry(0)  # ブラウザ終了時
            
            messages.success(self.request, f'ようこそ、{user.nickname or user.username}さん！深淵へのゲートが開かれました。')
            
            # リダイレクト先の決定
            next_url = self.request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(self.success_url)
        else:
            messages.error(self.request, 'ユーザー名またはパスワードが正しくありません。')
            return self.form_invalid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class CustomSignUpView(FormView):
    """カスタムサインアップビュー"""
    template_name = 'account/signup.html'
    form_class = CustomSignUpForm
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        user = form.save()
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        
        # 自動ログイン
        user = authenticate(username=username, password=password)
        if user is not None:
            login(self.request, user)
            messages.success(
                self.request, 
                f'アカウントが作成されました！ようこそ、{user.nickname or user.username}さん。'
                '新たなる信者として、深淵の探索を始めましょう。'
            )
        
        return redirect(self.success_url)
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class ProfileEditView(FormView):
    """プロフィール編集ビュー"""
    template_name = 'account/profile_edit.html'
    form_class = ProfileEditForm
    success_url = reverse_lazy('profile_edit')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'プロフィールが更新されました。')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """ユーザーダッシュボード"""
    template_name = 'account/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 統計情報を取得
        from schedules.models import TRPGSession, SessionParticipant
        from scenarios.models import PlayHistory
        from datetime import datetime
        
        current_year = datetime.now().year
        
        # 今年のセッション統計
        sessions_this_year = TRPGSession.objects.filter(
            participants=user,
            date__year=current_year,
            status='completed'
        ).count()
        
        # 今年のプレイ時間
        from django.db import models
        total_minutes = TRPGSession.objects.filter(
            participants=user,
            date__year=current_year,
            status='completed'
        ).aggregate(total=models.Sum('duration_minutes'))['total'] or 0
        
        total_hours = round(total_minutes / 60, 1)
        
        # 参加グループ数
        group_count = Group.objects.filter(members=user).count()
        
        # フレンド数
        friend_count = Friend.objects.filter(user=user).count()
        
        # 次回セッション
        from django.utils import timezone
        upcoming_sessions = TRPGSession.objects.filter(
            participants=user,
            date__gte=timezone.now(),
            status='planned'
        ).order_by('date')[:3]
        
        context.update({
            'sessions_this_year': sessions_this_year,
            'total_hours': total_hours,
            'group_count': group_count,
            'friend_count': friend_count,
            'upcoming_sessions': upcoming_sessions,
        })
        
        return context


def mock_social_login(request, provider):
    """
    開発環境用の疑似ソーシャルログイン
    実際のOAuth認証をせずにソーシャルログインをシミュレート
    """
    if not request.user.is_authenticated:
        # デモユーザーデータ
        mock_users = {
            'google': {
                'username': f'google_user_{timezone.now().microsecond}',
                'email': 'demo.google@example.com',
                'first_name': 'Google',
                'last_name': 'User',
                'nickname': 'Google Demo User',
                'extra_data': {
                    'id': '123456789',
                    'name': 'Google User',
                    'email': 'demo.google@example.com',
                    'picture': 'https://via.placeholder.com/150/4285f4/ffffff?text=G'
                }
            },
            'twitter': {
                'username': f'twitter_user_{timezone.now().microsecond}',
                'email': 'demo.twitter@example.com', 
                'first_name': 'Twitter',
                'last_name': 'User',
                'nickname': '@TwitterDemo',
                'extra_data': {
                    'id': '987654321',
                    'name': 'Twitter User',
                    'screen_name': 'TwitterDemo',
                    'profile_image_url': 'https://via.placeholder.com/150/1da1f2/ffffff?text=X'
                }
            }
        }
        
        if provider not in mock_users:
            messages.error(request, f'サポートされていないプロバイダーです: {provider}')
            return redirect('account_login')
        
        user_data = mock_users[provider]
        
        # ユーザーを作成またはログイン
        user, created = User.objects.get_or_create(
            email=user_data['email'],
            defaults={
                'username': user_data['username'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'nickname': user_data['nickname'],
            }
        )
        
        # ソーシャルアカウント情報を作成/更新
        social_account, created = SocialAccount.objects.get_or_create(
            user=user,
            provider=provider,
            defaults={
                'uid': user_data['extra_data']['id'],
                'extra_data': user_data['extra_data']
            }
        )
        
        if not created:
            social_account.extra_data = user_data['extra_data']
            social_account.save()
        
        # ユーザーをログイン（認証バックエンドを明示的に指定）
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        if created:
            messages.success(request, f'{provider.title()}アカウントでアカウントを作成し、ログインしました！ (デモモード)')
        else:
            messages.success(request, f'{provider.title()}アカウントでログインしました！ (デモモード)')
        
        return redirect('dashboard')
    else:
        messages.info(request, '既にログイン済みです。')
        return redirect('dashboard')


def demo_login_page(request):
    """開発環境用のデモログインページ"""
    return render(request, 'account/demo_login.html')


# Character Sheet Web Views

@method_decorator(login_required, name='dispatch')
class CharacterListView(TemplateView):
    """キャラクターシート一覧画面"""
    template_name = 'accounts/character_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # エディション別のフィルタリング
        edition = self.request.GET.get('edition', 'all')
        is_active = self.request.GET.get('active', 'all')
        
        # 基本クエリセット（全ユーザーのキャラクターシートを表示）
        queryset = CharacterSheet.objects.all().select_related(
            'parent_sheet', 'sixth_edition_data', 'seventh_edition_data', 'user'
        ).prefetch_related('skills', 'equipment').order_by('-updated_at')
        
        # フィルタ適用
        if edition in ['6th', '7th']:
            queryset = queryset.filter(edition=edition)
        
        if is_active == 'active':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # エディション別統計（全ユーザー分）
        sixth_count = CharacterSheet.objects.filter(edition='6th').count()
        seventh_count = CharacterSheet.objects.filter(edition='7th').count()
        active_count = CharacterSheet.objects.filter(is_active=True).count()
        total_count = CharacterSheet.objects.count()
        
        context.update({
            'character_sheets': queryset,
            'sixth_count': sixth_count,
            'seventh_count': seventh_count,
            'active_count': active_count,
            'total_count': total_count,
            'current_edition': edition,
            'current_active': is_active,
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class CharacterDetailView(TemplateView):
    """キャラクターシート詳細表示画面"""
    template_name = 'accounts/character_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        character_id = kwargs.get('character_id')
        
        try:
            character = CharacterSheet.objects.select_related(
                'parent_sheet', 'sixth_edition_data', 'seventh_edition_data', 'user'
            ).prefetch_related(
                'skills', 'equipment', 'versions'
            ).get(id=character_id)
            
            # スキルを基本値以上のもののみフィルタリング
            assigned_skills = character.skills.filter(
                current_value__gt=models.F('base_value')
            ).order_by('skill_name')
            
            # 装備をタイプ別に分類
            weapons = character.equipment.filter(item_type='weapon')
            armor = character.equipment.filter(item_type='armor')
            items = character.equipment.filter(item_type='item')
            
            # バージョン履歴
            if character.parent_sheet:
                base_sheet = character.parent_sheet
            else:
                base_sheet = character
            
            versions = CharacterSheet.objects.filter(
                parent_sheet=base_sheet
            ).order_by('version')
            all_versions = [base_sheet] + list(versions)
            
            context.update({
                'character': character,
                'assigned_skills': assigned_skills,
                'weapons': weapons,
                'armor': armor,
                'items': items,
                'versions': all_versions,
            })
            
        except CharacterSheet.DoesNotExist:
            from django.http import Http404
            raise Http404("キャラクターシートが見つかりません")
        
        return context


@method_decorator(login_required, name='dispatch')
class CharacterEditView(TemplateView):
    """キャラクターシート編集画面"""
    template_name = 'accounts/character_edit.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        character_id = kwargs.get('character_id')
        
        if character_id:
            # 編集モード
            try:
                character = CharacterSheet.objects.select_related(
                    'sixth_edition_data', 'seventh_edition_data'
                ).prefetch_related(
                    'skills', 'equipment'
                ).get(id=character_id, user=self.request.user)
                
                context['character'] = character
                context['mode'] = 'edit'
                
            except CharacterSheet.DoesNotExist:
                from django.http import Http404
                raise Http404("キャラクターシートが見つかりません")
        else:
            # 新規作成モード
            context['mode'] = 'create'
        
        # 共通の技能リスト（6版・7版共通の基本技能）
        common_skills = [
            '応急手当', '鍵開け', '隠す', '隠れる', '聞き耳', 'こぶし', 
            'キック', 'グレップル', '頭突き', '投擲', 'マーシャルアーツ',
            '拳銃', 'サブマシンガン', 'ショットガン', 'マシンガン', 'ライフル',
            '回避', '運転（自動車）', '機械修理', '重機械操作', '乗馬',
            '水泳', '制作', '操縦（航空機）', '跳躍', '電気修理',
            'ナビゲート', '変装', 'コンピューター', '考古学', '人類学',
            '鑑定', '経理', '図書館', 'オカルト', '化学', '地質学',
            '生物学', '博物学', '物理学', '天文学', '医学', '心理学',
            '精神分析', '法律', 'クトゥルフ神話', '母国語', '他の言語',
            '芸術', '威圧', '言いくるめ', '信用', '値切り', '説得',
            '魅惑', 'ナチュラルワールド', 'サバイバル', 'トラック'
        ]
        
        context['common_skills'] = common_skills
        
        return context


@method_decorator(login_required, name='dispatch')
class Character6thCreateView(FormView):
    """クトゥルフ神話TRPG 6版探索者作成ビュー"""
    template_name = 'accounts/character_6th_create.html'
    form_class = CharacterSheet6thForm
    success_url = '/accounts/character/list/'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edition'] = '6th'
        context['edition_name'] = '6版'
        
        # 6版の基本技能リスト
        sixth_skills = [
            '応急手当', '鍵開け', '隠す', '隠れる', '聞き耳', 'こぶし', 
            'キック', 'グレップル', '頭突き', '投擲', 'マーシャルアーツ',
            'ピストル', 'サブマシンガン', 'ショットガン', 'マシンガン', 'ライフル',
            '回避', '運転', '機械修理', '重機械操作', '乗馬',
            '水泳', '制作', '操縦', '跳躍', '電気修理',
            'ナビゲート', '変装', 'コンピューター', '考古学', '人類学',
            '鑑定', '経理', '図書館', 'オカルト', '化学', '地質学',
            '生物学', '博物学', '物理学', '天文学', '医学', '心理学',
            '精神分析', '法律', 'クトゥルフ神話', '母国語', '他の言語',
            '芸術', '威圧', '言いくるめ', '信用', '値切り', '説得',
            '魅惑', '忍び歩き', '写真術', '目星'
        ]
        
        context['available_skills'] = sixth_skills
        return context
    
    def form_valid(self, form):
        character_sheet = form.save()
        messages.success(
            self.request, 
            f'クトゥルフ神話TRPG 6版探索者「{character_sheet.name}」が作成されました！'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(
            self.request, 
            '探索者の作成に失敗しました。入力内容を確認してください。'
        )
        return super().form_invalid(form)
