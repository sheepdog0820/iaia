from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import Mock, patch

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Group, GroupMembership
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleIntegration, SessionParticipant, TRPGSession
from schedules.tasks import sync_google_calendar


class GoogleCalendarRevocationTest(TestCase):
    reasons = ("disabled", "scope", "inactive", "deleted", "visibility")
    denied_message = "Google Calendar連携が無効、またはセッションを同期する権限がありません。"

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="calendar-revocation-fixture")
        account = SocialAccount.objects.create(user=self.user, provider="google", uid="calendar-revocation-fixture")
        SocialToken.objects.create(account=account, token="isolated-token")  # Isolated fixture. # nosec B106
        self.other = get_user_model().objects.create_user(username="calendar-revocation-other")
        self.group = Group.objects.create(name="Calendar revocation fixture", created_by=self.user)
        self.session = TRPGSession.objects.create(
            title="Calendar revocation fixture",
            created_by=self.user,
            gm=self.user,
            group=self.group,
            date=timezone.now() + timedelta(days=1),
        )
        self.sync = GoogleCalendarSync.objects.create(user=self.user, session=self.session)

    def _prepare(self, mode="create"):
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=True)
        Group.objects.filter(pk=self.group.pk).update(created_by=self.user)
        TRPGSession.objects.filter(pk=self.session.pk).update(
            created_by=self.user, status="cancelled" if mode.startswith("cancel") else "planned"
        )
        GoogleIntegration.objects.update_or_create(
            user=self.user,
            defaults={"calendar_enabled": True, "scopes": [GoogleIntegration.REQUIRED_CALENDAR_SCOPE]},
        )
        external_id = "existing-fixture-event" if mode in ("update", "cancel-known") else ""
        GoogleCalendarSync.objects.filter(pk=self.sync.pk).update(
            external_event_id=external_id, status=GoogleCalendarSync.Status.PENDING, last_error="", synced_at=None
        )
        self.sync.refresh_from_db()
        return AsyncJob.objects.create(
            owner=self.user, job_type="google_calendar_sync", expires_at=timezone.now() + timedelta(days=1)
        )

    def _revoke(self, reason):
        if reason == "disabled":
            GoogleIntegration.objects.filter(user=self.user).update(calendar_enabled=False)
        elif reason == "scope":
            GoogleIntegration.objects.filter(user=self.user).update(scopes=[])
        elif reason == "inactive":
            get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        elif reason == "deleted":
            GoogleIntegration.objects.filter(user=self.user).delete()
        else:
            TRPGSession.objects.filter(pk=self.session.pk).update(created_by=self.other)
            Group.objects.filter(pk=self.group.pk).update(created_by=self.other)
            GroupMembership.objects.filter(group=self.group, user=self.user).delete()
            SessionParticipant.objects.filter(session=self.session, user=self.user).delete()

    def _response(self, code, data):
        response = Mock(status_code=code)
        response.json.return_value = data
        return response

    def _event_response(self, url, **kwargs):
        event_id = url.rsplit("/", 1)[1]
        return self._response(
            200,
            {
                "id": event_id,
                "extendedProperties": {
                    "private": {
                        "tableno_session_id": str(self.session.pk),
                        "tableno_sync_key": event_id,
                    }
                },
            },
        )

    def _requests(self, stack):
        sends = {
            method: stack.enter_context(patch(f"schedules.tasks.requests.{method}"))
            for method in ("post", "get", "put", "delete")
        }
        sends["post"].side_effect = lambda url, **kwargs: self._response(200, kwargs["json"])
        sends["get"].side_effect = self._event_response
        sends["put"].return_value = self._response(200, {})
        sends["delete"].return_value = self._response(204, {})
        return sends

    def _assert_failed(self, result, job):
        self.assertEqual(result, "not-authorized")
        job.refresh_from_db()
        self.sync.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(job.error, self.denied_message)
        self.assertIsNotNone(job.finished_at)
        self.assertEqual(self.sync.status, GoogleCalendarSync.Status.FAILED)
        self.assertEqual(self.sync.last_error, self.denied_message)
        self.assertIsNone(self.sync.synced_at)

    def test_revocation_before_start_never_refreshes_or_sends(self):
        for reason in self.reasons:
            with self.subTest(reason=reason), ExitStack() as stack:
                job = self._prepare()
                self._revoke(reason)
                sends = self._requests(stack)
                token = stack.enter_context(patch("schedules.tasks.get_google_access_token"))
                result = sync_google_calendar.run(self.sync.pk, str(job.pk))
                for send in sends.values():
                    send.assert_not_called()
                token.assert_not_called()
                self._assert_failed(result, job)
                self.assertEqual(job.progress, 0)

    def test_revocation_during_token_refresh_prevents_each_first_request(self):
        for mode in ("create", "update", "cancel-known", "cancel-unknown"):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), ExitStack() as stack:
                    job = self._prepare(mode)
                    sends = self._requests(stack)

                    def refresh(user):
                        self._revoke(reason)
                        return "isolated-token"

                    stack.enter_context(patch("schedules.tasks.get_google_access_token", side_effect=refresh))
                    retry = stack.enter_context(patch.object(sync_google_calendar, "retry"))
                    result = sync_google_calendar.run(self.sync.pk, str(job.pk))
                    for send in sends.values():
                        send.assert_not_called()
                    retry.assert_not_called()
                    self._assert_failed(result, job)
                    self.assertEqual(job.progress, 10)
                    self.assertEqual(
                        self.sync.external_event_id,
                        "existing-fixture-event" if mode in ("update", "cancel-known") else "",
                    )

    def test_revocation_between_requests_stops_conflict_recovery_and_cancellation(self):
        for mode in ("conflict-post", "conflict-get", "cancel-unknown"):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), ExitStack() as stack:
                    job = self._prepare(mode)
                    sends = self._requests(stack)

                    def conflict(url, **kwargs):
                        if mode == "conflict-post":
                            self._revoke(reason)
                        return self._response(409, {})

                    def fetch(url, **kwargs):
                        self._revoke(reason)
                        return self._event_response(url, **kwargs)

                    sends["post"].side_effect = conflict
                    sends["get"].side_effect = fetch
                    stack.enter_context(patch("schedules.tasks.get_google_access_token", return_value="isolated-token"))
                    retry = stack.enter_context(patch.object(sync_google_calendar, "retry"))
                    result = sync_google_calendar.run(self.sync.pk, str(job.pk))
                    self.assertEqual(sends["post"].call_count, int(mode != "cancel-unknown"))
                    self.assertEqual(sends["get"].call_count, int(mode != "conflict-post"))
                    sends["put"].assert_not_called()
                    sends["delete"].assert_not_called()
                    retry.assert_not_called()
                    self._assert_failed(result, job)
                    self.assertEqual(self.sync.external_event_id, "")

    def test_revocation_after_acknowledged_last_write_does_not_undo_it(self):
        for mode, method in (("create", "post"), ("update", "put"), ("cancel-known", "delete")):
            with self.subTest(mode=mode), ExitStack() as stack:
                job = self._prepare(mode)
                sends = self._requests(stack)

                def send(url, **kwargs):
                    self._revoke("disabled")
                    return self._response(204 if method == "delete" else 200, kwargs.get("json", {}))

                sends[method].side_effect = send
                stack.enter_context(patch("schedules.tasks.get_google_access_token", return_value="isolated-token"))
                expected = GoogleCalendarSync.Status.DELETED if method == "delete" else GoogleCalendarSync.Status.SYNCED
                self.assertEqual(sync_google_calendar.run(self.sync.pk, str(job.pk)), expected)
                sends[method].assert_called_once()
                for other in sends.keys() - {method}:
                    sends[other].assert_not_called()
                job.refresh_from_db()
                self.sync.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)
                self.assertIsNotNone(self.sync.synced_at)
