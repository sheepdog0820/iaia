"""Exercise emailed reset links through the real allauth views with local mail."""

import re
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

from allauth.account.forms import default_token_generator
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    ACCOUNT_PREVENT_ENUMERATION=True,
    ACCOUNT_RATE_LIMITS=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PasswordResetLifecycleTests(TestCase):
    # Synthetic credentials used only in disposable test databases.
    old_password = "isolated-original-recovery-password-2026"  # nosec B105
    new_password = "isolated-replacement-recovery-password-2026"  # nosec B105
    issued_at = datetime(2026, 10, 9, 10, 0, 0)

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="recovery-fixture",
            email="recovery-fixture@example.test",
            password=self.old_password,
        )
        EmailAddress.objects.create(user=self.user, email=self.user.email, primary=True, verified=True)

    def request_link(self):
        with patch.object(default_token_generator, "_now", return_value=self.issued_at):
            response = self.client.post(reverse("account_reset_password"), {"email": self.user.email})
        self.assertRedirects(response, reverse("account_reset_password_done"), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        link = re.search(r"https?://[^\s]+/accounts/password/reset/key/[^\s]+", mail.outbox[0].body)
        self.assertIsNotNone(link)
        return urlsplit(link.group()).path

    def open_form(self, path, at):
        with patch.object(default_token_generator, "_now", return_value=at):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            tokenless = response["Location"]
            self.assertTrue(tokenless.endswith("-set-password/"))
            self.assertNotEqual(tokenless, path)
            response = self.client.get(tokenless)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get("token_fail", False))
        self.assertContains(response, 'name="password1"')
        return tokenless

    def assert_link_rejected(self, path, at, method="get"):
        before = get_user_model().objects.get(pk=self.user.pk).password
        with patch.object(default_token_generator, "_now", return_value=at):
            if method == "post":
                response = self.client.post(path, {"password1": self.new_password, "password2": self.new_password})
            else:
                response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["token_fail"])
        self.assertNotContains(response, 'name="password1"')
        self.assertEqual(get_user_model().objects.get(pk=self.user.pk).password, before)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_configured_lifetime_matches_displayed_24_hours(self):
        self.assertEqual(settings.PASSWORD_RESET_TIMEOUT, 24 * 60 * 60)
        self.assertContains(self.client.get(reverse("account_reset_password_done")), "リンクの有効期限は24時間です")

    def test_reset_done_page_is_available_to_anonymous_user(self):
        response = self.client.get(reverse("account_reset_password_done"))
        self.assertEqual(response.status_code, 200, response.headers.get("Location"))

    def test_public_template_pages_are_not_globally_login_protected(self):
        for name in ("home", "account_email_verification_sent", "account_reset_password_from_key_done"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_private_template_routes_still_require_login(self):
        names = (
            "groups_view",
            "statistics_view",
            "character_create",
            "calendar_view",
            "notifications_view",
            "analytics_view",
            "integration-settings",
            "character_list",
            "dashboard",
            "billing",
        )
        for name in names:
            with self.subTest(name=name):
                path = reverse(name)
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith(reverse("account_login")))
                self.assertIn("next=", response["Location"])
        self.client.force_login(self.user)
        for name in names:
            with self.subTest(name=name, authenticated=True):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_link_is_usable_at_24_hour_boundary(self):
        self.open_form(self.request_link(), self.issued_at + timedelta(hours=24))

    def test_link_is_rejected_one_second_after_24_hours(self):
        self.assert_link_rejected(self.request_link(), self.issued_at + timedelta(hours=24, seconds=1))

    def test_open_form_cannot_submit_after_expiration(self):
        path = self.open_form(self.request_link(), self.issued_at + timedelta(hours=23))
        self.assert_link_rejected(path, self.issued_at + timedelta(hours=24, seconds=1), method="post")

    def test_reset_revokes_old_password_session_and_link_then_allows_new_login(self):
        previous_session = Client()
        previous_session.force_login(self.user)
        path = self.request_link()
        at = self.issued_at + timedelta(minutes=5)
        tokenless = self.open_form(path, at)
        with patch.object(default_token_generator, "_now", return_value=at):
            response = self.client.post(tokenless, {"password1": self.new_password, "password2": self.new_password})
        self.assertRedirects(response, reverse("account_reset_password_from_key_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertFalse(self.user.check_password(self.old_password))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(previous_session.get(reverse("dashboard")).status_code, 302)
        self.assertNotIn("_auth_user_id", previous_session.session)
        self.assert_link_rejected(path, at)
        self.assert_link_rejected(tokenless, at, method="post")
        response = self.client.post(
            reverse("account_login"), {"username": self.user.email, "password": self.old_password}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(
            reverse("account_login"), {"username": self.user.email, "password": self.new_password}
        )
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_mismatched_passwords_preserve_account_and_allow_valid_retry(self):
        path = self.open_form(self.request_link(), self.issued_at)
        with patch.object(default_token_generator, "_now", return_value=self.issued_at):
            response = self.client.post(path, {"password1": self.new_password, "password2": self.old_password})
            self.assertEqual(response.status_code, 200)
            self.assertIn("password2", response.context["form"].errors)
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password(self.old_password))
            response = self.client.post(path, {"password1": self.new_password, "password2": self.new_password})
        self.assertRedirects(response, reverse("account_reset_password_from_key_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_tampered_link_preserves_account(self):
        path = self.request_link()
        self.assert_link_rejected(path[:-2] + ("0" if path[-2] != "0" else "1") + "/", self.issued_at)

    def test_email_change_invalidates_previously_issued_link(self):
        path = self.request_link()
        self.user.email = "changed-recovery-fixture@example.test"
        self.user.save(update_fields=["email"])
        self.assert_link_rejected(path, self.issued_at)
