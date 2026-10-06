from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from schedules import test_google_connection_guard as connection_tests
from schedules.tasks import export_google_sheet, sync_google_calendar


class GoogleCredentialGuardTest(connection_tests.GoogleConnectionGuardTest):
    """Reuse the HTTP-boundary matrix with credential-only changes, not grants."""

    reasons = (
        "token-deleted",
        "account-deleted",
        "uid-changed",
        "provider-changed",
        "owner-changed",
        "app-changed",
        "token-recreated",
        "account-replaced",
        "new-latest-token",
        "access-rotated",
        "allauth-disconnect",
    )

    def _prepare(self, mode="sheets"):
        SocialAccount.objects.filter(uid__startswith="guard-").delete()
        return super()._prepare(mode)

    def _change(self, reason):
        if reason == "token-deleted":
            SocialToken.objects.filter(pk=self.token.pk).delete()
        elif reason == "account-deleted":
            SocialAccount.objects.filter(pk=self.account.pk).delete()
        elif reason == "uid-changed":
            SocialAccount.objects.filter(pk=self.account.pk).update(uid="guard-changed-identity")
        elif reason == "provider-changed":
            SocialAccount.objects.filter(pk=self.account.pk).update(provider="discord")
        elif reason == "owner-changed":
            other, _ = get_user_model().objects.get_or_create(username="credential-guard-other")
            SocialAccount.objects.filter(pk=self.account.pk).update(user=other)
        elif reason == "app-changed":
            app = SocialApp.objects.create(provider="discord", name="Isolated replacement", client_id="fixture")
            SocialToken.objects.filter(pk=self.token.pk).update(app=app)
        elif reason == "access-rotated":
            SocialToken.objects.filter(pk=self.token.pk).update(token=self.replacement_fixture)
        elif reason == "allauth-disconnect":
            self._disconnect()
        else:
            account = self.account
            if reason == "token-recreated":
                SocialToken.objects.filter(account=account).delete()
            else:
                if reason == "account-replaced":
                    SocialAccount.objects.filter(pk=self.account.pk).delete()
                account, _ = SocialAccount.objects.get_or_create(
                    user=self.user, provider="google", uid="guard-replacement-identity"
                )
            # The same token string must not conceal a different account/row.
            SocialToken.objects.create(account=account, token=self.access_fixture)
        self.integration.refresh_from_db()
        self.assertTrue(self.integration.calendar_enabled and self.integration.sheets_enabled)

    @override_settings(
        ACCOUNT_REAUTHENTICATION_REQUIRED=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SOCIALACCOUNT_PROVIDERS={"google": {"APP": {"client_id": "isolated", "secret": "fixture"}}},  # nosec B105
    )
    def _disconnect(self):
        if not SocialAccount.objects.filter(pk=self.account.pk).exists():
            return
        # Keep another login method, so the real allauth form allows disconnect.
        SocialAccount.objects.get_or_create(user=self.user, provider="discord", uid="guard-disconnect-remaining")
        client = Client()
        client.force_login(self.user)
        with patch("allauth.socialaccount.adapter.DefaultSocialAccountAdapter.send_notification_mail"):
            response = client.post(reverse("socialaccount_connections"), {"account": self.account.pk})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SocialAccount.objects.filter(pk=self.account.pk).exists())
        self.assertFalse(SocialToken.objects.filter(pk=self.token.pk).exists())

    def test_real_disconnect_is_idempotent_in_the_boundary_fixture(self):
        self._prepare()
        self._disconnect()
        self._disconnect()

    def test_mocked_token_without_an_initial_credential_cannot_send(self):
        for mode in ("sheets", "create"):
            with self.subTest(mode=mode):
                job = self._prepare(mode)
                SocialToken.objects.filter(pk=self.token.pk).delete()
                with (
                    patch("schedules.tasks.get_google_access_token", return_value=self.access_fixture),
                    patch("schedules.tasks.requests.put") as put,
                    patch("schedules.tasks.requests.post") as post,
                ):
                    if mode == "sheets":
                        result = export_google_sheet.run(str(job.pk), self.user.pk, "private-sheet-fixture", "A1", [])
                    else:
                        result = sync_google_calendar.run(self.sync.pk, str(job.pk))
                self._assert_failed(result, job)
                put.assert_not_called()
                post.assert_not_called()

    def test_delivery_validation_does_not_put_access_or_refresh_values_in_sql(self):
        job = self._prepare()
        with patch("schedules.tasks.requests.put", return_value=self._response(data={"updatedCells": 0})):
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual(
                    export_google_sheet.run(str(job.pk), self.user.pk, "private-sheet-fixture", "A1", []), "exported"
                )
        for query in queries:
            self.assertNotIn(self.access_fixture, query["sql"])
            self.assertNotIn(self.refresh_fixture, query["sql"])
