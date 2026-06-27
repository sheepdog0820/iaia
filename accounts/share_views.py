from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.character_models import CharacterSheet
from accounts.models import GroupMembership, ShareLink
from accounts.share_serializers import (
    ShareLinkIssueSerializer,
    ShareLinkSerializer,
    SharedCharacterSheetSerializer,
    SharedScenarioSerializer,
    SharedSessionSerializer,
    SharedStatsSerializer,
)
from scenarios.models import Scenario
from schedules.models import TRPGSession


SHARED_API_NAMES = {
    ShareLink.ResourceType.CHARACTER: 'shared-character-detail',
    ShareLink.ResourceType.SESSION: 'shared-session-detail',
    ShareLink.ResourceType.SCENARIO: 'shared-scenario-detail',
    ShareLink.ResourceType.PROFILE_STATS: 'shared-stats-detail',
}


def _can_manage_session(session, user):
    if not user or not user.is_authenticated:
        return False
    if session.gm_id == user.id or getattr(session, 'created_by_id', None) == user.id:
        return True
    if session.group_id:
        return GroupMembership.objects.filter(
            group_id=session.group_id,
            user=user,
            role='admin',
        ).exists()
    return False


def _build_share_url(request, resource_type, token):
    return request.build_absolute_uri(reverse(SHARED_API_NAMES[resource_type], kwargs={'token': token}))


def _require_shareable_resource(resource_type, object_id, user):
    if resource_type == ShareLink.ResourceType.SESSION:
        session = get_object_or_404(TRPGSession, pk=object_id)
        if not _can_manage_session(session, user):
            raise Http404("Session not found")
        if session.visibility not in ('link', 'public'):
            raise ValueError('Session visibility must be link or public before issuing a share URL.')
        return session

    if resource_type == ShareLink.ResourceType.CHARACTER:
        character = get_object_or_404(CharacterSheet, pk=object_id)
        if character.user_id != user.id:
            raise Http404("Character sheet not found")
        if character.access_scope not in ('link', 'public'):
            raise ValueError('Character access_scope must be link or public before issuing a share URL.')
        return character

    if resource_type == ShareLink.ResourceType.SCENARIO:
        scenario = get_object_or_404(Scenario, pk=object_id)
        if scenario.created_by_id != user.id:
            raise Http404("Scenario not found")
        if scenario.visibility not in ('link', 'public'):
            raise ValueError('Scenario visibility must be link or public before issuing a share URL.')
        return scenario

    if resource_type == ShareLink.ResourceType.PROFILE_STATS:
        session = get_object_or_404(TRPGSession, pk=object_id)
        if not _can_manage_session(session, user):
            raise Http404("Session not found")
        if session.visibility not in ('link', 'public'):
            raise ValueError('Session visibility must be link or public before issuing stats share URL.')
        return session

    raise Http404("Unsupported resource type")


def _active_share_or_404(token, resource_type, request):
    share_link = ShareLink.active_for_token(token, resource_type)
    if share_link is None:
        raise Http404("Share link not found")
    if not share_link.allow_anonymous and not request.user.is_authenticated:
        raise Http404("Share link not found")
    return share_link


class ShareLinkListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        links = ShareLink.objects.filter(created_by=request.user)
        return Response(ShareLinkSerializer(links, many=True).data)

    def post(self, request):
        serializer = ShareLinkIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            _require_shareable_resource(data['resource_type'], data['object_id'], request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        share_link, token = ShareLink.issue(
            resource_type=data['resource_type'],
            object_id=data['object_id'],
            created_by=request.user,
            expires_at=data.get('expires_at'),
            allow_anonymous=data.get('allow_anonymous', True),
            view_level=data.get('view_level', ShareLink.ViewLevel.STANDARD),
        )
        response_data = ShareLinkSerializer(share_link).data
        response_data['token'] = token
        response_data['share_url'] = _build_share_url(request, share_link.resource_type, token)
        return Response(response_data, status=status.HTTP_201_CREATED)


class ShareLinkRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        share_link = get_object_or_404(ShareLink, pk=pk, created_by=request.user)
        share_link.revoke()
        return Response(ShareLinkSerializer(share_link).data)


class ShareLinkReissueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        share_link = get_object_or_404(ShareLink, pk=pk, created_by=request.user)
        token = share_link.reissue()
        response_data = ShareLinkSerializer(share_link).data
        response_data['token'] = token
        response_data['share_url'] = _build_share_url(request, share_link.resource_type, token)
        return Response(response_data)


class SharedSessionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        share_link = _active_share_or_404(token, ShareLink.ResourceType.SESSION, request)
        session = get_object_or_404(
            TRPGSession.objects.select_related('gm', 'scenario'),
            pk=share_link.object_id,
            visibility__in=('link', 'public'),
        )
        return Response(SharedSessionSerializer(session, context={'request': request}).data)


class SharedCharacterDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        share_link = _active_share_or_404(token, ShareLink.ResourceType.CHARACTER, request)
        character = get_object_or_404(
            CharacterSheet.objects.prefetch_related('skills', 'equipment'),
            pk=share_link.object_id,
            access_scope__in=('link', 'public'),
        )
        return Response(SharedCharacterSheetSerializer(character, context={'request': request}).data)


class SharedScenarioDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        share_link = _active_share_or_404(token, ShareLink.ResourceType.SCENARIO, request)
        scenario = get_object_or_404(
            Scenario.objects.prefetch_related('handout_templates'),
            pk=share_link.object_id,
            visibility__in=('link', 'public'),
        )
        return Response(SharedScenarioSerializer(scenario, context={'request': request}).data)


class SharedStatsDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        share_link = _active_share_or_404(token, ShareLink.ResourceType.PROFILE_STATS, request)
        session = get_object_or_404(
            TRPGSession.objects.prefetch_related('sessionparticipant_set'),
            pk=share_link.object_id,
            visibility__in=('link', 'public'),
        )
        return Response(SharedStatsSerializer(session).data)
