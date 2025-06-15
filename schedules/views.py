from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
from .models import TRPGSession, SessionParticipant, HandoutInfo
from .serializers import (
    TRPGSessionSerializer, SessionParticipantSerializer, 
    HandoutInfoSerializer, CalendarEventSerializer, SessionListSerializer
)
from accounts.models import Group


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
        sessions = TRPGSession.objects.filter(
            Q(group__members=user) | 
            Q(visibility='public') |
            Q(participants=user)
        ).distinct().select_related('gm', 'group').order_by('-date')
        
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
        sessions = TRPGSession.objects.filter(
            Q(group__members=user) | 
            Q(visibility='public') |
            Q(participants=user)
        ).distinct().select_related('gm', 'group').order_by('-date')
        
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
        return TRPGSession.objects.filter(
            Q(group__members=user) | 
            Q(visibility='public') |
            Q(participants=user)
        ).distinct().order_by('-date')
    
    def perform_create(self, serializer):
        serializer.save(gm=self.request.user)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        session = self.get_object()
        participant, created = SessionParticipant.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={'role': 'player'}
        )
        
        if created:
            serializer = SessionParticipantSerializer(participant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Already joined'}, status=status.HTTP_400_BAD_REQUEST)
    
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


class SessionParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = SessionParticipantSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SessionParticipant.objects.filter(
            session__group__members=self.request.user
        ).distinct()


class HandoutInfoViewSet(viewsets.ModelViewSet):
    serializer_class = HandoutInfoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # GMは全て、参加者は自分宛+公開ハンドアウト
        return HandoutInfo.objects.filter(
            Q(session__gm=user) |  # GMは全て見られる
            Q(participant__user=user) |  # 自分宛は見られる
            (Q(session__participants=user) & Q(is_secret=False))  # 参加者は公開ハンドアウトも見られる
        ).distinct()
    
    def perform_create(self, serializer):
        # GMのみハンドアウト作成可能
        session = serializer.validated_data['session']
        if session.gm != self.request.user:
            raise PermissionError("Only GM can create handouts")
        serializer.save()


class CalendarView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')
        month_str = request.query_params.get('month')
        
        # 月指定の場合
        if month_str and not (start_date or end_date):
            try:
                # YYYY-MM形式をパース
                year, month = map(int, month_str.split('-'))
                start_date = datetime(year, month, 1)
                # 月末を計算
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            except (ValueError, AttributeError):
                return Response(
                    {'error': 'Invalid month format. Use YYYY-MM format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif start_date and end_date:
            try:
                start_date = datetime.fromisoformat(start_date)
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                return Response(
                    {'error': 'Invalid date format'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {'error': 'Either month or both start and end parameters are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sessions = TRPGSession.objects.filter(
            Q(group__members=request.user) | 
            Q(visibility='public') |
            Q(participants=request.user),
            date__range=[start_date, end_date]
        ).distinct()
        
        # イベント形式に変換
        events = []
        for session in sessions:
            # ユーザーのセッションとの関係を判定
            is_gm = session.gm == request.user
            is_participant = session.participants.filter(id=request.user.id).exists() and not is_gm
            is_public_only = not is_gm and not is_participant and session.visibility == 'public'
            
            # セッションタイプを決定
            if is_gm:
                session_type = 'gm'
            elif is_participant:
                session_type = 'participant'
            else:
                session_type = 'public'
            
            event = {
                'id': session.id,
                'title': session.title,
                'date': session.date.isoformat(),
                'type': session_type,
                'status': session.status,
                'visibility': session.visibility,
                'gm_id': session.gm.id,
                'gm_name': session.gm.nickname or session.gm.username,
                'location': session.location or '',
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
        upcoming_sessions = TRPGSession.objects.filter(
            Q(group__members=user) | 
            Q(visibility='public') |
            Q(participants=user),
            date__gte=now,
            date__lte=now + timedelta(days=7)
        ).distinct().select_related('gm', 'group').order_by('date')[:5]
        
        serializer = SessionListSerializer(upcoming_sessions, many=True)
        return Response(serializer.data)


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
            session = TRPGSession.objects.get(pk=pk)
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
        participants = SessionParticipant.objects.filter(session=session).select_related('user')
        
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
            not is_participant and 
            session.status == 'planned' and 
            (session.visibility != 'private' or session.group.members.filter(id=user.id).exists())
        )
        
        context = {
            'session': session,
            'participants': participants,
            'handouts': handouts,
            'is_gm': is_gm,
            'is_participant': is_participant,
            'can_edit': can_edit,
            'can_join': can_join,
            'user_participant': participants.filter(user=user).first(),
        }
        
        return render(request, 'schedules/session_detail.html', context)
