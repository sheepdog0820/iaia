from schedules.duration import effective_duration_expression
from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.db.models import Q, Count, Sum
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from datetime import datetime
from .models import Scenario, ScenarioNote, PlayHistory, ScenarioImage
from .access import visible_scenarios
from .serializers import (
    ScenarioSerializer,
    ScenarioNoteSerializer,
    PlayHistorySerializer,
    ScenarioImageSerializer,
)


class ScenarioViewSet(viewsets.ModelViewSet):
    serializer_class = ScenarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = visible_scenarios(Scenario.objects.all(), self.request.user)
        
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

    def update(self, request, *args, **kwargs):
        if self.get_object().created_by_id != request.user.id:
            return Response(
                {'detail': 'Only the scenario owner can update it.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().created_by_id != request.user.id:
            return Response(
                {'detail': 'Only the scenario owner can delete it.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)
    
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


class ScenarioImageViewSet(viewsets.ModelViewSet):
    """シナリオ画像ViewSet"""

    serializer_class = ScenarioImageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ScenarioImage.objects.select_related('scenario', 'uploaded_by')
        scenario_id = self.request.query_params.get('scenario_id') or self.request.query_params.get('scenario')
        if scenario_id:
            queryset = queryset.filter(scenario_id=scenario_id)
        return queryset

    def create(self, request, *args, **kwargs):
        scenario_id = request.data.get('scenario')
        if not scenario_id:
            return Response(
                {'error': 'scenario is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            Scenario.objects.get(id=scenario_id)
        except Scenario.DoesNotExist:
            return Response(
                {'error': 'Scenario not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        scenario_id = self.request.data.get('scenario')
        scenario = Scenario.objects.get(id=scenario_id)
        serializer.save(uploaded_by=self.request.user, scenario=scenario)

    def perform_update(self, serializer):
        instance = self.get_object()

        # シナリオ作成者またはアップロード者のみ編集可能
        if instance.scenario.created_by != self.request.user and instance.uploaded_by != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only scenario creator or uploader can edit images")

        serializer.save()

    def perform_destroy(self, instance):
        # シナリオ作成者またはアップロード者のみ削除可能
        if instance.scenario.created_by != self.request.user and instance.uploaded_by != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only scenario creator or uploader can delete images")

        instance.delete()

    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """複数画像の一括アップロード"""
        scenario_id = request.data.get('scenario_id')
        images = request.FILES.getlist('images', [])

        if not scenario_id:
            return Response(
                {'error': 'scenario_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            scenario = Scenario.objects.get(id=scenario_id)
        except Scenario.DoesNotExist:
            return Response(
                {'error': 'Scenario not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        created_images = []
        with transaction.atomic():
            for image_file in images[:10]:  # 最大10枚まで
                serializer = ScenarioImageSerializer(
                    data={
                        'image': image_file,
                        'title': image_file.name,
                    },
                    context={'request': request},
                )
                serializer.is_valid(raise_exception=True)
                created_images.append(
                    serializer.save(
                        scenario=scenario,
                        uploaded_by=request.user,
                    )
                )

        serializer = ScenarioImageSerializer(created_images, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """画像の表示順序変更（シナリオ作成者のみ）"""
        image = self.get_object()
        new_order = request.data.get('order')

        if new_order is None:
            return Response(
                {'error': 'order is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if image.scenario.created_by != request.user:
            return Response(
                {'error': 'Only scenario creator can reorder images'},
                status=status.HTTP_403_FORBIDDEN,
            )

        image.order = new_order
        image.save()

        return Response({'status': 'success', 'order': image.order})

    @action(detail=False, methods=['post'])
    def reorder_bulk(self, request):
        """画像の表示順序をまとめて変更（シナリオ作成者のみ）"""
        scenario_id = request.data.get('scenario_id')
        ordered_ids = request.data.get('ordered_ids')

        if not scenario_id:
            return Response(
                {'error': 'scenario_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(ordered_ids, list) or not ordered_ids:
            return Response(
                {'error': 'ordered_ids is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            scenario_id_int = int(scenario_id)
        except (TypeError, ValueError):
            return Response(
                {'error': 'scenario_id must be an integer'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ordered_ids_int = [int(item) for item in ordered_ids]
        except (TypeError, ValueError):
            return Response(
                {'error': 'ordered_ids must be a list of integers'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(set(ordered_ids_int)) != len(ordered_ids_int):
            return Response(
                {'error': 'ordered_ids must be unique'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scenario = get_object_or_404(Scenario, id=scenario_id_int)
        if scenario.created_by != request.user:
            return Response(
                {'error': 'Only scenario creator can reorder images'},
                status=status.HTTP_403_FORBIDDEN,
            )

        existing_ids = list(
            ScenarioImage.objects.filter(scenario_id=scenario_id_int).values_list('id', flat=True)
        )
        if set(existing_ids) != set(ordered_ids_int):
            return Response(
                {'error': 'ordered_ids must include all images in the scenario'},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            images = list(
                ScenarioImage.objects.select_for_update().filter(
                    scenario_id=scenario_id_int,
                    id__in=ordered_ids_int,
                )
            )
            if len(images) != len(ordered_ids_int):
                return Response(
                    {'error': 'Some images not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            images_by_id = {image.id: image for image in images}
            for index, image_id in enumerate(ordered_ids_int):
                images_by_id[image_id].order = index + 1

            ScenarioImage.objects.bulk_update(images, ['order'])

        return Response({'status': 'success'})


class ScenarioNoteViewSet(viewsets.ModelViewSet):
    queryset = ScenarioNote.objects.none()
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
    queryset = PlayHistory.objects.none()
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
        scenarios = visible_scenarios(Scenario.objects.all(), request.user).annotate(
            play_count=Count('play_histories'),
            total_play_time=Sum(effective_duration_expression('play_histories__session__'))
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
            total_time=Sum(effective_duration_expression('session__'))
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


class PremiumOnlyTemplateView(LoginRequiredMixin, TemplateView):
    """課金ユーザ（高権限ユーザ）向けの画面"""

    premium_denied_template_name = 'accounts/premium_required.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not getattr(request.user, 'has_premium_access', False):
            return render(request, self.premium_denied_template_name, status=403)
        return super().dispatch(request, *args, **kwargs)


class ScenarioArchivePageView(PremiumOnlyTemplateView):
    """シナリオAPI結果確認（アーカイブ画面）"""

    template_name = 'scenarios/archive.html'
