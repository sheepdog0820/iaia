"""Build owned synthetic transport rows; API contract tests use real producers."""

from accounts.character_models import CharacterSheet7th
from accounts.models import CharacterSheet
from schedules.google_job_connection import google_sheet_values_binding
from schedules.job_views import _sheet_export_values
from schedules.models import AsyncJob
from schedules.tasks import export_google_sheet


def run_sheet_fixture(job_id, user_id, spreadsheet_id, range_name, values):
    job = AsyncJob.objects.get(pk=job_id)
    # Preserve transport request/row counts, not the old arbitrary table grammar.
    characters = CharacterSheet.objects.bulk_create(
        [CharacterSheet(user_id=job.owner_id, edition="7th") for _ in values[1:]]
    )
    CharacterSheet7th.objects.bulk_create(
        [
            CharacterSheet7th(character_sheet=character, name=str(row[0]) if row else "合成配送試験")
            for character, row in zip(characters, values[1:])
        ]
    )
    job.payload["selection_snapshot"] = True
    job.payload["character_ids"] = [character.pk for character in characters]
    values = _sheet_export_values(job.owner, job.payload)
    job.payload["google_values"] = google_sheet_values_binding(values)
    job.save(update_fields=["payload"])
    return export_google_sheet.run(job_id, user_id, spreadsheet_id, range_name, values)
