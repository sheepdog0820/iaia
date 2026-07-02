from django.db import models
from django.db.models.functions import Coalesce


def effective_duration_expression(prefix=""):
    return Coalesce(
        f"{prefix}actual_duration_minutes",
        f"{prefix}duration_minutes",
        output_field=models.PositiveIntegerField(),
    )
