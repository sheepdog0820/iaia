from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase, override_settings

from accounts.forms import CustomLoginForm
from accounts.models import CustomUser


class LoginLookupFailureTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="lookup-user", email="lookup@example.test", password="fixture-password"
        )

    def form(self, username=None):
        return CustomLoginForm(data={"username": username or self.user.email, "password": "fixture-password"})

    def test_email_lookup_failure_does_not_fall_back_to_user_table(self):
        with patch("accounts.forms.EmailAddress.objects.select_related", side_effect=OperationalError("secret")):
            with patch("accounts.forms.CustomUser.objects.get") as fallback:
                with self.assertLogs("accounts.forms", level="WARNING") as logs:
                    form = self.form()
                    self.assertFalse(form.is_valid())
                fallback.assert_not_called()
        self.assertNotIn("secret", str(logs.output))
        self.assertIn("時間をおいて再度", str(form.errors))
        self.assertNotIn("secret", str(form.errors))

    def test_login_page_renders_retry_message_without_authenticating(self):
        with patch("accounts.forms.EmailAddress.objects.select_related", side_effect=OperationalError("secret")):
            response = self.client.post(
                "/accounts/login/", {"username": self.user.email, "password": "fixture-password"}
            )
        self.assertContains(response, "ログイン情報を確認できませんでした。時間をおいて再度お試しください。")
        self.assertNotContains(response, "secret")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_user_email_lookup_failure_is_retryable(self):
        with patch("accounts.forms.CustomUser.objects.get", side_effect=OperationalError("secret")):
            form = self.form()
            self.assertFalse(form.is_valid())
        self.assertIn("時間をおいて再度", str(form.errors))
        self.assertNotIn("secret", str(form.errors))

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_verification_lookup_failure_does_not_allow_login(self):
        with patch("accounts.forms.EmailAddress.objects.filter", side_effect=OperationalError("secret")):
            form = self.form(self.user.username)
            self.assertFalse(form.is_valid())
        self.assertIn("時間をおいて再度", str(form.errors))
        self.assertNotIn("secret", str(form.errors))
