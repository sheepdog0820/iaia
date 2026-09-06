from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from accounts.adapters import CustomSocialAccountAdapter


class AuthenticationErrorLoggingTests(SimpleTestCase):
    def test_callback_secrets_and_exception_text_are_not_logged(self):
        request = RequestFactory().get(
            "/accounts/google/login/callback/",
            {
                "code": "fixture-code",
                "state": "fixture-state",
                "error_description": "fixture-description",
                # Isolated test fixture or mocked credential; never a production secret.
                "new_token": "fixture-token",  # nosec B105
            },
            HTTP_HOST="fixture-host",
            HTTP_X_FORWARDED_HOST="fixture-forwarded-host",
            HTTP_COOKIE="sessionid=fixture-cookie",
        )
        request.session = SimpleNamespace(session_key="fixture-session")
        try:
            raise ValueError("fixture-exception-with-token")
        except ValueError as exception:
            with self.assertLogs("allauth", level="WARNING") as captured:
                CustomSocialAccountAdapter().on_authentication_error(
                    request, SimpleNamespace(id="google"), error="denied", exception=exception
                )
        output = " ".join(captured.output)
        self.assertNotIn("fixture-", output)
        self.assertNotIn("cookie", output)
        self.assertNotIn("session", output)
        self.assertIn("provider=google", output)
        self.assertIn("code=denied", output)
        self.assertIn("exception_type=ValueError", output)
        self.assertIsNone(captured.records[0].exc_info)

    def test_unknown_error_and_provider_values_are_not_echoed(self):
        with self.assertLogs("allauth", level="WARNING") as captured:
            CustomSocialAccountAdapter().on_authentication_error(
                None, SimpleNamespace(id="fixture-provider-secret"), error="fixture-error-secret"
            )
        output = " ".join(captured.output)
        self.assertNotIn("fixture-", output)
        self.assertIn("provider=unknown", output)
        self.assertIn("code=unknown", output)
        self.assertIn("exception_type=none", output)

    def test_supported_string_provider_retains_cancellation_diagnostic(self):
        with self.assertLogs("allauth", level="WARNING") as captured:
            CustomSocialAccountAdapter().on_authentication_error(None, "discord", error="cancelled")
        self.assertIn("provider=discord", captured.output[0])
        self.assertIn("code=cancelled", captured.output[0])


@override_settings(
    TWITTER_CLIENT_ID="isolated-client",
    # Isolated test fixture or mocked credential; never a production secret.
    TWITTER_CLIENT_SECRET="isolated-secret",  # nosec B106
    TWITTER_REDIRECT_URI="https://example.test/callback",
    DISCORD_CLIENT_ID="isolated-client",
    DISCORD_CLIENT_SECRET="isolated-secret",
    DISCORD_REDIRECT_URI="https://example.test/callback",
)
class ProviderApiErrorLoggingTests(APITestCase):
    def check_failure(self, provider, token_response, user_response, expected):
        with patch("accounts.views.api_auth_views.requests.post", return_value=token_response) as post:
            with patch("accounts.views.api_auth_views.requests.get", return_value=user_response):
                if isinstance(token_response, Exception):
                    post.side_effect = token_response
                with self.assertLogs("accounts.views.api_auth_views", level="ERROR") as captured:
                    response = self.client.post(
                        f"/api/auth/{provider}/",
                        {"code": "fixture-code", "code_verifier": "fixture-verifier"},
                        format="json",
                    )
        self.assertEqual(response.status_code, expected)
        self.assertNotIn("fixture-", " ".join(captured.output))
        self.assertNotIn("fixture-", str(response.data))
        self.assertNotIn("detail", response.data)

    def test_token_response_bodies_are_not_logged(self):
        for provider in ("twitter", "discord"):
            with self.subTest(provider=provider):
                self.check_failure(provider, SimpleNamespace(status_code=400, text="fixture-token-body"), None, 400)

    def test_user_response_bodies_are_not_logged(self):
        for provider in ("twitter", "discord"):
            with self.subTest(provider=provider):
                self.check_failure(
                    provider,
                    # Isolated test fixture or mocked credential; never a production secret.
                    SimpleNamespace(status_code=200, json=lambda: {"access_token": "fixture-token"}),  # nosec B105
                    SimpleNamespace(status_code=403, text="fixture-user-body"),
                    400,
                )

    def test_internal_exception_text_is_not_logged_or_returned(self):
        for provider in ("twitter", "discord"):
            with self.subTest(provider=provider):
                self.check_failure(provider, RuntimeError("fixture-exception-token"), None, 500)
