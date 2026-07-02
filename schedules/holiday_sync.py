import csv
import io
import logging
from datetime import datetime

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import JapaneseHoliday

logger = logging.getLogger(__name__)

DEFAULT_JAPANESE_HOLIDAY_CSV_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"


class JapaneseHolidaySyncError(RuntimeError):
    pass


def get_japanese_holiday_csv_url():
    return getattr(settings, "JAPANESE_HOLIDAY_CSV_URL", DEFAULT_JAPANESE_HOLIDAY_CSV_URL)


def fetch_japanese_holiday_csv(url=None, timeout=20):
    source_url = url or get_japanese_holiday_csv_url()
    response = requests.get(source_url, timeout=timeout)
    response.raise_for_status()
    return response.content, source_url


def parse_japanese_holiday_csv(content):
    text = content.decode("cp932")
    rows = csv.DictReader(io.StringIO(text))
    parsed = []

    for row in rows:
        date_value = (row.get("国民の祝日・休日月日") or "").strip()
        name = (row.get("国民の祝日・休日名称") or "").strip()
        if not date_value or not name:
            continue
        try:
            holiday_date = datetime.strptime(date_value, "%Y/%m/%d").date()
        except ValueError as exc:
            raise JapaneseHolidaySyncError(f"Invalid holiday date: {date_value}") from exc
        parsed.append((holiday_date, name))

    if not parsed:
        raise JapaneseHolidaySyncError("No Japanese holidays were parsed from CSV.")

    return parsed


@transaction.atomic
def upsert_japanese_holidays(holidays, source_url):
    fetched_at = timezone.now()
    created = 0
    updated = 0
    synced_dates = {holiday_date for holiday_date, _ in holidays}
    first_date = min(synced_dates)
    last_date = max(synced_dates)

    for holiday_date, name in holidays:
        _, was_created = JapaneseHoliday.objects.update_or_create(
            date=holiday_date,
            defaults={
                "name": name,
                "source": "cao_csv",
                "source_url": source_url,
                "fetched_at": fetched_at,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    deleted_stale = (
        JapaneseHoliday.objects.filter(
            source="cao_csv",
            date__gte=first_date,
            date__lte=last_date,
        )
        .exclude(date__in=synced_dates)
        .delete()[0]
    )

    return {
        "created": created,
        "updated": updated,
        "deleted_stale": deleted_stale,
        "total": len(holidays),
        "source_url": source_url,
        "fetched_at": fetched_at.isoformat(),
    }


def sync_japanese_holidays(url=None):
    content, source_url = fetch_japanese_holiday_csv(url=url)
    holidays = parse_japanese_holiday_csv(content)
    result = upsert_japanese_holidays(holidays, source_url)
    logger.info(
        "Japanese holidays synced from %s: created=%s updated=%s total=%s",
        source_url,
        result["created"],
        result["updated"],
        result["total"],
    )
    return result
