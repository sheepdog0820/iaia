from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings


class EnsureDevLoginUserCommandTests(TestCase):
    def call_command(self, **options):
        output = StringIO()
        call_command("ensure_dev_login_user", stdout=output, **options)
        return output.getvalue()

    @override_settings(DEBUG=True)
    def test_creates_login_user_with_supplied_password(self):
        output = self.call_command(
            username="testuser",
            password="testpass123",
            email="testuser@example.local",
            nickname="Test User",
        )

        user = get_user_model().objects.get(username="testuser")
        self.assertTrue(user.check_password("testpass123"))
        self.assertEqual(user.email, "testuser@example.local")
        self.assertEqual(user.nickname, "Test User")
        self.assertIn("Created development login user: testuser", output)

    @override_settings(DEBUG=True)
    def test_updates_existing_user_idempotently(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="testuser",
            password="oldpass123",
            email="old@example.local",
            nickname="Old",
        )

        output = self.call_command(
            username="testuser",
            password="newpass123",
            email="new@example.local",
            nickname="New",
            staff=True,
            premium=True,
        )

        user = user_model.objects.get(username="testuser")
        self.assertTrue(user.check_password("newpass123"))
        self.assertEqual(user.email, "new@example.local")
        self.assertEqual(user.nickname, "New")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_premium)
        self.assertIn("Updated development login user: testuser", output)

    @override_settings(DEBUG=False)
    def test_refuses_non_debug_without_explicit_override(self):
        with self.assertRaisesMessage(
            CommandError,
            "ensure_dev_login_user is only available when DEBUG=True",
        ):
            self.call_command(username="testuser", password="testpass123")

    @override_settings(DEBUG=False)
    def test_allows_non_debug_with_explicit_override(self):
        self.call_command(
            username="testuser",
            password="testpass123",
            allow_non_debug=True,
        )

        user = get_user_model().objects.get(username="testuser")
        self.assertTrue(user.check_password("testpass123"))

    @override_settings(DEBUG=True)
    def test_requires_password(self):
        with self.assertRaisesMessage(CommandError, "--password is required"):
            self.call_command(username="testuser", password="")
