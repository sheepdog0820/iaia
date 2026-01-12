"""
管理者用ユーザー管理API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from ..serializers import UserSerializer, UserDetailSerializer
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    管理者用ユーザー管理ViewSet
    
    管理者のみがアクセス可能なユーザー管理API
    """
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """ユーザー一覧取得（関連データ含む）"""
        return User.objects.select_related('auth_token').prefetch_related(
            'created_groups',
            'groupmembership_set',
            'character_sheets',
            'gm_sessions',
            'sessionparticipant_set'
        ).annotate(
            group_count=Count('groupmembership'),
            character_count=Count('character_sheets'),
            gm_session_count=Count('gm_sessions'),
            player_session_count=Count('sessionparticipant')
        ).order_by('-date_joined')
    
    def get_serializer_class(self):
        """アクションに応じたシリアライザー選択"""
        if self.action == 'list':
            return UserSerializer
        return UserDetailSerializer
    
    @action(detail=True, methods=['post'])
    def set_staff(self, request, pk=None):
        """ユーザーをスタッフに設定"""
        user = self.get_object()
        user.is_staff = True
        user.save()
        return Response({
            'message': f'{user.username}をスタッフに設定しました',
            'user': UserDetailSerializer(user).data
        })
    
    @action(detail=True, methods=['post'])
    def unset_staff(self, request, pk=None):
        """ユーザーのスタッフ権限を解除"""
        user = self.get_object()
        if user.is_superuser:
            return Response(
                {'error': 'スーパーユーザーのスタッフ権限は解除できません'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_staff = False
        user.save()
        return Response({
            'message': f'{user.username}のスタッフ権限を解除しました',
            'user': UserDetailSerializer(user).data
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """ユーザーをアクティブ化"""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({
            'message': f'{user.username}をアクティブ化しました',
            'user': UserDetailSerializer(user).data
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """ユーザーを非アクティブ化"""
        user = self.get_object()
        if user.is_superuser:
            return Response(
                {'error': 'スーパーユーザーは非アクティブ化できません'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_active = False
        user.save()
        return Response({
            'message': f'{user.username}を非アクティブ化しました',
            'user': UserDetailSerializer(user).data
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """ユーザー統計情報"""
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        staff_users = User.objects.filter(is_staff=True).count()
        oauth_users = User.objects.filter(
            Q(socialaccount__provider='google') | 
            Q(socialaccount__provider='twitter_oauth2') |
            Q(socialaccount__provider='discord')
        ).distinct().count()
        
        recent_users = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'staff_users': staff_users,
            'oauth_users': oauth_users,
            'recent_users': recent_users,
            'inactive_users': total_users - active_users
        })
    
    @action(detail=True, methods=['get'])
    def activity(self, request, pk=None):
        """ユーザーの活動履歴"""
        user = self.get_object()
        
        # 最近のセッション参加
        recent_sessions = user.sessionparticipant_set.select_related(
            'session__gm', 'session__group'
        ).order_by('-session__date')[:10]
        
        # GMとして開催したセッション
        gm_sessions = user.gm_sessions.select_related('group').order_by('-date')[:10]
        
        # 作成したキャラクター
        characters = user.character_sheets.filter(is_active=True).order_by('-created_at')[:10]
        
        return Response({
            'user': UserDetailSerializer(user).data,
            'recent_sessions': [{
                'id': p.session.id,
                'title': p.session.title,
                'date': p.session.date,
                'role': p.role,
                'gm': p.session.gm.username
            } for p in recent_sessions],
            'gm_sessions': [{
                'id': s.id,
                'title': s.title,
                'date': s.date,
                'participant_count': s.participants.count()
            } for s in gm_sessions],
            'characters': [{
                'id': c.id,
                'name': c.name,
                'occupation': c.occupation,
                'edition': c.edition,
                'created_at': c.created_at
            } for c in characters]
        })
