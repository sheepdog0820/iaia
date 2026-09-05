import hashlib
from datetime import timedelta
from urllib.parse import urlencode

import requests
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CharacterSheet

from .google_sheets import SHEET_COLUMNS, SHEETS_DEFAULT_START_RANGE
from .google_tokens import get_google_access_token
from .integration_access import visible_user_sessions as _visible_user_sessions
from .models import (
    AsyncJob,
    CalendarSubscription,
    GoogleCalendarSync,
    GoogleIntegration,
    SessionOccurrence,
    SessionParticipantRole,
)
from .tasks import queue_google_calendar_sync, queue_google_sheet_export

GOOGLE_INTEGRATION_SCOPES = [
    GoogleIntegration.REQUIRED_CALENDAR_SCOPE,
    GoogleIntegration.REQUIRED_SHEETS_SCOPE,
]


def _escape_ical(value):
    return str(value or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def _gm_role_session_ids_for(user):
    return set(
        SessionParticipantRole.objects.filter(
            participant__user=user,
            role=SessionParticipantRole.Role.GM,
        ).values_list("participant__session_id", flat=True)
    )


def _build_ical(user):
    now = timezone.now()
    end = now + timedelta(days=90)
    sessions = (
        _visible_user_sessions(user)
        .filter(Q(date__range=(now, end)) | Q(date__isnull=True))
        .select_related("gm", "group")
        .order_by("date", "id")
    )
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Tableno//Subscription Calendar//JP",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Tableno - {_escape_ical(user.nickname or user.username)}",
    ]
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    gm_role_session_ids = _gm_role_session_ids_for(user)
    for session in sessions:
        role = "GM" if session.id in gm_role_session_ids else "Player"
        if session.date is None:
            lines.extend(
                [
                    "BEGIN:VTODO",
                    f"UID:session-{session.pk}@tableno",
                    f"DTSTAMP:{stamp}",
                    f"SUMMARY:[{role}] {_escape_ical(session.title)}",
                    "STATUS:NEEDS-ACTION",
                    f"DESCRIPTION:{_escape_ical(session.description)}",
                    "END:VTODO",
                ]
            )
            continue
        end_at = session.date + timedelta(minutes=session.duration_minutes or 180)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:session-{session.pk}@tableno",
                f"DTSTAMP:{stamp}",
                f'DTSTART:{session.date.strftime("%Y%m%dT%H%M%SZ")}',
                f'DTEND:{end_at.strftime("%Y%m%dT%H%M%SZ")}',
                f"SUMMARY:[{role}] {_escape_ical(session.title)}",
                f"DESCRIPTION:{_escape_ical(session.description)}",
                f"LOCATION:{_escape_ical(session.location)}",
                "STATUS:CANCELLED" if session.status == "cancelled" else "STATUS:CONFIRMED",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


class CalendarSubscriptionRotateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _, token = CalendarSubscription.issue_for(request.user)
        path = reverse("calendar-subscription", kwargs={"token": token})
        return Response(
            {
                "token": token,
                "subscription_url": request.build_absolute_uri(path),
            }
        )


class CalendarSubscriptionView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        digest = CalendarSubscription.digest(token)
        subscription = CalendarSubscription.objects.select_related("user").filter(token_digest=digest).first()
        if not subscription:
            raise Http404
        response = HttpResponse(
            _build_ical(subscription.user),
            content_type="text/calendar; charset=utf-8",
        )
        response["Content-Disposition"] = 'inline; filename="tableno.ics"'
        response["Cache-Control"] = "private, no-store"
        return response


def _authorized_google_scopes(user):
    account = SocialAccount.objects.filter(user=user, provider="google").first()
    if not account or not SocialToken.objects.filter(account=account).exists():
        return set()
    raw = account.extra_data.get("scope", [])
    if isinstance(raw, str):
        return set(raw.split())
    return set(raw)


def _google_reconnect_url():
    query = urlencode(
        {
            "process": "connect",
            "scope": ",".join(GOOGLE_INTEGRATION_SCOPES),
        }
    )
    return f"/accounts/google/login/?{query}"


class GoogleIntegrationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        integration = GoogleIntegration.objects.filter(user=request.user).first()
        return Response(
            {
                "connected": bool(integration),
                "calendar_enabled": bool(integration and integration.calendar_enabled),
                "sheets_enabled": bool(integration and integration.sheets_enabled),
                "scopes": integration.scopes if integration else [],
                "reconnect_url": _google_reconnect_url(),
            }
        )

    def put(self, request):
        scopes = _authorized_google_scopes(request.user)
        calendar_enabled = bool(request.data.get("calendar_enabled"))
        sheets_enabled = bool(request.data.get("sheets_enabled"))
        errors = {}
        if calendar_enabled and GoogleIntegration.REQUIRED_CALENDAR_SCOPE not in scopes:
            errors["calendar_enabled"] = "Reconnect Google with Calendar permission."
        if sheets_enabled and GoogleIntegration.REQUIRED_SHEETS_SCOPE not in scopes:
            errors["sheets_enabled"] = "Reconnect Google with Sheets permission."
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        integration, _ = GoogleIntegration.objects.update_or_create(
            user=request.user,
            defaults={
                "scopes": sorted(scopes),
                "calendar_enabled": calendar_enabled,
                "sheets_enabled": sheets_enabled,
                "connected_at": timezone.now(),
            },
        )
        return Response(
            {
                "connected": True,
                "calendar_enabled": integration.calendar_enabled,
                "sheets_enabled": integration.sheets_enabled,
                "scopes": integration.scopes,
            }
        )


class GoogleCalendarSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = _visible_user_sessions(request.user).filter(pk=session_id).first()
        if not session:
            raise Http404
        integration = GoogleIntegration.objects.filter(
            user=request.user,
            calendar_enabled=True,
        ).first()
        if not integration or not integration.has_scope(GoogleIntegration.REQUIRED_CALENDAR_SCOPE):
            return Response(
                {"detail": "Google Calendar is not connected."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sync, _ = GoogleCalendarSync.objects.update_or_create(
            user=request.user,
            session=session,
            defaults={"status": GoogleCalendarSync.Status.PENDING, "last_error": ""},
        )
        job = AsyncJob.objects.create(
            owner=request.user,
            job_type="google_calendar_sync",
            payload={"sync_id": sync.pk},
            expires_at=timezone.now() + timedelta(days=7),
        )
        queued = queue_google_calendar_sync(sync.pk, str(job.pk))
        if not queued:
            job.mark_failed("Background task broker is unavailable.")
            sync.status = GoogleCalendarSync.Status.FAILED
            sync.last_error = "Background task broker is unavailable."
            sync.save(update_fields=["status", "last_error", "updated_at"])
        return Response(
            {
                "job_id": job.pk,
                "sync_status": sync.status,
                "queued": queued,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class GoogleSheetsExportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        integration = GoogleIntegration.objects.filter(user=request.user, sheets_enabled=True).first()
        if not integration or not integration.has_scope(GoogleIntegration.REQUIRED_SHEETS_SCOPE):
            return Response(
                {"detail": "Google Sheets is not connected."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        characters = CharacterSheet.objects.filter(user=request.user)
        if request.data.get("character_ids"):
            characters = characters.filter(pk__in=request.data["character_ids"])
        rows = []
        for character in characters.order_by("id"):
            detail = character.system_data
            rows.append(
                [
                    character.pk,
                    detail.name,
                    character.edition,
                    detail.age,
                    detail.occupation,
                    detail.str_value,
                    detail.con_value,
                    detail.pow_value,
                    detail.dex_value,
                    detail.app_value,
                    detail.siz_value,
                    detail.int_value,
                    detail.edu_value,
                    detail.hit_points_current,
                    detail.magic_points_current,
                    detail.sanity_current,
                    detail.luck_current if character.edition == "7th" else "",
                ]
            )
        spreadsheet_id = request.data.get("spreadsheet_id")
        if not spreadsheet_id:
            return Response({"columns": SHEET_COLUMNS, "rows": rows})
        job = AsyncJob.objects.create(
            owner=request.user,
            job_type="google_sheets_export",
            payload={
                "spreadsheet_id": spreadsheet_id,
                "range": request.data.get("range", SHEETS_DEFAULT_START_RANGE),
                "character_ids": request.data.get("character_ids", []),
            },
            expires_at=timezone.now() + timedelta(days=7),
        )
        values = [SHEET_COLUMNS] + rows
        queued = queue_google_sheet_export(
            str(job.pk),
            request.user.pk,
            spreadsheet_id,
            request.data.get("range", SHEETS_DEFAULT_START_RANGE),
            values,
        )
        if not queued:
            job.mark_failed("Background task broker is unavailable.")
        return Response(
            {"job_id": job.pk, "queued": queued},
            status=status.HTTP_202_ACCEPTED,
        )
