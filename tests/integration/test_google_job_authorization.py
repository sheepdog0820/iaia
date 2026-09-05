from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Group
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleIntegration, SessionParticipant, TRPGSession
from schedules.tasks import export_google_sheet, sync_google_calendar


class GoogleJobAuthorizationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="export-player")
        owner = get_user_model().objects.create_user(username="export-owner")
        group = Group.objects.create(name="Export group", created_by=owner)
        self.session = TRPGSession.objects.create(
            title="共有セッション",
            description="共有説明",
            created_by=owner,
            gm=owner,
            group=group,
            visibility="private",
            date=timezone.now() + timedelta(days=1),
        )
        self.participant = SessionParticipant.objects.create(session=self.session, user=self.user)
        self.sync = GoogleCalendarSync.objects.create(session=self.session, user=self.user)
        self.scopes = [GoogleIntegration.REQUIRED_CALENDAR_SCOPE, GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        self.integration = GoogleIntegration.objects.create(
            user=self.user,
            calendar_enabled=True,
            sheets_enabled=True,
            scopes=self.scopes,
        )

    def job(self, feature):
        return AsyncJob.objects.create(
            owner=self.user, job_type=f"google_{feature}", expires_at=timezone.now() + timedelta(days=1)
        )

    def run_job(self, feature, job):
        if feature == "calendar":
            return sync_google_calendar.run(self.sync.pk, str(job.pk))
        return export_google_sheet.run(
            str(job.pk), self.user.pk, "local-fixture", "Characters!A1", [["name"], ["=1+1"]]
        )

    @patch("schedules.tasks.requests.delete")
    @patch("schedules.tasks.requests.put")
    @patch("schedules.tasks.requests.post")
    @patch("schedules.tasks.get_google_access_token", return_value="local-fixture-token")
    def test_disabled_removed_or_scope_revoked_jobs_do_not_contact_google(self, token, post, put, delete):
        post.return_value = Mock()
        post.return_value.json.return_value = {"id": "external-fixture"}
        put.return_value = Mock()
        put.return_value.json.return_value = {"updatedCells": 2}
        for feature in ("calendar", "sheets"):
            for change in ("disabled", "scope", "deleted", "inactive"):
                with self.subTest(feature=feature, change=change):
                    self.user.is_active = True
                    self.user.save(update_fields=["is_active"])
                    integration, _ = GoogleIntegration.objects.update_or_create(
                        user=self.user,
                        defaults={
                            "calendar_enabled": True,
                            "sheets_enabled": True,
                            "scopes": self.scopes,
                        },
                    )
                    if change == "deleted":
                        integration.delete()
                    elif change == "inactive":
                        self.user.is_active = False
                        self.user.save(update_fields=["is_active"])
                    else:
                        if change == "scope":
                            integration.scopes = []
                        else:
                            setattr(integration, f"{feature}_enabled", False)
                        integration.save()
                    for mock in (token, post, put, delete):
                        mock.reset_mock()
                    job = self.job(feature)
                    self.run_job(feature, job)
                    job.refresh_from_db()
                    self.assertEqual(job.status, AsyncJob.Status.FAILED)
                    for mock in (token, post, put, delete):
                        mock.assert_not_called()

    @patch("schedules.tasks.requests.post")
    @patch("schedules.tasks.get_google_access_token", return_value="local-fixture-token")
    def test_removed_participant_cannot_export_new_session_content(self, token, post):
        post.return_value = Mock()
        post.return_value.json.return_value = {"id": "external-fixture"}
        job = self.job("calendar")
        self.participant.delete()
        self.session.description = "脱退後の新しい情報"
        self.session.save(update_fields=["description"])
        self.run_job("calendar", job)
        job.refresh_from_db()
        self.sync.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(self.sync.status, GoogleCalendarSync.Status.FAILED)
        token.assert_not_called()
        post.assert_not_called()

    @patch("schedules.tasks.requests.put")
    @patch("schedules.tasks.requests.post")
    @patch("schedules.tasks.get_google_access_token", return_value="local-fixture-token")
    def test_authorized_jobs_still_export_and_update_existing_calendar_event(self, token, post, put):
        post.return_value = Mock()
        post.return_value.json.return_value = {"id": "external-fixture"}
        put.return_value = Mock()
        put.return_value.json.return_value = {"updatedCells": 2}
        first = self.job("calendar")
        self.run_job("calendar", first)
        second = self.job("calendar")
        self.run_job("calendar", second)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(put.call_count, 1)
        self.assertTrue(put.call_args.args[0].endswith("/external-fixture"))
        self.assertEqual(post.call_args.kwargs["json"]["description"], "共有説明")
        sheet = self.job("sheets")
        self.run_job("sheets", sheet)
        self.assertEqual(put.call_args.kwargs["params"], {"valueInputOption": "RAW"})
        for job in (first, second, sheet):
            job.refresh_from_db()
            self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)
