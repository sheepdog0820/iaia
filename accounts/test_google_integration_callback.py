"""Verify integration grants through allauth's real state/connect callback."""

from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlparse

from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase, override_settings

from schedules.models import GoogleIntegration


@override_settings(
    SOCIALACCOUNT_PROVIDERS={
        "google": {
            # Isolated test fixture or mocked credential; never a production secret.
            "APP": {"client_id": "isolated-google", "secret": "fixture"},  # nosec B105
            "SCOPE": ["openid", "email", "profile"],
            "OAUTH_PKCE_ENABLED": True,
        }
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class GoogleIntegrationCallbackTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="grant-owner", email="owner@gmail.com")
        self.client.force_login(self.user)

    def callback(
        self, scopes=None, refresh="refresh-fixture", uid="google-owner", process="connect", access="access-fixture"
    ):
        start = self.client.post(
            "/accounts/google/login/?"
            + urlencode({"process": process, "scope": GoogleIntegration.REQUIRED_CALENDAR_SCOPE})
        )
        self.assertEqual(start.status_code, 302)
        state = parse_qs(urlparse(start.url).query)["state"][0]
        token_response = {
            "access_token": access,
            "refresh_token": refresh,
            # Isolated test fixture or mocked credential; never a production secret.
            "id_token": "id-fixture",  # nosec B105
            "expires_in": 3600,
        }
        if scopes is not None:
            token_response["scope"] = scopes
        with (
            patch(
                "allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token",
                return_value=token_response,
            ),
            patch(
                "allauth.socialaccount.providers.google.views.GoogleOAuth2Adapter._decode_id_token",
                return_value={"sub": uid, "email": "owner@gmail.com", "email_verified": True},
            ),
        ):
            return self.client.get(
                "/accounts/google/login/callback/?"
                + urlencode({"state": state, "code": "code-fixture", "scope": GoogleIntegration.REQUIRED_SHEETS_SCOPE})
            )

    def test_connect_stores_only_google_granted_scope_and_token(self):
        self.assertEqual(self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE).status_code, 302)
        account = SocialAccount.objects.get(user=self.user, provider="google")
        token = SocialToken.objects.get(account=account)
        self.assertEqual(token.token, "access-fixture")
        self.assertEqual(token.token_secret, "refresh-fixture")
        self.assertIsNotNone(token.expires_at)
        integration = GoogleIntegration.objects.get(user=self.user)
        self.assertEqual(integration.scopes, [GoogleIntegration.REQUIRED_CALENDAR_SCOPE])
        self.assertFalse(integration.calendar_enabled)
        response = self.client.put(
            "/api/google/integration/",
            {"calendar_enabled": True, "sheets_enabled": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["calendar_enabled"])
        response = self.client.put(
            "/api/google/integration/", {"sheets_enabled": True}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_reconnect_keeps_refresh_token_and_removes_ungranted_scope(self):
        self.callback(" ".join([GoogleIntegration.REQUIRED_CALENDAR_SCOPE, GoogleIntegration.REQUIRED_SHEETS_SCOPE]))
        GoogleIntegration.objects.filter(user=self.user).update(calendar_enabled=True, sheets_enabled=True)
        self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE, refresh="")
        token = SocialToken.objects.get(account__user=self.user)
        self.assertEqual(token.token_secret, "refresh-fixture")
        integration = GoogleIntegration.objects.get(user=self.user)
        self.assertTrue(integration.calendar_enabled)
        self.assertFalse(integration.sheets_enabled)
        self.assertEqual(integration.scopes, [GoogleIntegration.REQUIRED_CALENDAR_SCOPE])

    def test_missing_scope_does_not_trust_requested_or_callback_scope(self):
        self.callback()
        integration = GoogleIntegration.objects.get(user=self.user)
        self.assertEqual(integration.scopes, [])
        response = self.client.put(
            "/api/google/integration/", {"calendar_enabled": True}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_other_owners_account_cannot_receive_integration_changes(self):
        other = get_user_model().objects.create_user(username="other-grant-owner")
        account = SocialAccount.objects.create(user=other, provider="google", uid="other-google")
        # Isolated test fixture or mocked credential; never a production secret.
        SocialToken.objects.create(account=account, token="other-existing-fixture")  # nosec B106
        GoogleIntegration.objects.create(
            user=other, scopes=[GoogleIntegration.REQUIRED_SHEETS_SCOPE], sheets_enabled=True
        )
        self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE, uid="other-google")
        self.assertEqual(SocialToken.objects.get().token, "other-existing-fixture")
        integration = GoogleIntegration.objects.get()
        self.assertEqual(integration.user_id, other.pk)
        self.assertEqual(integration.scopes, [GoogleIntegration.REQUIRED_SHEETS_SCOPE])
        self.assertTrue(integration.sheets_enabled)

    def test_sign_in_does_not_replace_existing_integration_grant(self):
        self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE)
        self.callback("openid email profile", refresh="different-fixture", process="login", access="login-only-fixture")
        self.assertEqual(SocialToken.objects.get(account__user=self.user).token_secret, "refresh-fixture")
        self.assertEqual(SocialToken.objects.get(account__user=self.user).token, "access-fixture")
        self.assertEqual(
            GoogleIntegration.objects.get(user=self.user).scopes, [GoogleIntegration.REQUIRED_CALENDAR_SCOPE]
        )
        response = self.client.put(
            "/api/google/integration/", {"calendar_enabled": True}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

    def test_switching_back_to_an_older_account_uses_the_selected_credential(self):
        from schedules.google_tokens import get_google_access_token

        self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE, uid="first", access="first-fixture")
        self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE, uid="second", access="second-fixture")
        self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE, uid="first", access="first-new-fixture")
        self.assertEqual(SocialAccount.objects.filter(user=self.user, provider="google").count(), 2)
        self.assertEqual(get_google_access_token(self.user), "first-new-fixture")
        self.assertEqual(SocialToken.objects.filter(account__user=self.user).count(), 1)

    def test_invalid_state_never_exchanges_or_saves_credentials(self):
        with patch("allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token") as exchange:
            response = self.client.get("/accounts/google/login/callback/?state=invalid&code=unused")
        self.assertEqual(response.status_code, 401)
        exchange.assert_not_called()
        self.assertFalse(SocialToken.objects.exists())
        self.assertFalse(GoogleIntegration.objects.exists())

    @override_settings(SOCIALACCOUNT_PROVIDERS={"google": {"SCOPE": ["openid", "email", "profile"]}})
    def test_database_oauth_app_is_associated_with_the_credential(self):
        # Isolated test fixture or mocked credential; never a production secret.
        app = SocialApp.objects.create(
            provider="google", name="isolated", client_id="isolated", secret="fixture"
        )  # nosec B106
        app.sites.add(Site.objects.get_current())
        self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE)
        self.assertEqual(SocialToken.objects.get(account__user=self.user).app_id, app.pk)

    def test_integration_write_failure_rolls_back_credential_replacement(self):
        self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE)
        with patch.object(GoogleIntegration, "save", side_effect=RuntimeError("isolated write failure")):
            with self.assertRaises(RuntimeError):
                self.callback(GoogleIntegration.REQUIRED_SHEETS_SCOPE, access="replacement-fixture")
        self.assertEqual(SocialToken.objects.get(account__user=self.user).token, "access-fixture")
        self.assertEqual(
            GoogleIntegration.objects.get(user=self.user).scopes, [GoogleIntegration.REQUIRED_CALENDAR_SCOPE]
        )

    def test_connect_preserves_other_providers_credentials(self):
        account = SocialAccount.objects.create(user=self.user, provider="discord", uid="discord-owner")
        # Isolated test fixture or mocked credential; never a production secret.
        credential = SocialToken.objects.create(account=account, token="discord-fixture")  # nosec B106
        self.callback(GoogleIntegration.REQUIRED_CALENDAR_SCOPE)
        credential.refresh_from_db()
        self.assertEqual(credential.token, "discord-fixture")
