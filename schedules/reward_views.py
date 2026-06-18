from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.character_models import GrowthRecord

from .models import SessionParticipant, SessionReward, TRPGSession
from .serializers import SessionRewardSerializer


class SessionRewardViewSet(viewsets.ModelViewSet):
    queryset = SessionReward.objects.none()
    serializer_class = SessionRewardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        session_id = self.kwargs.get('session_id') or self.request.query_params.get('session_id')
        queryset = SessionReward.objects.select_related(
            'participant',
            'participant__session',
            'participant__session__scenario',
            'participant__session__gm',
            'participant__user',
            'participant__character_sheet',
            'created_by',
            'applied_growth_record',
        )

        if session_id:
            session = get_object_or_404(TRPGSession, id=session_id)
            if not self._has_session_access(session, user):
                return SessionReward.objects.none()
            if self._is_gm(session, user):
                return queryset.filter(participant__session=session)
            return queryset.filter(participant__session=session, participant__user=user)

        return queryset.filter(
            Q(participant__session__gm=user)
            | Q(participant__user=user)
            | Q(participant__session__sessionparticipant__user=user, participant__session__sessionparticipant__role='gm')
        ).distinct()

    def create(self, request, *args, **kwargs):
        session_id = self.kwargs.get('session_id') or request.data.get('session')
        if not session_id:
            return Response({'error': 'session is required'}, status=status.HTTP_400_BAD_REQUEST)

        session = get_object_or_404(TRPGSession, id=session_id)
        if not self._is_gm(session, request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        participant_id = request.data.get('participant')
        if not participant_id:
            return Response({'error': 'participant is required'}, status=status.HTTP_400_BAD_REQUEST)

        participant = get_object_or_404(SessionParticipant, id=participant_id)
        if participant.session_id != session.id:
            return Response({'error': 'participant is not part of this session'}, status=status.HTTP_400_BAD_REQUEST)
        if participant.role == 'gm':
            return Response({'error': 'Cannot create rewards for GM participants'}, status=status.HTTP_400_BAD_REQUEST)
        if SessionReward.objects.filter(participant=participant).exists():
            return Response({'error': 'Reward already exists for this participant'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(participant=participant, created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = self.get_object()
        if not self._is_gm(instance.participant.session, self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only GM can update rewards")
        serializer.save()

    def perform_destroy(self, instance):
        if not self._is_gm(instance.participant.session, self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only GM can delete rewards")
        instance.delete()

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        base_reward = self.get_object()
        session = base_reward.participant.session
        if not self._is_gm(session, request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            reward = (
                SessionReward.objects.select_for_update()
                .select_related(
                    'participant',
                    'participant__session',
                    'participant__session__scenario',
                    'participant__session__gm',
                    'participant__character_sheet',
                    'applied_growth_record',
                )
                .get(pk=base_reward.pk)
            )
            session = reward.participant.session

            character_sheet = reward.participant.character_sheet
            if not character_sheet:
                return Response(
                    {'error': 'character_sheet is not set for this participant'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            session_date = self._get_session_date(session)
            scenario_name = session.scenario.title if session.scenario else session.title
            gm_name = session.gm.nickname or session.gm.username

            growth_record = reward.applied_growth_record
            if growth_record:
                growth_record.session_date = session_date
                growth_record.scenario_name = scenario_name
                growth_record.gm_name = gm_name
                growth_record.experience_gained = reward.experience_points
                growth_record.special_rewards = reward.special_rewards
                growth_record.notes = reward.notes
                growth_record.save(update_fields=[
                    'session_date',
                    'scenario_name',
                    'gm_name',
                    'experience_gained',
                    'special_rewards',
                    'notes',
                    'updated_at',
                ])
            else:
                growth_record = GrowthRecord.objects.create(
                    character_sheet=character_sheet,
                    session_date=session_date,
                    scenario_name=scenario_name,
                    gm_name=gm_name,
                    experience_gained=reward.experience_points,
                    special_rewards=reward.special_rewards,
                    notes=reward.notes,
                )
                reward.applied_growth_record = growth_record

            reward.applied_at = timezone.now()
            reward.save(update_fields=['applied_growth_record', 'applied_at', 'updated_at'])

        return Response(self.get_serializer(reward).data, status=status.HTTP_200_OK)

    def _get_session_date(self, session):
        if session.date:
            dt = session.date
            if timezone.is_aware(dt):
                dt = timezone.localtime(dt)
            return dt.date()

        primary_start_at = session.occurrences.filter(is_primary=True).values_list('start_at', flat=True).first()
        if primary_start_at:
            dt = primary_start_at
            if timezone.is_aware(dt):
                dt = timezone.localtime(dt)
            return dt.date()

        return timezone.now().date()

    def _has_session_access(self, session, user):
        return session.gm == user or session.participants.filter(id=user.id).exists()

    def _is_gm(self, session, user):
        return session.gm == user or SessionParticipant.objects.filter(session=session, user=user, role='gm').exists()
