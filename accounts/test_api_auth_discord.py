from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

User = get_user_model()


class DummyResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(self._payload)

    def json(self):
        return self._payload


@override_settings(
    DISCORD_CLIENT_ID="test-client",
    DISCORD_CLIENT_SECRET="test-secret",
    DISCORD_REDIRECT_URI="http://localhost:3000/callback",
)
class DiscordAuthApiTests(APITestCase):
    def setUp(self):
        self.url = "/api/auth/discord/"

    def test_requires_code_or_token(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("accounts.views.api_auth_views.requests.post")
    def test_token_exchange_failure(self, mock_post):
        mock_post.return_value = DummyResponse(400, {"error": "invalid"})

        response = self.client.post(self.url, {"code": "bad"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("accounts.views.api_auth_views.requests.get")
    @patch("accounts.views.api_auth_views.requests.post")
    def test_user_fetch_failure(self, mock_post, mock_get):
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})
        mock_get.return_value = DummyResponse(400, {"error": "invalid"})

        response = self.client.post(self.url, {"code": "code"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("accounts.views.api_auth_views.requests.get")
    @patch("accounts.views.api_auth_views.requests.post")
    def test_create_user_from_discord(self, mock_post, mock_get):
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})
        mock_get.return_value = DummyResponse(
            200,
            {
                "id": "123",
                "username": "discorduser",
                "global_name": "Discord User",
                "email": "discord@example.com",
                "verified": True,
            },
        )

        response = self.client.post(
            self.url, {"code": "code", "redirect_uri": "http://localhost:3000/callback"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["created"])
        self.assertFalse(data.get("linked"))
        self.assertEqual(data["user"]["email"], "discord@example.com")
        user = User.objects.get(email="discord@example.com")
        self.assertTrue(SocialAccount.objects.filter(provider="discord", uid="123", user=user).exists())
        self.assertTrue(EmailAddress.objects.filter(user=user, email=user.email, verified=True, primary=True).exists())

    @patch("accounts.views.api_auth_views.requests.get")
    @patch("accounts.views.api_auth_views.requests.post")
    def test_verified_email_reuses_existing_user(self, mock_post, mock_get):
        existing = User.objects.create_user(
            username="existing-discord",
            email="same.discord@example.com",
            password="pass1234",
            nickname="",
        )
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})
        mock_get.return_value = DummyResponse(
            200,
            {
                "id": "456",
                "username": "discordexisting",
                "global_name": "Discord Existing",
                "email": "same.discord@example.com",
                "verified": True,
            },
        )

        response = self.client.post(
            self.url, {"code": "code", "redirect_uri": "http://localhost:3000/callback"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["created"])
        self.assertEqual(data["user"]["id"], existing.id)
        self.assertEqual(User.objects.filter(email="same.discord@example.com").count(), 1)
        self.assertTrue(
            SocialAccount.objects.filter(
                provider="discord",
                uid="456",
                user=existing,
            ).exists()
        )
        existing.refresh_from_db()
        self.assertEqual(existing.nickname, "Discord Existing")
        self.assertTrue(
            EmailAddress.objects.filter(user=existing, email=existing.email, verified=True, primary=True).exists()
        )

    @patch("accounts.views.api_auth_views.requests.get")
    @patch("accounts.views.api_auth_views.requests.post")
    def test_unverified_email_does_not_reuse_existing_user(self, mock_post, mock_get):
        existing = User.objects.create_user(
            username="existing-unverified-discord",
            email="unverified.discord@example.com",
            password="pass1234",
            nickname="",
        )
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})
        mock_get.return_value = DummyResponse(
            200,
            {
                "id": "789",
                "username": "discordunverified",
                "global_name": "Discord Unverified",
                "email": "unverified.discord@example.com",
                "verified": False,
            },
        )

        response = self.client.post(
            self.url, {"code": "code", "redirect_uri": "http://localhost:3000/callback"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["created"])
        self.assertNotEqual(data["user"]["id"], existing.id)
        self.assertEqual(data["user"]["email"], "")
        self.assertEqual(User.objects.filter(email="unverified.discord@example.com").count(), 1)
        self.assertFalse(EmailAddress.objects.filter(email="unverified.discord@example.com").exists())
        self.assertTrue(
            SocialAccount.objects.filter(
                provider="discord",
                uid="789",
                user_id=data["user"]["id"],
            ).exists()
        )

    @patch("accounts.views.api_auth_views.requests.get")
    @patch("accounts.views.api_auth_views.requests.post")
    def test_link_conflict(self, mock_post, mock_get):
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})
        mock_get.return_value = DummyResponse(
            200,
            {
                "id": "999",
                "username": "conflict_user",
            },
        )

        owner = User.objects.create_user(username="owner", email="")
        SocialAccount.objects.create(
            user=owner,
            provider="discord",
            uid="999",
            extra_data={"id": "999"},
        )

        other = User.objects.create_user(username="other", email="")
        self.client.force_authenticate(user=other)

        response = self.client.post(self.url, {"code": "code"}, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertIn("error", response.json())
