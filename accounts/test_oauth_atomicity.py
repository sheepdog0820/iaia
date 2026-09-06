from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase


@override_settings(TWITTER_CLIENT_ID="isolated", TWITTER_REDIRECT_URI="https://example.test/callback")
class OAuthAtomicityTests(APITestCase):
    def login(self, provider):
        profile = {"id": "fixture-id", "username": "fixture-name", "email": "fixture@example.test", "verified": True}
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

    def test_token_creation_failure_leaves_no_partial_signup(self):
        for provider in ("twitter", "discord"):
            with self.subTest(provider=provider):
                with patch(
                    "accounts.views.api_auth_views.Token.objects.get_or_create",
                    side_effect=IntegrityError("fixture collision"),
                ):
                    response = self.login(provider)
                self.assertFalse(get_user_model().objects.exists())
                self.assertFalse(SocialAccount.objects.exists())
                self.assertFalse(EmailAddress.objects.exists())
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("fixture collision", str(response.data))

    def test_failed_existing_login_preserves_profile_and_verification(self):
        for provider, provider_id in (("twitter", "twitter_oauth2"), ("discord", "discord")):
            with self.subTest(provider=provider):
                user = get_user_model().objects.create_user(
                    username=provider, email="fixture@example.test", nickname=""
                )
                account = SocialAccount.objects.create(
                    user=user, provider=provider_id, uid="fixture-id", extra_data={"before": True}
                )
                address = EmailAddress.objects.create(user=user, email=user.email, verified=False, primary=True)
                with patch(
                    "accounts.views.api_auth_views.Token.objects.get_or_create",
                    side_effect=IntegrityError("fixture collision"),
                ):
                    response = self.login(provider)
                self.assertEqual(response.status_code, 503)
                account.refresh_from_db()
                address.refresh_from_db()
                user.refresh_from_db()
                self.assertEqual(account.extra_data, {"before": True})
                self.assertFalse(address.verified)
                self.assertEqual(user.nickname, "")


@skipUnlessDBFeature("has_select_for_update")
@override_settings(TWITTER_CLIENT_ID="isolated", TWITTER_REDIRECT_URI="https://example.test/callback")
class OAuthSignupConcurrencyTests(TransactionTestCase):
    def check_concurrent_signup(self, provider):
        barrier = Barrier(2)
        original_create = get_user_model().objects.create_user
        profile = {
            "id": "concurrent-id",
            "username": "concurrent",
            "email": "concurrent@example.test",
            "verified": True,
        }
        payload = {"data": profile} if provider == "twitter" else profile

        def create_user(*args, **kwargs):
            barrier.wait(timeout=15)
            return original_create(*args, **kwargs)

        def login():
            close_old_connections()
            try:
                response = APIClient().post(
                    f"/api/auth/{provider}/",
                    # Isolated test fixture or mocked credential; never a production secret.
                    {"access_token": "fixture", "code": "fixture", "code_verifier": "fixture"},  # nosec B105
                    format="json",
                )
                return response.status_code, response.data
            finally:
                close_old_connections()

        with patch(
            "accounts.views.api_auth_views.requests.post",
            # Isolated test fixture or mocked credential; never a production secret.
            return_value=SimpleNamespace(status_code=200, json=lambda: {"access_token": "fixture"}),  # nosec B105
        ):
            with patch(
                "accounts.views.api_auth_views.requests.get",
                return_value=SimpleNamespace(status_code=200, json=lambda: payload),
            ):
                with patch("accounts.views.api_auth_views.User.objects.create_user", side_effect=create_user):
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        results = list(executor.map(lambda _: login(), range(2)))
                self.assertEqual(sorted(result[0] for result in results), [200, 503])
                successful = next(data for code, data in results if code == 200)
                rejected = next(data for code, data in results if code == 503)
                self.assertNotIn("token", rejected)
                retry_status, retry = login()
                self.assertEqual(retry_status, 200)
                self.assertEqual(retry["user"]["id"], successful["user"]["id"])
                self.assertEqual(retry["token"], successful["token"])
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(SocialAccount.objects.count(), 1)
        self.assertEqual(Token.objects.count(), 1)
        self.assertEqual(EmailAddress.objects.count(), 1 if provider == "discord" else 0)

    def test_concurrent_twitter_signup_and_retry(self):
        self.check_concurrent_signup("twitter")

    def test_concurrent_discord_signup_and_retry(self):
        self.check_concurrent_signup("discord")
