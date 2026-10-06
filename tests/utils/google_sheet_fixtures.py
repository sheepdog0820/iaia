"""Seal synthetic transport fixtures; API contract tests use real producers instead."""

from schedules.google_job_connection import google_sheet_values_binding
from schedules.models import AsyncJob
from schedules.tasks import export_google_sheet


def run_sheet_fixture(job_id, user_id, spreadsheet_id, range_name, values):
    job = AsyncJob.objects.get(pk=job_id)
    job.payload["google_values"] = google_sheet_values_binding(values)
    job.save(update_fields=["payload"])
    return export_google_sheet.run(job_id, user_id, spreadsheet_id, range_name, values)
