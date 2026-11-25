from django.db.models import Q
from django.utils import timezone

from accounts.character_models import CharacterSheet
from schedules.models import SessionOccurrence
from schedules.session_permissions import sessions_for_participant_or_creator


def get_next_session(user, *, now=None):
    now = now or timezone.now()
    my_sessions = sessions_for_participant_or_creator(user).filter(status__in=("planned", "ongoing")).order_by()
    occurrence = (
        SessionOccurrence.objects.filter(session__in=my_sessions, start_at__gte=now)
        .select_related("session")
        .only("start_at", "session__title", "session__duration_minutes", "session__status")
        .order_by("start_at", "pk")
        .first()
    )
    # Legacy sessions may have a date without an occurrence record.
    legacy = (
        my_sessions.filter(date__gte=now, occurrences__isnull=True)
        .only("date", "title", "duration_minutes", "status")
        .order_by("date", "pk")
        .first()
    )
    if occurrence and (legacy is None or occurrence.start_at <= legacy.date):
        session, start_at, occurrence_id = occurrence.session, occurrence.start_at, str(occurrence.pk)
    elif legacy:
        session, start_at, occurrence_id = legacy, legacy.date, None
    else:
        return {"session": None}

    return {
        "session": {
            "id": str(session.pk),
            "occurrence_id": occurrence_id,
            "title": session.title,
            "start_at": timezone.localtime(start_at).isoformat(),
            "duration_minutes": session.duration_minutes,
            "status": session.status,
        }
    }


def _owned_characters(user):
    # Ownership is the same boundary as the character list API. Incomplete registry rows have no sheet to return.
    return (
        CharacterSheet.objects.filter(user=user)
        .filter(
            Q(edition="6th", sixth_edition_data__isnull=False) | Q(edition="7th", seventh_edition_data__isnull=False)
        )
        .select_related("sixth_edition_data", "seventh_edition_data")
    )


def _character_summary(sheet, detail):
    return {
        "id": str(sheet.pk),
        "name": detail.name,
        "edition": sheet.edition,
        "occupation": detail.occupation,
        "version": detail.version,
        "is_active": detail.is_active,
    }


def list_my_characters(user, *, query="", page=1, limit=20):
    sheets = _owned_characters(user)
    if query := query.strip():
        sheets = sheets.filter(
            Q(sixth_edition_data__name__icontains=query)
            | Q(sixth_edition_data__name_kana__icontains=query)
            | Q(seventh_edition_data__name__icontains=query)
            | Q(seventh_edition_data__name_kana__icontains=query)
        )
    offset = (page - 1) * limit
    rows = list(sheets.order_by("-updated_at", "-pk")[offset : offset + limit + 1])
    return {
        "items": [_character_summary(sheet, sheet.system_data) for sheet in rows[:limit]],
        "has_more": len(rows) > limit,
    }


def get_character(user, character_id):
    sheet = _owned_characters(user).filter(pk=character_id).first()
    if sheet is None:
        return {"character": None}

    detail = sheet.system_data
    return {
        "character": {
            **_character_summary(sheet, detail),
            "abilities": detail.abilities,
            "status_summary": {
                "hp": {"current": detail.hit_points_current, "max": detail.hit_points_max},
                "mp": {"current": detail.magic_points_current, "max": detail.magic_points_max},
                "san": {"current": detail.sanity_current, "max": detail.sanity_max},
            },
            "skills": [
                {"name": name, "value": value}
                for name, value in detail.skills.values_list("skill_name", "current_value")
            ],
            "equipment": [
                {"name": name, "quantity": quantity}
                for name, quantity in detail.equipment.values_list("name", "quantity")
            ],
        }
    }
