from django.shortcuts import render
from django.db.models import Q, Count, Sum
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from .models import Scenario, ScenarioNote, PlayHistory
from .serializers import ScenarioSerializer, ScenarioNoteSerializer, PlayHistorySerializer


class ScenarioViewSet(viewsets.ModelViewSet):
    serializer_class = ScenarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Scenario.objects.all()
        
        # 検索フィルター
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(author__icontains=search) |
                Q(summary__icontains=search)
            )
        
        # ゲームシステムフィルター
        game_system = self.request.query_params.get('game_system')
        if game_system:
            queryset = queryset.filter(game_system=game_system)
        
        # プレイヤー数フィルター
        player_count = self.request.query_params.get('player_count')
        if player_count:
            queryset = queryset.filter(player_count=player_count)
        
        # 難易度フィルター
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # 推定時間フィルター
        estimated_duration = self.request.query_params.get('estimated_duration')
        if estimated_duration:
            queryset = queryset.filter(estimated_duration=estimated_duration)
        
        return queryset.order_by('title')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        scenario = self.get_object()
        notes = ScenarioNote.objects.filter(
            scenario=scenario,
            user=request.user
        )
        serializer = ScenarioNoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def play_history(self, request, pk=None):
        scenario = self.get_object()
        history = PlayHistory.objects.filter(
            scenario=scenario,
            user=request.user
        )
        serializer = PlayHistorySerializer(history, many=True)
        return Response(serializer.data)


class ScenarioNoteViewSet(viewsets.ModelViewSet):
    serializer_class = ScenarioNoteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # 自分が作成したメモ、または公開メモを表示
        from django.db.models import Q
        return ScenarioNote.objects.filter(
            Q(user=self.request.user) | Q(is_private=False)
        )
    
    def get_object(self):
        """オブジェクト取得時の権限チェック"""
        obj = super().get_object()
        
        # 自分が作成したメモ、または公開メモのみアクセス可能
        if obj.user == self.request.user or not obj.is_private:
            return obj
        
        # プライベートメモで作成者でない場合は404を返す
        from django.http import Http404
        raise Http404("Note not found")
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PlayHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = PlayHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PlayHistory.objects.filter(user=self.request.user).order_by('-played_date')
    
    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if 'played_date' not in data and 'session_date' in data:
            data['played_date'] = data['session_date']

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        session = serializer.validated_data.get('session')
        scenario = serializer.validated_data.get('scenario')
        role = serializer.validated_data.get('role')
        played_date = serializer.validated_data.get('played_date')
        notes_provided = 'notes' in serializer.validated_data
        notes = serializer.validated_data.get('notes', '')

        if session:
            existing = PlayHistory.objects.filter(
                user=request.user,
                session=session,
                role=role
            ).first()
            if existing:
                existing.scenario = scenario
                existing.played_date = played_date
                if notes_provided:
                    existing.notes = notes
                update_fields = ['scenario', 'played_date']
                if notes_provided:
                    update_fields.append('notes')
                existing.save(update_fields=update_fields)
                output = self.get_serializer(existing)
                headers = self.get_success_headers(output.data)
                return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

        instance = serializer.save(user=request.user)
        output = self.get_serializer(instance)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)


class ScenarioArchiveView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # シナリオ一覧とプレイ統計
        scenarios = Scenario.objects.annotate(
            play_count=Count('play_histories'),
            total_play_time=Sum('play_histories__session__duration_minutes')
        ).order_by('-play_count', 'title')
        
        # ユーザーのプレイ履歴も含める
        user_played_scenarios = PlayHistory.objects.filter(
            user=request.user
        ).values_list('scenario_id', flat=True)
        
        serializer = ScenarioSerializer(scenarios, many=True)
        data = serializer.data
        
        # プレイ済みフラグを追加
        for item in data:
            item['user_played'] = item['id'] in user_played_scenarios
        
        return Response(data)


class PlayStatisticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        year = request.query_params.get('year', datetime.now().year)
        
        # 年間統計
        histories = PlayHistory.objects.filter(
            user=user,
            played_date__year=year
        )
        
        # ゲームシステム別統計
        system_stats = histories.values('scenario__game_system').annotate(
            count=Count('id'),
            total_time=Sum('session__duration_minutes')
        ).order_by('-count')
        
        # 役割別統計
        role_stats = histories.values('role').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 月別統計
        monthly_stats = histories.extra(
            select={'month': 'EXTRACT(month FROM played_date)'}
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        total_sessions = histories.count()
        total_scenarios = histories.values('scenario').distinct().count()
        
        return Response({
            'year': year,
            'total_sessions': total_sessions,
            'total_scenarios': total_scenarios,
            'system_statistics': list(system_stats),
            'role_statistics': list(role_stats),
            'monthly_statistics': list(monthly_stats),
        })
