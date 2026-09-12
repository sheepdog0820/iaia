from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Group
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleIntegration, TRPGSession
from schedules.tasks import sync_google_calendar


class GoogleCalendarDeliveryTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="delivery-fixture")
        group = Group.objects.create(name="Delivery fixture", created_by=self.user)
        self.session = TRPGSession.objects.create(
            title="Initial title", gm=self.user, group=group, date=timezone.now() + timedelta(days=1)
        )
        self.sync = GoogleCalendarSync.objects.create(user=self.user, session=self.session)
        GoogleIntegration.objects.create(
            user=self.user, calendar_enabled=True, scopes=[GoogleIntegration.REQUIRED_CALENDAR_SCOPE]
        )

    def job(self):
        return AsyncJob.objects.create(
            owner=self.user, job_type="google_calendar_sync", expires_at=timezone.now() + timedelta(days=1)
        )

    def response(self, code, data):
        result = Mock(status_code=code)
        result.json.return_value = data
        result.raise_for_status.side_effect = requests.HTTPError("fixture failure") if code >= 400 else None
        return result

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_malformed_creation_response_finishes_job_as_failed(self, token):
        for data in (None, [], "unexpected", 42):
            with self.subTest(data=data), patch("schedules.tasks.requests.post", return_value=self.response(200, data)):
                job = self.job()
                self.assertEqual(sync_google_calendar.run(self.sync.pk, str(job.pk)), "invalid-response")
                job.refresh_from_db()
                self.sync.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)
                self.assertEqual(self.sync.status, GoogleCalendarSync.Status.FAILED)
                self.assertEqual(self.sync.external_event_id, "")
                self.assertEqual(job.error, "Google Calendarの応答形式を確認できません。連携状態を確認してください。")
                self.assertEqual(self.sync.last_error, job.error)

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_malformed_identity_response_never_updates_or_deletes_event(self, token):
        malformed = (None, [], "unexpected", {"extendedProperties": None}, {"extendedProperties": []})
        for cancelling in (False, True):
            self.session.status = "cancelled" if cancelling else "planned"
            self.session.save(update_fields=["status"])
            for data in malformed:
                with (
                    self.subTest(cancelling=cancelling, data=data),
                    patch("schedules.tasks.requests.post", return_value=self.response(409, {})),
                    patch("schedules.tasks.requests.get", return_value=self.response(200, data)),
                    patch("schedules.tasks.requests.put") as put,
                    patch("schedules.tasks.requests.delete") as delete,
                ):
                    job = self.job()
                    self.assertEqual(sync_google_calendar.run(self.sync.pk, str(job.pk)), "invalid-response")
                    job.refresh_from_db()
                    self.sync.refresh_from_db()
                    self.assertEqual(job.status, AsyncJob.Status.FAILED)
                    self.assertEqual(self.sync.status, GoogleCalendarSync.Status.FAILED)
                    self.assertEqual(self.sync.external_event_id, "")
                    self.assertEqual(
                        job.error, "Google Calendarの応答形式を確認できません。連携状態を確認してください。"
                    )
                    self.assertEqual(self.sync.last_error, job.error)
                    put.assert_not_called()
                    delete.assert_not_called()

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_create_cancel_resume_keeps_identity_metadata(self, token):
        events = {}

        def insert(url, *, json, **kwargs):
            events[json["id"]] = json
            return self.response(200, json)

        def delete(url, **kwargs):
            events[url.rsplit("/", 1)[1]]["status"] = "cancelled"
            return self.response(204, {})

        def update(url, *, json, **kwargs):
            event_id = url.rsplit("/", 1)[1]
            events[event_id] = {**json, "id": event_id}
            return self.response(200, events[event_id])

        with (
            patch("schedules.tasks.requests.post", side_effect=insert) as post,
            patch("schedules.tasks.requests.delete", side_effect=delete),
            patch("schedules.tasks.requests.put", side_effect=update),
        ):
            sync_google_calendar.run(self.sync.pk, str(self.job().pk))
            self.sync.refresh_from_db()
            event_id = self.sync.external_event_id
            identity = dict(events[event_id]["extendedProperties"]["private"])
            self.session.status = "cancelled"
            self.session.save(update_fields=["status"])
            sync_google_calendar.run(self.sync.pk, str(self.job().pk))
            self.assertEqual(events[event_id]["status"], "cancelled")
            self.session.status = "planned"
            self.session.title = "再開後のタイトル"
            self.session.save(update_fields=["status", "title"])
            sync_google_calendar.run(self.sync.pk, str(self.job().pk))
        self.assertEqual(post.call_count, 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[event_id]["status"], "confirmed")
        self.assertEqual(events[event_id]["summary"], "再開後のタイトル")
        self.assertEqual(events[event_id]["extendedProperties"]["private"], identity)

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_cancel_after_lost_creation_response_finds_and_deletes_event(self, token):
        events = {}

        def insert(url, *, json, **kwargs):
            events[json["id"]] = json
            raise requests.Timeout("created but response lost")

        def fetch(url, **kwargs):
            return self.response(200, events[url.rsplit("/", 1)[1]])

        with (
            patch("schedules.tasks.requests.post", side_effect=insert) as post,
            patch("schedules.tasks.requests.get", side_effect=fetch),
            patch("schedules.tasks.requests.put") as put,
            patch("schedules.tasks.requests.delete", return_value=self.response(204, {})) as delete,
            patch.object(sync_google_calendar, "retry", side_effect=Retry()),
        ):
            with self.assertRaises(Retry):
                sync_google_calendar.run(self.sync.pk, str(self.job().pk))
            self.session.status = "cancelled"
            self.session.date = None
            self.session.save(update_fields=["status", "date"])
            job = self.job()
            self.assertEqual(sync_google_calendar.run(self.sync.pk, str(job.pk)), GoogleCalendarSync.Status.DELETED)
        self.assertEqual(post.call_count, 1)
        put.assert_not_called()
        delete.assert_called_once()
        self.assertTrue(delete.call_args.args[0].endswith("/" + next(iter(events))))
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    @patch("schedules.tasks.requests.post")
    @patch("schedules.tasks.requests.delete")
    @patch("schedules.tasks.requests.get")
    def test_cancel_without_saved_id_does_not_create_or_delete_unrelated_event(self, get, delete, post, token):
        self.session.status = "cancelled"
        self.session.save(update_fields=["status"])
        for code in (404, 410, 200):
            with self.subTest(code=code):
                get.return_value = self.response(code, {"id": "unrelated"})
                job = self.job()
                result = sync_google_calendar.run(self.sync.pk, str(job.pk))
                job.refresh_from_db()
                if code == 200:
                    self.assertEqual(result, "invalid-response")
                    self.assertEqual(job.status, AsyncJob.Status.FAILED)
                else:
                    self.assertEqual(result, GoogleCalendarSync.Status.DELETED)
                    self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)
        post.assert_not_called()
        delete.assert_not_called()

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    @patch("schedules.tasks.requests.delete")
    def test_cancelled_session_without_date_removes_existing_event(self, delete, token):
        self.session.status = "cancelled"
        self.session.date = None
        self.session.save(update_fields=["status", "date"])
        self.sync.external_event_id = "existing-event"
        self.sync.save(update_fields=["external_event_id"])
        delete.return_value = self.response(204, {})
        job = self.job()
        self.assertEqual(sync_google_calendar.run(self.sync.pk, str(job.pk)), GoogleCalendarSync.Status.DELETED)
        delete.assert_called_once_with(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events/existing-event",
            headers={"Authorization": "Bearer isolated-token", "Content-Type": "application/json"},
            timeout=15,
        )
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    @patch("schedules.tasks.requests.delete")
    @patch("schedules.tasks.requests.put")
    @patch("schedules.tasks.requests.post")
    def test_undated_active_session_does_not_send_event(self, post, put, delete, token):
        self.session.date = None
        self.session.save(update_fields=["date"])
        for external_id in ("", "existing-event"):
            with self.subTest(external_id=external_id):
                self.sync.external_event_id = external_id
                self.sync.save(update_fields=["external_event_id"])
                job = self.job()
                self.assertEqual(sync_google_calendar.run(self.sync.pk, str(job.pk)), "undated")
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)
        post.assert_not_called()
        put.assert_not_called()
        delete.assert_not_called()

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    @patch("schedules.tasks.requests.delete")
    def test_lost_deletion_response_completes_on_already_deleted_retry(self, delete, token):
        self.session.status = "cancelled"
        self.session.save(update_fields=["status"])
        self.sync.external_event_id = "existing-event"
        self.sync.save(update_fields=["external_event_id"])
        delete.side_effect = [requests.Timeout("response lost after deletion"), self.response(410, {})]
        with patch.object(sync_google_calendar, "retry", side_effect=Retry()) as retry:
            with self.assertRaises(Retry):
                sync_google_calendar.run(self.sync.pk, str(self.job().pk))
            job = self.job()
            self.assertEqual(sync_google_calendar.run(self.sync.pk, str(job.pk)), GoogleCalendarSync.Status.DELETED)
        self.sync.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(retry.call_count, 1)
        self.assertEqual(delete.call_count, 2)
        self.assertEqual(delete.call_args_list[0], delete.call_args_list[1])
        self.assertEqual(self.sync.external_event_id, "existing-event")
        self.assertEqual(self.sync.last_error, "")
        self.assertIsNotNone(self.sync.synced_at)
        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    @patch("schedules.tasks.requests.delete")
    def test_cancellation_does_not_hide_other_http_failures(self, delete, token):
        self.session.status = "cancelled"
        self.session.save(update_fields=["status"])
        self.sync.external_event_id = "existing-event"
        self.sync.save(update_fields=["external_event_id"])
        for code in (401, 403, 429, 500):
            with self.subTest(code=code):
                delete.return_value = self.response(code, {})
                job = self.job()
                with patch.object(sync_google_calendar, "retry", side_effect=Retry()):
                    with self.assertRaises(Retry):
                        sync_google_calendar.run(self.sync.pk, str(job.pk))
                job.refresh_from_db()
                self.sync.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)
                self.assertEqual(self.sync.status, GoogleCalendarSync.Status.FAILED)

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_lost_creation_response_does_not_duplicate_event_on_new_job(self, token):
        events = {}
        attempts = []

        def insert(url, *, json, **kwargs):
            event_id = json.get("id", f"automatic{len(events)}")
            attempts.append(event_id)
            if event_id in events:
                return self.response(409, {})
            events[event_id] = {**json, "id": event_id}
            if len(attempts) == 1:
                raise requests.Timeout("response lost after storage")
            return self.response(200, events[event_id])

        def fetch(url, **kwargs):
            return self.response(200, events[url.rsplit("/", 1)[1]])

        def update(url, *, json, **kwargs):
            event_id = url.rsplit("/", 1)[1]
            events[event_id] = {**json, "id": event_id}
            return self.response(200, events[event_id])

        with (
            patch("schedules.tasks.requests.post", side_effect=insert),
            patch("schedules.tasks.requests.get", side_effect=fetch),
            patch("schedules.tasks.requests.put", side_effect=update),
            patch.object(sync_google_calendar, "retry", side_effect=Retry()),
        ):
            with self.assertRaises(Retry):
                sync_google_calendar.run(self.sync.pk, str(self.job().pk))
            self.session.title = "Updated before retry"
            self.session.save(update_fields=["title"])
            job = self.job()
            sync_google_calendar.run(self.sync.pk, str(job.pk))
        self.assertEqual(len(events), 1)
        self.assertEqual(attempts[0], attempts[1])
        self.assertRegex(attempts[0], r"^[0-9a-v]{5,1024}$")
        self.sync.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)
        self.assertEqual(events[self.sync.external_event_id]["summary"], "Updated before retry")

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    @patch("schedules.tasks.requests.put")
    @patch("schedules.tasks.requests.get")
    @patch("schedules.tasks.requests.post")
    def test_duplicate_id_does_not_overwrite_unrelated_event(self, post, get, put, token):
        post.return_value = self.response(409, {})
        get.return_value = self.response(200, {"id": "unrelated", "extendedProperties": {"private": {}}})
        job = self.job()
        with patch.object(sync_google_calendar, "retry", side_effect=Retry()):
            try:
                result = sync_google_calendar.run(self.sync.pk, str(job.pk))
            except Retry:
                result = "retried"
        self.assertEqual(result, "invalid-response")
        job.refresh_from_db()
        self.sync.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(self.sync.external_event_id, "")
        self.assertEqual(job.error, "Google Calendarの予定IDが一致しません。連携状態を確認してください。")
        put.assert_not_called()

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    @patch("schedules.tasks.requests.put")
    @patch("schedules.tasks.requests.get")
    @patch("schedules.tasks.requests.post")
    def test_matching_id_without_sync_metadata_is_rejected(self, post, get, put, token):
        post.return_value = self.response(409, {})
        get.side_effect = lambda url, **kwargs: self.response(200, {"id": url.rsplit("/", 1)[1]})
        job = self.job()
        self.assertEqual(sync_google_calendar.run(self.sync.pk, str(job.pk)), "invalid-response")
        job.refresh_from_db()
        self.sync.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(self.sync.external_event_id, "")
        put.assert_not_called()
