from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.authtoken.models import Token
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
    # Isolated test fixture or mocked credential; never a production secret.
    DISCORD_CLIENT_SECRET="test-secret",  # nosec B106
    DISCORD_REDIRECT_URI="http://localhost:3000/callback",
)
class DiscordAuthApiTests(APITestCase):
    def setUp(self):
        self.url = "/api/auth/discord/"

    @patch("accounts.views.api_auth_views.requests.get")
    def test_only_boolean_true_can_match_an_existing_email(self, mock_get):
        owner = User.objects.create_user(username="mailbox-owner", email="owner@example.test")
        for index, value in enumerate((False, None, "false", "true", 1)):
            with self.subTest(value=value):
                mock_get.return_value = DummyResponse(
                    200,
                    {"id": f"unverified-{index}", "username": f"new-{index}", "email": owner.email, "verified": value},
                )
                # Isolated test fixture or mocked credential; never a production secret.
                response = self.client.post(self.url, {"access_token": "fixture"}, format="json")  # nosec B105
                self.assertEqual(response.status_code, 200)
                self.assertNotEqual(response.data["user"]["id"], owner.pk)
                self.assertFalse(Token.objects.filter(user=owner).exists())
                self.assertFalse(SocialAccount.objects.filter(user=owner).exists())
                self.assertFalse(EmailAddress.objects.filter(user=owner, verified=True).exists())

    @patch("accounts.views.api_auth_views.requests.get")
    def test_existing_identity_email_case_change_does_not_duplicate_mailbox(self, mock_get):
        owner = User.objects.create_user(username="case-owner", email="case@example.test")
        EmailAddress.objects.create(user=owner, email=owner.email, verified=True, primary=True)
        SocialAccount.objects.create(user=owner, provider="discord", uid="case-id")
        mock_get.return_value = DummyResponse(
            200, {"id": "case-id", "username": "case-owner", "email": owner.email.upper(), "verified": True}
        )
        # Isolated test fixture or mocked credential; never a production secret.
        response = self.client.post(self.url, {"access_token": "fixture"}, format="json")  # nosec B105
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], owner.pk)
        self.assertEqual(EmailAddress.objects.filter(user=owner).count(), 1)

    @patch("accounts.views.api_auth_views.requests.get")
    def test_existing_identity_email_change_preserves_local_mailbox(self, mock_get):
        owner = User.objects.create_user(username="original", email="original@example.test")
        other = User.objects.create_user(username="other", email="other@example.test")
        EmailAddress.objects.create(user=owner, email=owner.email, verified=True, primary=True)
        SocialAccount.objects.create(user=owner, provider="discord", uid="stable-id")
        mock_get.return_value = DummyResponse(
            200, {"id": "stable-id", "username": "original", "email": other.email, "verified": True}
        )
        # Isolated test fixture or mocked credential; never a production secret.
        response = self.client.post(self.url, {"access_token": "fixture"}, format="json")  # nosec B105
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], owner.pk)
        owner.refresh_from_db()
        self.assertEqual(owner.email, "original@example.test")
        self.assertEqual(list(EmailAddress.objects.filter(user=owner).values_list("email", flat=True)), [owner.email])
        self.assertFalse(Token.objects.filter(user=other).exists())
        self.assertFalse(EmailAddress.objects.filter(user=other).exists())

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
        # Isolated test fixture or mocked credential; never a production secret.
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})  # nosec B105
        mock_get.return_value = DummyResponse(400, {"error": "invalid"})

        response = self.client.post(self.url, {"code": "code"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("accounts.views.api_auth_views.requests.get")
    @patch("accounts.views.api_auth_views.requests.post")
    def test_create_user_from_discord(self, mock_post, mock_get):
        # Isolated test fixture or mocked credential; never a production secret.
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})  # nosec B105
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
            # Isolated test fixture or mocked credential; never a production secret.
            password="pass1234",  # nosec B106
            nickname="",
        )
        # Isolated test fixture or mocked credential; never a production secret.
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})  # nosec B105
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
            # Isolated test fixture or mocked credential; never a production secret.
            password="pass1234",  # nosec B106
            nickname="",
        )
        # Isolated test fixture or mocked credential; never a production secret.
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})  # nosec B105
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
        # Isolated test fixture or mocked credential; never a production secret.
        mock_post.return_value = DummyResponse(200, {"access_token": "token"})  # nosec B105
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
