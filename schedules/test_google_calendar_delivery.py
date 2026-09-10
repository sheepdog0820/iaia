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
