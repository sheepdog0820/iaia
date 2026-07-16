import json
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse

from django.db import transaction
from django.db.models import Case, Count, DateTimeField, F, IntegerField, Prefetch, Q, Sum, Value, When
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import (
    CharacterSheet,
    CharacterSkill6th,
    CharacterSkill7th,
    CustomUser,
    Group,
    GroupLink,
    GroupLinkShare,
    GroupMembership,
)
from accounts.views.mixins import CharacterSheetAccessMixin
from schedules.duration import effective_duration_expression

from .models import (  # 高度なスケジューリング機能（ISSUE-017）
    DatePoll,
    DatePollComment,
    DatePollOption,
    DatePollVote,
    HandoutInfo,
    HandoutView,
    JapaneseHoliday,
    ParticipantIdentity,
    SessionAvailability,
    SessionImage,
    SessionInvitation,
    SessionOccurrence,
    SessionParticipant,
    SessionParticipantRole,
    SessionSeries,
    SessionYouTubeLink,
    TRPGSession,
)
from .notifications import SessionNotificationService
from .recommended_skill_comparison import build_recommended_skill_comparison
from .serializers import CalendarEventSerializer  # 高度なスケジューリング機能（ISSUE-017）
from .serializers import (
    DatePollCommentSerializer,
    DatePollCreateSerializer,
    DatePollOptionSerializer,
    DatePollSerializer,
    DatePollVoteSerializer,
    HandoutInfoSerializer,
    SessionAvailabilitySerializer,
    SessionImageSerializer,
    SessionInvitationSerializer,
    SessionListSerializer,
    SessionOccurrenceSerializer,
    SessionParticipantSerializer,
    SessionSeriesCreateSerializer,
    SessionSeriesSerializer,
    SessionYouTubeLinkSerializer,
    TRPGSessionSerializer,
    build_internal_character_url,
)
from .services import YouTubeService
from . import session_permissions
from .template_services import bind_slot_handouts_to_participant, clone_scenario_handouts_to_session


def _visible_sessions_for(user):
    group_ids = GroupMembership.objects.filter(user=user).values_list("group_id", flat=True)
    owned_group_ids = Group.objects.filter(created_by=user).values_list("id", flat=True)
    participant_session_ids = SessionParticipant.objects.filter(user=user).values_list("session_id", flat=True)
    shared_session_ids = (
        GroupLinkShare.objects.filter(
            resource_type=GroupLinkShare.ResourceType.SESSION,
            link__status=GroupLink.Status.ACCEPTED,
        )
        .filter(
            Q(owner_group_id=F("link__source_group_id"), link__target_group_id__in=group_ids)
            | Q(owner_group_id=F("link__target_group_id"), link__source_group_id__in=group_ids)
        )
        .values_list("object_id", flat=True)
    )
    return TRPGSession.objects.filter(
        Q(created_by=user)
        | Q(visibility="public")
        | Q(group_id__in=group_ids)
        | Q(group_id__in=owned_group_ids)
        | Q(id__in=participant_session_ids)
        | Q(id__in=shared_session_ids)
    ).distinct()


def _tableno_character_from_url(character_sheet_url, user):
    value = str(character_sheet_url or "").strip()
    if not value:
        return None

    try:
        parsed_url = urlparse(value)
    except (TypeError, ValueError):
        return None

    path_parts = [part for part in parsed_url.path.split("/") if part]
    character_sheet = None

    def readable_character_sheet_by_id(raw_id):
        try:
            character_sheet_id = int(raw_id)
        except (TypeError, ValueError):
            return None
        sheet = CharacterSheet.objects.filter(pk=character_sheet_id).first()
        if sheet and not CharacterSheetAccessMixin.can_read_character_sheet(sheet, user):
            return None
        return sheet

    if len(path_parts) >= 3 and path_parts[0:2] == ["share", "characters"]:
        try:
            share_token = uuid.UUID(path_parts[2])
        except (TypeError, ValueError):
            return None
        character_sheet = CharacterSheet.objects.filter(
            share_token=share_token,
            access_scope__in=("link", "public"),
        ).first()
    elif len(path_parts) >= 4 and path_parts[0:3] == ["api", "accounts", "character-sheets"]:
        character_sheet = readable_character_sheet_by_id(path_parts[3])
    elif len(path_parts) >= 4 and path_parts[0:3] == ["accounts", "character", "6th"]:
        character_sheet = readable_character_sheet_by_id(path_parts[3])
    elif len(path_parts) >= 3 and path_parts[0:2] == ["accounts", "character"]:
        character_sheet = readable_character_sheet_by_id(path_parts[2])

    return character_sheet


def _tableno_character_name_from_url(character_sheet_url, user):
    character_sheet = _tableno_character_from_url(character_sheet_url, user)
    return character_sheet.system_data.name if character_sheet else ""


def _gm_role_session_ids_for(user):
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    return set(
        SessionParticipantRole.objects.filter(
            participant__user=user,
            role=SessionParticipantRole.Role.GM,
        ).values_list("participant__session_id", flat=True)
    )


def _is_session_gm_for_user(session, user, gm_role_session_ids=None):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if gm_role_session_ids is None:
        return session_permissions.is_session_gm(user, session)
    return session.id in gm_role_session_ids


def _filter_sessions_by_period(sessions, period, now=None):
    now = now or timezone.now()
    if period in ("", "all"):
        return sessions
    if period in ("past", "past_all"):
        return sessions.filter(date__lt=now)
    if period == "past7":
        return sessions.filter(date__gte=now - timedelta(days=7), date__lt=now)
    if period == "past30":
        return sessions.filter(date__gte=now - timedelta(days=30), date__lt=now)
    if period == "past90":
        return sessions.filter(date__gte=now - timedelta(days=90), date__lt=now)
    return sessions.filter(date__gte=now)


def _order_sessions_by_period(sessions, period, now=None):
    now = now or timezone.now()
    if period in ("past", "past_all", "past7", "past30", "past90"):
        return sessions.order_by("-date")
    if period in ("", "all"):
        return sessions.annotate(
            _period_sort_group=Case(
                When(date__gte=now, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            _future_date=Case(
                When(date__gte=now, then=F("date")),
                default=Value(None),
                output_field=DateTimeField(),
            ),
            _past_date=Case(
                When(date__lt=now, then=F("date")),
                default=Value(None),
                output_field=DateTimeField(),
            ),
        ).order_by("_period_sort_group", "_future_date", "-_past_date")
    return sessions.order_by("date")


def _is_assignable_session_user(session, user):
    if not user:
        return False
    if session.visibility == "public":
        return True
    if session.group_id and session.group.members.filter(id=user.id).exists():
        return True
    if getattr(session, "created_by_id", None) == user.id:
        return True
    if SessionParticipant.objects.filter(session=session, user=user).exists():
        return True
    return session_permissions.is_session_gm(user, session)


def _can_access_session_basic(session, user):
    return session_permissions.can_view_session_basic(user, session)


def _participant_has_role(participant, role):
    roles = getattr(participant, "_prefetched_objects_cache", {}).get("participant_roles")
    if roles is not None:
        return any(participant_role.role == role for participant_role in roles)
    return participant.participant_roles.filter(role=role).exists()


def _participant_role_values(participant):
    roles = getattr(participant, "_prefetched_objects_cache", {}).get("participant_roles")
    if roles is not None:
        return {participant_role.role for participant_role in roles}
    return session_permissions.get_participant_role_values(participant)


def _participant_primary_role(participant):
    roles = _participant_role_values(participant)
    if SessionParticipantRole.Role.OWNER.value in roles:
        return SessionParticipantRole.Role.OWNER.value
    if SessionParticipantRole.Role.MANAGER.value in roles:
        return SessionParticipantRole.Role.MANAGER.value
    if SessionParticipantRole.Role.GM.value in roles:
        return SessionParticipantRole.Role.GM.value
    if SessionParticipantRole.Role.PLAYER.value in roles:
        return SessionParticipantRole.Role.PLAYER.value
    return SessionParticipantRole.Role.PLAYER.value


def _roles_from_request_data(data, *, default_roles=None):
    if "role" in data:
        raise ValueError("Use roles instead of role.")

    raw_roles = None
    if hasattr(data, "getlist") and "roles" in data:
        raw_roles = data.getlist("roles")
    elif "roles" in data:
        raw_roles = data.get("roles")
    elif hasattr(data, "getlist") and "participant_roles" in data:
        raw_roles = data.getlist("participant_roles")
    elif "participant_roles" in data:
        raw_roles = data.get("participant_roles")

    if isinstance(raw_roles, str):
        raw_roles = [raw_roles]
    elif raw_roles is None:
        raw_roles = default_roles

    return session_permissions.normalize_participant_roles(raw_roles or default_roles or [])


def _resolve_participant_identity_for_session(session, raw_identity_id, *, exclude_participant_id=None):
    if raw_identity_id in [None, "", "null", "None"]:
        return None
    try:
        identity_id = int(raw_identity_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("participant_identity must be an integer.") from exc

    try:
        identity = ParticipantIdentity.objects.get(pk=identity_id, user__isnull=True, is_active=True)
    except ParticipantIdentity.DoesNotExist as exc:
        raise ValueError("Temporary member not found.") from exc

    if session.group_id:
        if identity.group_id != session.group_id:
            raise ValueError("Temporary member must belong to the session group.")
    elif identity.group_id is not None:
        raise ValueError("Group temporary member cannot be used for a personal session.")

    existing = SessionParticipant.objects.filter(session=session, participant_identity=identity)
    if exclude_participant_id:
        existing = existing.exclude(pk=exclude_participant_id)
    if existing.exists():
        raise ValueError("Temporary member is already linked to this session.")
    return identity


def _attach_participant_role_flags(participants):
    for participant in participants:
        role_values = _participant_role_values(participant)
        participant.role_values = sorted(role_values)
        participant.is_owner_role = SessionParticipantRole.Role.OWNER.value in role_values
        participant.is_manager_role = SessionParticipantRole.Role.MANAGER.value in role_values
        participant.is_gm_role = SessionParticipantRole.Role.GM.value in role_values
        participant.is_player_role = SessionParticipantRole.Role.PLAYER.value in role_values
    return participants


def _sync_participant_roles(participant, roles, *, granted_by=None):
    return session_permissions.set_participant_roles(participant, roles, granted_by=granted_by)


def _handout_player_slot_options(handouts, *, include_titles=True):
    options_by_slot = {}
    for handout in handouts:
        slot = handout.assigned_player_slot
        if not slot or slot in options_by_slot:
            continue
        code = handout.code or (f"HO{handout.handout_number}" if handout.handout_number else f"PL{slot}")
        title = (handout.name or handout.title or "") if include_titles else ""
        label = f"{code}: {title}" if title else code
        options_by_slot[slot] = {"value": slot, "label": label}
    return [options_by_slot[slot] for slot in sorted(options_by_slot)]


def _user_display_name(user):
    return user.nickname or user.get_full_name() or user.username


def _session_permission_scope_payload(session):
    participants = list(
        SessionParticipant.objects.filter(session=session)
        .select_related("user")
        .prefetch_related("participant_roles")
        .order_by("id")
    )
    participant_by_user_id = {participant.user_id: participant for participant in participants if participant.user_id}

    group_admin_ids = set()
    if session.group_id:
        if session.group.created_by_id:
            group_admin_ids.add(session.group.created_by_id)
        group_admin_ids.update(
            GroupMembership.objects.filter(group=session.group, role="admin").values_list("user_id", flat=True)
        )

    users = CustomUser.objects.filter(id__in=participant_by_user_id).order_by("nickname", "username", "id")
    user_rows = []
    for user in users:
        participant = participant_by_user_id.get(user.id)
        if participant and SessionParticipantRole.Role.MANAGER.value in _participant_role_values(participant):
            continue
        user_rows.append(
            {
                "user_id": user.id,
                "display_name": _user_display_name(user),
                "username": user.username,
                "participant_id": participant.id if participant else None,
                "participant_roles": sorted(_participant_role_values(participant)) if participant else [],
                "is_participant": bool(participant),
                "is_created_by": session.created_by_id == user.id,
                "is_legacy_gm": session.gm_id == user.id,
                "is_group_admin": user.id in group_admin_ids,
            }
        )

    guest_rows = [
        {
            "participant_id": participant.id,
            "display_name": participant.display_name,
            "participant_roles": sorted(_participant_role_values(participant)),
        }
        for participant in participants
        if participant.user_id is None
    ]

    return {
        "participant_roles": [
            {"value": SessionParticipantRole.Role.GM.value, "label": SessionParticipantRole.Role.GM.label},
            {"value": SessionParticipantRole.Role.PLAYER.value, "label": SessionParticipantRole.Role.PLAYER.label},
        ],
        "users": user_rows,
        "guests": guest_rows,
    }


def _session_gm_name(session):
    if not session.gm_id:
        return ""
    return session.gm.nickname or session.gm.username


def _session_gm_payload(session):
    if not session.gm_id:
        return None
    return {"id": session.gm.id, "name": _session_gm_name(session)}


class SessionsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Accept headerをチェックしてJSONまたはHTMLを返す
        if "application/json" in request.headers.get("Accept", ""):
            return self.get_json_response(request)
        else:
            return self.get_html_response(request)

    def get_json_response(self, request):
        user = request.user
        period = request.query_params.get("period", "future")
        sessions = (
            _visible_sessions_for(user)
            .select_related("gm", "group")
            .annotate(
                guest_count=Count(
                    "sessionparticipant",
                    filter=Q(sessionparticipant__user__isnull=True),
                )
            )
        )
        sessions = _filter_sessions_by_period(sessions, period)
        sessions = _order_sessions_by_period(sessions, period)

        # ページネーション対応
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))

        total_count = sessions.count()
        sessions = sessions[offset : offset + limit]

        serializer = SessionListSerializer(sessions, many=True)

        return Response(
            {
                "count": total_count,
                "results": serializer.data,
                "limit": limit,
                "offset": offset,
                "period": period,
                "has_next": (offset + limit) < total_count,
                "has_previous": offset > 0,
            }
        )

    def get_html_response(self, request):
        user = request.user
        period = request.GET.get("period", "future")
        sessions = (
            _visible_sessions_for(user)
            .select_related("gm", "group")
            .annotate(
                guest_count=Count(
                    "sessionparticipant",
                    filter=Q(sessionparticipant__user__isnull=True),
                )
            )
        )
        sessions = _filter_sessions_by_period(sessions, period)
        sessions = _order_sessions_by_period(sessions, period)

        # ページネーション対応
        limit = int(request.GET.get("limit", 20))
        offset = int(request.GET.get("offset", 0))

        total_count = sessions.count()
        sessions = sessions[offset : offset + limit]

        context = {
            "sessions": sessions,
            "count": total_count,
            "limit": limit,
            "offset": offset,
            "period": period,
            "has_next": (offset + limit) < total_count,
            "has_previous": offset > 0,
        }

        return render(request, "schedules/sessions_list.html", context)


class TRPGSessionViewSet(viewsets.ModelViewSet):
    queryset = TRPGSession.objects.none()
    serializer_class = TRPGSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # ユーザーが参加しているグループのセッション、または公開セッション
        sessions = _visible_sessions_for(user).select_related("scenario")
        if getattr(self, "action", None) == "list":
            period = self.request.query_params.get("period", "future")
            sessions = _filter_sessions_by_period(sessions, period)
            return _order_sessions_by_period(sessions, period)
        return sessions.order_by("-date")

    def perform_create(self, serializer):
        self_as_gm = str(
            self.request.data.get("as_gm")
            or self.request.data.get("self_as_gm")
            or self.request.data.get("is_gm")
            or ""
        ).lower() in {"1", "true", "yes", "on"}
        serializer.save(
            created_by=self.request.user,
            gm=self.request.user if self_as_gm else None,
        )
        session = serializer.instance
        session_permissions.initialize_created_session_permissions(
            session,
            created_by=self.request.user,
            gm=self.request.user if self_as_gm else None,
        )
        clone_scenario_handouts_to_session(session.scenario, session)
        from .tasks import queue_discord_event

        queue_discord_event(
            session.group_id,
            "session_created",
            {"content": f"Session created: {session.title}"},
            f"session-created:{session.pk}",
        )
        from .tasks import schedule_session_google_syncs

        schedule_session_google_syncs(session)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if not session_permissions.can_edit_session_basic(request.user, instance):
            return Response(
                {"detail": "Only a session manager can update this session."},
                status=status.HTTP_403_FORBIDDEN,
            )

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
            notification_service.send_session_schedule_change_notification(instance, old_date, instance.date)

        # キャンセル通知
        if old_status != "cancelled" and instance.status == "cancelled":
            cancel_reason = request.data.get("cancel_reason", "")
            notification_service.send_session_cancelled_notification(instance, cancel_reason)

        # セッション完了時の統計更新
        if old_status != "completed" and instance.status == "completed":
            self._update_session_statistics(instance)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        from .tasks import queue_discord_event, schedule_session_google_syncs

        event_type = (
            "session_cancelled" if old_status != "cancelled" and instance.status == "cancelled" else "session_updated"
        )
        queue_discord_event(
            instance.group_id,
            event_type,
            {"content": f"Session updated: {instance.title}"},
            f"{event_type}:{instance.pk}:{instance.updated_at.isoformat()}",
        )
        schedule_session_google_syncs(instance)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not session_permissions.can_edit_session_basic(request.user, instance):
            return Response(
                {"detail": "Only a session manager can delete this session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": ("This session has protected audit records and cannot be deleted.")},
                status=status.HTTP_409_CONFLICT,
            )

    def _update_session_statistics(self, session):
        """セッション完了時の統計を更新"""
        from scenarios.models import PlayHistory, Scenario

        # セッション参加者の統計更新
        participants = (
            SessionParticipant.objects.filter(session=session)
            .select_related("user", "character_sheet")
            .prefetch_related("participant_roles")
        )

        scenario = session.scenario
        if not scenario:
            # ダミーシナリオを作成（シナリオ未連携時のフォールバック）
            scenario, _ = Scenario.objects.get_or_create(
                title=f"Session: {session.title}",
                defaults={
                    "game_system": "coc",
                    "created_by": session.gm or session.created_by,
                    "summary": session.description,
                },
            )

        for participant in participants:
            if participant.user_id is None:
                continue
            played_at = session.date
            if not played_at:
                occurrence = session.occurrences.order_by("start_at", "id").first()
                played_at = occurrence.start_at if occurrence else timezone.now()

            # プレイ履歴の作成
            PlayHistory.objects.get_or_create(
                user=participant.user,
                session=session,
                role=_participant_primary_role(participant),
                defaults={
                    "scenario": scenario,
                    "played_date": played_at,
                    "notes": f"Character: {participant.character_name}",
                },
            )

            # キャラクターのセッション数増加
            if participant.character_sheet:
                detail = participant.character_sheet.system_data
                detail.session_count += 1
                detail.save(update_fields=["session_count"])

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        session = self.get_object()

        # 公開設定に応じた参加制限
        if session.visibility == "private" and not session_permissions.can_edit_session_basic(request.user, session):
            return Response({"error": "このセッションはプライベートです"}, status=status.HTTP_403_FORBIDDEN)
        if session.visibility == "group":
            if not session.group_id or (
                not session.group.members.filter(id=request.user.id).exists()
                and not session_permissions.can_edit_session_basic(request.user, session)
            ):
                return Response({"error": "このセッションはグループメンバー限定です"}, status=status.HTTP_403_FORBIDDEN)

        # プレイヤー枠とキャラクターシートを取得
        try:
            requested_roles = _roles_from_request_data(
                request.data,
                default_roles=[SessionParticipantRole.Role.PLAYER],
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if requested_roles != {SessionParticipantRole.Role.PLAYER.value}:
            return Response(
                {"error": "Self-join only accepts the player role"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        player_slot = request.data.get("player_slot")
        if player_slot not in [None, "", "null", "None"]:
            try:
                player_slot = int(player_slot)
            except (TypeError, ValueError):
                return Response({"error": "player_slot must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            player_slot = None
        character_sheet_id = request.data.get("character_sheet_id") or request.data.get("character_sheet")
        character_sheet = None
        if character_sheet_id:
            try:
                character_sheet = CharacterSheet.objects.get(id=character_sheet_id, user=request.user)
            except CharacterSheet.DoesNotExist:
                return Response(
                    {"error": "Character sheet not found or not owned by you"}, status=status.HTTP_400_BAD_REQUEST
                )

        # プレイヤー枠の重複チェック
        if player_slot:
            existing_slot = (
                SessionParticipant.objects.filter(session=session, player_slot=player_slot)
                .exclude(user=request.user)
                .exists()
            )

            if existing_slot:
                return Response(
                    {"error": f"Player slot {player_slot} is already taken"}, status=status.HTTP_400_BAD_REQUEST
                )

        character_name = request.data.get("character_name", "").strip()
        if character_sheet:
            character_name = character_sheet.system_data.name
        character_sheet_url = request.data.get("character_sheet_url", "")
        if not character_sheet:
            character_sheet_from_url = _tableno_character_from_url(character_sheet_url, request.user)
            if character_sheet_from_url and character_sheet_from_url.user_id == request.user.id:
                character_sheet = character_sheet_from_url
                character_name = character_sheet.system_data.name
        if character_sheet:
            character_sheet_url = build_internal_character_url(request, character_sheet)

        participant, created = SessionParticipant.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={
                "player_slot": player_slot,
                "character_name": character_name,
                "character_sheet_url": character_sheet_url,
                "character_sheet": character_sheet,
            },
        )

        if not created:
            # 既存の参加者の情報を更新
            if player_slot:
                participant.player_slot = player_slot
            if "character_name" in request.data or character_sheet:
                participant.character_name = character_sheet.system_data.name if character_sheet else request.data.get("character_name", "")
            if "character_sheet_url" in request.data or character_sheet:
                participant.character_sheet_url = character_sheet_url
            if "character_sheet_id" in request.data or "character_sheet" in request.data:
                participant.character_sheet = character_sheet
            participant.save()

        bind_slot_handouts_to_participant(participant)
        if created:
            _sync_participant_roles(participant, [SessionParticipantRole.Role.PLAYER], granted_by=request.user)

        serializer = SessionParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def register(self, request, pk=None):
        """join の互換エンドポイント"""
        response = self.join(request, pk=pk)
        if response.status_code == status.HTTP_201_CREATED:
            response.status_code = status.HTTP_200_OK
        return response

    @action(detail=True, methods=["delete"])
    def leave(self, request, pk=None):
        session = self.get_object()
        try:
            participant = SessionParticipant.objects.get(session=session, user=request.user)
            participant.delete()
            bind_slot_handouts_to_participant(participant)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except SessionParticipant.DoesNotExist:
            return Response({"error": "Not a participant"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def participants(self, request, pk=None):
        """セッションの参加者一覧を取得"""
        session = self.get_object()
        participants = SessionParticipant.objects.filter(session=session).select_related(
            "user",
            "character_sheet",
            "participant_identity",
        )

        serializer = SessionParticipantSerializer(participants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "patch"], url_path="permissions")
    def permissions(self, request, pk=None):
        session = self.get_object()
        if not session_permissions.can_manage_permissions(request.user, session):
            return Response(
                {"detail": "権限管理者のみ権限を管理できます。"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == "GET":
            return Response(_session_permission_scope_payload(session))

        participant_id = request.data.get("participant_id") or request.data.get("participant")
        if not participant_id:
            return Response({"error": "participant_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            participant = SessionParticipant.objects.get(id=participant_id, session=session)
        except (SessionParticipant.DoesNotExist, TypeError, ValueError):
            return Response({"error": "Participant not found"}, status=status.HTTP_404_NOT_FOUND)

        if participant.user_id == session.created_by_id:
            return Response({"error": "The session creator role cannot be changed"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            desired_roles = session_permissions.normalize_assignable_participant_roles(
                _roles_from_request_data(request.data)
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            _sync_participant_roles(participant, desired_roles, granted_by=request.user)
            if SessionParticipantRole.Role.GM.value in desired_roles and participant.user_id:
                session.gm = participant.user
                session.save(update_fields=["gm", "updated_at"])

        return Response(_session_permission_scope_payload(session))

    @action(detail=True, methods=["post"])
    def add_co_gm(self, request, pk=None):
        """協力GMを追加"""
        session = self.get_object()

        # メインGMのみ実行可能
        if not session_permissions.can_manage_participants(request.user, session):
            return Response({"error": "Only a session manager can add co-GMs"}, status=status.HTTP_403_FORBIDDEN)

        co_gm_id = request.data.get("user_id")
        if not co_gm_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            co_gm = CustomUser.objects.get(id=co_gm_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # 既に参加者の場合
        existing = SessionParticipant.objects.filter(session=session, user=co_gm).first()

        if existing:
            if _participant_has_role(existing, SessionParticipantRole.Role.GM):
                return Response({"error": "User is already a co-GM"}, status=status.HTTP_400_BAD_REQUEST)
            # プレイヤーから昇格
            _sync_participant_roles(existing, [SessionParticipantRole.Role.GM], granted_by=request.user)
        else:
            # 新規追加
            session_permissions.create_participant(
                session=session,
                user=co_gm,
                roles=[SessionParticipantRole.Role.GM],
                granted_by=request.user,
            )

        return Response({"message": "Co-GM added successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="assign-roles")
    def assign_roles(self, request, pk=None):
        session = self.get_object()
        if not session_permissions.can_manage_participants(request.user, session):
            return Response(
                {"error": "Only a session manager can assign roles"},
                status=status.HTTP_403_FORBIDDEN,
            )

        gm_user_id = request.data.get("gm_user_id") or request.data.get("gm")
        participant_items = request.data.get("participants", [])
        if participant_items is None:
            participant_items = []
        if not isinstance(participant_items, list):
            return Response(
                {"error": "participants must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_participants = []

        def get_assignable_user(user_id):
            try:
                target_user = CustomUser.objects.get(id=user_id)
            except (CustomUser.DoesNotExist, TypeError, ValueError):
                return None, Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not _is_assignable_session_user(session, target_user):
                return None, Response(
                    {"error": "User is not a member of this session scope"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return target_user, None

        with transaction.atomic():
            if gm_user_id:
                gm_user, error_response = get_assignable_user(gm_user_id)
                if error_response:
                    return error_response
                session.gm = gm_user
                session.save(update_fields=["gm", "updated_at"])
                participant, _ = SessionParticipant.objects.update_or_create(
                    session=session,
                    user=gm_user,
                    defaults={"player_slot": None},
                )
                _sync_participant_roles(participant, [SessionParticipantRole.Role.GM], granted_by=request.user)
                updated_participants.append(participant)

            for item in participant_items:
                if not isinstance(item, dict):
                    return Response(
                        {"error": "participant entries must be objects"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                target_user, error_response = get_assignable_user(item.get("user_id") or item.get("user"))
                if error_response:
                    return error_response

                try:
                    desired_roles = session_permissions.normalize_assignable_participant_roles(
                        _roles_from_request_data(
                            item,
                            default_roles=[SessionParticipantRole.Role.PLAYER],
                        )
                    )
                except ValueError as exc:
                    return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

                raw_slot = item.get("player_slot")
                player_slot = None
                if SessionParticipantRole.Role.PLAYER.value in desired_roles and raw_slot not in [None, "", "null", "None"]:
                    try:
                        player_slot = int(raw_slot)
                    except (TypeError, ValueError):
                        return Response(
                            {"error": "player_slot must be an integer"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                if player_slot:
                    existing_slot = (
                        SessionParticipant.objects.filter(
                            session=session,
                            player_slot=player_slot,
                        )
                        .exclude(user=target_user)
                        .first()
                    )
                    if existing_slot:
                        return Response(
                            {"error": f"Player slot {player_slot} is already taken"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                character_sheet = None
                character_sheet_id = item.get("character_sheet_id") or item.get("character_sheet")
                if character_sheet_id:
                    try:
                        character_sheet = CharacterSheet.objects.get(
                            id=character_sheet_id,
                            user=target_user,
                        )
                    except CharacterSheet.DoesNotExist:
                        return Response(
                            {"error": "Character sheet not found or not owned by the user"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                participant, _ = SessionParticipant.objects.update_or_create(
                    session=session,
                    user=target_user,
                    defaults={
                        "player_slot": player_slot if SessionParticipantRole.Role.PLAYER.value in desired_roles else None,
                        "character_sheet": character_sheet,
                    },
                )
                if gm_user_id and target_user.id == int(gm_user_id):
                    desired_roles = {SessionParticipantRole.Role.GM.value}
                _sync_participant_roles(participant, desired_roles, granted_by=request.user)
                bind_slot_handouts_to_participant(participant)
                updated_participants.append(participant)

        return Response(
            {
                "session": TRPGSessionSerializer(session, context={"request": request}).data,
                "participants": SessionParticipantSerializer(updated_participants, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def invite(self, request, pk=None):
        """セッションに参加者を招待（ISSUE-013実装）"""
        session = self.get_object()

        # GMのみ招待可能（メインGMまたは協力GM）
        if not session_permissions.can_manage_participants(request.user, session):
            return Response({"error": "Only GM can invite participants"}, status=status.HTTP_403_FORBIDDEN)

        invitee_id = request.data.get("user_id")
        if not invitee_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invitee = CustomUser.objects.get(id=invitee_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # 既に参加者の場合
        if SessionParticipant.objects.filter(session=session, user=invitee).exists():
            return Response({"error": "User is already a participant"}, status=status.HTTP_400_BAD_REQUEST)

        if "invited_role" in request.data:
            return Response(
                {"error": "Use roles instead of invited_role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        message = (request.data.get("message") or "").strip()
        try:
            invited_roles = session_permissions.normalize_assignable_participant_roles(
                _roles_from_request_data(
                    request.data,
                    default_roles=[SessionParticipantRole.Role.PLAYER],
                )
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if len(invited_roles) != 1:
            return Response(
                {"error": "Session invitations accept exactly one participant role"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invited_role = next(iter(invited_roles))

        invitation, created = SessionInvitation.objects.get_or_create(
            session=session,
            invitee=invitee,
            defaults={
                "inviter": request.user,
                "status": "pending",
                "invited_role": invited_role,
                "message": message,
            },
        )

        if not created:
            invitation.inviter = request.user
            invitation.status = "pending"
            invitation.message = message
            invitation.invited_role = invited_role
            invitation.created_at = timezone.now()
            invitation.responded_at = None
            invitation.save(
                update_fields=[
                    "inviter",
                    "status",
                    "message",
                    "invited_role",
                    "created_at",
                    "responded_at",
                ]
            )

        notification_service = SessionNotificationService()
        notification_sent = notification_service.send_session_invitation_notification(
            session, request.user, invitee, invitation_id=invitation.id
        )

        return Response(
            {
                "status": "success",
                "invitation_id": invitation.id,
                "notification_sent": bool(notification_sent),
                "message": f"Invitation created for {invitee.nickname or invitee.username}",
            }
        )

    @action(detail=True, methods=["post"])
    def assign_player(self, request, pk=None):
        """GM専用: プレイヤー枠にユーザーを割り当て"""
        session = self.get_object()

        # GMのみ実行可能
        if not session_permissions.can_manage_participants(request.user, session):
            return Response({"error": "Only a session manager can assign players"}, status=status.HTTP_403_FORBIDDEN)

        player_slot = request.data.get("player_slot")
        user_id = request.data.get("user_id")
        character_sheet_id = request.data.get("character_sheet_id") or request.data.get("character_sheet")

        if not player_slot or not user_id:
            return Response({"error": "player_slot and user_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        # 対象ユーザーの確認
        try:
            target_user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # グループメンバーかチェック
        if not _is_assignable_session_user(session, target_user):
            return Response({"error": "User is not a member of this group"}, status=status.HTTP_400_BAD_REQUEST)

        # 既存の枠チェック
        existing_slot = (
            SessionParticipant.objects.filter(session=session, player_slot=player_slot)
            .exclude(user=target_user)
            .first()
        )

        if existing_slot:
            return Response(
                {"error": f"Player slot {player_slot} is already taken by {existing_slot.display_name}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        character_sheet = None
        if character_sheet_id:
            try:
                character_sheet = CharacterSheet.objects.get(id=character_sheet_id, user=target_user)
            except CharacterSheet.DoesNotExist:
                return Response(
                    {"error": "Character sheet not found or not owned by the user"}, status=status.HTTP_400_BAD_REQUEST
                )

        # 参加者の作成または更新
        participant, created = SessionParticipant.objects.update_or_create(
            session=session,
            user=target_user,
            defaults={"player_slot": player_slot, "character_sheet": character_sheet},
        )
        _sync_participant_roles(participant, [SessionParticipantRole.Role.PLAYER], granted_by=request.user)

        bind_slot_handouts_to_participant(participant)

        serializer = SessionParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        from django.utils import timezone

        from .serializers import UpcomingSessionSerializer

        now = timezone.now()
        sessions = (
            self.get_queryset()
            .filter(date__gte=now, status="planned")
            .select_related("gm", "group")
            .prefetch_related("sessionparticipant_set__user")
            .order_by("date")[:5]
        )

        serializer = UpcomingSessionSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="my-sessions")
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
        participant_session_ids = SessionParticipant.objects.filter(user=user).values_list("session_id", flat=True)
        gm_role_session_ids = SessionParticipantRole.objects.filter(
            participant__user=user,
            role=SessionParticipantRole.Role.GM,
        ).values_list("participant__session_id", flat=True)
        legacy_gm_session_ids = TRPGSession.objects.filter(gm=user).values_list("id", flat=True)
        gm_role_session_ids = set(gm_role_session_ids) | set(legacy_gm_session_ids)
        gm_role_session_id_set = set(gm_role_session_ids)

        sessions = (
            TRPGSession.objects.filter(
                Q(created_by=user)
                | Q(id__in=participant_session_ids)
            )
            .select_related("gm", "group", "scenario")
            .prefetch_related("sessionparticipant_set__user")
            .distinct()
        )

        # ロールフィルター
        role = request.query_params.get("role", "")
        if role == "gm":
            sessions = sessions.filter(id__in=gm_role_session_ids)
        elif role == "player":
            sessions = sessions.filter(id__in=participant_session_ids).exclude(id__in=gm_role_session_ids)

        # ステータスフィルター
        period = request.query_params.get("period", "future")
        status_filter = request.query_params.get("status", "")
        if status_filter:
            sessions = sessions.filter(status=status_filter)
        elif period == "future":
            # デフォルト: 予定と進行中
            sessions = sessions.filter(status__in=["planned", "ongoing"])

        # 期間フィルター
        sessions = _filter_sessions_by_period(sessions, period, now)
        # period='' の場合はフィルターなし（すべて）

        # ソート: futureは昇順、past系は降順、allは未来→過去の順
        sessions = _order_sessions_by_period(sessions, period, now)

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

        page = _safe_positive_int(request.query_params.get("page", 1), 1)
        page_size = _safe_positive_int(request.query_params.get("page_size", 20), 20, max_value=100)
        offset = (page - 1) * page_size

        total_count = sessions.count()
        sessions_page = sessions[offset : offset + page_size]

        # ユーザーのロール情報を付加してシリアライズ
        result = []
        for session in sessions_page:
            session_data = TRPGSessionSerializer(session, context={"request": request}).data
            # ユーザーのロールを追加
            if session.id in gm_role_session_id_set:
                session_data["my_role"] = "gm"
            else:
                session_data["my_role"] = "player"
            result.append(session_data)

        return Response(
            {
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
                "results": result,
            }
        )

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        user = request.user
        year = request.query_params.get("year", datetime.now().year)

        # 年間プレイ時間計算
        sessions = TRPGSession.objects.filter(participants=user, date__year=year, status="completed")

        total_minutes = sessions.aggregate(total=Sum(effective_duration_expression()))["total"] or 0

        total_hours = total_minutes / 60
        session_count = sessions.count()

        return Response(
            {
                "year": year,
                "total_hours": round(total_hours, 1),
                "total_minutes": total_minutes,
                "session_count": session_count,
                "average_session_hours": round(total_hours / session_count, 1) if session_count > 0 else 0,
            }
        )

    @action(detail=False, methods=["get"], url_path="editable-choices")
    def editable_choices(self, request):
        manageable_session_ids = SessionParticipantRole.objects.filter(
            participant__user=request.user,
            role__in=session_permissions.MANAGEMENT_ROLES,
        ).values_list("participant__session_id", flat=True)
        legacy_gm_session_ids = TRPGSession.objects.filter(gm=request.user).values_list("id", flat=True)
        sessions = (
            self.get_queryset()
            .filter(Q(id__in=manageable_session_ids) | Q(id__in=legacy_gm_session_ids))
            .select_related("group")[:200]
        )
        return Response(
            [
                {
                    "id": session.id,
                    "title": session.title,
                    "group_id": session.group_id,
                    "group_name": session.group.name if session.group_id else "",
                }
                for session in sessions
            ]
        )


class SessionInvitationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SessionInvitation.objects.none()
    serializer_class = SessionInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = SessionInvitation.objects.filter(invitee=self.request.user).select_related(
            "session",
            "session__group",
            "inviter",
        )

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        invitation = self.get_object()

        if invitation.is_expired:
            invitation.mark_expired()
            return Response({"error": "招待の期限が切れています"}, status=status.HTTP_400_BAD_REQUEST)

        if invitation.status == "accepted":
            participant = SessionParticipant.objects.filter(session=invitation.session, user=request.user).first()
            return Response(
                {
                    "status": "already_accepted",
                    "session_id": invitation.session.id,
                    "participant_id": participant.id if participant else None,
                }
            )

        if invitation.status != "pending":
            return Response({"error": "この招待は保留状態ではありません"}, status=status.HTTP_400_BAD_REQUEST)

        participant, created = SessionParticipant.objects.get_or_create(
            session=invitation.session,
            user=request.user,
        )
        if invitation.invited_role == "gm" and participant.player_slot is not None:
            participant.player_slot = None
            participant.save(update_fields=["player_slot"])
        _sync_participant_roles(participant, [invitation.invited_role], granted_by=invitation.inviter)

        invitation.status = "accepted"
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at"])

        return Response(
            {
                "status": "success",
                "session_id": invitation.session.id,
                "participant_id": participant.id,
                "already_participating": not created,
            }
        )

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        invitation = self.get_object()

        if invitation.is_expired:
            invitation.mark_expired()
            return Response({"error": "招待の期限が切れています"}, status=status.HTTP_400_BAD_REQUEST)

        if invitation.status == "declined":
            return Response({"status": "already_declined"})

        if invitation.status != "pending":
            return Response({"error": "この招待は保留状態ではありません"}, status=status.HTTP_400_BAD_REQUEST)

        invitation.status = "declined"
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at"])

        return Response({"status": "success"})


class SessionOccurrenceViewSet(viewsets.ModelViewSet):
    queryset = SessionOccurrence.objects.none()
    serializer_class = SessionOccurrenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        visible_session_ids = _visible_sessions_for(user).values_list("id", flat=True)

        queryset = (
            SessionOccurrence.objects.select_related(
                "session",
                "session__gm",
                "session__group",
            )
            .prefetch_related("participants")
            .filter(session_id__in=visible_session_ids)
        )

        session_id = self.request.query_params.get("session_id")
        if session_id:
            queryset = queryset.filter(session_id=session_id)

        return queryset.order_by("start_at", "id")

    def perform_create(self, serializer):
        session = serializer.validated_data.get("session")
        if not session or not session_permissions.can_edit_session_basic(self.request.user, session):
            raise PermissionDenied("Only a session manager can add session dates.")

        is_primary = session.date is None and not session.occurrences.filter(is_primary=True).exists()
        occurrence = serializer.save(is_primary=is_primary)

        if is_primary:
            session.date = occurrence.start_at
            session.save(update_fields=["date", "updated_at"])

    def perform_update(self, serializer):
        instance = serializer.instance
        if not session_permissions.can_edit_session_basic(self.request.user, instance.session):
            raise PermissionDenied("Only a session manager can edit session dates.")

        old_start_at = instance.start_at
        new_session = serializer.validated_data.get("session")
        if new_session and new_session.id != instance.session_id:
            raise ValidationError({"session": "Cannot change the session of an occurrence."})

        serializer.save()

        if (
            instance.is_primary
            and "start_at" in serializer.validated_data
            and old_start_at != instance.start_at
            and instance.session.date != instance.start_at
        ):
            session = instance.session
            session.date = instance.start_at
            session.save(update_fields=["date", "updated_at"])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not session_permissions.can_edit_session_basic(request.user, instance.session):
            raise PermissionDenied("Only a session manager can delete session dates.")
        if instance.is_primary:
            raise ValidationError({"detail": "Cannot delete the primary session date."})
        return super().destroy(request, *args, **kwargs)


class SessionParticipantViewSet(viewsets.ModelViewSet):
    queryset = SessionParticipant.objects.none()
    serializer_class = SessionParticipantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # セッションIDでフィルタリング可能
        session_id = self.request.query_params.get("session_id")
        queryset = SessionParticipant.objects.select_related("session", "user", "character_sheet", "participant_identity")

        if session_id:
            queryset = queryset.filter(session_id=session_id)

        # アクセス可能なセッションの参加者のみ
        visible_session_ids = _visible_sessions_for(self.request.user).values_list("id", flat=True)
        return queryset.filter(session_id__in=visible_session_ids).distinct()

    def create(self, request, *args, **kwargs):
        """参加申請の作成（クロス参加対応）"""
        session_id = request.data.get("session")

        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        can_manage_participants = session_permissions.can_manage_participants(request.user, session)

        raw_user_value = request.data.get("user")
        raw_guest_name = request.data.get("guest_name")
        raw_identity_id = request.data.get("participant_identity")
        guest_name = (raw_guest_name or "").strip()
        raw_user_is_empty = raw_user_value in [None, "", "null", "None"]
        identity_requested = raw_identity_id not in [None, "", "null", "None"]
        participant_identity = None

        # ゲスト参加者作成（GMのみ）
        if raw_user_is_empty and (guest_name or identity_requested):
            if not can_manage_participants:
                return Response(
                    {"error": "Only GM can add guest participants"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            try:
                participant_identity = _resolve_participant_identity_for_session(session, raw_identity_id)
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if participant_identity:
                guest_name = participant_identity.display_name
            elif not guest_name:
                return Response(
                    {"error": "guest_name or participant_identity is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                participant_roles = session_permissions.normalize_assignable_participant_roles(
                    _roles_from_request_data(
                        request.data,
                        default_roles=[SessionParticipantRole.Role.PLAYER],
                    )
                )
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            raw_slot = request.data.get("player_slot")
            slot_value = None
            if SessionParticipantRole.Role.PLAYER.value in participant_roles and raw_slot not in [None, "", "null", "None"]:
                try:
                    slot_value = int(raw_slot)
                except (TypeError, ValueError):
                    slot_value = None

            if slot_value:
                existing_slot = SessionParticipant.objects.filter(
                    session=session,
                    player_slot=slot_value,
                ).exists()
                if existing_slot:
                    return Response(
                        {"error": f"Player slot {slot_value} is already taken"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            character_sheet_url = request.data.get("character_sheet_url", "")
            character_name = request.data.get("character_name", "")
            resolved_character_name = _tableno_character_name_from_url(character_sheet_url, request.user)
            if resolved_character_name:
                character_name = resolved_character_name

            serializer = self.get_serializer(
                data={
                    "session": session.id,
                    "user": None,
                    "participant_identity": participant_identity.id if participant_identity else None,
                    "guest_name": guest_name,
                    "character_name": character_name,
                    "character_sheet_url": character_sheet_url,
                    "player_slot": slot_value,
                    "character_sheet": None,
                }
            )
            serializer.is_valid(raise_exception=True)
            self._participant_roles_for_save = participant_roles
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # セッションへのアクセス権限チェック
        target_user_id = request.data.get("user") or request.user.id
        try:
            target_user = CustomUser.objects.get(id=target_user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if target_user != request.user and not can_manage_participants:
            return Response(
                {"error": "You do not have permission to add other participants"}, status=status.HTTP_403_FORBIDDEN
            )

        can_participate = _is_assignable_session_user(session, target_user)

        if not can_participate:
            return Response(
                {"error": "You do not have permission to join this session"}, status=status.HTTP_403_FORBIDDEN
            )

        # 既に参加している場合
        if SessionParticipant.objects.filter(session=session, user=target_user).exists():
            return Response(
                {"error": "You are already participating in this session"}, status=status.HTTP_400_BAD_REQUEST
            )

        # キャラクターシートの取得
        character_sheet_id = request.data.get("character_sheet_id")
        character_sheet = None
        if character_sheet_id:
            try:
                character_sheet = CharacterSheet.objects.get(id=character_sheet_id, user=target_user)
            except CharacterSheet.DoesNotExist:
                return Response(
                    {"error": "Character sheet not found or not owned by you"}, status=status.HTTP_400_BAD_REQUEST
                )

        try:
            participant_roles = session_permissions.normalize_assignable_participant_roles(
                _roles_from_request_data(
                    request.data,
                    default_roles=[SessionParticipantRole.Role.PLAYER],
                )
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # 権限昇格防止: セッション管理者以外は GM ロールを指定できない
        if SessionParticipantRole.Role.GM.value in participant_roles and not can_manage_participants:
            return Response({"error": "Only a session manager can assign GM role"}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(
            data={
                "session": session.id,
                "user": target_user.id,
                "character_name": request.data.get("character_name", ""),
                "character_sheet": character_sheet.id if character_sheet else None,
            }
        )

        serializer.is_valid(raise_exception=True)
        self._participant_roles_for_save = participant_roles
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """参加情報の更新（GM承認機能）"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        can_manage_participants = session_permissions.can_manage_participants(request.user, instance.session)

        # GMまたは本人のみ更新可能
        if not can_manage_participants and instance.user != request.user:
            return Response(
                {"error": "You do not have permission to update this participant"}, status=status.HTTP_403_FORBIDDEN
            )

        # ステータス変更はGMのみ
        request_payload = request.data
        data = request_payload.copy()
        if hasattr(data, "dict"):
            data = data.dict()

        # session/user の変更は禁止（データ改ざん防止）
        for immutable_field in ["session", "user"]:
            if immutable_field in data:
                return Response({"error": f"{immutable_field} cannot be changed"}, status=status.HTTP_400_BAD_REQUEST)

        if "role" in request_payload:
            return Response({"error": "Use roles instead of role."}, status=status.HTTP_400_BAD_REQUEST)

        role_change_requested = "roles" in request_payload or "participant_roles" in request_payload
        if role_change_requested and not can_manage_participants:
            return Response(
                {"error": "Only a session manager can change participant role"}, status=status.HTTP_403_FORBIDDEN
            )
        if role_change_requested and instance.user_id == instance.session.created_by_id:
            return Response({"error": "The session creator role cannot be changed"}, status=status.HTTP_400_BAD_REQUEST)
        if role_change_requested:
            try:
                self._participant_roles_for_save = session_permissions.normalize_assignable_participant_roles(
                    _roles_from_request_data(request_payload)
                )
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            data.pop("roles", None)
            data.pop("participant_roles", None)

        if "participant_identity" in data:
            if not can_manage_participants:
                return Response(
                    {"error": "Only a session manager can change participant identity"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if instance.user_id:
                return Response(
                    {"error": "Registered participant cannot be linked to a temporary member"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                participant_identity = _resolve_participant_identity_for_session(
                    instance.session,
                    data.get("participant_identity"),
                    exclude_participant_id=instance.id,
                )
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            data["participant_identity"] = participant_identity.id if participant_identity else None
            if participant_identity and not (data.get("guest_name") or "").strip():
                data["guest_name"] = participant_identity.display_name

        # プレイヤー枠の重複チェック（joinと同等）
        if "player_slot" in data:
            raw_slot = data.get("player_slot")
            slot_value = None
            if raw_slot not in [None, "", "null", "None"]:
                try:
                    slot_value = int(raw_slot)
                except (TypeError, ValueError):
                    slot_value = None

            if slot_value:
                existing_slot = (
                    SessionParticipant.objects.filter(session=instance.session, player_slot=slot_value)
                    .exclude(id=instance.id)
                    .exists()
                )

                if existing_slot:
                    return Response(
                        {"error": f"Player slot {slot_value} is already taken"}, status=status.HTTP_400_BAD_REQUEST
                    )
        if "character_sheet_id" in data and "character_sheet" not in data:
            data["character_sheet"] = data.get("character_sheet_id")
            data.pop("character_sheet_id", None)

        if "character_sheet" in data:
            raw_value = data.get("character_sheet")
            if raw_value in [None, "", "null", "None"]:
                data["character_sheet"] = None
            else:
                if instance.user_id is None:
                    return Response(
                        {"error": "Guest participant cannot have character_sheet"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                try:
                    character_sheet = CharacterSheet.objects.get(id=raw_value, user=instance.user)
                except CharacterSheet.DoesNotExist:
                    return Response(
                        {"error": "Character sheet not found or not owned by participant"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                data["character_name"] = character_sheet.system_data.name

        if "character_sheet_url" in data:
            character_sheet_from_url = _tableno_character_from_url(data.get("character_sheet_url"), request.user)
            if character_sheet_from_url:
                data["character_name"] = character_sheet_from_url.system_data.name
                if instance.user_id and character_sheet_from_url.user_id == instance.user_id:
                    if data.get("character_sheet") in [None, "", "null", "None"]:
                        data["character_sheet"] = character_sheet_from_url.id

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def perform_create(self, serializer):
        participant = serializer.save()
        roles = getattr(self, "_participant_roles_for_save", [SessionParticipantRole.Role.PLAYER])
        _sync_participant_roles(participant, roles, granted_by=self.request.user)
        if SessionParticipantRole.Role.GM.value in roles and participant.user_id:
            participant.session.gm = participant.user
            participant.session.save(update_fields=["gm", "updated_at"])
        bind_slot_handouts_to_participant(participant)

    def perform_update(self, serializer):
        participant = serializer.save()
        if hasattr(self, "_participant_roles_for_save"):
            _sync_participant_roles(participant, self._participant_roles_for_save, granted_by=self.request.user)
            if SessionParticipantRole.Role.GM.value in self._participant_roles_for_save and participant.user_id:
                participant.session.gm = participant.user
                participant.session.save(update_fields=["gm", "updated_at"])
        bind_slot_handouts_to_participant(participant)

    def destroy(self, request, *args, **kwargs):
        """Only the participant or a session manager can remove a participant."""
        instance = self.get_object()

        is_session_manager = session_permissions.can_manage_participants(request.user, instance.session)

        if instance.user_id == instance.session.gm_id:
            return Response({"error": "GMは除名できません。"}, status=status.HTTP_400_BAD_REQUEST)

        # Participants can remove themselves.
        if instance.user == request.user:
            instance.delete()
            bind_slot_handouts_to_participant(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)

        # Session managers can remove participants.
        if is_session_manager:
            instance.delete()
            bind_slot_handouts_to_participant(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response({"error": "Only GM can remove other participants"}, status=status.HTTP_403_FORBIDDEN)


class HandoutInfoViewSet(viewsets.ModelViewSet):
    queryset = HandoutInfo.objects.none()
    serializer_class = HandoutInfoSerializer
    permission_classes = [IsAuthenticated]

    class DefaultPagination(PageNumberPagination):
        page_size = 20
        page_size_query_param = "page_size"
        max_page_size = 100

    pagination_class = DefaultPagination

    def get_queryset(self):
        user = self.request.user
        # GMは全て、参加者は自分宛+公開ハンドアウト
        # プレイヤー枠に基づくハンドアウトも含める
        from django.db.models import Exists, OuterRef

        matching_assigned_slot = SessionParticipant.objects.filter(
            user=user,
            session_id=OuterRef("session_id"),
            player_slot=OuterRef("assigned_player_slot"),
        )
        secret_session_ids = TRPGSession.objects.filter(
            Q(gm=user) | Q(sessionparticipant__user=user, sessionparticipant__participant_roles__role=SessionParticipantRole.Role.GM)
        ).values_list("id", flat=True)

        return (
            HandoutInfo.objects.annotate(matches_assigned_slot=Exists(matching_assigned_slot))
            .filter(
                Q(session_id__in=secret_session_ids)
                | Q(participant__user=user)
                | (Q(session__participants=user) & Q(is_secret=False))
                | Q(matches_assigned_slot=True)
            )
            .distinct()
        )

    def perform_create(self, serializer):
        # GMのみハンドアウト作成可能
        session = serializer.validated_data["session"]
        if not session_permissions.can_manage_secret_content(self.request.user, session):
            raise PermissionDenied("Only a session manager can create handouts")

        # ハンドアウト番号とプレイヤー枠の整合性チェック
        handout_number = serializer.validated_data.get("handout_number")
        assigned_player_slot = serializer.validated_data.get("assigned_player_slot")

        if handout_number and assigned_player_slot:
            # 通常、HO1はプレイヤー1、HO2はプレイヤー2...に対応
            if handout_number != assigned_player_slot:
                # 警告ログを出力（強制はしない）
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Handout number {handout_number} assigned to player slot {assigned_player_slot}")

        serializer.save()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not session_permissions.can_view_secret_content(request.user, instance.session):
            HandoutView.objects.update_or_create(
                handout=instance,
                user=request.user,
                defaults={"viewed_at": timezone.now()},
            )
        return Response(self.get_serializer(instance).data)

    @action(detail=False, methods=["post"])
    def toggle_visibility(self, request):
        """ハンドアウトの公開/秘匿切り替え（GMのみ）"""
        handout_id = request.data.get("handout_id")

        if not handout_id:
            return Response({"error": "handout_idが必要です"}, status=status.HTTP_400_BAD_REQUEST)

        handout = get_object_or_404(HandoutInfo, id=handout_id)

        if not session_permissions.can_manage_secret_content(request.user, handout.session):
            return Response({"error": "GM権限が必要です"}, status=status.HTTP_403_FORBIDDEN)

        handout.is_secret = not handout.is_secret
        handout.release_status = (
            HandoutInfo.ReleaseStatus.MANUAL if handout.is_secret else HandoutInfo.ReleaseStatus.RELEASED
        )
        handout.released_at = None if handout.is_secret else timezone.now()
        handout.next_evaluation_at = None
        handout.save()

        serializer = HandoutInfoSerializer(handout)
        return Response(
            {
                "handout": serializer.data,
                "message": f'ハンドアウトを{"秘匿" if handout.is_secret else "公開"}に設定しました',
            }
        )


class CalendarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_raw = request.query_params.get("start")
        end_raw = request.query_params.get("end")
        month_str = request.query_params.get("month")

        # 月指定の場合
        if month_str and not (start_raw or end_raw):
            try:
                # YYYY-MM形式をパース
                year, month = map(int, month_str.split("-"))
                tz = timezone.get_current_timezone()
                start_date = timezone.make_aware(datetime(year, month, 1), tz)
                if month == 12:
                    month_end = datetime(year + 1, 1, 1)
                else:
                    month_end = datetime(year, month + 1, 1)
                end_date = timezone.make_aware(month_end, tz) - timedelta(microseconds=1)
            except (ValueError, AttributeError):
                return Response(
                    {"error": "Invalid month format. Use YYYY-MM format"}, status=status.HTTP_400_BAD_REQUEST
                )
        elif start_raw and end_raw:
            try:
                start_date = datetime.fromisoformat(start_raw)
                end_date = datetime.fromisoformat(end_raw)
            except ValueError:
                return Response({"error": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)

            tz = timezone.get_current_timezone()
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date, tz)
            if timezone.is_naive(end_date):
                if "T" not in end_raw:
                    end_date = end_date + timedelta(days=1) - timedelta(microseconds=1)
                end_date = timezone.make_aware(end_date, tz)
        else:
            return Response(
                {"error": "Either month or both start and end parameters are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        visible_session_ids = _visible_sessions_for(request.user).values_list("id", flat=True)
        participant_session_ids = set(
            SessionParticipant.objects.filter(user=request.user).values_list("session_id", flat=True)
        )
        gm_role_session_ids = _gm_role_session_ids_for(request.user)

        participant_prefetch = Prefetch(
            "session__sessionparticipant_set",
            queryset=SessionParticipant.objects.select_related("user").only(
                "id",
                "session_id",
                "user_id",
                "guest_name",
                "player_slot",
                "user__id",
                "user__username",
                "user__nickname",
            ),
        )

        occurrences = (
            SessionOccurrence.objects.filter(
                session_id__in=visible_session_ids,
                start_at__range=[start_date, end_date],
            )
            .select_related("session", "session__gm", "session__group")
            .prefetch_related(participant_prefetch)
            .order_by("start_at", "id")
        )

        # イベント形式に変換
        attendee_names_by_session_id = {}
        events = []
        for occurrence in occurrences:
            session = occurrence.session
            # ユーザーのセッションとの関係を判定
            is_gm = _is_session_gm_for_user(session, request.user, gm_role_session_ids)
            is_participant = (session.id in participant_session_ids) and not is_gm
            is_public_only = not is_gm and not is_participant and session.visibility == "public"

            # セッションタイプを決定
            if is_gm:
                session_type = "gm"
            elif is_participant:
                session_type = "participant"
            else:
                session_type = "public"

            attendee_summary = attendee_names_by_session_id.get(session.id)
            if attendee_summary is None:
                participant_names = set()
                guest_names = set()
                for participant in session.sessionparticipant_set.all():
                    if getattr(participant, "user_id", None):
                        user = getattr(participant, "user", None)
                        if user is None:
                            continue
                        participant_names.add(user.nickname or user.username)
                    else:
                        guest_name = (getattr(participant, "guest_name", "") or "").strip()
                        if guest_name:
                            guest_names.add(guest_name)

                attendee_summary = (sorted(participant_names), sorted(guest_names))
                attendee_names_by_session_id[session.id] = attendee_summary

            participant_names, guest_names = attendee_summary

            event = {
                "id": occurrence.id,
                "session_id": session.id,
                "occurrence_id": occurrence.id,
                "title": session.title,
                "date": occurrence.start_at.isoformat(),
                "type": session_type,
                "status": session.status,
                "visibility": session.visibility,
                "gm_id": session.gm_id,
                "gm_name": _session_gm_name(session),
                "location": session.location or "",
                "content": occurrence.content or "",
                "participant_names": participant_names,
                "guest_names": guest_names,
                "participant_count": len(participant_names),
                "guest_count": len(guest_names),
                "is_gm": is_gm,
                "is_participant": is_participant,
                "is_public_only": is_public_only,
            }
            events.append(event)

        # month指定の場合は特別なレスポンス形式
        if month_str:
            return Response({"month": month_str, "events": events})
        else:
            return Response(events)


class JapaneseHolidayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_raw = request.query_params.get("start")
        end_raw = request.query_params.get("end")
        if not start_raw or not end_raw:
            return Response(
                {"error": "Both start and end parameters are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date = datetime.fromisoformat(start_raw).date()
            end_date = datetime.fromisoformat(end_raw).date()
        except ValueError:
            return Response(
                {"error": "Invalid date format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        holidays = JapaneseHoliday.objects.filter(
            date__gte=start_date,
            date__lt=end_date,
        ).order_by("date")
        return Response(
            [
                {
                    "date": holiday.date.isoformat(),
                    "name": holiday.name,
                }
                for holiday in holidays
            ]
        )


class MonthlyEventListView(APIView):
    """月別イベント一覧API（ISSUE-008実装）"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # YYYY-MM形式の月指定を取得
        month_str = request.query_params.get("month")
        if not month_str:
            return Response(
                {"error": "month parameter is required (YYYY-MM format)"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            year, month = map(int, month_str.split("-"))
            tz = timezone.get_current_timezone()
            start_date = timezone.make_aware(datetime(year, month, 1), tz)
            if month == 12:
                month_end = datetime(year + 1, 1, 1)
            else:
                month_end = datetime(year, month + 1, 1)
            end_date = timezone.make_aware(month_end, tz) - timedelta(microseconds=1)
        except (ValueError, AttributeError):
            return Response({"error": "Invalid month format. Use YYYY-MM format"}, status=status.HTTP_400_BAD_REQUEST)

        # セッションを取得
        visible_session_ids = _visible_sessions_for(request.user).values_list("id", flat=True)
        participant_session_ids = set(
            SessionParticipant.objects.filter(user=request.user).values_list("session_id", flat=True)
        )
        gm_role_session_ids = _gm_role_session_ids_for(request.user)

        occurrences = (
            SessionOccurrence.objects.filter(
                session_id__in=visible_session_ids,
                start_at__range=[start_date, end_date],
            )
            .select_related("session", "session__gm", "session__group")
            .prefetch_related("participants")
            .order_by("start_at", "id")
        )

        # 日付別にグループ化
        events_by_date = {}
        for occurrence in occurrences:
            session = occurrence.session
            date_str = occurrence.start_at.strftime("%Y-%m-%d")
            if date_str not in events_by_date:
                events_by_date[date_str] = {"date": date_str, "events": []}

            # ユーザーとの関係を判定
            is_gm = _is_session_gm_for_user(session, request.user, gm_role_session_ids)
            is_participant = (session.id in participant_session_ids) and not is_gm

            event_data = {
                "id": occurrence.id,
                "session_id": session.id,
                "occurrence_id": occurrence.id,
                "title": session.title,
                "time": occurrence.start_at.strftime("%H:%M"),
                "duration_minutes": session.effective_duration_minutes,
                "status": session.status,
                "visibility": session.visibility,
                "group": {"id": session.group.id, "name": session.group.name} if session.group else None,
                "gm": _session_gm_payload(session),
                "participant_count": len(occurrence.participants.all()),
                "is_gm": is_gm,
                "is_participant": is_participant,
                "location": session.location or "",
                "content": occurrence.content or "",
            }

            events_by_date[date_str]["events"].append(event_data)

        # 日付順にソート
        sorted_dates = sorted(events_by_date.values(), key=lambda x: x["date"])

        return Response(
            {
                "month": month_str,
                "year": year,
                "month_name": f"{year}年{month}月",
                "dates": sorted_dates,
                "total_sessions": occurrences.count(),
                "summary": {
                    "planned": occurrences.filter(session__status="planned").count(),
                    "ongoing": occurrences.filter(session__status="ongoing").count(),
                    "completed": occurrences.filter(session__status="completed").count(),
                    "cancelled": occurrences.filter(session__status="cancelled").count(),
                },
            }
        )


class SessionAggregationView(APIView):
    """セッション予定集約API（ISSUE-008実装）"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 期間指定
        days = int(request.query_params.get("days", 30))
        start_date = timezone.now()
        end_date = start_date + timedelta(days=days)

        # ユーザーのセッションを取得
        visible_session_ids = _visible_sessions_for(request.user).values_list("id", flat=True)
        participant_session_ids = set(
            SessionParticipant.objects.filter(user=request.user).values_list("session_id", flat=True)
        )
        gm_role_session_ids = _gm_role_session_ids_for(request.user)

        occurrences = (
            SessionOccurrence.objects.filter(
                session_id__in=visible_session_ids,
                start_at__range=[start_date, end_date],
                session__status__in=["planned", "ongoing"],
            )
            .select_related("session", "session__gm", "session__group")
            .order_by("start_at", "id")
        )

        # グループ別、システム別に集約
        aggregations = {"by_group": {}, "by_system": {}, "by_week": {}, "by_role": {"as_gm": [], "as_player": []}}

        for occurrence in occurrences:
            session = occurrence.session
            # グループ別集約
            if session.group:
                group_key = session.group.id
                if group_key not in aggregations["by_group"]:
                    aggregations["by_group"][group_key] = {
                        "group_id": session.group.id,
                        "group_name": session.group.name,
                        "sessions": [],
                    }
                aggregations["by_group"][group_key]["sessions"].append(
                    {
                        "id": occurrence.id,
                        "session_id": session.id,
                        "occurrence_id": occurrence.id,
                        "title": session.title,
                        "date": occurrence.start_at.isoformat(),
                    }
                )

            # 週別集約
            week_key = occurrence.start_at.strftime("%Y-W%U")
            if week_key not in aggregations["by_week"]:
                aggregations["by_week"][week_key] = {
                    "week": week_key,
                    "start_date": (occurrence.start_at - timedelta(days=occurrence.start_at.weekday())).strftime(
                        "%Y-%m-%d"
                    ),
                    "sessions": [],
                }
            aggregations["by_week"][week_key]["sessions"].append(
                {
                    "id": occurrence.id,
                    "session_id": session.id,
                    "occurrence_id": occurrence.id,
                    "title": session.title,
                    "date": occurrence.start_at.isoformat(),
                }
            )

            # 役割別集約
            if _is_session_gm_for_user(session, request.user, gm_role_session_ids):
                aggregations["by_role"]["as_gm"].append(
                    {
                        "id": occurrence.id,
                        "session_id": session.id,
                        "occurrence_id": occurrence.id,
                        "title": session.title,
                        "date": occurrence.start_at.isoformat(),
                        "participant_count": session.participants.count(),
                    }
                )
            elif session.id in participant_session_ids:
                aggregations["by_role"]["as_player"].append(
                    {
                        "id": occurrence.id,
                        "session_id": session.id,
                        "occurrence_id": occurrence.id,
                        "title": session.title,
                        "date": occurrence.start_at.isoformat(),
                        "gm_name": _session_gm_name(session),
                    }
                )

        return Response(
            {
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days},
                "total_sessions": occurrences.count(),
                "aggregations": aggregations,
                "upcoming_sessions": [
                    {
                        "id": upcoming.id,
                        "session_id": upcoming.session.id,
                        "occurrence_id": upcoming.id,
                        "title": upcoming.session.title,
                        "date": upcoming.start_at.isoformat(),
                    }
                    for upcoming in occurrences.order_by("start_at")[:5]
                ],
            }
        )


class ICalExportView(APIView):
    """iCal形式エクスポートAPI（ISSUE-008実装）"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        import uuid

        from django.http import HttpResponse

        # 期間指定
        days = int(request.query_params.get("days", 90))
        start_date = timezone.now()
        end_date = start_date + timedelta(days=days)

        # セッションを取得
        visible_session_ids = _visible_sessions_for(request.user).values_list("id", flat=True)
        gm_role_session_ids = _gm_role_session_ids_for(request.user)
        occurrences = (
            SessionOccurrence.objects.filter(
                session_id__in=visible_session_ids,
                start_at__range=[start_date, end_date],
            )
            .select_related("session", "session__gm", "session__group")
            .order_by("start_at", "id")
        )

        # iCal形式の生成
        lines = []
        lines.append("BEGIN:VCALENDAR")
        lines.append("VERSION:2.0")
        lines.append("PRODID:-//タブレノ//TRPG Session Calendar//JP")
        lines.append("CALSCALE:GREGORIAN")
        lines.append("METHOD:PUBLISH")
        lines.append(f"X-WR-CALNAME:タブレノ - {request.user.nickname or request.user.username}")
        lines.append("X-WR-TIMEZONE:Asia/Tokyo")

        for occurrence in occurrences:
            # イベントの開始・終了時刻
            session = occurrence.session
            dtstart = occurrence.start_at
            dtend = dtstart + timedelta(minutes=session.duration_minutes or 180)

            # ユーザーとの関係
            is_gm = _is_session_gm_for_user(session, request.user, gm_role_session_ids)
            role = "GM" if is_gm else "Player"

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uuid.uuid4()}@tableno.jp")
            lines.append(f'DTSTAMP:{timezone.now().strftime("%Y%m%dT%H%M%SZ")}')
            lines.append(f'DTSTART:{dtstart.strftime("%Y%m%dT%H%M%S")}')
            lines.append(f'DTEND:{dtend.strftime("%Y%m%dT%H%M%S")}')
            lines.append(f"SUMMARY:[{role}] {session.title}")

            # 詳細説明
            description_parts = []
            description_parts.append(f"Status: {session.get_status_display()}")
            description_parts.append(f"GM: {_session_gm_name(session) or '未設定'}")
            if session.group:
                description_parts.append(f"Group: {session.group.name}")
            if session.location:
                description_parts.append(f"Location: {session.location}")
            if session.description:
                description_parts.append(f"\\n{session.description}")

            lines.append(f'DESCRIPTION:{" | ".join(description_parts)}')

            if session.location:
                lines.append(f"LOCATION:{session.location}")

            # ステータスに応じた設定
            if session.status == "cancelled":
                lines.append("STATUS:CANCELLED")
            elif session.status == "completed":
                lines.append("STATUS:CONFIRMED")
            else:
                lines.append("STATUS:TENTATIVE")

            # カテゴリ
            lines.append(f"CATEGORIES:TRPG,{role}")

            # アラーム設定（1日前と1時間前）
            if session.status == "planned":
                # 1日前のリマインダー
                lines.append("BEGIN:VALARM")
                lines.append("TRIGGER:-P1D")
                lines.append("ACTION:DISPLAY")
                lines.append(f"DESCRIPTION:明日のTRPGセッション: {session.title}")
                lines.append("END:VALARM")

                # 1時間前のリマインダー
                lines.append("BEGIN:VALARM")
                lines.append("TRIGGER:-PT1H")
                lines.append("ACTION:DISPLAY")
                lines.append(f"DESCRIPTION:1時間後のTRPGセッション: {session.title}")
                lines.append("END:VALARM")

            lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")

        # レスポンス生成
        response = HttpResponse("\r\n".join(lines), content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="tableno_sessions_{timezone.now().strftime("%Y%m%d")}.ics"'
        )

        return response


class CreateSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TRPGSessionSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            # GMとして自動設定
            self_as_gm = str(
                request.data.get("as_gm")
                or request.data.get("self_as_gm")
                or request.data.get("is_gm")
                or ""
            ).lower() in {"1", "true", "yes", "on"}
            session = serializer.save(
                created_by=request.user,
                gm=request.user if self_as_gm else None,
            )
            clone_scenario_handouts_to_session(session.scenario, session)

            session_permissions.initialize_created_session_permissions(
                session,
                created_by=request.user,
                gm=request.user if self_as_gm else None,
            )

            return Response(
                TRPGSessionSerializer(session, context={"request": request}).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JoinSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(TRPGSession, pk=pk)

        # 参加可能かチェック
        if session.visibility == "private":
            return Response({"error": "This session is private"}, status=status.HTTP_403_FORBIDDEN)

        try:
            requested_roles = _roles_from_request_data(
                request.data,
                default_roles=[SessionParticipantRole.Role.PLAYER],
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if requested_roles != {SessionParticipantRole.Role.PLAYER.value}:
            return Response(
                {"error": "Self-join only accepts the player role"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        participant, created = SessionParticipant.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={
                "character_name": request.data.get("character_name", ""),
                "character_sheet_url": request.data.get("character_sheet_url", ""),
            },
        )

        if created:
            _sync_participant_roles(
                participant,
                [SessionParticipantRole.Role.PLAYER],
                granted_by=request.user,
            )
            bind_slot_handouts_to_participant(participant)
            serializer = SessionParticipantSerializer(participant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": "Already joined this session"}, status=status.HTTP_400_BAD_REQUEST)


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
            local_dt = dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt
            local_now = now.replace(tzinfo=None) if getattr(now, "tzinfo", None) else now

            if local_dt.date() == local_now.date():
                return f"今日 {dt.strftime('%H:%M')}"
            if local_dt.date() == (local_now + timedelta(days=1)).date():
                return f"明日 {dt.strftime('%H:%M')}"
            if local_dt.date() <= (local_now + timedelta(days=7)).date():
                weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                weekday = weekdays[local_dt.weekday()]
                return f"{local_dt.strftime('%m/%d')}({weekday}) {dt.strftime('%H:%M')}"
            return dt.strftime("%Y年%m月%d日 %H:%M")

        occurrences = (
            SessionOccurrence.objects.filter(
                Q(session__gm=user) | Q(session__participants=user),
                start_at__gte=now,
                session__status="planned",
            )
            .select_related(
                "session",
                "session__gm",
                "session__group",
                "session__scenario",
            )
            .prefetch_related(
                "session__sessionparticipant_set__user",
            )
            .distinct()
            .order_by("start_at", "id")[:5]
        )

        results = []
        for occurrence in occurrences:
            session = occurrence.session
            participants = list(session.sessionparticipant_set.all())
            guest_count = sum(1 for p in participants if p.user_id is None)
            member_count = len(participants) - guest_count
            players = [p for p in participants if not _participant_has_role(p, SessionParticipantRole.Role.GM)]

            if len(players) == 0:
                participants_summary = "GM のみ"
            elif len(players) <= 3:
                participants_summary = ", ".join([p.display_name for p in players])
            else:
                names = [p.display_name for p in players[:2]]
                participants_summary = f"{', '.join(names)} 他{len(players) - 2}人"

            results.append(
                {
                    "id": session.id,
                    "session_id": session.id,
                    "occurrence_id": occurrence.id,
                    "title": session.title,
                    "date": occurrence.start_at.isoformat(),
                    "date_formatted": occurrence.start_at.strftime("%Y年%m月%d日 %H:%M"),
                    "date_display": format_date_display(occurrence.start_at),
                    "location": session.location or "",
                    "status": session.status,
                    "gm_name": _session_gm_name(session),
                    "group_name": session.group.name if session.group_id else "",
                    "participant_count": member_count,
                    "guest_count": guest_count,
                    "participants_summary": participants_summary,
                    "duration_minutes": session.effective_duration_minutes,
                    "duration_display": format_duration(session.effective_duration_minutes),
                }
            )

        return Response(results)


class NextSessionContextView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        occurrence = None

        session_id = request.query_params.get("session_id")
        if session_id:
            try:
                session_id = int(session_id)
            except (TypeError, ValueError):
                return Response({"error": "session_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

            session = TRPGSession.objects.select_related("scenario").filter(id=session_id).first()
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

            if not session_permissions.can_view_session_basic(user, session):
                return Response(
                    {"error": "このセッションにアクセスする権限がありません"}, status=status.HTTP_403_FORBIDDEN
                )
        else:
            occurrence = (
                SessionOccurrence.objects.filter(
                    session_id__in=_visible_sessions_for(user).values_list("id", flat=True),
                    start_at__gte=now,
                    session__status="planned",
                )
                .select_related("session", "session__scenario")
                .order_by("start_at", "id")
                .first()
            )
            session = occurrence.session if occurrence else None

        if not session:
            return Response({"session_id": None})

        if occurrence is None:
            occurrence = (
                session.occurrences.filter(start_at__gte=now).order_by("start_at", "id").first()
                or session.occurrences.order_by("start_at", "id").first()
            )

        scenario = session.scenario
        scenario_data = None
        if scenario:
            scenario_data = {
                "id": scenario.id,
                "title": scenario.title,
                "game_system": scenario.game_system,
                "recommended_skills": scenario.recommended_skills or "",
                "semi_recommended_skills": scenario.semi_recommended_skills or "",
                "recommended_skill_items": [
                    {
                        "id": skill.id,
                        "name": skill.name,
                        "level": skill.level,
                        "description": skill.description,
                        "order": skill.order,
                    }
                    for skill in scenario.recommended_skill_items.order_by("order", "id")
                ],
            }

        participant = SessionParticipant.objects.filter(session=session, user=user).first()
        handout_skills = []
        handout_titles = []
        if participant:
            handouts = HandoutInfo.objects.filter(
                Q(participant=participant) | Q(handout_number__isnull=True, assigned_player_slot__isnull=True),
                session=session,
            )
            for handout in handouts:
                if handout.recommended_skills:
                    handout_skills.append(handout.recommended_skills)
                    handout_titles.append(handout.name or handout.title)

        return Response(
            {
                "session_id": session.id,
                "session_title": session.title,
                "session_date": occurrence.start_at if occurrence else session.date,
                "occurrence_id": occurrence.id if occurrence else None,
                "scenario": scenario_data,
                "handout_recommended_skills": handout_skills,
                "handout_titles": handout_titles,
            }
        )


class ParticipatingScenarioChoicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        occurrence = None

        try:
            days = int(request.query_params.get("days", 365))
        except (TypeError, ValueError):
            days = 365
        try:
            limit = int(request.query_params.get("limit", 50))
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

        occurrences = (
            SessionOccurrence.objects.filter(
                Q(session__gm=user) | Q(session__participants=user),
                start_at__gte=now,
                start_at__lte=now + timedelta(days=days),
                session__status="planned",
                session__scenario__isnull=False,
            )
            .select_related("session", "session__scenario", "session__group")
            .order_by("start_at", "id")[:limit]
        )

        results = []
        for occurrence in occurrences:
            session = occurrence.session
            scenario = session.scenario
            if not scenario:
                continue

            session_date_display = None
            if occurrence.start_at:
                session_date_display = occurrence.start_at.strftime("%Y/%m/%d %H:%M")

            results.append(
                {
                    "session_id": session.id,
                    "occurrence_id": occurrence.id,
                    "session_title": session.title,
                    "session_date": occurrence.start_at,
                    "session_date_display": session_date_display,
                    "group_name": session.group.name if session.group else "",
                    "scenario": {
                        "id": scenario.id,
                        "title": scenario.title,
                        "game_system": scenario.game_system,
                    },
                }
            )

        return Response(results)


class SessionStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        year_ago = now - timedelta(days=365)

        # 年間統計
        user_sessions = TRPGSession.objects.filter(
            Q(participants=user) | Q(gm=user), date__gte=year_ago, date__lte=now
        ).distinct()

        session_count = user_sessions.count()
        total_minutes = user_sessions.aggregate(total=Sum(effective_duration_expression()))["total"] or 0
        total_hours = round(total_minutes / 60, 1)

        return Response({"session_count": session_count, "total_hours": total_hours, "total_minutes": total_minutes})


def _get_selected_occurrence_from_request(request, occurrences):
    try:
        occurrence_id_raw = request.query_params.get("occurrence_id")
    except AttributeError:
        occurrence_id_raw = request.GET.get("occurrence_id")

    if not occurrence_id_raw:
        return None, None

    try:
        occurrence_id = int(occurrence_id_raw)
    except (TypeError, ValueError):
        return None, None

    if occurrence_id <= 0:
        return None, None

    selected_occurrence = occurrences.filter(id=occurrence_id).first()
    return selected_occurrence, selected_occurrence.id if selected_occurrence else None


def _fixed_character_share_url(request, character_sheet):
    if not character_sheet or character_sheet.access_scope not in ("link", "public"):
        return ""

    return request.build_absolute_uri(
        reverse("fixed-shared-character-view", kwargs={"share_token": character_sheet.share_token})
    )


def _attach_participant_character_share_urls(request, participants):
    for participant in participants:
        participant.character_sheet_share_url = _fixed_character_share_url(
            request,
            getattr(participant, "character_sheet", None),
        )


class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # セッション詳細取得
        try:
            session = TRPGSession.objects.select_related("scenario").get(pk=pk)
        except TRPGSession.DoesNotExist:
            if "application/json" in request.headers.get("Accept", ""):
                return Response({"error": "Session not found"}, status=404)
            else:
                from django.http import Http404

                raise Http404("Session not found")

        # アクセス権限チェック
        user = request.user
        has_access = _can_access_session_basic(session, user)

        if not has_access:
            if "application/json" in request.headers.get("Accept", ""):
                return Response({"error": "Permission denied"}, status=403)
            else:
                from django.core.exceptions import PermissionDenied

                raise PermissionDenied("このセッションにアクセスする権限がありません")

        # HTMLまたはJSONレスポンス
        if "application/json" in request.headers.get("Accept", ""):
            return self.get_json_response(request, session, user)
        else:
            return self.get_html_response(request, session, user)

    def get_json_response(self, request, session, user):
        from .serializers import TRPGSessionSerializer

        serializer = TRPGSessionSerializer(session, context={"request": request})
        return Response(serializer.data)

    def get_html_response(self, request, session, user):
        # 参加者情報
        participants = (
            SessionParticipant.objects.filter(session=session)
            .select_related("user", "character_sheet", "participant_identity")
            .prefetch_related(
                "participant_roles",
                Prefetch("character_sheet__sixth_edition_data__skills", queryset=CharacterSkill6th.objects.order_by("id")),
                Prefetch("character_sheet__seventh_edition_data__skills", queryset=CharacterSkill7th.objects.order_by("id")),
            )
        )
        guest_count = participants.filter(user__isnull=True).count()
        has_temporary_member_participant = participants.filter(
            participant_identity__user__isnull=True,
            participant_identity__is_active=True,
        ).exists()

        occurrences = session.occurrences.prefetch_related("participants").order_by("start_at", "id")

        selected_occurrence, selected_occurrence_id = _get_selected_occurrence_from_request(
            request,
            occurrences,
        )

        can_manage_secret_content = session_permissions.can_manage_secret_content(user, session)
        can_view_secret_content = session_permissions.can_view_secret_content(user, session)
        can_manage_permissions = session_permissions.can_manage_permissions(user, session)

        # ハンドアウト情報（権限に応じて）
        if can_view_secret_content:
            handouts = HandoutInfo.objects.filter(session=session).select_related("participant__user")
        else:
            user_participant = participants.filter(user=user).first()
            if user_participant:
                handouts = HandoutInfo.objects.filter(
                    Q(participant=user_participant)
                    | Q(session=session, is_secret=False, session__participants=user)
                    | Q(
                        session=session,
                        assigned_player_slot__isnull=False,
                        assigned_player_slot=user_participant.player_slot,
                    )
                ).select_related("participant__user")
            else:
                handouts = HandoutInfo.objects.none()

        # ユーザーの権限
        is_gm = session_permissions.is_session_gm(user, session)
        is_co_gm = is_gm
        is_session_manager = session_permissions.can_edit_session_basic(user, session)
        is_participant = participants.filter(user=user).exists()
        can_edit = is_session_manager
        can_invite = session_permissions.can_manage_participants(user, session)
        can_join = (
            (not is_gm)
            and (not is_participant)
            and session.status == "planned"
            and session.visibility != "private"
            and (
                session.visibility != "group"
                or (session.group_id and session.group.members.filter(id=user.id).exists())
            )
        )
        _attach_participant_character_share_urls(request, participants)
        _attach_participant_role_flags(participants)
        gm_participants = [
            participant
            for participant in participants
            if participant.is_gm_role or (participant.user_id and participant.user_id == session.gm_id)
        ]
        player_participants = [
            participant
            for participant in participants
            if participant.is_player_role
            and not participant.is_gm_role
            and not participant.is_owner_role
            and not participant.is_manager_role
        ]
        recommended_skill_comparison = None
        if session.scenario and (is_gm or is_participant):
            recommended_skill_comparison = build_recommended_skill_comparison(
                session.scenario,
                player_participants,
            )
        if can_view_secret_content:
            player_slot_handouts = handouts
            include_player_slot_titles = True
        elif can_edit:
            player_slot_handouts = HandoutInfo.objects.filter(
                session=session,
                assigned_player_slot__isnull=False,
            ).only("assigned_player_slot", "code", "handout_number", "name", "title")
            include_player_slot_titles = False
        else:
            player_slot_handouts = handouts
            include_player_slot_titles = True
        player_slot_options = _handout_player_slot_options(
            player_slot_handouts,
            include_titles=include_player_slot_titles,
        )

        open_date_poll = DatePoll.objects.filter(session=session, is_closed=False).first()
        invitation_status_by_user_id = {}
        for invitation in session.invitations.exclude(status="accepted"):
            status_value = "expired" if invitation.is_expired else invitation.status
            invitation_status_by_user_id[str(invitation.invitee_id)] = status_value
        invitation_status_by_user_id_json = json.dumps(invitation_status_by_user_id)

        public_session_url = None
        if session.visibility in ("link", "public"):
            public_session_url = request.build_absolute_uri(
                reverse("fixed-shared-session-view", kwargs={"share_token": session.share_token})
            )
        can_edit_scenario = can_manage_secret_content and getattr(user, "has_premium_access", False)
        scenario_choices = []
        if can_edit_scenario:
            from scenarios.access import visible_scenarios
            from scenarios.models import Scenario

            scenario_choices = visible_scenarios(Scenario.objects.all(), user).order_by("title", "id")

        context = {
            "session": session,
            "participants": participants,
            "gm_participants": gm_participants,
            "player_participants": player_participants,
            "recommended_skill_comparison": recommended_skill_comparison,
            "has_temporary_member_participant": has_temporary_member_participant,
            "occurrences": occurrences,
            "handouts": handouts,
            "player_slot_options": player_slot_options,
            "is_gm": is_gm,
            "is_co_gm": is_co_gm,
            "is_session_manager": is_session_manager,
            "is_participant": is_participant,
            "can_edit": can_edit,
            "can_invite": can_invite,
            "can_manage_secret_content": can_manage_secret_content,
            "can_manage_permissions": can_manage_permissions,
            "can_join": can_join,
            "user_participant": participants.filter(user=user).first(),
            "public_session_url": public_session_url,
            "is_public_view": False,
            "guest_count": guest_count,
            "open_date_poll": open_date_poll,
            "invitation_status_by_user_id_json": invitation_status_by_user_id_json,
            "selected_occurrence": selected_occurrence,
            "selected_occurrence_id": selected_occurrence_id,
            "can_edit_scenario": can_edit_scenario,
            "scenario_choices": scenario_choices,
        }

        return render(request, "schedules/session_detail.html", context)


class SessionDatePollView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            session = TRPGSession.objects.select_related("scenario", "gm", "group").get(pk=pk)
        except TRPGSession.DoesNotExist:
            if "application/json" in request.headers.get("Accept", ""):
                return Response({"error": "Session not found"}, status=404)
            else:
                from django.http import Http404

                raise Http404("Session not found")

        user = request.user
        has_access = _can_access_session_basic(session, user)

        if not has_access:
            if "application/json" in request.headers.get("Accept", ""):
                return Response({"error": "Permission denied"}, status=403)
            raise PermissionDenied("このセッションにアクセスする権限がありません")

        is_gm = session_permissions.can_edit_session_basic(user, session)
        is_participant = session.participants.filter(id=user.id).exists()
        can_edit = session_permissions.can_edit_session_basic(user, session)

        if "application/json" in request.headers.get("Accept", ""):
            return Response(
                {
                    "id": session.id,
                    "title": session.title,
                    "date": session.date.isoformat() if session.date else None,
                    "group": session.group_id,
                    "is_gm": is_gm,
                    "is_participant": is_participant,
                    "can_edit": can_edit,
                }
            )

        context = {
            "session": session,
            "is_gm": is_gm,
            "is_participant": is_participant,
            "can_edit": can_edit,
            "is_public_view": False,
        }

        return render(request, "schedules/session_date_poll.html", context)


class PublicSessionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, share_token):
        session = get_object_or_404(
            TRPGSession.objects.select_related("scenario", "gm", "group"),
            share_token=share_token,
            visibility="public",
        )

        participants = (
            SessionParticipant.objects.filter(session=session)
            .select_related("user", "character_sheet", "participant_identity")
            .prefetch_related("participant_roles")
        )
        _attach_participant_character_share_urls(request, participants)
        _attach_participant_role_flags(participants)
        gm_participants = [
            participant
            for participant in participants
            if participant.is_gm_role or (participant.user_id and participant.user_id == session.gm_id)
        ]
        player_participants = [
            participant
            for participant in participants
            if participant.is_player_role and not participant.is_gm_role and not participant.is_owner_role and not participant.is_manager_role
        ]
        guest_count = participants.filter(user__isnull=True).count()

        occurrences = session.occurrences.prefetch_related("participants").order_by("start_at", "id")

        selected_occurrence, selected_occurrence_id = _get_selected_occurrence_from_request(
            request,
            occurrences,
        )

        public_session_url = request.build_absolute_uri(
            reverse("fixed-shared-session-view", kwargs={"share_token": session.share_token})
        )

        context = {
            "session": session,
            "participants": participants,
            "gm_participants": gm_participants,
            "player_participants": player_participants,
            "occurrences": occurrences,
            "handouts": HandoutInfo.objects.none(),
            "player_slot_options": [],
            "is_gm": False,
            "is_participant": False,
            "can_edit": False,
            "can_invite": False,
            "can_manage_secret_content": False,
            "can_manage_permissions": False,
            "can_join": False,
            "user_participant": None,
            "public_session_url": public_session_url,
            "is_public_view": True,
            "guest_count": guest_count,
            "selected_occurrence": selected_occurrence,
            "selected_occurrence_id": selected_occurrence_id,
        }

        return render(request, "schedules/session_detail.html", context)


class SessionImageViewSet(viewsets.ModelViewSet):
    queryset = SessionImage.objects.none()
    """セッション画像ViewSet"""
    serializer_class = SessionImageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """ユーザーがアクセス可能なセッションの画像のみ取得"""
        user = self.request.user
        return SessionImage.objects.filter(
            Q(session__gm=user)  # GMは全て見られる
            | Q(session__participants=user)  # 参加者は見られる
            | Q(session__group__members=user)  # グループメンバーは見られる
        ).distinct()

    def create(self, request, *args, **kwargs):
        """画像作成時の権限チェック"""
        session_id = request.data.get("session")
        if not session_id:
            return Response({"error": "session is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        # 権限チェック
        if (
            not session_permissions.can_edit_session_basic(request.user, session)
            and not session.participants.filter(id=request.user.id).exists()
        ):
            return Response({"error": "Only GM or participants can upload images"}, status=status.HTTP_403_FORBIDDEN)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """画像アップロード時の処理"""
        # createメソッドで権限チェック済みなので、ここでは保存のみ
        session_id = self.request.data.get("session")
        session = TRPGSession.objects.get(id=session_id)
        serializer.save(uploaded_by=self.request.user, session=session)

    def perform_update(self, serializer):
        """画像更新時の処理"""
        instance = self.get_object()

        # GMまたはアップロード者のみ編集可能
        if (
            not session_permissions.can_edit_session_basic(self.request.user, instance.session)
            and instance.uploaded_by != self.request.user
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only GM or uploader can edit images")

        serializer.save()

    def perform_destroy(self, instance):
        """画像削除時の処理"""
        # GMまたはアップロード者のみ削除可能
        if (
            not session_permissions.can_edit_session_basic(self.request.user, instance.session)
            and instance.uploaded_by != self.request.user
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only GM or uploader can delete images")

        instance.delete()

    @action(detail=False, methods=["post"])
    def bulk_upload(self, request):
        """複数画像の一括アップロード"""
        session_id = request.data.get("session_id")
        images = request.FILES.getlist("images", [])

        if not session_id:
            return Response({"error": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        # 権限チェック
        if (
            not session_permissions.can_edit_session_basic(request.user, session)
            and not session.participants.filter(id=request.user.id).exists()
        ):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        created_images = []
        with transaction.atomic():
            for image_file in images[:10]:  # 最大10枚まで
                serializer = SessionImageSerializer(
                    data={
                        "image": image_file,
                        "title": image_file.name,
                    },
                    context={"request": request},
                )
                serializer.is_valid(raise_exception=True)
                created_images.append(
                    serializer.save(
                        session=session,
                        uploaded_by=request.user,
                    )
                )

        serializer = SessionImageSerializer(created_images, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reorder(self, request, pk=None):
        """画像の表示順序変更"""
        image = self.get_object()
        new_order = request.data.get("order")

        if new_order is None:
            return Response({"error": "order is required"}, status=status.HTTP_400_BAD_REQUEST)

        # GMのみ順序変更可能
        if not session_permissions.can_edit_session_basic(request.user, image.session):
            return Response({"error": "Only GM can reorder images"}, status=status.HTTP_403_FORBIDDEN)

        image.order = new_order
        image.save()

        return Response({"status": "success", "order": image.order})

    @action(detail=False, methods=["post"])
    def reorder_bulk(self, request):
        """画像の表示順序をまとめて変更（GMのみ）"""
        session_id = request.data.get("session_id")
        ordered_ids = request.data.get("ordered_ids")

        if not session_id:
            return Response(
                {"error": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(ordered_ids, list) or not ordered_ids:
            return Response(
                {"error": "ordered_ids is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session_id_int = int(session_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "session_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ordered_ids_int = [int(item) for item in ordered_ids]
        except (TypeError, ValueError):
            return Response(
                {"error": "ordered_ids must be a list of integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(set(ordered_ids_int)) != len(ordered_ids_int):
            return Response(
                {"error": "ordered_ids must be unique"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = get_object_or_404(TRPGSession, id=session_id_int)
        if not session_permissions.can_edit_session_basic(request.user, session):
            return Response(
                {"error": "Only GM can reorder images"},
                status=status.HTTP_403_FORBIDDEN,
            )

        existing_ids = list(SessionImage.objects.filter(session_id=session_id_int).values_list("id", flat=True))
        if set(existing_ids) != set(ordered_ids_int):
            return Response(
                {"error": "ordered_ids must include all images in the session"},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            images = list(
                SessionImage.objects.select_for_update().filter(
                    session_id=session_id_int,
                    id__in=ordered_ids_int,
                )
            )
            if len(images) != len(ordered_ids_int):
                return Response(
                    {"error": "Some images not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            images_by_id = {image.id: image for image in images}
            for index, image_id in enumerate(ordered_ids_int):
                images_by_id[image_id].order = index + 1

            SessionImage.objects.bulk_update(images, ["order"])

        return Response({"status": "success"})


class SessionYouTubeLinkViewSet(viewsets.ModelViewSet):
    queryset = SessionYouTubeLink.objects.none()
    """セッションYouTube動画リンク管理ViewSet"""
    serializer_class = SessionYouTubeLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """クエリセット取得"""
        user = self.request.user

        # session_id が指定されている場合
        session_id = self.kwargs.get("session_id")
        if session_id:
            # セッションへのアクセス権限確認
            session = get_object_or_404(TRPGSession, id=session_id)
            if session_permissions.can_edit_session_basic(user, session) or session.participants.filter(id=user.id).exists():
                return SessionYouTubeLink.objects.filter(session_id=session_id)
            else:
                return SessionYouTubeLink.objects.none()

        # 通常のクエリ
        return SessionYouTubeLink.objects.filter(Q(session__gm=user) | Q(session__participants=user)).distinct()

    def create(self, request, *args, **kwargs):
        """YouTube動画リンクの追加"""
        session_id = self.kwargs.get("session_id")
        if not session_id:
            session_id = request.data.get("session")

        if not session_id:
            return Response({"error": "session is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        # 権限チェック
        if (
            not session_permissions.can_edit_session_basic(request.user, session)
            and not session.participants.filter(id=request.user.id).exists()
        ):
            return Response(
                {"error": "Only GM or participants can add YouTube links"}, status=status.HTTP_403_FORBIDDEN
            )

        # YouTube URLから動画情報を取得
        youtube_url = request.data.get("youtube_url")
        if not youtube_url:
            return Response({"error": "youtube_url is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 動画IDの抽出
        video_id = SessionYouTubeLink.extract_video_id(youtube_url)
        if not video_id:
            return Response({"error": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)

        # 重複チェック
        if SessionYouTubeLink.objects.filter(session=session, video_id=video_id).exists():
            return Response(
                {"error": "This video is already linked to the session"}, status=status.HTTP_400_BAD_REQUEST
            )

        # YouTube API から動画情報取得
        video_info = YouTubeService.fetch_video_info(video_id)
        if not video_info:
            return Response({"error": "Could not fetch video information"}, status=status.HTTP_400_BAD_REQUEST)

        # シリアライザーでインスタンス作成
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            session=session,
            added_by=request.user,
            video_id=video_id,
            title=video_info["title"],
            duration_seconds=video_info["duration"],
            channel_name=video_info["channel_name"],
            thumbnail_url=video_info["thumbnail_url"],
        )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        """動画リンク更新時の処理"""
        instance = self.get_object()

        # GMまたは追加者のみ編集可能
        if (
            not session_permissions.can_edit_session_basic(self.request.user, instance.session)
            and instance.added_by != self.request.user
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only GM or the person who added can edit")

        serializer.save()

    def perform_destroy(self, instance):
        """動画リンク削除時の処理"""
        # GMまたは追加者のみ削除可能
        if (
            not session_permissions.can_edit_session_basic(self.request.user, instance.session)
            and instance.added_by != self.request.user
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only GM or the person who added can delete")

        instance.delete()

    @action(detail=False, methods=["post"])
    def fetch_info(self, request):
        """YouTube URLから動画情報を取得"""
        youtube_url = request.data.get("youtube_url")
        if not youtube_url:
            return Response({"error": "youtube_url is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 動画IDの抽出
        video_id = SessionYouTubeLink.extract_video_id(youtube_url)
        if not video_id:
            return Response({"error": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)

        # YouTube API から動画情報取得
        video_info = YouTubeService.fetch_video_info(video_id)
        if not video_info:
            return Response({"error": "Could not fetch video information"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "video_id": video_id,
                "title": video_info["title"],
                "duration_seconds": video_info["duration"],
                "channel_name": video_info["channel_name"],
                "thumbnail_url": video_info["thumbnail_url"],
            }
        )

    @action(detail=True, methods=["post"])
    def reorder(self, request, pk=None):
        """動画リンクの表示順序変更"""
        link = self.get_object()
        new_order = request.data.get("order")

        if new_order is None:
            return Response({"error": "order is required"}, status=status.HTTP_400_BAD_REQUEST)

        # GMのみ順序変更可能
        if not session_permissions.can_edit_session_basic(request.user, link.session):
            return Response({"error": "Only GM can reorder videos"}, status=status.HTTP_403_FORBIDDEN)

        link.order = new_order
        link.save()

        serializer = self.get_serializer(link)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request, session_id=None):
        """セッションの動画統計情報を取得"""
        if not session_id:
            session_id = self.kwargs.get("session_id")
        if not session_id:
            session_id = request.query_params.get("session_id")

        if not session_id:
            return Response({"error": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = TRPGSession.objects.get(id=session_id)
        except TRPGSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        # 権限チェック
        if (
            not session_permissions.can_edit_session_basic(request.user, session)
            and not session.participants.filter(id=request.user.id).exists()
        ):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        # 統計情報取得
        statistics = SessionYouTubeLink.get_session_statistics(session)

        return Response(statistics)


# =====================================================
# 高度なスケジューリング機能（ISSUE-017）
# =====================================================


class SessionSeriesViewSet(viewsets.ModelViewSet):
    queryset = SessionSeries.objects.none()
    """セッションシリーズ/キャンペーン管理ViewSet（ISSUE-017）"""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return SessionSeriesCreateSerializer
        return SessionSeriesSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        output_serializer = SessionSeriesSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        user = self.request.user
        # GMとして作成したシリーズ、または参加グループのシリーズ
        group_ids = GroupMembership.objects.filter(user=user).values_list("group_id", flat=True)
        return (
            SessionSeries.objects.filter(Q(gm=user) | Q(group_id__in=group_ids))
            .select_related("gm", "group", "scenario")
            .distinct()
        )

    @action(detail=True, methods=["post"])
    def generate_sessions(self, request, pk=None):
        """定期セッションを生成"""
        series = self.get_object()

        if series.gm != request.user:
            raise PermissionDenied("シリーズのGMのみが生成できます")

        try:
            count = int(request.data.get("count", 4))
        except (TypeError, ValueError):
            raise ValidationError({"count": "count must be an integer"})
        if count <= 0:
            raise ValidationError({"count": "count must be positive"})
        dates = series.get_next_session_dates(count=count)

        created_sessions = []
        existing_dates = set(series.sessions.values_list("date__date", flat=True))

        for d in dates:
            if d not in existing_dates:
                session = series.create_session_for_date(d)
                created_sessions.append(
                    {
                        "id": session.id,
                        "title": session.title,
                        "date": session.date.isoformat(),
                    }
                )

        return Response(
            {
                "created_count": len(created_sessions),
                "sessions": created_sessions,
            }
        )

    @action(detail=True, methods=["get"])
    def sessions(self, request, pk=None):
        """シリーズに属するセッション一覧"""
        series = self.get_object()
        sessions = series.sessions.order_by("date")
        serializer = SessionListSerializer(sessions, many=True, context={"request": request})
        return Response(serializer.data)


class SessionAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = SessionAvailability.objects.none()
    """参加可能日投票ViewSet（ISSUE-017）"""

    serializer_class = SessionAvailabilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SessionAvailability.objects.filter(user=user).select_related("session", "occurrence", "user")

    @action(detail=False, methods=["get"])
    def for_session(self, request):
        """セッションの投票一覧"""
        session_id = request.query_params.get("session_id")
        if not session_id:
            raise ValidationError({"session_id": "session_id is required"})

        session = get_object_or_404(_visible_sessions_for(request.user), id=session_id)
        votes = SessionAvailability.objects.filter(session=session).select_related("user")
        serializer = self.get_serializer(votes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def vote(self, request):
        """投票する/更新する"""
        session_id = request.data.get("session_id")
        occurrence_id = request.data.get("occurrence_id")
        vote_status = request.data.get("status", "available")
        comment = request.data.get("comment", "")

        if session_id:
            get_object_or_404(_visible_sessions_for(request.user), id=session_id)
            vote, created = SessionAvailability.objects.update_or_create(
                session_id=session_id, user=request.user, defaults={"status": vote_status, "comment": comment}
            )
        elif occurrence_id:
            visible_session_ids = _visible_sessions_for(request.user).values_list("id", flat=True)
            get_object_or_404(SessionOccurrence, id=occurrence_id, session_id__in=visible_session_ids)
            vote, created = SessionAvailability.objects.update_or_create(
                occurrence_id=occurrence_id, user=request.user, defaults={"status": vote_status, "comment": comment}
            )
        else:
            raise ValidationError({"error": "session_id or occurrence_id is required"})

        serializer = self.get_serializer(vote)
        return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)


class DatePollViewSet(viewsets.ModelViewSet):
    queryset = DatePoll.objects.none()
    """日程調整ViewSet（ISSUE-017）"""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return DatePollCreateSerializer
        return DatePollSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        output_serializer = DatePollSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        if self.get_object().created_by_id != request.user.id:
            return Response(
                {"detail": "Only the poll owner can update it."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().created_by_id != request.user.id:
            return Response(
                {"detail": "Only the poll owner can delete it."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        group_ids = GroupMembership.objects.filter(user=user).values_list("group_id", flat=True)
        shared_poll_ids = (
            GroupLinkShare.objects.filter(
                resource_type=GroupLinkShare.ResourceType.DATE_POLL,
                link__status=GroupLink.Status.ACCEPTED,
            )
            .filter(
                Q(owner_group_id=F("link__source_group_id"), link__target_group_id__in=group_ids)
                | Q(owner_group_id=F("link__target_group_id"), link__source_group_id__in=group_ids)
            )
            .values_list("object_id", flat=True)
        )
        queryset = (
            DatePoll.objects.filter(Q(created_by=user) | Q(group_id__in=group_ids) | Q(id__in=shared_poll_ids))
            .select_related("created_by", "group", "session")
            .prefetch_related("options__votes__user")
            .distinct()
        )

        session_id = self.request.query_params.get("session_id")
        if session_id:
            try:
                session_id = int(session_id)
            except (TypeError, ValueError):
                raise ValidationError({"session_id": "session_id must be an integer"})
            queryset = queryset.filter(session_id=session_id)

        is_closed_param = self.request.query_params.get("is_closed")
        if is_closed_param is not None:
            is_closed_str = str(is_closed_param).strip().lower()
            if is_closed_str in ("true", "1", "yes"):
                queryset = queryset.filter(is_closed=True)
            elif is_closed_str in ("false", "0", "no"):
                queryset = queryset.filter(is_closed=False)
            else:
                raise ValidationError({"is_closed": "is_closed must be a boolean"})

        return queryset

    @action(detail=True, methods=["post"])
    def vote(self, request, pk=None):
        """日程調整に投票"""
        poll = self.get_object()

        if poll.is_closed:
            raise ValidationError({"error": "投票は締め切られています"})

        votes_data = request.data.get("votes", [])
        if not votes_data:
            raise ValidationError({"votes": "投票データが必要です"})

        results = []
        for vote_data in votes_data:
            option_id = vote_data.get("option_id")
            vote_status = vote_data.get("status", "available")
            comment = vote_data.get("comment", "")

            try:
                option = poll.options.get(id=option_id)
            except DatePollOption.DoesNotExist:
                continue

            vote, _ = DatePollVote.objects.update_or_create(
                option=option, user=request.user, defaults={"status": vote_status, "comment": comment}
            )
            results.append(DatePollVoteSerializer(vote).data)

        return Response({"votes": results})

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """日程を確定"""
        poll = self.get_object()

        if poll.created_by != request.user:
            raise PermissionDenied("作成者のみが確定できます")

        if poll.is_closed:
            raise ValidationError({"error": "投票は締め切られています"})

        option_id = request.data.get("option_id")
        if not option_id:
            raise ValidationError({"option_id": "確定する候補日を指定してください"})

        try:
            option = poll.options.get(id=option_id)
        except DatePollOption.DoesNotExist:
            raise ValidationError({"option_id": "候補日が見つかりません"})

        session = poll.confirm_date(option)

        serializer = self.get_serializer(poll)
        response_data = serializer.data
        if session:
            response_data["created_session"] = {
                "id": session.id,
                "title": session.title,
                "date": session.date.isoformat() if session.date else None,
            }

        return Response(response_data)

    @action(detail=True, methods=["post"])
    def add_option(self, request, pk=None):
        """候補日を追加"""
        poll = self.get_object()

        if poll.is_closed:
            raise ValidationError({"error": "投票は締め切られています"})

        datetime_str = request.data.get("datetime")
        note = request.data.get("note", "")

        if not datetime_str:
            raise ValidationError({"datetime": "日時を指定してください"})

        from django.utils.dateparse import parse_datetime

        parsed_datetime = parse_datetime(datetime_str)
        if parsed_datetime is None:
            raise ValidationError({"datetime": "Invalid datetime format"})
        if timezone.is_naive(parsed_datetime):
            parsed_datetime = timezone.make_aware(parsed_datetime, timezone.get_current_timezone())

        option = DatePollOption.objects.create(
            poll=poll,
            datetime=parsed_datetime,
            note=note,
        )

        return Response(DatePollOptionSerializer(option).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """投票サマリーを取得"""
        poll = self.get_object()
        options = poll.get_vote_summary()

        result = []
        for opt in options:
            result.append(
                {
                    "id": opt.id,
                    "datetime": opt.datetime.isoformat(),
                    "note": opt.note,
                    "available_count": opt.available_count,
                    "maybe_count": opt.maybe_count,
                    "unavailable_count": opt.unavailable_count,
                }
            )

        return Response(
            {
                "poll_id": poll.id,
                "title": poll.title,
                "is_closed": poll.is_closed,
                "selected_date": poll.selected_date.isoformat() if poll.selected_date else None,
                "options": result,
            }
        )

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        """日程調整のコメント（チャット）一覧/投稿"""
        poll = self.get_object()

        if request.method == "GET":
            limit_param = request.query_params.get("limit", 200)
            try:
                limit = int(limit_param)
            except (TypeError, ValueError):
                raise ValidationError({"limit": "limit must be an integer"})

            limit = max(1, min(limit, 500))
            qs = poll.comments.select_related("user").order_by("-created_at", "-id")[:limit]
            comments = list(qs)[::-1]
            return Response(DatePollCommentSerializer(comments, many=True).data)

        content = (request.data.get("content") or "").strip()
        if not content:
            raise ValidationError({"content": "コメントを入力してください"})
        if len(content) > 500:
            raise ValidationError({"content": "コメントは500文字以内で入力してください"})

        comment = DatePollComment.objects.create(
            poll=poll,
            user=request.user,
            content=content,
        )
        return Response(DatePollCommentSerializer(comment).data, status=status.HTTP_201_CREATED)
