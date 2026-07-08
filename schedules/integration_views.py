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

from accounts.models import CharacterSheet, GroupMembership

from .google_tokens import get_google_access_token
from .models import (
    AsyncJob,
    CalendarSubscription,
    GoogleCalendarSync,
    GoogleIntegration,
    SessionParticipantRole,
    SessionOccurrence,
    TRPGSession,
)
from .tasks import queue_google_calendar_sync, queue_google_sheet_export

SHEET_COLUMNS = [
    "id",
    "name",
    "edition",
    "age",
    "occupation",
    "STR",
    "CON",
    "POW",
    "DEX",
    "APP",
    "SIZ",
    "INT",
    "EDU",
    "HP",
    "MP",
    "SAN",
]


GOOGLE_INTEGRATION_SCOPES = [
    GoogleIntegration.REQUIRED_CALENDAR_SCOPE,
    GoogleIntegration.REQUIRED_SHEETS_SCOPE,
]


def _escape_ical(value):
    return str(value or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def _visible_user_sessions(user):
    admin_group_ids = GroupMembership.objects.filter(user=user, role="admin").values_list("group_id", flat=True)
    return TRPGSession.objects.filter(
        Q(created_by=user)
        | Q(group__created_by=user)
        | Q(group_id__in=admin_group_ids)
        | Q(sessionparticipant__user=user)
        | Q(session_permissions__user=user)
    ).distinct()


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


def _read_sheet_rows(user, spreadsheet_id, range_name):
    token = get_google_access_token(user)
    response = requests.get(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()
    values = response.json().get("values", [])
    if not values:
        return []
    headers = values[0]
    return [dict(zip(headers, row)) for row in values[1:]]


def _validate_character_row(row):
    errors = {}
    for key in ["name", "edition", "age", "STR", "CON", "POW", "DEX", "APP", "SIZ", "INT", "EDU"]:
        if row.get(key) in (None, ""):
            errors[key] = "required"
    if row.get("edition") not in {"6th", "7th"}:
        errors["edition"] = "must be 6th or 7th"
    for key in ["age", "STR", "CON", "POW", "DEX", "APP", "SIZ", "INT", "EDU"]:
        try:
            int(row.get(key))
        except (TypeError, ValueError):
            errors[key] = "must be an integer"
    return errors


class GoogleSheetsImportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        integration = GoogleIntegration.objects.filter(user=request.user, sheets_enabled=True).first()
        if not integration or not integration.has_scope(GoogleIntegration.REQUIRED_SHEETS_SCOPE):
            return Response(
                {"detail": "Google Sheets is not connected."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rows = request.data.get("rows")
        if rows is None:
            try:
                rows = _read_sheet_rows(
                    request.user,
                    request.data["spreadsheet_id"],
                    request.data.get("range", "Characters!A:P"),
                )
            except (KeyError, ValueError, requests.RequestException) as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        results = [
            {"row": index + 2, "data": row, "errors": _validate_character_row(row)} for index, row in enumerate(rows)
        ]
        if request.data.get("preview", True):
            return Response({"columns": SHEET_COLUMNS, "rows": results})
        if any(item["errors"] for item in results):
            return Response({"rows": results}, status=status.HTTP_400_BAD_REQUEST)
        conflict_action = request.data.get("conflict_action", "create")
        imported = []
        for item in results:
            row = item["data"]
            instance = None
            if conflict_action == "update" and row.get("id"):
                instance = CharacterSheet.objects.filter(pk=row["id"], user=request.user).first()
            values = {
                "name": row["name"],
                "edition": row["edition"],
                "age": int(row["age"]),
                "occupation": row.get("occupation", ""),
                "str_value": int(row["STR"]),
                "con_value": int(row["CON"]),
                "pow_value": int(row["POW"]),
                "dex_value": int(row["DEX"]),
                "app_value": int(row["APP"]),
                "siz_value": int(row["SIZ"]),
                "int_value": int(row["INT"]),
                "edu_value": int(row["EDU"]),
            }
            if instance:
                for field, value in values.items():
                    setattr(instance, field, value)
                instance.save()
            else:
                instance = CharacterSheet.objects.create(
                    user=request.user,
                    hit_points_max=1,
                    hit_points_current=1,
                    magic_points_max=1,
                    magic_points_current=1,
                    sanity_starting=int(row.get("SAN") or row["POW"]),
                    sanity_max=99,
                    sanity_current=int(row.get("SAN") or row["POW"]),
                    **values,
                )
            imported.append(instance.pk)
        return Response({"imported_ids": imported}, status=status.HTTP_201_CREATED)


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
            rows.append(
                [
                    character.pk,
                    character.name,
                    character.edition,
                    character.age,
                    character.occupation,
                    character.str_value,
                    character.con_value,
                    character.pow_value,
                    character.dex_value,
                    character.app_value,
                    character.siz_value,
                    character.int_value,
                    character.edu_value,
                    character.hit_points_current,
                    character.magic_points_current,
                    character.sanity_current,
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
                "range": request.data.get("range", "Characters!A1"),
                "character_ids": request.data.get("character_ids", []),
            },
            expires_at=timezone.now() + timedelta(days=7),
        )
        values = [SHEET_COLUMNS] + rows
        queued = queue_google_sheet_export(
            str(job.pk),
            request.user.pk,
            spreadsheet_id,
            request.data.get("range", "Characters!A1"),
            values,
        )
        if not queued:
            job.mark_failed("Background task broker is unavailable.")
        return Response(
            {"job_id": job.pk, "queued": queued},
            status=status.HTTP_202_ACCEPTED,
        )
