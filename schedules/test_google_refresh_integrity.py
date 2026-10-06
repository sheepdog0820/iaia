from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from allauth.socialaccount.models import SocialAccount, SocialLogin, SocialToken
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.google_oauth import store_google_integration_grant
from accounts.models import Group
from schedules.google_job_connection import google_connection_binding
from schedules.google_tokens import get_google_access_token
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleIntegration, TRPGSession
from schedules.tasks import export_google_sheet, sync_google_calendar


class GoogleRefreshFixtures:
    changed_message = (
        "Googleの認証情報が更新中に変更されました。もう一度操作し、必要に応じてGoogleを再連携してください。"
    )

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="google-refresh-integrity-fixture")
        self.account = SocialAccount.objects.create(user=self.user, provider="google", uid="refresh-fixture-identity")
        GoogleIntegration.objects.create(
            user=self.user,
            calendar_enabled=True,
            sheets_enabled=True,
            scopes=[GoogleIntegration.REQUIRED_CALENDAR_SCOPE, GoogleIntegration.REQUIRED_SHEETS_SCOPE],
        )
        self.reset_token()

    def reset_token(self):
        SocialToken.objects.filter(account__user=self.user).delete()
        self.token = SocialToken.objects.create(
            account=self.account,
            token="initial-access-fixture",  # Isolated fixture. # nosec B106
            token_secret="initial-refresh-fixture",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

    def credentials(self):
        return Mock(
            token="refreshed-access-fixture",  # Isolated fixture. # nosec B106
            refresh_token="refreshed-secret-fixture",
            expiry=timezone.now() + timedelta(hours=1),
        )

    def grant(self, account):
        login = SocialLogin(
            account=account,
            user=self.user,
            token=SocialToken(
                account=account,
                token="reconnected-access-fixture",  # Isolated fixture. # nosec B106
                token_secret="reconnected-secret-fixture",
                expires_at=timezone.now() + timedelta(hours=2),
            ),
        )
        login.state = {"process": "connect"}
        login.google_integration_scopes = [GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        store_google_integration_grant(sender=SocialLogin, request=SimpleNamespace(user=self.user), sociallogin=login)
        return SocialToken.objects.get(account__user=self.user)


# Isolated settings and credentials; never production secrets.
@override_settings(GOOGLE_OAUTH_CLIENT_ID="isolated-client", GOOGLE_OAUTH_CLIENT_SECRET="isolated-secret")  # nosec B106
class GoogleRefreshIntegrityTests(GoogleRefreshFixtures, TestCase):
    def test_reconnect_same_token_row_is_not_overwritten(self):
        credentials = self.credentials()
        credentials.refresh.side_effect = lambda request: self.grant(self.account)
        with patch("schedules.google_tokens.Credentials", return_value=credentials):
            with self.assertRaisesMessage(ValueError, self.changed_message):
                get_google_access_token(self.user)
        self.token.refresh_from_db()
        self.assertEqual(self.token.token, "reconnected-access-fixture")
        self.assertEqual(self.token.token_secret, "reconnected-secret-fixture")
        self.assertGreater(self.token.expires_at, credentials.expiry)
        self.assertEqual(
            GoogleIntegration.objects.get(user=self.user).scopes, [GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        )

    def test_account_switch_does_not_resurrect_deleted_credential(self):
        other = SocialAccount.objects.create(user=self.user, provider="google", uid="replacement-fixture-identity")
        credentials = self.credentials()
        credentials.refresh.side_effect = lambda request: self.grant(other)
        old_pk = self.token.pk
        with patch("schedules.google_tokens.Credentials", return_value=credentials):
            with self.assertRaisesMessage(ValueError, self.changed_message):
                get_google_access_token(self.user)
        self.assertFalse(SocialToken.objects.filter(pk=old_pk).exists())
        selected = SocialToken.objects.get(account__user=self.user)
        self.assertEqual(selected.account_id, other.pk)
        self.assertEqual(selected.token, "reconnected-access-fixture")

    def test_changed_secret_or_expiry_is_not_overwritten(self):
        for field, value in (
            ("token_secret", "competing-refresh-fixture"),
            ("expires_at", timezone.now() + timedelta(hours=3)),
        ):
            with self.subTest(field=field):
                self.reset_token()
                credentials = self.credentials()
                credentials.refresh.side_effect = lambda request: SocialToken.objects.filter(pk=self.token.pk).update(
                    **{field: value}
                )
                with patch("schedules.google_tokens.Credentials", return_value=credentials):
                    with self.assertRaisesMessage(ValueError, self.changed_message):
                        get_google_access_token(self.user)
                self.token.refresh_from_db()
                self.assertEqual(getattr(self.token, field), value)
                self.assertEqual(self.token.token, "initial-access-fixture")

    def test_deleted_token_finishes_both_workers_without_delivery(self):
        group = Group.objects.create(name="Refresh fixture group", created_by=self.user)
        session = TRPGSession.objects.create(
            title="Refresh fixture session",
            group=group,
            created_by=self.user,
            date=timezone.now() + timedelta(days=1),
        )
        sync = GoogleCalendarSync.objects.create(user=self.user, session=session)
        for kind in ("google_calendar_sync", "google_sheets_export"):
            with self.subTest(kind=kind), transaction.atomic():
                self.reset_token()
                credentials = self.credentials()
                credentials.refresh.side_effect = lambda request: SocialToken.objects.filter(pk=self.token.pk).delete()
                job = AsyncJob.objects.create(
                    owner=self.user,
                    job_type=kind,
                    expires_at=timezone.now() + timedelta(days=1),
                    payload={
                        "google_connection": google_connection_binding(GoogleIntegration.objects.get(user=self.user))
                    },
                )
                with (
                    patch("schedules.google_tokens.Credentials", return_value=credentials),
                    patch("schedules.tasks.requests.post") as post,
                    patch("schedules.tasks.requests.put") as put,
                    patch.object(sync_google_calendar, "retry") as calendar_retry,
                    patch.object(export_google_sheet, "retry") as sheets_retry,
                ):
                    if kind == "google_calendar_sync":
                        result = sync_google_calendar.run(sync.pk, str(job.pk))
                    else:
                        result = export_google_sheet.run(str(job.pk), self.user.pk, "isolated-sheet", "A1", [[1]])
                    self.assertEqual(result, "missing-token")
                    post.assert_not_called()
                    put.assert_not_called()
                    calendar_retry.assert_not_called()
                    sheets_retry.assert_not_called()
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)
                self.assertEqual(job.error, self.changed_message)
                self.assertIsNotNone(job.finished_at)
                if kind == "google_calendar_sync":
                    sync.refresh_from_db()
                    self.assertEqual(sync.status, GoogleCalendarSync.Status.FAILED)
                    self.assertEqual(sync.last_error, self.changed_message)
                self.assertFalse(SocialToken.objects.filter(account__user=self.user).exists())

    def test_account_identity_change_rejects_refreshed_result(self):
        for field, value in (("provider", "discord"), ("uid", "changed-fixture-identity")):
            with self.subTest(field=field):
                SocialAccount.objects.filter(pk=self.account.pk).update(
                    provider="google", uid="refresh-fixture-identity"
                )
                self.reset_token()
                credentials = self.credentials()
                credentials.refresh.side_effect = lambda request: SocialAccount.objects.filter(
                    pk=self.account.pk
                ).update(**{field: value})
                with patch("schedules.google_tokens.Credentials", return_value=credentials):
                    with self.assertRaisesMessage(ValueError, self.changed_message):
                        get_google_access_token(self.user)
                self.token.refresh_from_db()
                self.assertEqual(self.token.token, "initial-access-fixture")

    def test_refresh_without_rotated_secret_or_expiry_preserves_original_fields(self):
        original = (self.token.token_secret, self.token.expires_at)
        credentials = self.credentials()
        credentials.refresh_token = None
        credentials.expiry = None
        with patch("schedules.google_tokens.Credentials", return_value=credentials):
            self.assertEqual(get_google_access_token(self.user), credentials.token)
        self.token.refresh_from_db()
        self.assertEqual((self.token.token_secret, self.token.expires_at), original)
