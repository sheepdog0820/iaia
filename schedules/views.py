from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Sum, Count, Case, When, Value, IntegerField, DateTimeField, F
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.urls import reverse
from datetime import datetime, timedelta
from .models import (
    TRPGSession,
    SessionOccurrence,
    SessionParticipant,
    SessionInvitation,
    SessionNote,
    SessionLog,
    HandoutInfo,
    SessionImage,
    SessionYouTubeLink,
)
from .serializers import (
    TRPGSessionSerializer,
    SessionOccurrenceSerializer,
    SessionParticipantSerializer,
    SessionInvitationSerializer,
    SessionNoteSerializer,
    SessionLogSerializer,
    HandoutInfoSerializer,
    CalendarEventSerializer,
    SessionListSerializer,
    SessionImageSerializer,
    SessionYouTubeLinkSerializer,
)
from .services import YouTubeService
from .notifications import SessionNotificationService
from accounts.models import Group, GroupMembership, CustomUser, CharacterSheet


def _visible_sessions_for(user):
    group_ids = GroupMembership.objects.filter(user=user).values_list('group_id', flat=True)
    participant_session_ids = SessionParticipant.objects.filter(user=user).values_list('session_id', flat=True)
    return TRPGSession.objects.filter(
        Q(gm=user) |
        Q(visibility='public') |
        Q(group_id__in=group_ids) |
        Q(id__in=participant_session_ids)
    ).distinct()


class SessionsListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Accept headerをチェックしてJSONまたはHTMLを返す
        if 'application/json' in request.headers.get('Accept', ''):
            return self.get_json_response(request)
        else:
            return self.get_html_response(request)
    
    def get_json_response(self, request):
        user = request.user
        sessions = _visible_sessions_for(user).select_related('gm', 'group').order_by('-date')
        
        # ページネーション対応
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        total_count = sessions.count()
        sessions = sessions[offset:offset + limit]
        
        serializer = SessionListSerializer(sessions, many=True)
        
        return Response({
            'count': total_count,
            'results': serializer.data,
            'limit': limit,
            'offset': offset,
            'has_next': (offset + limit) < total_count,
            'has_previous': offset > 0
        })
    
    def get_html_response(self, request):
        user = request.user
        sessions = _visible_sessions_for(user).select_related('gm', 'group').order_by('-date')
        
        # ページネーション対応
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        total_count = sessions.count()
        sessions = sessions[offset:offset + limit]
        
        context = {
            'sessions': sessions,
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'has_next': (offset + limit) < total_count,
            'has_previous': offset > 0
        }
        
        return render(request, 'schedules/sessions_list.html', context)


class TRPGSessionViewSet(viewsets.ModelViewSet):
    serializer_class = TRPGSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # ユーザーが参加しているグループのセッション、または公開セッション
        return _visible_sessions_for(user).select_related('scenario').order_by('-date')
    
    def perform_create(self, serializer):
        serializer.save(gm=self.request.user)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # 変更前の日時を保存
        old_date = instance.date
        old_status = instance.status
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # 保存
        self.perform_update(serializer)
        
        # 通知サービス
        notification_service = SessionNotificationService()
        
        # スケジュール変更通知
        if old_date != instance.date:
            notification_service.send_session_schedule_change_notification(
                instance, old_date, instance.date
            )
        
        # キャンセル通知
        if old_status != 'cancelled' and instance.status == 'cancelled':
            cancel_reason = request.data.get('cancel_reason', '')
            notification_service.send_session_cancelled_notification(
                instance, cancel_reason
            )

        # セッション完了時の統計更新
        if old_status != 'completed' and instance.status == 'completed':
            self._update_session_statistics(instance)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        
        return Response(serializer.data)
    
    def _update_session_statistics(self, session):
        """セッション完了時の統計を更新"""
        from scenarios.models import PlayHistory, Scenario
        
        # セッション参加者の統計更新
        participants = SessionParticipant.objects.filter(
            session=session
        ).select_related('user', 'character_sheet')
        
        scenario = session.scenario
        if not scenario:
            # ダミーシナリオを作成（シナリオ未連携時のフォールバック）
            scenario, _ = Scenario.objects.get_or_create(
                title=f"Session: {session.title}",
                defaults={
                    'game_system': 'coc',
                    'created_by': session.gm,
                    'summary': session.description
                }
            )
        
        for participant in participants:
            # プレイ履歴の作成
            PlayHistory.objects.get_or_create(
                user=participant.user,
                session=session,
                role=participant.role,
                defaults={
                    'scenario': scenario,
                    'played_date': session.date,
                    'notes': f"Character: {participant.character_name}"
                }
            )
            
            # キャラクターのセッション数増加
            if participant.character_sheet:
                participant.character_sheet.session_count += 1
                participant.character_sheet.save()
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        session = self.get_object()

        # 公開設定に応じた参加制限
        if session.visibility == 'private' and session.gm != request.user:
            return Response(
                {'error': 'このセッションはプライベートです'},
                status=status.HTTP_403_FORBIDDEN
            )
        if session.visibility == 'group':
            if not session.group.members.filter(id=request.user.id).exists() and session.gm != request.user:
                return Response(
                    {'error': 'このセッションはグループメンバー限定です'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # プレイヤー枠とキャラクターシートを取得
        player_slot = request.data.get('player_slot')
        character_sheet_id = request.data.get('character_sheet_id') or request.data.get('character_sheet')
        character_sheet = None
        if character_sheet_id:
            try:
                character_sheet = CharacterSheet.objects.get(
                    id=character_sheet_id,
                    user=request.user
                )
            except CharacterSheet.DoesNotExist:
                return Response(
                    {'error': 'Character sheet not found or not owned by you'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # プレイヤー枠の重複チェック
        if player_slot:
            existing_slot = SessionParticipant.objects.filter(
                session=session,
                player_slot=player_slot
            ).exclude(user=request.user).exists()
            
            if existing_slot:
                return Response(
                    {'error': f'Player slot {player_slot} is already taken'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        character_name = request.data.get('character_name', '').strip()
        if not character_name and character_sheet:
            character_name = character_sheet.name

        participant, created = SessionParticipant.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={
                'role': 'player',
                'player_slot': player_slot,
                'character_name': character_name,
                'character_sheet_url': request.data.get('character_sheet_url', ''),
                'character_sheet': character_sheet
            }
        )
        
        if not created:
            # 既存の参加者の情報を更新
            if player_slot:
                participant.player_slot = player_slot
            if 'character_name' in request.data:
                participant.character_name = request.data.get('character_name', '')
            if 'character_sheet_url' in request.data:
                participant.character_sheet_url = request.data.get('character_sheet_url', '')
            if 'character_sheet_id' in request.data or 'character_sheet' in request.data:
                participant.character_sheet = character_sheet
            participant.save()
        
        serializer = SessionParticipantSerializer(participant)
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        """join の互換エンドポイント"""
        response = self.join(request, pk=pk)
        if response.status_code == status.HTTP_201_CREATED:
            response.status_code = status.HTTP_200_OK
        return response
    
    @action(detail=True, methods=['delete'])
    def leave(self, request, pk=None):
        session = self.get_object()
        try:
            participant = SessionParticipant.objects.get(
                session=session,
                user=request.user
            )
            participant.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except SessionParticipant.DoesNotExist:
            return Response({'error': 'Not a participant'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """セッションの参加者一覧を取得"""
        session = self.get_object()
        participants = SessionParticipant.objects.filter(
            session=session
        ).select_related('user', 'character_sheet')
        
        serializer = SessionParticipantSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_co_gm(self, request, pk=None):
        """協力GMを追加"""
        session = self.get_object()
        
        # メインGMのみ実行可能
        if session.gm != request.user:
            return Response(
                {'error': 'Only main GM can add co-GMs'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        co_gm_id = request.data.get('user_id')
        if not co_gm_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            co_gm = CustomUser.objects.get(id=co_gm_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 既に参加者の場合
        existing = SessionParticipant.objects.filter(
            session=session, user=co_gm
        ).first()
        
        if existing:
            if existing.role == 'gm':
                return Response(
                    {'error': 'User is already a co-GM'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # プレイヤーから昇格
            existing.role = 'gm'
            existing.save()
        else:
            # 新規追加
            SessionParticipant.objects.create(
                session=session,
                user=co_gm,
                role='gm'
            )
        
        return Response({'message': 'Co-GM added successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """セッションに参加者を招待（ISSUE-013実装）"""
        session = self.get_object()
        
        # GMのみ招待可能（メインGMまたは協力GM）
        is_gm = session.gm == request.user
        is_co_gm = SessionParticipant.objects.filter(
            session=session, user=request.user, role='gm'
        ).exists()
        
        if not is_gm and not is_co_gm:
            return Response(
                {'error': 'Only GM can invite participants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        invitee_id = request.data.get('user_id')
        if not invitee_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            invitee = CustomUser.objects.get(id=invitee_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 既に参加者の場合
        if SessionParticipant.objects.filter(session=session, user=invitee).exists():
            return Response(
                {'error': 'User is already a participant'},
                status=status.HTTP_400_BAD_REQUEST
            )

        message = (request.data.get('message') or '').strip()

        invitation, created = SessionInvitation.objects.get_or_create(
            session=session,
            invitee=invitee,
            defaults={
                'inviter': request.user,
                'status': 'pending',
                'message': message,
            }
        )

        if not created:
            invitation.inviter = request.user
            invitation.status = 'pending'
            invitation.message = message
            invitation.created_at = timezone.now()
            invitation.responded_at = None
            invitation.save(update_fields=[
                'inviter',
                'status',
                'message',
                'created_at',
                'responded_at',
            ])

        notification_service = SessionNotificationService()
        notification_sent = notification_service.send_session_invitation_notification(
            session, request.user, invitee, invitation_id=invitation.id
        )

        return Response({
            'status': 'success',
            'invitation_id': invitation.id,
            'notification_sent': bool(notification_sent),
            'message': f'Invitation created for {invitee.nickname or invitee.username}'
        })
    
    @action(detail=True, methods=['post'])
    def assign_player(self, request, pk=None):
        """GM専用: プレイヤー枠にユーザーを割り当て"""
        session = self.get_object()
        
        # GMのみ実行可能
        if session.gm != request.user:
            return Response(
                {'error': 'Only GM can assign players'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        player_slot = request.data.get('player_slot')
        user_id = request.data.get('user_id')
        character_sheet_id = request.data.get('character_sheet_id') or request.data.get('character_sheet')
        
        if not player_slot or not user_id:
            return Response(
                {'error': 'player_slot and user_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 対象ユーザーの確認
        try:
            target_user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # グループメンバーかチェック
        if session.group and not session.group.members.filter(id=target_user.id).exists():
            return Response(
                {'error': 'User is not a member of this group'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 既存の枠チェック
        existing_slot = SessionParticipant.objects.filter(
            session=session,
            player_slot=player_slot
        ).exclude(user=target_user).first()
        
        if existing_slot:
            return Response(
                {'error': f'Player slot {player_slot} is already taken by {existing_slot.user.nickname}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        character_sheet = None
        if character_sheet_id:
            try:
                character_sheet = CharacterSheet.objects.get(
                    id=character_sheet_id,
                    user=target_user
                )
            except CharacterSheet.DoesNotExist:
                return Response(
                    {'error': 'Character sheet not found or not owned by the user'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 参加者の作成または更新
        participant, created = SessionParticipant.objects.update_or_create(
            session=session,
            user=target_user,
            defaults={
                'role': 'player',
                'player_slot': player_slot,
                'character_sheet': character_sheet
            }
        )
        
        serializer = SessionParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        from .serializers import UpcomingSessionSerializer
        from django.utils import timezone

        now = timezone.now()
        sessions = self.get_queryset().filter(
            date__gte=now,
            status='planned'
        ).select_related('gm', 'group').prefetch_related(
            'sessionparticipant_set__user'
        ).order_by('date')[:5]

        serializer = UpcomingSessionSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-sessions')
    def my_sessions(self, request):
        """参加予定セッション一覧API（ISSUE-030）

        フィルター:
        - role: gm/player（デフォルト: すべて）
        - status: planned/ongoing/completed/cancelled（デフォルト: planned,ongoing）
        - period: future/past7/past30/past90（デフォルト: future、空の場合はすべて）
        """
        user = request.user
        now = timezone.now()

        # 基本クエリ: ユーザーが参加しているセッション
        participant_session_ids = SessionParticipant.objects.filter(
            user=user
        ).values_list('session_id', flat=True)

        sessions = TRPGSession.objects.filter(
            Q(gm=user) | Q(id__in=participant_session_ids)
        ).select_related('gm', 'group', 'scenario').prefetch_related(
            'sessionparticipant_set__user'
        ).distinct()

        # ロールフィルター
        role = request.query_params.get('role', '')
        if role == 'gm':
            sessions = sessions.filter(gm=user)
        elif role == 'player':
            sessions = sessions.filter(id__in=participant_session_ids).exclude(gm=user)

        # ステータスフィルター
        status_filter = request.query_params.get('status', '')
        if status_filter:
            sessions = sessions.filter(status=status_filter)
        else:
            # デフォルト: 予定と進行中
            sessions = sessions.filter(status__in=['planned', 'ongoing'])

        # 期間フィルター
        period = request.query_params.get('period', 'future')
        if period == 'future':
            sessions = sessions.filter(date__gte=now)
        elif period == 'past7':
            sessions = sessions.filter(date__gte=now - timedelta(days=7), date__lt=now)
        elif period == 'past30':
            sessions = sessions.filter(date__gte=now - timedelta(days=30), date__lt=now)
        elif period == 'past90':
            sessions = sessions.filter(date__gte=now - timedelta(days=90), date__lt=now)
        # period='' の場合はフィルターなし（すべて）

        # ソート: futureは昇順、past系は降順、allは未来→過去の順
        if period == 'future':
            sessions = sessions.order_by('date')
        elif period in {'past7', 'past30', 'past90'}:
            sessions = sessions.order_by('-date')
        else:
            sessions = sessions.annotate(
                _period_sort_group=Case(
                    When(date__gte=now, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                _future_date=Case(
                    When(date__gte=now, then=F('date')),
                    default=Value(None),
                    output_field=DateTimeField(),
                ),
                _past_date=Case(
                    When(date__lt=now, then=F('date')),
                    default=Value(None),
                    output_field=DateTimeField(),
                ),
            ).order_by('_period_sort_group', '_future_date', '-_past_date')

        # ページネーション
        def _safe_positive_int(value, default, *, max_value=None):
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                return default
            if parsed < 1:
                return default
            if max_value is not None and parsed > max_value:
                return max_value
            return parsed

        page = _safe_positive_int(request.query_params.get('page', 1), 1)
        page_size = _safe_positive_int(request.query_params.get('page_size', 20), 20, max_value=100)
        offset = (page - 1) * page_size

        total_count = sessions.count()
        sessions_page = sessions[offset:offset + page_size]

        # ユーザーのロール情報を付加してシリアライズ
        result = []
        for session in sessions_page:
            session_data = TRPGSessionSerializer(session, context={'request': request}).data
            # ユーザーのロールを追加
            if session.gm_id == user.id:
                session_data['my_role'] = 'gm'
            else:
                session_data['my_role'] = 'player'
            result.append(session_data)

        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': result
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        user = request.user
        year = request.query_params.get('year', datetime.now().year)
        
        # 年間プレイ時間計算
        sessions = TRPGSession.objects.filter(
            participants=user,
            date__year=year,
            status='completed'
        )
        
        total_minutes = sessions.aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0
        
        total_hours = total_minutes / 60
        session_count = sessions.count()
        
        return Response({
            'year': year,
            'total_hours': round(total_hours, 1),
            'total_minutes': total_minutes,
            'session_count': session_count,
            'average_session_hours': round(total_hours / session_count, 1) if session_count > 0 else 0
        })

    @action(detail=False, methods=['get'], url_path='editable-choices')
    def editable_choices(self, request):
        sessions = self.get_queryset().filter(gm=request.user).select_related('group')[:200]
        return Response([
            {
                'id': session.id,
                'title': session.title,
                'group_id': session.group_id,
                'group_name': session.group.name if session.group_id else '',
            }
            for session in sessions
        ])


class SessionInvitationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SessionInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = SessionInvitation.objects.filter(
            invitee=self.request.user
        ).select_related(
            'session',
            'session__group',
            'inviter',
        )

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        invitation = self.get_object()

        if invitation.is_expired:
            invitation.mark_expired()
            return Response(
                {'error': '招待の期限が切れています'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if invitation.status == 'accepted':
            participant = SessionParticipant.objects.filter(
                session=invitation.session,
                user=request.user
            ).first()
            return Response({
                'status': 'already_accepted',
                'session_id': invitation.session.id,
                'participant_id': participant.id if participant else None,
            })

        if invitation.status != 'pending':
            return Response(
                {'error': 'この招待は保留状態ではありません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        participant, created = SessionParticipant.objects.get_or_create(
            session=invitation.session,
            user=request.user,
            defaults={'role': 'player'}
        )

        invitation.status = 'accepted'
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=['status', 'responded_at'])

        return Response({
            'status': 'success',
            'session_id': invitation.session.id,
            'participant_id': participant.id,
            'already_participating': not created,
        })

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        invitation = self.get_object()

        if invitation.is_expired:
            invitation.mark_expired()
            return Response(
                {'error': '招待の期限が切れています'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if invitation.status == 'declined':
            return Response({'status': 'already_declined'})

        if invitation.status != 'pending':
            return Response(
                {'error': 'この招待は保留状態ではありません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invitation.status = 'declined'
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=['status', 'responded_at'])

        return Response({'status': 'success'})


class SessionOccurrenceViewSet(viewsets.ModelViewSet):
    serializer_class = SessionOccurrenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        visible_session_ids = _visible_sessions_for(user).values_list('id', flat=True)

        queryset = SessionOccurrence.objects.select_related(
            'session',
            'session__gm',
            'session__group',
        ).prefetch_related('participants').filter(session_id__in=visible_session_ids)

        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)

        return queryset.order_by('start_at', 'id')

    def perform_create(self, serializer):
        session = serializer.validated_data.get('session')
        if not session or session.gm_id != self.request.user.id:
            raise PermissionDenied('Only the GM can add session dates.')
        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.session.gm_id != self.request.user.id:
            raise PermissionDenied('Only the GM can edit session dates.')

        old_start_at = instance.start_at
        new_session = serializer.validated_data.get('session')
        if new_session and new_session.id != instance.session_id:
            raise ValidationError({'session': 'Cannot change the session of an occurrence.'})

        serializer.save()

        if (
            instance.is_primary
            and 'start_at' in serializer.validated_data
            and old_start_at != instance.start_at
            and instance.session.date != instance.start_at
        ):
            session = instance.session
            session.date = instance.start_at
            session.save(update_fields=['date', 'updated_at'])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.session.gm_id != request.user.id:
            raise PermissionDenied('Only the GM can delete session dates.')
        if instance.is_primary:
            raise ValidationError({'detail': 'Cannot delete the primary session date.'})
        return super().destroy(request, *args, **kwargs)


class SessionParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = SessionParticipantSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # セッションIDでフィルタリング可能
        session_id = self.request.query_params.get('session_id')
        queryset = SessionParticipant.objects.select_related(
            'session',
            'user',
            'character_sheet'
        )
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        # アクセス可能なセッションの参加者のみ
        return queryset.filter(
            Q(session__group__members=self.request.user) |  # グループメンバー
            Q(session__visibility='public') |  # 公開セッション
            Q(session__gm=self.request.user) |  # GM
            Q(user=self.request.user)  # 自分の参加
        ).distinct()
    
    def create(self, request, *args, **kwargs):
        """参加申請の作成（クロス参加対応）"""
        session_id = request.data.get('session')
        
        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # セッションへのアクセス権限チェック
        target_user_id = request.data.get('user') or request.user.id
        try:
            target_user = CustomUser.objects.get(id=target_user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        is_gm = session.gm == request.user or SessionParticipant.objects.filter(
            session=session,
            user=request.user,
            role='gm'
        ).exists()

        if target_user != request.user and not is_gm:
            return Response(
                {'error': 'You do not have permission to add other participants'},
                status=status.HTTP_403_FORBIDDEN
            )

        can_participate = (
            session.visibility == 'public' or  # 公開セッション
            session.group.members.filter(id=target_user.id).exists() or  # グループメンバー
            session.gm == target_user  # GM
        )
        
        if not can_participate:
            return Response(
                {'error': 'You do not have permission to join this session'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 既に参加している場合
        if SessionParticipant.objects.filter(session=session, user=target_user).exists():
            return Response(
                {'error': 'You are already participating in this session'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # キャラクターシートの取得
        character_sheet_id = request.data.get('character_sheet_id')
        character_sheet = None
        if character_sheet_id:
            try:
                character_sheet = CharacterSheet.objects.get(
                    id=character_sheet_id,
                    user=target_user
                )
            except CharacterSheet.DoesNotExist:
                return Response(
                    {'error': 'Character sheet not found or not owned by you'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 参加者作成
        role = request.data.get('role', 'player')
        if role not in ['player', 'gm']:
            role = 'player'

        # 権限昇格防止: メインGM以外は role='gm' を指定できない
        if role == 'gm' and session.gm != request.user:
            return Response(
                {'error': 'Only main GM can assign GM role'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data={
            'session': session.id,
            'user': target_user.id,
            'character_name': request.data.get('character_name', ''),
            'character_sheet': character_sheet.id if character_sheet else None,
            'role': role
        })
        
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """参加情報の更新（GM承認機能）"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # GM権限チェック（メインGMまたは協力GM）
        is_main_gm = instance.session.gm == request.user
        is_co_gm = SessionParticipant.objects.filter(
            session=instance.session, user=request.user, role='gm'
        ).exists()
        is_gm = is_main_gm or is_co_gm
        
        # GMまたは本人のみ更新可能
        if not is_gm and instance.user != request.user:
            return Response(
                {'error': 'You do not have permission to update this participant'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # ステータス変更はGMのみ
        data = request.data.copy()
        if hasattr(data, 'dict'):
            data = data.dict()

        # session/user の変更は禁止（データ改ざん防止）
        for immutable_field in ['session', 'user']:
            if immutable_field in data:
                return Response(
                    {'error': f'{immutable_field} cannot be changed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # role 変更はメインGMのみ（権限昇格防止）
        if 'role' in data and not is_main_gm:
            return Response(
                {'error': 'Only main GM can change participant role'},
                status=status.HTTP_403_FORBIDDEN
            )

        # プレイヤー枠の重複チェック（joinと同等）
        if 'player_slot' in data:
            raw_slot = data.get('player_slot')
            slot_value = None
            if raw_slot not in [None, '', 'null', 'None']:
                try:
                    slot_value = int(raw_slot)
                except (TypeError, ValueError):
                    slot_value = None

            if slot_value:
                existing_slot = SessionParticipant.objects.filter(
                    session=instance.session,
                    player_slot=slot_value
                ).exclude(id=instance.id).exists()

                if existing_slot:
                    return Response(
                        {'error': f'Player slot {slot_value} is already taken'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        if 'character_sheet_id' in data and 'character_sheet' not in data:
            data['character_sheet'] = data.get('character_sheet_id')
            data.pop('character_sheet_id', None)

        if 'character_sheet' in data:
            raw_value = data.get('character_sheet')
            if raw_value in [None, '', 'null', 'None']:
                data['character_sheet'] = None
            else:
                try:
                    CharacterSheet.objects.get(id=raw_value, user=instance.user)
                except CharacterSheet.DoesNotExist:
                    return Response(
                        {'error': 'Character sheet not found or not owned by participant'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """参加者削除（本人の脱退 or GMによる除名のみ許可）"""
        instance = self.get_object()

        is_main_gm = instance.session.gm == request.user
        is_co_gm = SessionParticipant.objects.filter(
            session=instance.session,
            user=request.user,
            role='gm'
        ).exists()

        # 本人は自分の参加情報を削除できる（脱退）
        if instance.user == request.user:
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # GM（メイン/協力）のみ他人を削除できる
        if is_main_gm or is_co_gm:
            if instance.user == instance.session.gm:
                return Response(
                    {'error': 'Cannot remove main GM'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {'error': 'Only GM can remove other participants'},
            status=status.HTTP_403_FORBIDDEN
        )


class HandoutInfoViewSet(viewsets.ModelViewSet):
    serializer_class = HandoutInfoSerializer
    permission_classes = [IsAuthenticated]

    class DefaultPagination(PageNumberPagination):
        page_size = 20
        page_size_query_param = 'page_size'
        max_page_size = 100

    pagination_class = DefaultPagination
    
    def get_queryset(self):
        user = self.request.user
        # GMは全て、参加者は自分宛+公開ハンドアウト
        # プレイヤー枠に基づくハンドアウトも含める
        from django.db.models import OuterRef, Subquery
        
        # ユーザーのプレイヤー枠を取得
        user_slots = SessionParticipant.objects.filter(
            user=user
        ).values_list('player_slot', 'session_id')
        
        return HandoutInfo.objects.filter(
            Q(session__gm=user) |  # GMは全て見られる
            Q(participant__user=user) |  # 自分宛は見られる
            (Q(session__participants=user) & Q(is_secret=False)) |  # 参加者は公開ハンドアウトも見られる
            Q(  # プレイヤー枠に割り当てられたハンドアウト
                assigned_player_slot__in=[slot[0] for slot in user_slots if slot[0]],
                session_id__in=[slot[1] for slot in user_slots]
            )
        ).distinct()
    
    def perform_create(self, serializer):
        # GMのみハンドアウト作成可能
        session = serializer.validated_data['session']
        if session.gm != self.request.user:
            raise PermissionError("Only GM can create handouts")
        
        # ハンドアウト番号とプレイヤー枠の整合性チェック
        handout_number = serializer.validated_data.get('handout_number')
        assigned_player_slot = serializer.validated_data.get('assigned_player_slot')
        
        if handout_number and assigned_player_slot:
            # 通常、HO1はプレイヤー1、HO2はプレイヤー2...に対応
            if handout_number != assigned_player_slot:
                # 警告ログを出力（強制はしない）
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Handout number {handout_number} assigned to player slot {assigned_player_slot}"
                )
        
        serializer.save()

    @action(detail=False, methods=['post'])
    def toggle_visibility(self, request):
        """ハンドアウトの公開/秘匿切り替え（GMのみ）"""
        handout_id = request.data.get('handout_id')

        if not handout_id:
            return Response({'error': 'handout_idが必要です'}, status=status.HTTP_400_BAD_REQUEST)

        handout = get_object_or_404(HandoutInfo, id=handout_id)

        if handout.session.gm != request.user:
            return Response({'error': 'GM権限が必要です'}, status=status.HTTP_403_FORBIDDEN)

        handout.is_secret = not handout.is_secret
        handout.save()

        serializer = HandoutInfoSerializer(handout)
        return Response({
            'handout': serializer.data,
            'message': f'ハンドアウトを{"秘匿" if handout.is_secret else "公開"}に設定しました'
        })


class CalendarView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        start_raw = request.query_params.get('start')
        end_raw = request.query_params.get('end')
        month_str = request.query_params.get('month')
        
        # 月指定の場合
        if month_str and not (start_raw or end_raw):
            try:
                # YYYY-MM形式をパース
                year, month = map(int, month_str.split('-'))
                tz = timezone.get_current_timezone()
                start_date = timezone.make_aware(datetime(year, month, 1), tz)
                if month == 12:
                    month_end = datetime(year + 1, 1, 1)
                else:
                    month_end = datetime(year, month + 1, 1)
                end_date = timezone.make_aware(month_end, tz) - timedelta(microseconds=1)
            except (ValueError, AttributeError):
                return Response(
                    {'error': 'Invalid month format. Use YYYY-MM format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif start_raw and end_raw:
            try:
                start_date = datetime.fromisoformat(start_raw)
                end_date = datetime.fromisoformat(end_raw)
            except ValueError:
                return Response(
                    {'error': 'Invalid date format'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            tz = timezone.get_current_timezone()
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date, tz)
            if timezone.is_naive(end_date):
                if 'T' not in end_raw:
                    end_date = end_date + timedelta(days=1) - timedelta(microseconds=1)
                end_date = timezone.make_aware(end_date, tz)
        else:
            return Response(
                {'error': 'Either month or both start and end parameters are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        visible_session_ids = _visible_sessions_for(request.user).values_list('id', flat=True)
        participant_session_ids = set(
            SessionParticipant.objects.filter(user=request.user).values_list('session_id', flat=True)
        )

        occurrences = SessionOccurrence.objects.filter(
            session_id__in=visible_session_ids,
            start_at__range=[start_date, end_date],
        ).select_related('session', 'session__gm', 'session__group').order_by('start_at', 'id')
        
        # イベント形式に変換
        events = []
        for occurrence in occurrences:
            session = occurrence.session
            # ユーザーのセッションとの関係を判定
            is_gm = session.gm == request.user
            is_gm = session.gm_id == request.user.id
            is_participant = (session.id in participant_session_ids) and not is_gm
            is_public_only = not is_gm and not is_participant and session.visibility == 'public'
            
            # セッションタイプを決定
            if is_gm:
                session_type = 'gm'
            elif is_participant:
                session_type = 'participant'
            else:
                session_type = 'public'
            
            event = {
                'id': occurrence.id,
                'session_id': session.id,
                'occurrence_id': occurrence.id,
                'title': session.title,
                'date': occurrence.start_at.isoformat(),
                'type': session_type,
                'status': session.status,
                'visibility': session.visibility,
                'gm_id': session.gm.id,
                'gm_name': session.gm.nickname or session.gm.username,
                'location': session.location or '',
                'content': occurrence.content or '',
                'is_gm': is_gm,
                'is_participant': is_participant,
                'is_public_only': is_public_only
            }
            events.append(event)
        
        # month指定の場合は特別なレスポンス形式
        if month_str:
            return Response({
                'month': month_str,
                'events': events
            })
        else:
            return Response(events)


class MonthlyEventListView(APIView):
    """月別イベント一覧API（ISSUE-008実装）"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # YYYY-MM形式の月指定を取得
        month_str = request.query_params.get('month')
        if not month_str:
            return Response(
                {'error': 'month parameter is required (YYYY-MM format)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year, month = map(int, month_str.split('-'))
            tz = timezone.get_current_timezone()
            start_date = timezone.make_aware(datetime(year, month, 1), tz)
            if month == 12:
                month_end = datetime(year + 1, 1, 1)
            else:
                month_end = datetime(year, month + 1, 1)
            end_date = timezone.make_aware(month_end, tz) - timedelta(microseconds=1)
        except (ValueError, AttributeError):
            return Response(
                {'error': 'Invalid month format. Use YYYY-MM format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # セッションを取得
        visible_session_ids = _visible_sessions_for(request.user).values_list('id', flat=True)
        participant_session_ids = set(
            SessionParticipant.objects.filter(user=request.user).values_list('session_id', flat=True)
        )

        occurrences = SessionOccurrence.objects.filter(
            session_id__in=visible_session_ids,
            start_at__range=[start_date, end_date],
        ).select_related('session', 'session__gm', 'session__group').prefetch_related('participants').order_by('start_at', 'id')
        
        # 日付別にグループ化
        events_by_date = {}
        for occurrence in occurrences:
            session = occurrence.session
            date_str = occurrence.start_at.strftime('%Y-%m-%d')
            if date_str not in events_by_date:
                events_by_date[date_str] = {
                    'date': date_str,
                    'events': []
                }
            
            # ユーザーとの関係を判定
            is_gm = session.gm_id == request.user.id
            is_participant = (session.id in participant_session_ids) and not is_gm
            
            event_data = {
                'id': occurrence.id,
                'session_id': session.id,
                'occurrence_id': occurrence.id,
                'title': session.title,
                'time': occurrence.start_at.strftime('%H:%M'),
                'duration_minutes': session.duration_minutes,
                'status': session.status,
                'visibility': session.visibility,
                'group': {
                    'id': session.group.id,
                    'name': session.group.name
                } if session.group else None,
                'gm': {
                    'id': session.gm.id,
                    'name': session.gm.nickname or session.gm.username
                },
                'participant_count': len(occurrence.participants.all()),
                'is_gm': is_gm,
                'is_participant': is_participant,
                'location': session.location or '',
                'content': occurrence.content or '',
            }
            
            events_by_date[date_str]['events'].append(event_data)
        
        # 日付順にソート
        sorted_dates = sorted(events_by_date.values(), key=lambda x: x['date'])
        
        return Response({
            'month': month_str,
            'year': year,
            'month_name': f"{year}年{month}月",
            'dates': sorted_dates,
            'total_sessions': occurrences.count(),
            'summary': {
                'planned': occurrences.filter(session__status='planned').count(),
                'ongoing': occurrences.filter(session__status='ongoing').count(),
                'completed': occurrences.filter(session__status='completed').count(),
                'cancelled': occurrences.filter(session__status='cancelled').count()
            }
        })


class SessionAggregationView(APIView):
    """セッション予定集約API（ISSUE-008実装）"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 期間指定
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now()
        end_date = start_date + timedelta(days=days)
        
        # ユーザーのセッションを取得
        visible_session_ids = _visible_sessions_for(request.user).values_list('id', flat=True)
        participant_session_ids = set(
            SessionParticipant.objects.filter(user=request.user).values_list('session_id', flat=True)
        )

        occurrences = SessionOccurrence.objects.filter(
            session_id__in=visible_session_ids,
            start_at__range=[start_date, end_date],
            session__status__in=['planned', 'ongoing'],
        ).select_related('session', 'session__gm', 'session__group').order_by('start_at', 'id')
        
        # グループ別、システム別に集約
        aggregations = {
            'by_group': {},
            'by_system': {},
            'by_week': {},
            'by_role': {
                'as_gm': [],
                'as_player': []
            }
        }
        
        for occurrence in occurrences:
            session = occurrence.session
            # グループ別集約
            if session.group:
                group_key = session.group.id
                if group_key not in aggregations['by_group']:
                    aggregations['by_group'][group_key] = {
                        'group_id': session.group.id,
                        'group_name': session.group.name,
                        'sessions': []
                    }
                aggregations['by_group'][group_key]['sessions'].append({
                    'id': occurrence.id,
                    'session_id': session.id,
                    'occurrence_id': occurrence.id,
                    'title': session.title,
                    'date': occurrence.start_at.isoformat()
                })
            
            # 週別集約
            week_key = occurrence.start_at.strftime('%Y-W%U')
            if week_key not in aggregations['by_week']:
                aggregations['by_week'][week_key] = {
                    'week': week_key,
                    'start_date': (occurrence.start_at - timedelta(days=occurrence.start_at.weekday())).strftime('%Y-%m-%d'),
                    'sessions': []
                }
            aggregations['by_week'][week_key]['sessions'].append({
                'id': occurrence.id,
                'session_id': session.id,
                'occurrence_id': occurrence.id,
                'title': session.title,
                'date': occurrence.start_at.isoformat()
            })
            
            # 役割別集約
            if session.gm_id == request.user.id:
                aggregations['by_role']['as_gm'].append({
                    'id': occurrence.id,
                    'session_id': session.id,
                    'occurrence_id': occurrence.id,
                    'title': session.title,
                    'date': occurrence.start_at.isoformat(),
                    'participant_count': session.participants.count()
                })
            elif session.id in participant_session_ids:
                aggregations['by_role']['as_player'].append({
                    'id': occurrence.id,
                    'session_id': session.id,
                    'occurrence_id': occurrence.id,
                    'title': session.title,
                    'date': occurrence.start_at.isoformat(),
                    'gm_name': session.gm.nickname or session.gm.username
                })
        
        return Response({
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'total_sessions': occurrences.count(),
            'aggregations': aggregations,
            'upcoming_sessions': [
                {
                    'id': upcoming.id,
                    'session_id': upcoming.session.id,
                    'occurrence_id': upcoming.id,
                    'title': upcoming.session.title,
                    'date': upcoming.start_at.isoformat(),
                }
                for upcoming in occurrences.order_by('start_at')[:5]
            ]
        })


class ICalExportView(APIView):
    """iCal形式エクスポートAPI（ISSUE-008実装）"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.http import HttpResponse
        import uuid
        
        # 期間指定
        days = int(request.query_params.get('days', 90))
        start_date = timezone.now()
        end_date = start_date + timedelta(days=days)
        
        # セッションを取得
        visible_session_ids = _visible_sessions_for(request.user).values_list('id', flat=True)
        occurrences = SessionOccurrence.objects.filter(
            session_id__in=visible_session_ids,
            start_at__range=[start_date, end_date],
        ).select_related('session', 'session__gm', 'session__group').order_by('start_at', 'id')
        
        # iCal形式の生成
        lines = []
        lines.append('BEGIN:VCALENDAR')
        lines.append('VERSION:2.0')
        lines.append('PRODID:-//タブレノ//TRPG Session Calendar//JP')
        lines.append('CALSCALE:GREGORIAN')
        lines.append('METHOD:PUBLISH')
        lines.append(f'X-WR-CALNAME:タブレノ - {request.user.nickname or request.user.username}')
        lines.append('X-WR-TIMEZONE:Asia/Tokyo')
        
        for occurrence in occurrences:
            # イベントの開始・終了時刻
            session = occurrence.session
            dtstart = occurrence.start_at
            dtend = dtstart + timedelta(minutes=session.duration_minutes or 180)
            
            # ユーザーとの関係
            is_gm = session.gm_id == request.user.id
            role = 'GM' if is_gm else 'Player'
            
            lines.append('BEGIN:VEVENT')
            lines.append(f'UID:{uuid.uuid4()}@tableno.jp')
            lines.append(f'DTSTAMP:{timezone.now().strftime("%Y%m%dT%H%M%SZ")}')
            lines.append(f'DTSTART:{dtstart.strftime("%Y%m%dT%H%M%S")}')
            lines.append(f'DTEND:{dtend.strftime("%Y%m%dT%H%M%S")}')
            lines.append(f'SUMMARY:[{role}] {session.title}')
            
            # 詳細説明
            description_parts = []
            description_parts.append(f'Status: {session.get_status_display()}')
            description_parts.append(f'GM: {session.gm.nickname or session.gm.username}')
            if session.group:
                description_parts.append(f'Group: {session.group.name}')
            if session.location:
                description_parts.append(f'Location: {session.location}')
            if session.description:
                description_parts.append(f'\\n{session.description}')
            
            lines.append(f'DESCRIPTION:{" | ".join(description_parts)}')
            
            if session.location:
                lines.append(f'LOCATION:{session.location}')
            
            # ステータスに応じた設定
            if session.status == 'cancelled':
                lines.append('STATUS:CANCELLED')
            elif session.status == 'completed':
                lines.append('STATUS:CONFIRMED')
            else:
                lines.append('STATUS:TENTATIVE')
            
            # カテゴリ
            lines.append(f'CATEGORIES:TRPG,{role}')
            
            # アラーム設定（1日前と1時間前）
            if session.status == 'planned':
                # 1日前のリマインダー
                lines.append('BEGIN:VALARM')
                lines.append('TRIGGER:-P1D')
                lines.append('ACTION:DISPLAY')
                lines.append(f'DESCRIPTION:明日のTRPGセッション: {session.title}')
                lines.append('END:VALARM')
                
                # 1時間前のリマインダー
                lines.append('BEGIN:VALARM')
                lines.append('TRIGGER:-PT1H')
                lines.append('ACTION:DISPLAY')
                lines.append(f'DESCRIPTION:1時間後のTRPGセッション: {session.title}')
                lines.append('END:VALARM')
            
            lines.append('END:VEVENT')
        
        lines.append('END:VCALENDAR')
        
        # レスポンス生成
        response = HttpResponse(
            '\r\n'.join(lines),
            content_type='text/calendar; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="tableno_sessions_{timezone.now().strftime("%Y%m%d")}.ics"'
        
        return response


class CreateSessionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = TRPGSessionSerializer(data=request.data)
        if serializer.is_valid():
            # GMとして自動設定
            session = serializer.save(gm=request.user)
            
            # GMを参加者として自動追加
            SessionParticipant.objects.create(
                session=session,
                user=request.user,
                role='gm'
            )
            
            return Response(
                TRPGSessionSerializer(session).data, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JoinSessionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        session = get_object_or_404(TRPGSession, pk=pk)
        
        # 参加可能かチェック
        if session.visibility == 'private':
            return Response(
                {'error': 'This session is private'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        participant, created = SessionParticipant.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={
                'role': 'player',
                'character_name': request.data.get('character_name', ''),
                'character_sheet_url': request.data.get('character_sheet_url', '')
            }
        )
        
        if created:
            serializer = SessionParticipantSerializer(participant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': 'Already joined this session'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class UpcomingSessionsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        now = timezone.now()
        
        # 今日から7日以内のセッション
        def format_duration(minutes):
            if not minutes:
                return None
            hours = minutes // 60
            mins = minutes % 60
            if hours > 0 and mins > 0:
                return f"{hours}時間{mins}分"
            if hours > 0:
                return f"{hours}時間"
            return f"{mins}分"

        def format_date_display(dt):
            if not dt:
                return None
            local_dt = dt.replace(tzinfo=None) if getattr(dt, 'tzinfo', None) else dt
            local_now = now.replace(tzinfo=None) if getattr(now, 'tzinfo', None) else now

            if local_dt.date() == local_now.date():
                return f"今日 {dt.strftime('%H:%M')}"
            if local_dt.date() == (local_now + timedelta(days=1)).date():
                return f"明日 {dt.strftime('%H:%M')}"
            if local_dt.date() <= (local_now + timedelta(days=7)).date():
                weekdays = ['月', '火', '水', '木', '金', '土', '日']
                weekday = weekdays[local_dt.weekday()]
                return f"{local_dt.strftime('%m/%d')}({weekday}) {dt.strftime('%H:%M')}"
            return dt.strftime('%Y年%m月%d日 %H:%M')

        visible_session_ids = _visible_sessions_for(user).values_list('id', flat=True)
        occurrences = SessionOccurrence.objects.filter(
            session_id__in=visible_session_ids,
            start_at__gte=now,
            start_at__lte=now + timedelta(days=7),
        ).select_related(
            'session',
            'session__gm',
            'session__group',
            'session__scenario',
        ).prefetch_related(
            'session__sessionparticipant_set__user',
        ).order_by('start_at', 'id')[:5]

        results = []
        for occurrence in occurrences:
            session = occurrence.session
            participants = list(session.sessionparticipant_set.all())
            players = [p for p in participants if p.user_id != session.gm_id]

            if len(players) == 0:
                participants_summary = "GM のみ"
            elif len(players) <= 3:
                participants_summary = ", ".join([p.user.nickname or p.user.username for p in players])
            else:
                names = [p.user.nickname or p.user.username for p in players[:2]]
                participants_summary = f"{', '.join(names)} 他{len(players) - 2}人"

            results.append({
                'id': session.id,
                'session_id': session.id,
                'occurrence_id': occurrence.id,
                'title': session.title,
                'date': occurrence.start_at.isoformat(),
                'date_formatted': occurrence.start_at.strftime('%Y年%m月%d日 %H:%M'),
                'date_display': format_date_display(occurrence.start_at),
                'location': session.location or '',
                'status': session.status,
                'gm_name': session.gm.nickname or session.gm.username,
                'group_name': session.group.name if session.group_id else '',
                'participant_count': len(participants),
                'participants_summary': participants_summary,
                'duration_minutes': session.duration_minutes,
                'duration_display': format_duration(session.duration_minutes),
            })

        return Response(results)


class NextSessionContextView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        occurrence = None

        session_id = request.query_params.get('session_id')
        if session_id:
            try:
                session_id = int(session_id)
            except (TypeError, ValueError):
                return Response({'error': 'session_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

            session = TRPGSession.objects.select_related('scenario').filter(id=session_id).first()
            if not session:
                return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

            if session.gm != user and not session.participants.filter(id=user.id).exists():
                return Response({'error': 'このセッションにアクセスする権限がありません'}, status=status.HTTP_403_FORBIDDEN)
        else:
            occurrence = SessionOccurrence.objects.filter(
                Q(session__gm=user) | Q(session__participants=user),
                start_at__gte=now,
                session__status='planned',
            ).select_related('session', 'session__scenario').order_by('start_at', 'id').first()
            session = occurrence.session if occurrence else None

        if not session:
            return Response({'session_id': None})

        if occurrence is None:
            occurrence = (
                session.occurrences.filter(start_at__gte=now).order_by('start_at', 'id').first()
                or session.occurrences.order_by('start_at', 'id').first()
            )

        scenario = session.scenario
        scenario_data = None
        if scenario:
            scenario_data = {
                'id': scenario.id,
                'title': scenario.title,
                'game_system': scenario.game_system,
                'recommended_skills': scenario.recommended_skills or '',
            }

        participant = SessionParticipant.objects.filter(session=session, user=user).first()
        handout_skills = []
        handout_titles = []
        if participant:
            handouts = HandoutInfo.objects.filter(session=session, participant=participant)
            for handout in handouts:
                if handout.recommended_skills:
                    handout_skills.append(handout.recommended_skills)
                    handout_titles.append(handout.title)

        return Response({
            'session_id': session.id,
            'session_title': session.title,
            'session_date': occurrence.start_at if occurrence else session.date,
            'occurrence_id': occurrence.id if occurrence else None,
            'scenario': scenario_data,
            'handout_recommended_skills': handout_skills,
            'handout_titles': handout_titles,
        })


class ParticipatingScenarioChoicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        occurrence = None

        try:
            days = int(request.query_params.get('days', 365))
        except (TypeError, ValueError):
            days = 365
        try:
            limit = int(request.query_params.get('limit', 50))
        except (TypeError, ValueError):
            limit = 50

        if days < 1:
            days = 1
        if days > 365:
            days = 365
        if limit < 1:
            limit = 1
        if limit > 100:
            limit = 100

        occurrences = SessionOccurrence.objects.filter(
            Q(session__gm=user) | Q(session__participants=user),
            start_at__gte=now,
            start_at__lte=now + timedelta(days=days),
            session__status='planned',
            session__scenario__isnull=False,
        ).select_related('session', 'session__scenario', 'session__group').order_by('start_at', 'id')[:limit]

        results = []
        for occurrence in occurrences:
            session = occurrence.session
            scenario = session.scenario
            if not scenario:
                continue

            session_date_display = None
            if occurrence.start_at:
                session_date_display = occurrence.start_at.strftime('%Y/%m/%d %H:%M')

            results.append({
                'session_id': session.id,
                'occurrence_id': occurrence.id,
                'session_title': session.title,
                'session_date': occurrence.start_at,
                'session_date_display': session_date_display,
                'group_name': session.group.name if session.group else '',
                'scenario': {
                    'id': scenario.id,
                    'title': scenario.title,
                    'game_system': scenario.game_system,
                }
            })

        return Response(results)


class SessionStatisticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        now = timezone.now()
        year_ago = now - timedelta(days=365)
        
        # 年間統計
        user_sessions = TRPGSession.objects.filter(
            Q(participants=user) | Q(gm=user),
            date__gte=year_ago,
            date__lte=now
        ).distinct()
        
        session_count = user_sessions.count()
        total_minutes = user_sessions.aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0
        total_hours = round(total_minutes / 60, 1)
        
        return Response({
            'session_count': session_count,
            'total_hours': total_hours,
            'total_minutes': total_minutes
        })


class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        # セッション詳細取得
        try:
            session = TRPGSession.objects.select_related('scenario').get(pk=pk)
        except TRPGSession.DoesNotExist:
            if 'application/json' in request.headers.get('Accept', ''):
                return Response({'error': 'Session not found'}, status=404)
            else:
                from django.http import Http404
                raise Http404("Session not found")
        
        # アクセス権限チェック
        user = request.user
        has_access = (
            session.visibility == 'public' or
            session.gm == user or
            session.group.members.filter(id=user.id).exists() or
            session.participants.filter(id=user.id).exists()
        )
        
        if not has_access:
            if 'application/json' in request.headers.get('Accept', ''):
                return Response({'error': 'Permission denied'}, status=403)
            else:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("このセッションにアクセスする権限がありません")
        
        # HTMLまたはJSONレスポンス
        if 'application/json' in request.headers.get('Accept', ''):
            return self.get_json_response(session, user)
        else:
            return self.get_html_response(request, session, user)
    
    def get_json_response(self, session, user):
        from .serializers import TRPGSessionSerializer
        serializer = TRPGSessionSerializer(session)
        return Response(serializer.data)
    
    def get_html_response(self, request, session, user):
        # 参加者情報
        participants = SessionParticipant.objects.filter(
            session=session
        ).select_related('user', 'character_sheet')

        occurrences = session.occurrences.prefetch_related('participants').order_by('start_at', 'id')
        
        # ハンドアウト情報（権限に応じて）
        if session.gm == user:
            # GMは全てのハンドアウトを見られる
            handouts = HandoutInfo.objects.filter(session=session).select_related('participant__user')
        else:
            # 一般参加者は自分のハンドアウトのみ
            user_participant = participants.filter(user=user).first()
            if user_participant:
                handouts = HandoutInfo.objects.filter(participant=user_participant)
            else:
                handouts = HandoutInfo.objects.none()
        
        # ユーザーの権限
        is_gm = session.gm == user
        is_participant = participants.filter(user=user).exists()
        can_edit = is_gm
        can_join = (
            (not is_gm) and
            (not is_participant) and
            session.status == 'planned' and
            session.visibility != 'private' and
            (session.visibility != 'group' or session.group.members.filter(id=user.id).exists())
        )

        public_session_url = request.build_absolute_uri(
            reverse('public_session_detail', kwargs={'share_token': session.share_token})
        )
        
        context = {
            'session': session,
            'participants': participants,
            'occurrences': occurrences,
            'handouts': handouts,
            'is_gm': is_gm,
            'is_participant': is_participant,
            'can_edit': can_edit,
            'can_join': can_join,
            'user_participant': participants.filter(user=user).first(),
            'public_session_url': public_session_url,
            'is_public_view': False,
        }
        
        return render(request, 'schedules/session_detail.html', context)


class PublicSessionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, share_token):
        session = get_object_or_404(
            TRPGSession.objects.select_related('scenario', 'gm', 'group'),
            share_token=share_token,
        )

        participants = SessionParticipant.objects.filter(
            session=session
        ).select_related('user', 'character_sheet')

        occurrences = session.occurrences.prefetch_related('participants').order_by('start_at', 'id')

        public_session_url = request.build_absolute_uri(
            reverse('public_session_detail', kwargs={'share_token': session.share_token})
        )

        context = {
            'session': session,
            'participants': participants,
            'occurrences': occurrences,
            'handouts': HandoutInfo.objects.none(),
            'is_gm': False,
            'is_participant': False,
            'can_edit': False,
            'can_join': False,
            'user_participant': None,
            'public_session_url': public_session_url,
            'is_public_view': True,
        }

        return render(request, 'schedules/session_detail.html', context)


class SessionNoteViewSet(viewsets.ModelViewSet):
    """セッションノート管理ViewSet"""
    serializer_class = SessionNoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        session_id = self.kwargs.get('session_id') or self.request.query_params.get('session_id')
        queryset = SessionNote.objects.select_related('session', 'author')

        if session_id:
            session = get_object_or_404(TRPGSession, id=session_id)
            if not self._has_session_access(session, user):
                return SessionNote.objects.none()
            if self._is_gm(session, user):
                return queryset.filter(session=session)
            return queryset.filter(session=session).filter(
                Q(note_type__in=['public_summary', 'handover']) |
                Q(note_type='player_note', author=user)
            )

        return queryset.filter(
            Q(session__gm=user) |
            (Q(session__participants=user) & (
                Q(note_type__in=['public_summary', 'handover']) |
                Q(note_type='player_note', author=user)
            ))
        ).distinct()

    def create(self, request, *args, **kwargs):
        session_id = self.kwargs.get('session_id') or request.data.get('session')
        if not session_id:
            return Response(
                {'error': 'session is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = get_object_or_404(TRPGSession, id=session_id)
        if not self._has_session_access(session, request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        is_gm = self._is_gm(session, request.user)
        note_type = request.data.get('note_type') or 'player_note'

        if not is_gm and note_type != 'player_note':
            return Response(
                {'error': 'Only GM can create this note type'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not is_gm and str(request.data.get('is_pinned', '')).lower() in ['1', 'true', 'yes']:
            return Response(
                {'error': 'Only GM can pin notes'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session, author=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = self.get_object()
        session = instance.session
        user = self.request.user
        is_gm = self._is_gm(session, user)

        if not self._can_edit_note(instance, user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only GM or author can update notes")

        if not is_gm:
            if 'note_type' in self.request.data and self.request.data['note_type'] != instance.note_type:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Only GM can change note type")
            if 'is_pinned' in self.request.data:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Only GM can pin notes")

        serializer.save()

    def perform_destroy(self, instance):
        if not self._can_edit_note(instance, self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only GM or author can delete notes")
        instance.delete()

    def _has_session_access(self, session, user):
        return session.gm == user or session.participants.filter(id=user.id).exists()

    def _is_gm(self, session, user):
        return session.gm == user or SessionParticipant.objects.filter(
            session=session,
            user=user,
            role='gm'
        ).exists()

    def _can_edit_note(self, note, user):
        if self._is_gm(note.session, user):
            return True
        return note.author == user and note.note_type == 'player_note'


class SessionLogViewSet(viewsets.ModelViewSet):
    """セッションログ管理ViewSet"""
    serializer_class = SessionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        session_id = self.kwargs.get('session_id') or self.request.query_params.get('session_id')
        queryset = SessionLog.objects.select_related(
            'session',
            'created_by',
            'related_character'
        )

        if session_id:
            session = get_object_or_404(TRPGSession, id=session_id)
            if not self._has_session_access(session, user):
                return SessionLog.objects.none()
            return queryset.filter(session=session)

        return queryset.filter(
            Q(session__gm=user) | Q(session__participants=user)
        ).distinct()

    def create(self, request, *args, **kwargs):
        session_id = self.kwargs.get('session_id') or request.data.get('session')
        if not session_id:
            return Response(
                {'error': 'session is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = get_object_or_404(TRPGSession, id=session_id)
        if not self._has_session_access(session, request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        related_character_id = data.get('related_character')
        if related_character_id:
            if not SessionParticipant.objects.filter(
                session=session,
                character_sheet_id=related_character_id
            ).exists():
                return Response(
                    {'error': 'related_character is not part of this session'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session, created_by=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = self.get_object()
        if not self._can_edit_log(instance, self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only GM or creator can update logs")

        serializer.save()

    def perform_destroy(self, instance):
        if not self._can_edit_log(instance, self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only GM or creator can delete logs")
        instance.delete()

    def _has_session_access(self, session, user):
        return session.gm == user or session.participants.filter(id=user.id).exists()

    def _is_gm(self, session, user):
        return session.gm == user or SessionParticipant.objects.filter(
            session=session,
            user=user,
            role='gm'
        ).exists()

    def _can_edit_log(self, log, user):
        if self._is_gm(log.session, user):
            return True
        return log.created_by == user


class SessionImageViewSet(viewsets.ModelViewSet):
    """セッション画像ViewSet"""
    serializer_class = SessionImageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """ユーザーがアクセス可能なセッションの画像のみ取得"""
        user = self.request.user
        return SessionImage.objects.filter(
            Q(session__gm=user) |  # GMは全て見られる
            Q(session__participants=user) |  # 参加者は見られる
            Q(session__group__members=user)  # グループメンバーは見られる
        ).distinct()
    
    def create(self, request, *args, **kwargs):
        """画像作成時の権限チェック"""
        session_id = request.data.get('session')
        if not session_id:
            return Response(
                {'error': 'session is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 権限チェック
        if session.gm != request.user and not session.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'Only GM or participants can upload images'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """画像アップロード時の処理"""
        # createメソッドで権限チェック済みなので、ここでは保存のみ
        session_id = self.request.data.get('session')
        session = TRPGSession.objects.get(id=session_id)
        serializer.save(uploaded_by=self.request.user, session=session)
    
    def perform_update(self, serializer):
        """画像更新時の処理"""
        instance = self.get_object()
        
        # GMまたはアップロード者のみ編集可能
        if instance.session.gm != self.request.user and instance.uploaded_by != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only GM or uploader can edit images")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """画像削除時の処理"""
        # GMまたはアップロード者のみ削除可能
        if instance.session.gm != self.request.user and instance.uploaded_by != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only GM or uploader can delete images")
        
        instance.delete()
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """複数画像の一括アップロード"""
        session_id = request.data.get('session_id')
        images = request.FILES.getlist('images', [])
        
        if not session_id:
            return Response(
                {'error': 'session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 権限チェック
        if session.gm != request.user and not session.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 画像を一括作成
        created_images = []
        for image_file in images[:10]:  # 最大10枚まで
            session_image = SessionImage.objects.create(
                session=session,
                image=image_file,
                title=image_file.name,
                uploaded_by=request.user
            )
            created_images.append(session_image)
        
        serializer = SessionImageSerializer(created_images, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """画像の表示順序変更"""
        image = self.get_object()
        new_order = request.data.get('order')
        
        if new_order is None:
            return Response(
                {'error': 'order is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # GMのみ順序変更可能
        if image.session.gm != request.user:
            return Response(
                {'error': 'Only GM can reorder images'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        image.order = new_order
        image.save()
        
        return Response({'status': 'success', 'order': image.order})


class SessionYouTubeLinkViewSet(viewsets.ModelViewSet):
    """セッションYouTube動画リンク管理ViewSet"""
    serializer_class = SessionYouTubeLinkSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """クエリセット取得"""
        user = self.request.user
        
        # session_id が指定されている場合
        session_id = self.kwargs.get('session_id')
        if session_id:
            # セッションへのアクセス権限確認
            session = get_object_or_404(TRPGSession, id=session_id)
            if session.gm == user or session.participants.filter(id=user.id).exists():
                return SessionYouTubeLink.objects.filter(session_id=session_id)
            else:
                return SessionYouTubeLink.objects.none()
        
        # 通常のクエリ
        return SessionYouTubeLink.objects.filter(
            Q(session__gm=user) | Q(session__participants=user)
        ).distinct()
    
    def create(self, request, *args, **kwargs):
        """YouTube動画リンクの追加"""
        session_id = self.kwargs.get('session_id')
        if not session_id:
            session_id = request.data.get('session')
        
        if not session_id:
            return Response(
                {'error': 'session is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 権限チェック
        if session.gm != request.user and not session.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'Only GM or participants can add YouTube links'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # YouTube URLから動画情報を取得
        youtube_url = request.data.get('youtube_url')
        if not youtube_url:
            return Response(
                {'error': 'youtube_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 動画IDの抽出
        video_id = SessionYouTubeLink.extract_video_id(youtube_url)
        if not video_id:
            return Response(
                {'error': 'Invalid YouTube URL'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 重複チェック
        if SessionYouTubeLink.objects.filter(session=session, video_id=video_id).exists():
            return Response(
                {'error': 'This video is already linked to the session'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # YouTube API から動画情報取得
        video_info = YouTubeService.fetch_video_info(video_id)
        if not video_info:
            return Response(
                {'error': 'Could not fetch video information'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # シリアライザーでインスタンス作成
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            session=session,
            added_by=request.user,
            video_id=video_id,
            title=video_info['title'],
            duration_seconds=video_info['duration'],
            channel_name=video_info['channel_name'],
            thumbnail_url=video_info['thumbnail_url']
        )
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_update(self, serializer):
        """動画リンク更新時の処理"""
        instance = self.get_object()
        
        # GMまたは追加者のみ編集可能
        if instance.session.gm != self.request.user and instance.added_by != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only GM or the person who added can edit")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """動画リンク削除時の処理"""
        # GMまたは追加者のみ削除可能
        if instance.session.gm != self.request.user and instance.added_by != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only GM or the person who added can delete")
        
        instance.delete()
    
    @action(detail=False, methods=['post'])
    def fetch_info(self, request):
        """YouTube URLから動画情報を取得"""
        youtube_url = request.data.get('youtube_url')
        if not youtube_url:
            return Response(
                {'error': 'youtube_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 動画IDの抽出
        video_id = SessionYouTubeLink.extract_video_id(youtube_url)
        if not video_id:
            return Response(
                {'error': 'Invalid YouTube URL'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # YouTube API から動画情報取得
        video_info = YouTubeService.fetch_video_info(video_id)
        if not video_info:
            return Response(
                {'error': 'Could not fetch video information'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'video_id': video_id,
            'title': video_info['title'],
            'duration_seconds': video_info['duration'],
            'channel_name': video_info['channel_name'],
            'thumbnail_url': video_info['thumbnail_url']
        })
    
    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """動画リンクの表示順序変更"""
        link = self.get_object()
        new_order = request.data.get('order')
        
        if new_order is None:
            return Response(
                {'error': 'order is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # GMのみ順序変更可能
        if link.session.gm != request.user:
            return Response(
                {'error': 'Only GM can reorder videos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        link.order = new_order
        link.save()
        
        serializer = self.get_serializer(link)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request, session_id=None):
        """セッションの動画統計情報を取得"""
        if not session_id:
            session_id = self.kwargs.get('session_id')
        if not session_id:
            session_id = request.query_params.get('session_id')
        
        if not session_id:
            return Response(
                {'error': 'session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 権限チェック
        if session.gm != request.user and not session.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 統計情報取得
        statistics = SessionYouTubeLink.get_session_statistics(session)
        
        return Response(statistics)
