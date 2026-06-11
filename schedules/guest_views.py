from datetime import timedelta

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    GuestClaimAudit,
    GuestInvitation,
    SessionParticipant,
    TRPGSession,
)


class GuestInvitationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(TRPGSession, pk=session_id)
        if session.gm_id != request.user.id:
            self.permission_denied(request)
        try:
            expires_in_hours = int(request.data.get('expires_in_hours', 168))
        except (TypeError, ValueError):
            return Response(
                {'expires_in_hours': 'Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        expires_in_hours = max(1, min(expires_in_hours, 720))
        invitation, token = GuestInvitation.issue(
            session=session,
            created_by=request.user,
            expires_at=timezone.now() + timedelta(hours=expires_in_hours),
        )
        path = reverse('guest-invitation-respond', kwargs={'token': token})
        return Response({
            'id': invitation.pk,
            'token': token,
            'invitation_url': request.build_absolute_uri(path),
            'expires_at': invitation.expires_at,
        }, status=status.HTTP_201_CREATED)


class GuestInvitationRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id, invitation_id):
        invitation = get_object_or_404(
            GuestInvitation,
            pk=invitation_id,
            session_id=session_id,
        )
        if invitation.session.gm_id != request.user.id:
            self.permission_denied(request)
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=['revoked_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class GuestInvitationRespondView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, token):
        invitation = GuestInvitation.objects.select_related('session').filter(
            token_digest=GuestInvitation.digest(token)
        ).first()
        if not invitation:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not invitation.is_active:
            return Response(
                {'detail': 'Invitation is expired or revoked.'},
                status=status.HTTP_410_GONE,
            )
        if invitation.participant_id:
            return Response(
                {'detail': 'Invitation has already been used.'},
                status=status.HTTP_409_CONFLICT,
            )
        guest_name = str(request.data.get('guest_name', '')).strip()
        if not guest_name:
            return Response(
                {'guest_name': 'This field is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        player_slot = request.data.get('player_slot')
        if player_slot not in (None, ''):
            try:
                player_slot = int(player_slot)
            except (TypeError, ValueError):
                return Response(
                    {'player_slot': 'Must be an integer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if player_slot not in {1, 2, 3, 4}:
                return Response(
                    {'player_slot': 'Must be between 1 and 4.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            player_slot = None
        try:
            with transaction.atomic():
                locked = GuestInvitation.objects.select_for_update().get(
                    pk=invitation.pk
                )
                if locked.participant_id:
                    return Response(
                        {'detail': 'Invitation has already been used.'},
                        status=status.HTTP_409_CONFLICT,
                    )
                participant = SessionParticipant.objects.create(
                    session=locked.session,
                    user=None,
                    guest_name=guest_name,
                    role='player',
                    player_slot=player_slot,
                    character_name=request.data.get('character_name', ''),
                    character_sheet_url=request.data.get('character_sheet_url', ''),
                )
                locked.participant = participant
                locked.responded_at = timezone.now()
                locked.save(update_fields=['participant', 'responded_at'])
        except IntegrityError:
            return Response(
                {'detail': 'The requested player slot is already occupied.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({
            'participant_id': participant.pk,
            'session_id': participant.session_id,
            'guest_name': participant.guest_name,
            'player_slot': participant.player_slot,
        }, status=status.HTTP_201_CREATED)


class GuestParticipantClaimView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, participant_id):
        try:
            with transaction.atomic():
                participant = SessionParticipant.objects.select_for_update().select_related(
                    'session'
                ).get(pk=participant_id)
                if participant.user_id:
                    return Response(
                        {'detail': 'Participant is already claimed.'},
                        status=status.HTTP_409_CONFLICT,
                    )
                invitation = GuestInvitation.objects.select_for_update().filter(
                    participant=participant
                ).first()
                if not invitation or not invitation.is_active:
                    return Response(
                        {'detail': 'Guest invitation is expired or revoked.'},
                        status=status.HTTP_410_GONE,
                    )
                if SessionParticipant.objects.filter(
                    session=participant.session,
                    user=request.user,
                ).exclude(pk=participant.pk).exists():
                    return Response(
                        {'detail': 'User already participates in this session.'},
                        status=status.HTTP_409_CONFLICT,
                    )
                guest_name = participant.guest_name
                GuestClaimAudit.objects.create(
                    invitation=invitation,
                    participant=participant,
                    claimed_by=request.user,
                    guest_name=guest_name,
                    character_name=participant.character_name,
                    character_sheet_url=participant.character_sheet_url,
                )
                participant.user = request.user
                participant.guest_name = ''
                participant.save(update_fields=['user', 'guest_name'])
        except SessionParticipant.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            return Response(
                {'detail': 'Participant claim conflicts with an existing slot.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({
            'participant_id': participant.pk,
            'session_id': participant.session_id,
            'claimed_by': request.user.pk,
            'character_name': participant.character_name,
            'character_sheet_url': participant.character_sheet_url,
        })
