from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import models
from django.db.models.functions import Coalesce


def effective_duration_expression(prefix=""):
    return Coalesce(
        f"{prefix}actual_duration_minutes",
        f"{prefix}duration_minutes",
        output_field=models.PositiveIntegerField(),
    )


def format_duration_hours(minutes, empty_label="未設定"):
    hours_text = minutes_to_hours(minutes)
    if hours_text is None:
        return empty_label
    return f"{hours_text}時間"


def minutes_to_hours(minutes):
    if minutes in (None, ""):
        return None
    try:
        minute_value = Decimal(str(minutes))
        if minute_value <= 0:
            return None
        hours = (minute_value / Decimal("60")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return format(hours.normalize(), "f")


def hours_to_minutes(hours):
    if hours in (None, ""):
        return None
    try:
        return int((Decimal(str(hours)) * Decimal("60")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError):
        return None
