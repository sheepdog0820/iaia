from datetime import timedelta
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import session_permissions
from .models import SessionParticipant, SessionRecruitmentLink, TRPGSession
from .recruitment import (
    RecruitmentLinkInactive,
    RecruitmentLinkNotFound,
    get_recruitment_link,
    join_recruitment_link,
)


def _serialize_recruitment_link(recruitment_link):
    return {
        "id": recruitment_link.pk,
        "expires_at": recruitment_link.expires_at,
        "max_uses": recruitment_link.max_uses,
        "use_count": recruitment_link.use_count,
        "revoked_at": recruitment_link.revoked_at,
        "is_active": recruitment_link.is_active,
        "created_at": recruitment_link.created_at,
    }


def _bounded_integer(data, field_name, *, default, minimum, maximum):
    raw_value = data.get(field_name, default)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer.") from None
    if value < minimum or value > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}.")
    return value


class SessionRecruitmentLinkListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_session(self, request, session_id):
        session = get_object_or_404(TRPGSession, pk=session_id)
        if not session_permissions.can_manage_participants(request.user, session):
            self.permission_denied(request)
        return session

    def get(self, request, session_id):
        session = self._get_session(request, session_id)
        links = session.recruitment_links.select_related("created_by").all()
        return Response([_serialize_recruitment_link(link) for link in links])

    def post(self, request, session_id):
        session = self._get_session(request, session_id)
        try:
            expires_in_hours = _bounded_integer(
                request.data,
                "expires_in_hours",
                default=168,
                minimum=1,
                maximum=720,
            )
            max_uses = _bounded_integer(
                request.data,
                "max_uses",
                default=1,
                minimum=1,
                maximum=1000,
            )
        except ValueError as exc:
            field_name = str(exc).split(" ", 1)[0]
            return Response(
                {field_name: str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recruitment_link, token = SessionRecruitmentLink.issue(
            session=session,
            created_by=request.user,
            expires_at=timezone.now() + timedelta(hours=expires_in_hours),
            max_uses=max_uses,
        )
        path = reverse("session-recruitment-landing", kwargs={"token": token})
        response_data = _serialize_recruitment_link(recruitment_link)
        response_data["recruitment_url"] = request.build_absolute_uri(path)
        return Response(response_data, status=status.HTTP_201_CREATED)


class SessionRecruitmentLinkRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id, link_id):
        recruitment_link = get_object_or_404(
            SessionRecruitmentLink.objects.select_related("session"),
            pk=link_id,
            session_id=session_id,
        )
        if not session_permissions.can_manage_participants(request.user, recruitment_link.session):
            self.permission_denied(request)
        if recruitment_link.revoked_at is None:
            recruitment_link.revoked_at = timezone.now()
            recruitment_link.save(update_fields=["revoked_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionRecruitmentJoinAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, token):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            result = join_recruitment_link(token=token, user=request.user)
        except RecruitmentLinkNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except RecruitmentLinkInactive:
            return Response(
                {"detail": "Recruitment link is expired, revoked, or fully used."},
                status=status.HTTP_410_GONE,
            )
        return Response(
            {
                "participant_id": result.participant.pk,
                "session_id": result.participant.session_id,
                "already_joined": result.already_joined,
            },
            status=status.HTTP_200_OK if result.already_joined else status.HTTP_201_CREATED,
        )


def _inactive_landing(request, *, invalid=False):
    return render(
        request,
        "schedules/session_recruitment.html",
        {"invalid": invalid, "inactive": not invalid},
        status=status.HTTP_404_NOT_FOUND if invalid else status.HTTP_410_GONE,
    )


def _success_context(recruitment_link, *, already_joined, participant):
    return {
        "recruitment_link": recruitment_link,
        "session": recruitment_link.session,
        "participant": participant,
        "already_joined": already_joined,
        "joined": not already_joined,
        "session_detail_url": reverse(
            "session_detail",
            kwargs={"pk": recruitment_link.session_id},
        ),
    }


class SessionRecruitmentLandingView(View):
    def get(self, request, token):
        recruitment_link = get_recruitment_link(token)
        if recruitment_link is None:
            return _inactive_landing(request, invalid=True)

        if request.user.is_authenticated:
            participant = SessionParticipant.objects.filter(
                session=recruitment_link.session,
                user=request.user,
            ).first()
            if participant:
                return render(
                    request,
                    "schedules/session_recruitment.html",
                    _success_context(
                        recruitment_link,
                        already_joined=True,
                        participant=participant,
                    ),
                )

        if not recruitment_link.is_active:
            return _inactive_landing(request)

        landing_path = reverse("session-recruitment-landing", kwargs={"token": token})
        context = {
            "recruitment_link": recruitment_link,
            "session": recruitment_link.session,
            "token": token,
            "login_url": f"{reverse('account_login')}?{urlencode({'next': landing_path})}",
            "signup_url": f"{reverse('account_signup')}?{urlencode({'next': landing_path})}",
            "auto_join": request.user.is_authenticated,
        }
        return render(request, "schedules/session_recruitment.html", context)


class SessionRecruitmentJoinView(View):
    def post(self, request, token):
        if not request.user.is_authenticated:
            landing_path = reverse("session-recruitment-landing", kwargs={"token": token})
            login_url = f"{reverse('account_login')}?{urlencode({'next': landing_path})}"
            return redirect(login_url)
        try:
            result = join_recruitment_link(token=token, user=request.user)
        except RecruitmentLinkNotFound:
            return _inactive_landing(request, invalid=True)
        except RecruitmentLinkInactive:
            return _inactive_landing(request)

        return render(
            request,
            "schedules/session_recruitment.html",
            _success_context(
                result.recruitment_link,
                already_joined=result.already_joined,
                participant=result.participant,
            ),
        )
