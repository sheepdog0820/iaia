"""Observe real producer lock order, not a claim about future worker fencing."""

from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.db import OperationalError, close_old_connections, connection, transaction
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from schedules import tasks
from schedules.google_write_intake import calendar_event_key
from schedules.google_write_ledger import calendar_event_target_key, calendar_session_target_key, sheet_target_key
from schedules.models import GoogleCalendarSync, GoogleIntegration, GoogleWriteReservation, GoogleWriteTarget
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の実受付ロック順検証")
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleWriteIntakeConcurrencyTest(GoogleDispatchStateFixtures, TransactionTestCase):
    def _request(self, route, source, pids, user=None):
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '15s'")
                cursor.execute("SET lock_timeout = '10s'")
                cursor.execute("SELECT pg_backend_pid()")
                pids.append(cursor.fetchone()[0])
            if route == "session":
                tasks.schedule_session_google_syncs(self.session)
                return 202
            api = APIClient()
            api.force_authenticate(user or self.user)
            if route == "sheets":
                return api.post(
                    "/api/character-sheets/google-sheets/export/",
                    {"spreadsheet_id": "intake-shared-owner-sheet", "range": "Other!A1" if user else "Sheet1!A1"},
                    format="json",
                ).status_code
            url = (
                reverse("async-job-retry", kwargs={"pk": source.pk})
                if source is not None
                else f"/api/sessions/{self.session.pk}/google-calendar/sync/"
            )
            return api.post(url).status_code
        finally:
            close_old_connections()

    def _observe(self, pids, table, phrase, minimum=1, timeout=5):
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                cursor.execute(
                    "SELECT pid, length(query) FROM pg_stat_activity "
                    "WHERE pid=ANY(%s) AND datname=current_database() AND wait_event_type='Lock' "
                    "AND query LIKE %s AND query LIKE %s",
                    [pids, f"%{table}%", f"%{phrase}%"],
                )
                rows = cursor.fetchall()
                if len(rows) >= minimum:
                    print(f"GOOGLE_INTAKE_LOCK table={table} phrase={phrase} pids_lengths={rows}")
                    return
            sleep(0.01)
        self.fail("実受付のロック順を制限時間内に観測できませんでした。")

    def test_calendar_api_retry_and_automatic_intake_lock_targets_before_sync_update(self):
        logical = calendar_session_target_key(self.user.pk, self.session.pk)
        physical = calendar_event_target_key("delivery-fixture", calendar_event_key(self.sync))
        for route in ("calendar", "retry-calendar", "session"):
            with self.subTest(route=route), patch("django.db.transaction.on_commit"):
                sources = [None, None]
                if route == "retry-calendar":
                    sources = [self._queue("calendar")[0] for _ in range(2)]
                    for source in sources:
                        source.mark_failed("合成の元ジョブ失敗")
                for key in (logical, physical):
                    GoogleWriteTarget.objects.get_or_create(resource_key=key)
                before = GoogleWriteTarget.objects.get(pk=logical).last_sequence
                first_pids, second_pids = [], []
                with ThreadPoolExecutor(max_workers=2) as pool:
                    with transaction.atomic():
                        GoogleCalendarSync.objects.select_for_update().get(pk=self.sync.pk)
                        first = pool.submit(self._request, route, sources[0], first_pids)
                        self._observe(first_pids, "schedules_googlecalendarsync", "UPDATE")
                        with self.assertRaises(OperationalError) as failure, transaction.atomic():
                            GoogleWriteTarget.objects.select_for_update(nowait=True).get(pk=logical)
                        cause = failure.exception.__cause__
                        self.assertEqual(getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None), "55P03")
                        second = pool.submit(self._request, route, sources[1], second_pids)
                        self._observe(second_pids, "schedules_googlewritetarget", "FOR UPDATE")
                    self.assertEqual([first.result(timeout=15), second.result(timeout=15)], [202, 202])
                self.assertEqual(len(set(first_pids + second_pids)), 2)
                self.assertEqual(GoogleWriteTarget.objects.get(pk=logical).last_sequence, before + 2)
                self.assertCountEqual(
                    list(
                        GoogleWriteReservation.objects.filter(target_id=logical, sequence__gt=before).values_list(
                            "sequence", flat=True
                        )
                    ),
                    [before + 1, before + 2],
                )

    def test_two_owners_and_connections_and_ranges_share_the_whole_spreadsheet_counter(self):
        account = SocialAccount.objects.create(user=self.other, provider="google", uid="intake-other-owner")
        transport_fixture = "synthetic-intake-transport-material"
        SocialToken.objects.create(account=account, token=transport_fixture)
        GoogleIntegration.objects.create(
            user=self.other, sheets_enabled=True, scopes=[GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        )
        key = sheet_target_key("intake-shared-owner-sheet")
        GoogleWriteTarget.objects.create(resource_key=key)
        pids = []
        with patch("django.db.transaction.on_commit"), ThreadPoolExecutor(max_workers=2) as pool:
            with transaction.atomic():
                GoogleWriteTarget.objects.select_for_update().get(pk=key)
                first = pool.submit(self._request, "sheets", None, pids)
                second = pool.submit(self._request, "sheets", None, pids, self.other)
                self._observe(pids, "schedules_googlewritetarget", "FOR UPDATE", minimum=2)
            self.assertEqual([first.result(timeout=15), second.result(timeout=15)], [202, 202])
        self.assertEqual(len(set(pids)), 2)
        self.assertEqual(GoogleWriteTarget.objects.count(), 1)
        self.assertCountEqual(list(GoogleWriteReservation.objects.values_list("sequence", flat=True)), [1, 2])

    def test_observation_failure_is_bounded_and_not_a_success(self):
        with self.assertRaisesRegex(AssertionError, "制限時間内"):
            self._observe([], "schedules_googlewritetarget", "FOR UPDATE", timeout=0.02)
