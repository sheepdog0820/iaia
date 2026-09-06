from types import SimpleNamespace
from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


@override_settings(
    # Isolated test fixture or mocked credential; never a production secret.
    TWITTER_CLIENT_ID="isolated",
    TWITTER_CLIENT_SECRET="fixture",
    TWITTER_REDIRECT_URI="https://example.test/callback",  # nosec B106
)
class InactiveOAuthUserTests(APITestCase):
    def authenticate(self, provider, uid="existing-id", email="disabled@example.test"):
        profile = {"id": uid, "username": "provider-name", "email": email, "verified": True}
        payload = {"data": profile} if provider == "twitter" else profile
        with patch(
            "accounts.views.api_auth_views.requests.post",
            # Isolated test fixture or mocked credential; never a production secret.
            return_value=SimpleNamespace(status_code=200, json=lambda: {"access_token": "fixture"}),  # nosec B105
        ):
            with patch(
                "accounts.views.api_auth_views.requests.get",
                return_value=SimpleNamespace(status_code=200, json=lambda: payload),
            ):
                return self.client.post(
                    f"/api/auth/{provider}/",
                    # Isolated test fixture or mocked credential; never a production secret.
                    {"access_token": "fixture", "code": "fixture", "code_verifier": "fixture"},  # nosec B105
                    format="json",
                )

    def test_inactive_existing_identity_is_rejected_without_mutation(self):
        for provider, social_provider in (("twitter", "twitter_oauth2"), ("discord", "discord")):
            with self.subTest(provider=provider):
                user = get_user_model().objects.create_user(
                    username=provider, email="disabled@example.test", is_active=False
                )
                account = SocialAccount.objects.create(
                    user=user, provider=social_provider, uid="existing-id", extra_data={"before": True}
                )
                response = self.authenticate(provider)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("token", response.data)
                self.assertFalse(Token.objects.filter(user=user).exists())
                self.assertFalse(EmailAddress.objects.filter(user=user).exists())
                account.refresh_from_db()
                self.assertEqual(account.extra_data, {"before": True})

    def test_inactive_email_match_does_not_create_discord_link(self):
        user = get_user_model().objects.create_user(username="mailbox", email="disabled@example.test", is_active=False)
        response = self.authenticate("discord", uid="new-id")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(SocialAccount.objects.filter(user=user).exists())
        self.assertFalse(Token.objects.filter(user=user).exists())
        self.assertFalse(EmailAddress.objects.filter(user=user).exists())

    def test_existing_token_is_not_returned_for_inactive_identity(self):
        user = get_user_model().objects.create_user(username="disabled-token", is_active=False)
        token = Token.objects.create(user=user)
        for provider, social_provider in (("twitter", "twitter_oauth2"), ("discord", "discord")):
            with self.subTest(provider=provider):
                SocialAccount.objects.create(user=user, provider=social_provider, uid="existing-id")
                response = self.authenticate(provider)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(token.key, str(response.data))
                self.assertNotIn("token", response.data)
        self.assertEqual(Token.objects.filter(user=user).count(), 1)

    def test_inactive_authenticated_user_cannot_link_provider(self):
        user = get_user_model().objects.create_user(username="disabled-link", is_active=False)
        self.client.force_authenticate(user)
        for provider in ("twitter", "discord"):
            with self.subTest(provider=provider):
                response = self.authenticate(provider, uid="new-id")
                self.assertEqual(response.status_code, 403)
                self.assertFalse(SocialAccount.objects.filter(user=user).exists())
                self.assertFalse(Token.objects.filter(user=user).exists())
