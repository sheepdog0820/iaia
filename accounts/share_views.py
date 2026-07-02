import json
import mimetypes
import os
import uuid

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.character_detail_context import build_character_detail_context
from accounts.character_image_utils import get_character_preview_image_field
from accounts.character_models import CharacterSheet
from accounts.models import GroupMembership, ShareLink
from accounts.serializers import CharacterImageSerializer
from accounts.share_serializers import (
    FixedShareUrlIssueSerializer,
    SharedCharacterSheetSerializer,
    SharedScenarioSerializer,
    SharedSessionSerializer,
    SharedStatsSerializer,
    ShareLinkIssueSerializer,
    ShareLinkSerializer,
)
from accounts.views.character_image_views import build_character_images_zip_response
from scenarios.models import Scenario
from schedules.models import DatePoll, HandoutInfo, SessionParticipant, TRPGSession

SHARED_API_NAMES = {
    ShareLink.ResourceType.CHARACTER: "shared-character-detail",
    ShareLink.ResourceType.SESSION: "shared-session-detail",
    ShareLink.ResourceType.SCENARIO: "shared-scenario-detail",
    ShareLink.ResourceType.PROFILE_STATS: "shared-stats-detail",
}

FIXED_SHARED_VIEW_NAMES = {
    ShareLink.ResourceType.CHARACTER: "fixed-shared-character-view",
    ShareLink.ResourceType.SESSION: "fixed-shared-session-view",
    ShareLink.ResourceType.SCENARIO: "fixed-shared-scenario-view",
}


def _can_manage_session(session, user):
    if not user or not user.is_authenticated:
        return False
    if session.gm_id == user.id:
        return True
    if getattr(session, "created_by_id", None) == user.id:
        return True
    if session.group_id:
        if session.group.created_by_id == user.id:
            return True
        if GroupMembership.objects.filter(
            group_id=session.group_id,
            user=user,
            role="admin",
        ).exists():
            return True
    return SessionParticipant.objects.filter(
        session=session,
        user=user,
        role="gm",
    ).exists()


def _build_share_url(request, resource_type, token):
    return request.build_absolute_uri(reverse(SHARED_API_NAMES[resource_type], kwargs={"token": token}))


def _build_fixed_share_url(request, resource_type, share_token):
    return request.build_absolute_uri(
        reverse(FIXED_SHARED_VIEW_NAMES[resource_type], kwargs={"share_token": share_token})
    )


def _require_shareable_resource(resource_type, object_id, user):
    if resource_type == ShareLink.ResourceType.SESSION:
        session = get_object_or_404(TRPGSession, pk=object_id)
        if not _can_manage_session(session, user):
            raise Http404("Session not found")
        if session.visibility not in ("link", "public"):
            raise ValueError("Session visibility must be link or public before issuing a share URL.")
        return session

    if resource_type == ShareLink.ResourceType.CHARACTER:
        character = get_object_or_404(CharacterSheet, pk=object_id)
        if character.user_id != user.id:
            raise Http404("Character sheet not found")
        if character.access_scope not in ("link", "public"):
            raise ValueError("Character access_scope must be link or public before issuing a share URL.")
        return character

    if resource_type == ShareLink.ResourceType.SCENARIO:
        scenario = get_object_or_404(Scenario, pk=object_id)
        if scenario.created_by_id != user.id:
            raise Http404("Scenario not found")
        if scenario.visibility not in ("link", "public"):
            raise ValueError("Scenario visibility must be link or public before issuing a share URL.")
        return scenario

    if resource_type == ShareLink.ResourceType.PROFILE_STATS:
        session = get_object_or_404(TRPGSession, pk=object_id)
        if not _can_manage_session(session, user):
            raise Http404("Session not found")
        if session.visibility not in ("link", "public"):
            raise ValueError("Session visibility must be link or public before issuing stats share URL.")
        return session

    raise Http404("Unsupported resource type")


def _require_fixed_share_resource(resource_type, object_id, user, *, auto_enable_link=False):
    if resource_type == ShareLink.ResourceType.SESSION:
        session = get_object_or_404(TRPGSession, pk=object_id)
        if not _can_manage_session(session, user):
            raise Http404("Session not found")
        if session.visibility not in ("link", "public"):
            if not auto_enable_link:
                raise ValueError("Session visibility must be link or public before copying a share URL.")
            session.visibility = "link"
            session.save(update_fields=["visibility", "updated_at"])
        return session

    if resource_type == ShareLink.ResourceType.CHARACTER:
        character = get_object_or_404(CharacterSheet, pk=object_id)
        if character.user_id != user.id:
            raise Http404("Character sheet not found")
        if character.access_scope not in ("link", "public"):
            if not auto_enable_link:
                raise ValueError("Character access_scope must be link or public before copying a share URL.")
            character.access_scope = "link"
            character.save(update_fields=["access_scope", "updated_at"])
        return character

    if resource_type == ShareLink.ResourceType.SCENARIO:
        scenario = get_object_or_404(Scenario, pk=object_id)
        if scenario.created_by_id != user.id:
            raise Http404("Scenario not found")
        if scenario.visibility not in ("link", "public"):
            if not auto_enable_link:
                raise ValueError("Scenario visibility must be link or public before copying a share URL.")
            scenario.visibility = "link"
            scenario.save(update_fields=["visibility", "updated_at"])
        return scenario

    raise Http404("Unsupported resource type")


def _active_share_or_404(token, resource_type, request):
    share_link = ShareLink.active_for_token(token, resource_type)
    if share_link is None:
        raise Http404("Share link not found")
    if not share_link.allow_anonymous and not request.user.is_authenticated:
        raise Http404("Share link not found")
    return share_link


def _active_share_or_none(token, resource_type, request):
    share_link = ShareLink.active_for_token(token, resource_type)
    if share_link is None:
        return None
    if not share_link.allow_anonymous and not request.user.is_authenticated:
        raise Http404("Share link not found")
    return share_link


def _uuid_token_or_404(token):
    try:
        return uuid.UUID(str(token))
    except (TypeError, ValueError, AttributeError):
        raise Http404("Share link not found")


def _get_selected_occurrence_from_request(request, occurrences):
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


def _build_session_detail_context(request, session, *, is_public_view):
    participants = SessionParticipant.objects.filter(session=session).select_related("user", "character_sheet")
    _attach_participant_character_share_urls(request, participants)

    guest_count = participants.filter(user__isnull=True).count()
    occurrences = session.occurrences.prefetch_related("participants").order_by("start_at", "id")
    selected_occurrence, selected_occurrence_id = _get_selected_occurrence_from_request(
        request,
        occurrences,
    )
    public_session_url = request.build_absolute_uri(
        reverse("fixed-shared-session-view", kwargs={"share_token": session.share_token})
    )

    if is_public_view:
        return {
            "session": session,
            "participants": participants,
            "occurrences": occurrences,
            "handouts": HandoutInfo.objects.none(),
            "is_gm": False,
            "is_co_gm": False,
            "is_session_manager": False,
            "is_participant": False,
            "can_edit": False,
            "can_invite": False,
            "can_join": False,
            "user_participant": None,
            "public_session_url": public_session_url,
            "is_public_view": True,
            "is_shared_view": True,
            "guest_count": guest_count,
            "selected_occurrence": selected_occurrence,
            "selected_occurrence_id": selected_occurrence_id,
            "can_edit_scenario": False,
            "scenario_choices": [],
            "invitation_status_by_user_id_json": "{}",
            "open_date_poll": None,
        }

    user = request.user
    user_participant = participants.filter(user=user).first()
    is_gm = session.gm == user
    is_co_gm = participants.filter(user=user, role="gm").exists()
    is_session_manager = _can_manage_session(session, user)
    is_participant = participants.filter(user=user).exists()

    if is_gm:
        handouts = HandoutInfo.objects.filter(session=session).select_related("participant__user")
    elif user_participant:
        handouts = HandoutInfo.objects.filter(participant=user_participant)
    else:
        handouts = HandoutInfo.objects.none()

    open_date_poll = DatePoll.objects.filter(session=session, is_closed=False).first()
    invitation_status_by_user_id = {}
    for invitation in session.invitations.exclude(status="accepted"):
        status_value = "expired" if invitation.is_expired else invitation.status
        invitation_status_by_user_id[str(invitation.invitee_id)] = status_value

    can_edit_scenario = is_session_manager and getattr(user, "has_premium_access", False)
    scenario_choices = []
    if can_edit_scenario:
        from scenarios.access import visible_scenarios

        scenario_choices = visible_scenarios(
            Scenario.objects.all(),
            user,
        ).order_by("title", "id")

    return {
        "session": session,
        "participants": participants,
        "occurrences": occurrences,
        "handouts": handouts,
        "is_gm": is_gm,
        "is_co_gm": is_co_gm,
        "is_session_manager": is_session_manager,
        "is_participant": is_participant,
        "can_edit": is_session_manager,
        "can_invite": is_session_manager,
        "can_join": False,
        "user_participant": user_participant,
        "public_session_url": public_session_url,
        "is_public_view": False,
        "is_shared_view": True,
        "guest_count": guest_count,
        "open_date_poll": open_date_poll,
        "invitation_status_by_user_id_json": json.dumps(invitation_status_by_user_id),
        "selected_occurrence": selected_occurrence,
        "selected_occurrence_id": selected_occurrence_id,
        "can_edit_scenario": can_edit_scenario,
        "scenario_choices": scenario_choices,
    }


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
            _require_shareable_resource(data["resource_type"], data["object_id"], request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        share_link, token = ShareLink.issue(
            resource_type=data["resource_type"],
            object_id=data["object_id"],
            created_by=request.user,
            expires_at=data.get("expires_at"),
            allow_anonymous=data.get("allow_anonymous", True),
            view_level=data.get("view_level", ShareLink.ViewLevel.STANDARD),
        )
        response_data = ShareLinkSerializer(share_link).data
        response_data["token"] = token
        response_data["share_url"] = _build_share_url(request, share_link.resource_type, token)
        return Response(response_data, status=status.HTTP_201_CREATED)


class FixedShareUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FixedShareUrlIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            resource = _require_fixed_share_resource(
                data["resource_type"],
                data["object_id"],
                request.user,
                auto_enable_link=data.get("auto_enable_link", False),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        share_url = _build_fixed_share_url(request, data["resource_type"], resource.share_token)
        return Response(
            {
                "resource_type": data["resource_type"],
                "share_token": str(resource.share_token),
                "share_url": share_url,
            }
        )


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
        response_data["token"] = token
        response_data["share_url"] = _build_share_url(request, share_link.resource_type, token)
        return Response(response_data)


class SharedSessionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        share_link = _active_share_or_none(token, ShareLink.ResourceType.SESSION, request)
        queryset = TRPGSession.objects.select_related("gm", "scenario")
        if share_link:
            session = get_object_or_404(
                queryset,
                pk=share_link.object_id,
                visibility__in=("link", "public"),
            )
        else:
            session = get_object_or_404(
                queryset,
                share_token=_uuid_token_or_404(token),
                visibility__in=("link", "public"),
            )
        return Response(SharedSessionSerializer(session, context={"request": request}).data)


def _shared_character_or_404(token, request):
    share_link = _active_share_or_none(token, ShareLink.ResourceType.CHARACTER, request)
    queryset = CharacterSheet.objects.prefetch_related("skills", "equipment", "images")
    if share_link:
        return get_object_or_404(
            queryset,
            pk=share_link.object_id,
            access_scope__in=("link", "public"),
        )
    return get_object_or_404(
        queryset,
        share_token=_uuid_token_or_404(token),
        access_scope__in=("link", "public"),
    )


class SharedCharacterDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        share_link = _active_share_or_none(token, ShareLink.ResourceType.CHARACTER, request)
        queryset = CharacterSheet.objects.prefetch_related("skills", "equipment")
        if share_link:
            character = get_object_or_404(
                queryset,
                pk=share_link.object_id,
                access_scope__in=("link", "public"),
            )
        else:
            character = get_object_or_404(
                queryset,
                share_token=_uuid_token_or_404(token),
                access_scope__in=("link", "public"),
            )
        return Response(SharedCharacterSheetSerializer(character, context={"request": request}).data)


class SharedCharacterImagesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        character = _shared_character_or_404(token, request)
        images = character.images.order_by("order", "uploaded_at", "id")
        serializer = CharacterImageSerializer(images, many=True, context={"request": request})
        return Response({"count": images.count(), "results": serializer.data})


class SharedCharacterImagesZipView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        character = _shared_character_or_404(token, request)
        return build_character_images_zip_response(character)


class SharedCharacterPreviewImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        character = _shared_character_or_404(token, request)
        image_field = get_character_preview_image_field(character)
        if not image_field:
            raise Http404("Character preview image not found")

        try:
            image_file = image_field.open("rb")
        except (FileNotFoundError, ValueError, OSError):
            raise Http404("Character preview image not found")

        content_type = mimetypes.guess_type(image_field.name)[0] or "application/octet-stream"
        _, extension = os.path.splitext(image_field.name)
        response = FileResponse(
            image_file,
            as_attachment=False,
            content_type=content_type,
            filename=f"character-image{extension.lower()}",
        )
        response["Cache-Control"] = "private, max-age=300"
        return response


class SharedCharacterCcfoliaJsonView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        character = _shared_character_or_404(token, request)
        return Response(character.export_ccfolia_format())


class SharedScenarioDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        share_link = _active_share_or_none(token, ShareLink.ResourceType.SCENARIO, request)
        queryset = Scenario.objects.prefetch_related("handout_templates")
        if share_link:
            scenario = get_object_or_404(
                queryset,
                pk=share_link.object_id,
                visibility__in=("link", "public"),
            )
        else:
            scenario = get_object_or_404(
                queryset,
                share_token=_uuid_token_or_404(token),
                visibility__in=("link", "public"),
            )
        return Response(SharedScenarioSerializer(scenario, context={"request": request}).data)


class SharedStatsDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        share_link = _active_share_or_404(token, ShareLink.ResourceType.PROFILE_STATS, request)
        session = get_object_or_404(
            TRPGSession.objects.prefetch_related("sessionparticipant_set"),
            pk=share_link.object_id,
            visibility__in=("link", "public"),
        )
        return Response(SharedStatsSerializer(session).data)


class FixedSharedCharacterView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, share_token):
        character = get_object_or_404(
            CharacterSheet.objects.select_related(
                "parent_sheet",
                "sixth_edition_data",
                "user",
            ).prefetch_related("skills", "equipment", "images"),
            share_token=share_token,
            access_scope__in=("link", "public"),
        )
        is_owner = request.user.is_authenticated and character.user_id == request.user.id
        shared_api_url = ""
        if not is_owner:
            shared_api_url = reverse(
                "shared-character-detail",
                kwargs={"token": character.share_token},
            )
        images_api_url = reverse(
            "shared-character-images-list",
            kwargs={"token": character.share_token},
        )
        images_zip_url = reverse(
            "shared-character-images-zip",
            kwargs={"token": character.share_token},
        )
        ccfolia_json_url = reverse(
            "shared-character-ccfolia-json",
            kwargs={"token": character.share_token},
        )
        reference_url = reverse(
            "fixed-shared-character-view",
            kwargs={"share_token": character.share_token},
        )
        preview_image_url = ""
        if get_character_preview_image_field(character):
            preview_image_url = request.build_absolute_uri(
                reverse("shared-character-preview-image", kwargs={"token": character.share_token})
            )
        return render(
            request,
            "accounts/character_detail.html",
            build_character_detail_context(
                request,
                character,
                is_public_view=not is_owner,
                is_shared_view=True,
                can_edit_character=is_owner,
                shared_api_url=shared_api_url,
                images_api_url=images_api_url,
                images_zip_url=images_zip_url,
                ccfolia_json_url=ccfolia_json_url,
                reference_url=reference_url,
                preview_image_url=preview_image_url,
            ),
        )


class FixedSharedSessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, share_token):
        session = get_object_or_404(
            TRPGSession.objects.select_related("scenario", "gm", "group"),
            share_token=share_token,
            visibility__in=("link", "public"),
        )
        is_manager = _can_manage_session(session, request.user)
        return render(
            request,
            "schedules/session_detail.html",
            _build_session_detail_context(request, session, is_public_view=not is_manager),
        )


class FixedSharedScenarioView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, share_token):
        scenario = get_object_or_404(
            Scenario.objects.select_related("created_by").prefetch_related("images", "handout_templates"),
            share_token=share_token,
            visibility__in=("link", "public"),
        )
        return render(
            request,
            "scenarios/scenario_public_detail.html",
            {
                "scenario": scenario,
                "images": scenario.images.all(),
                "is_public_view": True,
                "is_shared_view": True,
                "can_edit_scenario": request.user.is_authenticated and scenario.created_by_id == request.user.id,
            },
        )
