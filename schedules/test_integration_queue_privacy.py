import logging
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Group, GroupDiscordSettings
from schedules.models import AsyncJob
from schedules.tasks import queue_discord_event, queue_google_calendar_sync, queue_google_sheet_export


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class IntegrationQueuePrivacyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="queue-privacy-fixture")
        group = Group.objects.create(name="隔離テスト", created_by=self.user)
        self.discord = GroupDiscordSettings.objects.create(group=group, enabled=True, event_types=["session_updated"])
        self.job = AsyncJob.objects.create(
            owner=self.user, job_type="google_sheets_export", expires_at=timezone.now() + timedelta(days=1)
        )
        # Synthetic markers only. No credential, business row, or real recipient is used.
        self.private = "synthetic-broker-password-and-private-export"

    def assert_private_failure(self, invoke, target):
        with (
            patch("schedules.tasks._broker_available", return_value=True),
            patch(target, side_effect=RuntimeError(self.private)),
            self.assertLogs("schedules.tasks", level="ERROR") as captured,
        ):
            self.assertFalse(invoke())
        formatter = logging.Formatter()
        for record in captured.records:
            self.assertNotIn(self.private, formatter.format(record))
            self.assertIsNone(record.exc_info)
            self.assertIsNone(record.stack_info)
        self.job.refresh_from_db()
        self.assertEqual(self.job.celery_task_id, "")

    def test_discord_queue_failure_does_not_log_exception_payload(self):
        self.assert_private_failure(
            lambda: queue_discord_event(
                self.discord.group_id, "session_updated", {"content": self.private}, "privacy-fixture"
            ),
            "schedules.tasks.send_discord_webhook.delay",
        )

    def test_calendar_queue_failure_does_not_log_exception_payload(self):
        self.assert_private_failure(
            lambda: queue_google_calendar_sync(1, str(self.job.pk)), "schedules.tasks.sync_google_calendar.delay"
        )

    def test_sheet_queue_failure_does_not_log_exception_payload(self):
        self.assert_private_failure(
            lambda: queue_google_sheet_export(
                str(self.job.pk), self.user.pk, "synthetic-sheet", "A1", [[self.private]]
            ),
            "schedules.tasks.export_google_sheet.delay",
        )

    def test_calendar_and_sheet_record_failure_does_not_log_database_exception(self):
        for invoke, target in (
            (lambda: queue_google_calendar_sync(1, str(self.job.pk)), "schedules.tasks.sync_google_calendar.delay"),
            (
                lambda: queue_google_sheet_export(str(self.job.pk), self.user.pk, "synthetic-sheet", "A1", []),
                "schedules.tasks.export_google_sheet.delay",
            ),
        ):
            with (
                self.subTest(target=target),
                patch(target, return_value=Mock(id="synthetic-task")),
            ):
                self.assert_private_failure(invoke, "schedules.tasks.AsyncJob.objects.filter")

    def test_success_still_records_task_ids_and_preserves_arguments(self):
        with (
            patch("schedules.tasks._broker_available", return_value=True),
            patch("schedules.tasks.sync_google_calendar.delay", return_value=Mock(id="calendar-task")) as calendar,
            patch("schedules.tasks.export_google_sheet.delay", return_value=Mock(id="sheet-task")) as sheets,
            patch("schedules.tasks.send_discord_webhook.delay") as discord,
        ):
            self.assertTrue(queue_google_calendar_sync(7, str(self.job.pk)))
            self.job.refresh_from_db()
            self.assertEqual(self.job.celery_task_id, "calendar-task")
            values = [["合成値"]]
            self.assertTrue(queue_google_sheet_export(str(self.job.pk), self.user.pk, "synthetic-sheet", "A1", values))
            self.job.refresh_from_db()
            self.assertEqual(self.job.celery_task_id, "sheet-task")
            self.assertTrue(queue_discord_event(self.discord.group_id, "session_updated", {"content": "合成値"}, "key"))
        calendar.assert_called_once_with(7, str(self.job.pk))
        sheets.assert_called_once_with(str(self.job.pk), self.user.pk, "synthetic-sheet", "A1", values)
        discord.assert_called_once_with(self.discord.group_id, "session_updated", {"content": "合成値"}, "key")
