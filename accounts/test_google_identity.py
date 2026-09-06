from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


@override_settings(GOOGLE_OAUTH_CLIENT_ID="isolated-client")
class GoogleIdentityProbe(APITestCase):
    def post_claims(self, claims, **data):
        with patch(
            "accounts.views.api_auth_views.id_token.verify_oauth2_token",
            return_value={"iss": "accounts.google.com", **claims},
        ):
            # Isolated test fixture or mocked credential; never a production secret.
            return self.client.post("/api/auth/google/", {"id_token": "fixture", **data}, format="json")  # nosec B105

    def test_pending_browser_signup_cannot_bypass_mail_confirmation(self):
        owner = get_user_model().objects.create_user(username="pending", email="pending@example.test")
        SocialAccount.objects.create(user=owner, provider="google", uid="pending-id")
        address = EmailAddress.objects.create(user=owner, email=owner.email, verified=False)
        claims = {"sub": "pending-id", "email": owner.email, "email_verified": True}
        self.assertEqual(self.post_claims(claims).status_code, 409)
        self.assertFalse(Token.objects.exists())
        address.verified = True
        address.save()
        response = self.post_claims(claims)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], owner.pk)

    def test_google_login_without_current_email_keeps_verified_identity(self):
        owner = get_user_model().objects.create_user(username="existing", email="existing@example.test")
        SocialAccount.objects.create(user=owner, provider="google", uid="existing-id")
        EmailAddress.objects.create(user=owner, email=owner.email, verified=True)
        response = self.post_claims({"sub": "existing-id"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], owner.pk)

    def test_gmail_signup_is_idempotent_and_preserves_local_profile(self):
        claims = {"sub": "gmail-id", "email": "Name@gmail.com", "email_verified": True, "name": "初期名"}
        first = self.post_claims(claims)
        self.assertEqual(first.status_code, 200)
        second = self.post_claims({**claims, "name": "別名"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["token"], first.data["token"])
        self.assertFalse(second.data["created"])
        self.assertEqual(second.data["user"]["nickname"], "初期名")
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(SocialAccount.objects.count(), 1)

    def test_invalid_new_identity_inputs_leave_no_rows(self):
        valid = {"sub": "valid", "email": "valid@gmail.com", "email_verified": True}
        for changes, data, expected in [
            ({"sub": ""}, {}, 400),
            ({"sub": 123}, {}, 400),
            ({"sub": "a" * 192}, {}, 400),
            ({}, {"link": "true"}, 400),
            ({}, {"link": True}, 401),
            ({"email": None}, {}, 400),
            ({"email_verified": "true"}, {}, 400),
        ]:
            with self.subTest(changes=changes, data=data):
                self.assertEqual(self.post_claims({**valid, **changes}, **data).status_code, expected)
                self.assertFalse(get_user_model().objects.exists())
                self.assertFalse(SocialAccount.objects.exists())
                self.assertFalse(Token.objects.exists())

    def test_duplicate_local_email_requires_confirmation(self):
        for suffix in ("a", "b"):
            get_user_model().objects.create_user(username=suffix, email="duplicate@gmail.com")
        response = self.post_claims({"sub": "new", "email": "duplicate@gmail.com", "email_verified": True})
        self.assertEqual(response.status_code, 409)
        self.assertFalse(SocialAccount.objects.exists())

    def test_integrity_failure_rolls_back_new_user_before_retry(self):
        manager = SocialAccount.objects
        original = manager.create
        attempts = []

        def create(**kwargs):
            attempts.append(kwargs["uid"])
            if len(attempts) == 1:
                raise IntegrityError("isolated collision")
            return original(**kwargs)

        with patch.object(manager, "create", side_effect=create):
            response = self.post_claims({"sub": "retry", "email": "retry@gmail.com", "email_verified": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(SocialAccount.objects.count(), 1)

    def test_repeated_integrity_failure_returns_retry_without_partial_rows(self):
        with patch(
            "accounts.google_identity.SocialAccount.objects.create", side_effect=IntegrityError("secret fixture")
        ):
            response = self.post_claims({"sub": "retry", "email": "retry@gmail.com", "email_verified": True})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", str(response.data))
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(Token.objects.exists())

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_third_party_google_can_be_explicitly_linked_after_local_login(self, verify):
        owner = get_user_model().objects.create_user(username="local-login", email="local@example.test")
        verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "third-party-google",
            "email": "different@example.test",
            "email_verified": True,
        }
        self.client.force_authenticate(owner)
        # Isolated test fixture or mocked credential; never a production secret.
        response = self.client.post(
            "/api/auth/google/", {"id_token": "fixture", "link": True}, format="json"  # nosec B105
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], owner.pk)
        self.assertTrue(SocialAccount.objects.filter(user=owner, provider="google", uid="third-party-google").exists())
        owner.refresh_from_db()
        self.assertEqual(owner.email, "local@example.test")

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_explicit_link_cannot_move_another_users_google_identity(self, verify):
        owner = get_user_model().objects.create_user(username="identity-owner", email="owner@example.test")
        other = get_user_model().objects.create_user(username="other-user", email="other@example.test")
        SocialAccount.objects.create(user=owner, provider="google", uid="owned-id")
        verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "owned-id",
            "email": owner.email,
            "email_verified": True,
        }
        self.client.force_authenticate(other)
        # Isolated test fixture or mocked credential; never a production secret.
        response = self.client.post(
            "/api/auth/google/", {"id_token": "fixture", "link": True}, format="json"  # nosec B105
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(SocialAccount.objects.get(provider="google", uid="owned-id").user_id, owner.pk)

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_new_third_party_google_gets_verification_instructions_without_new_user(self, verify):
        verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "new-id",
            "email": "new@example.test",
            "email_verified": True,
        }
        # Isolated test fixture or mocked credential; never a production secret.
        response = self.client.post("/api/auth/google/", {"id_token": "fixture"}, format="json")  # nosec B105
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "google_link_confirmation_required")
        self.assertIn("login_url", response.data)
        self.assertIn("signup_url", response.data)
        self.assertIn("connections_url", response.data)
        self.assertFalse(get_user_model().objects.exists())

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_inactive_linked_user_gets_no_token(self, verify):
        owner = get_user_model().objects.create_user(username="disabled", is_active=False)
        SocialAccount.objects.create(user=owner, provider="google", uid="disabled-id")
        verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "disabled-id",
            "email": "active@gmail.com",
            "email_verified": True,
        }
        # Isolated test fixture or mocked credential; never a production secret.
        response = self.client.post("/api/auth/google/", {"id_token": "fixture"}, format="json")  # nosec B105
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Token.objects.exists())

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_missing_google_id_is_rejected(self, verify):
        verify.return_value = {"iss": "accounts.google.com", "email": "valid@gmail.com", "email_verified": True}
        # Isolated test fixture or mocked credential; never a production secret.
        response = self.client.post("/api/auth/google/", {"id_token": "fixture"}, format="json")  # nosec B105
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Token.objects.exists())

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_unlinked_third_party_email_cannot_take_existing_account(self, verify):
        owner = get_user_model().objects.create_user(username="mailbox-owner", email="owner@example.test")
        verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "different-google-identity",
            "email": owner.email,
            "email_verified": True,
        }
        # Isolated test fixture or mocked credential; never a production secret.
        response = self.client.post("/api/auth/google/", {"id_token": "fixture"}, format="json")  # nosec B105
        self.assertNotEqual(response.status_code, 200)
        self.assertFalse(Token.objects.filter(user=owner).exists())

    @patch("accounts.views.api_auth_views.id_token.verify_oauth2_token")
    def test_existing_google_identity_does_not_switch_to_new_email_owner(self, verify):
        original = get_user_model().objects.create_user(username="original", email="old@example.test")
        mailbox_owner = get_user_model().objects.create_user(username="new-mailbox", email="new@example.test")
        SocialAccount.objects.create(user=original, provider="google", uid="stable-google-identity")
        EmailAddress.objects.create(user=original, email=original.email, verified=True, primary=True)
        verify.return_value = {
            "iss": "accounts.google.com",
            "sub": "stable-google-identity",
            "email": mailbox_owner.email,
            "email_verified": True,
        }
        # Isolated test fixture or mocked credential; never a production secret.
        response = self.client.post("/api/auth/google/", {"id_token": "fixture"}, format="json")  # nosec B105
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], original.id)
        self.assertFalse(Token.objects.filter(user=mailbox_owner).exists())
