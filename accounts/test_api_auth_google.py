from types import SimpleNamespace
from unittest.mock import patch

import requests
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

User = get_user_model()


class DummyResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class DummyFlow:
    def __init__(self):
        self.redirect_uri = None
        self.credentials = None

    def fetch_token(self, code, timeout):
        self.credentials = SimpleNamespace(id_token="dummy-id-token")


@override_settings(GOOGLE_OAUTH_CLIENT_ID="test-client", GOOGLE_OAUTH_CLIENT_SECRET="test-secret")
class GoogleAuthApiTests(APITestCase):
    def setUp(self):
        self.url = "/api/auth/google/"

    def test_google_auth_requires_credentials(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("accounts.views.api_auth_views.requests.get")
    def test_access_token_requires_matching_client_and_subject(self, mock_get):
        info = {"audience": "test-client", "issued_to": "test-client", "user_id": "uid", "expires_in": 3600}
        profile = {"id": "uid", "email": "owner@gmail.com", "verified_email": True}
        for changes in (
            {"audience": "other-client"},
            {"issued_to": "other-client"},
            {"expires_in": 0},
            {"user_id": "other-id"},
        ):
            with self.subTest(changes=changes):
                mock_get.side_effect = [DummyResponse(200, {**info, **changes}), DummyResponse(200, profile)]
                response = self.client.post(self.url, {"access_token": "fixture"}, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertFalse(User.objects.exists())

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="")
    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_missing_client_configuration_does_not_disable_audience_validation(self, verify):
        response = self.client.post(self.url, {"id_token": "fixture"}, format="json")
        self.assertEqual(response.status_code, 503)
        verify.assert_not_called()

    @patch("accounts.views.api_auth_views.Flow.from_client_config")
    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_code_flow_rejects_wrong_issuer(self, verify, flow):
        flow.return_value = DummyFlow()
        verify.return_value = {"iss": "other-issuer", "sub": "uid", "email": "owner@gmail.com", "email_verified": True}
        response = self.client.post(self.url, {"code": "fixture"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    @patch("accounts.views.api_auth_views.requests.get")
    def test_access_profile_failure_is_rejected(self, mock_get):
        info = {"audience": "test-client", "issued_to": "test-client", "user_id": "uid", "expires_in": 3600}
        mock_get.side_effect = [DummyResponse(200, info), DummyResponse(401)]
        response = self.client.post(self.url, {"access_token": "fixture"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    @patch("accounts.views.api_auth_views.requests.get")
    def test_google_failures_do_not_expose_tokens_or_exception_details(self, mock_get):
        for exception, expected in ((requests.Timeout("secret-token"), 503), (RuntimeError("secret-token"), 500)):
            with self.subTest(exception=type(exception).__name__):
                mock_get.side_effect = exception
                with self.assertLogs("accounts.views.api_auth_views", level="WARNING") as logs:
                    response = self.client.post(self.url, {"access_token": "secret-token"}, format="json")
                self.assertEqual(response.status_code, expected)
                self.assertNotIn("secret-token", str(response.data))
                self.assertNotIn("secret-token", str(logs.output))
                self.assertFalse(User.objects.exists())

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_google_auth_id_token_creates_user(self, mock_verify):
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "google-fixture-uid",
            "hd": "example.com",
            "email": "idtoken.user@example.com",
            "given_name": "IdToken",
            "family_name": "User",
            "name": "IdToken User",
            "picture": "http://example.com/pic.jpg",
            "email_verified": True,
        }

        response = self.client.post(self.url, {"id_token": "fake"}, format="json")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("token", data)
        self.assertIn("user", data)
        self.assertTrue(data["created"])
        self.assertEqual(data["user"]["email"], "idtoken.user@example.com")

        user = User.objects.get(email="idtoken.user@example.com")
        self.assertTrue(EmailAddress.objects.filter(user=user, email=user.email, verified=True, primary=True).exists())

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_google_auth_id_token_reuses_existing_email_user(self, mock_verify):
        existing = User.objects.create_user(
            username="existing-google",
            email="same.google@example.com",
            password="pass1234",
            nickname="",
        )
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "google-fixture-uid",
            "hd": "example.com",
            "email": "same.google@example.com",
            "given_name": "Existing",
            "family_name": "Google",
            "name": "Existing Google",
            "email_verified": True,
        }

        response = self.client.post(self.url, {"id_token": "fake"}, format="json")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["created"])
        self.assertEqual(data["user"]["id"], existing.id)
        self.assertEqual(User.objects.filter(email="same.google@example.com").count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.nickname, "Existing Google")
        self.assertTrue(
            EmailAddress.objects.filter(user=existing, email=existing.email, verified=True, primary=True).exists()
        )

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_google_auth_id_token_invalid_issuer(self, mock_verify):
        mock_verify.return_value = {
            "iss": "https://invalid.example.com",
            "email": "badissuer@example.com",
            "email_verified": True,
        }

        response = self.client.post(self.url, {"id_token": "fake"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_google_auth_id_token_unverified_email(self, mock_verify):
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "google-fixture-uid",
            "hd": "example.com",
            "email": "unverified@example.com",
            "email_verified": False,
        }

        response = self.client.post(self.url, {"id_token": "fake"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("accounts.views.api_auth_views.requests.get")
    def test_google_auth_access_token_success(self, mock_get):
        mock_get.return_value = DummyResponse(
            200,
            {
                "email": "access.user@example.com",
                "given_name": "Access",
                "family_name": "User",
                "name": "Access User",
                "picture": "http://example.com/pic.jpg",
                "verified_email": True,
                "id": "google-access-uid",
                "user_id": "google-access-uid",
                "audience": "test-client",
                "issued_to": "test-client",
                "expires_in": 3600,
                "hd": "example.com",
            },
        )

        response = self.client.post(self.url, {"access_token": "fake"}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertTrue(data["created"])
        self.assertEqual(data["user"]["email"], "access.user@example.com")
        user = User.objects.get(email="access.user@example.com")
        self.assertTrue(EmailAddress.objects.filter(user=user, email=user.email, verified=True, primary=True).exists())

    @patch("accounts.views.api_auth_views.requests.get")
    def test_google_auth_access_token_invalid(self, mock_get):
        mock_get.return_value = DummyResponse(400, {"error": "invalid"})

        response = self.client.post(self.url, {"access_token": "fake"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("accounts.views.api_auth_views.Flow.from_client_config")
    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_google_auth_code_flow_success(self, mock_verify, mock_flow):
        mock_flow.return_value = DummyFlow()
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "google-fixture-uid",
            "hd": "example.com",
            "email": "code.user@example.com",
            "given_name": "Code",
            "family_name": "User",
            "name": "Code User",
            "email_verified": True,
        }

        response = self.client.post(
            self.url,
            {"code": "fake-code", "redirect_uri": "http://localhost:3000"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertTrue(data["created"])
        self.assertEqual(data["user"]["email"], "code.user@example.com")
        user = User.objects.get(email="code.user@example.com")
        self.assertTrue(EmailAddress.objects.filter(user=user, email=user.email, verified=True, primary=True).exists())
