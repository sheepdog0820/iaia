from types import SimpleNamespace
from unittest.mock import Mock

from django.test import RequestFactory, TestCase

from accounts.adapters import CustomSocialAccountAdapter
from accounts.models import CustomUser


class SocialLinkSafetyTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(username="social-link-owner", email="owner@example.test")
        self.request = RequestFactory().get("/accounts/google/login/callback/")
        self.adapter = CustomSocialAccountAdapter()

    def login(self, provider, data, existing=False):
        return SimpleNamespace(
            account=SimpleNamespace(provider=provider, extra_data=data),
            is_existing=existing,
            connect=Mock(),
        )

    def test_google_unverified_missing_and_non_boolean_claims_cannot_link(self):
        for extra in ({}, {"email_verified": False}, {"verified_email": False}, {"email_verified": "true"}):
            with self.subTest(extra=extra):
                login = self.login("google", {"email": self.owner.email, **extra})
                self.adapter.pre_social_login(self.request, login)
                login.connect.assert_not_called()

    def test_verified_google_and_discord_can_link(self):
        for provider, claim in (("google", "email_verified"), ("google", "verified_email"), ("discord", "verified")):
            with self.subTest(provider=provider, claim=claim):
                login = self.login(provider, {"email": self.owner.email, claim: True, "hd": "example.test"})
                self.adapter.pre_social_login(self.request, login)
                login.connect.assert_called_once_with(self.request, self.owner)

    def test_existing_social_identity_is_not_relinked_by_email(self):
        login = self.login("google", {"email": self.owner.email, "email_verified": True}, existing=True)
        self.adapter.pre_social_login(self.request, login)
        login.connect.assert_not_called()

    def test_unverified_discord_and_unknown_provider_cannot_link(self):
        for provider, value in (("discord", False), ("discord", "false"), ("twitter_oauth2", True)):
            with self.subTest(provider=provider, value=value):
                login = self.login(provider, {"email": self.owner.email, "verified": value})
                self.adapter.pre_social_login(self.request, login)
                login.connect.assert_not_called()

    def test_third_party_google_requires_mailbox_confirmation(self):
        login = self.login("google", {"email": self.owner.email, "email_verified": True})
        address = SimpleNamespace(verified=True)
        login.email_addresses = [address]
        self.adapter.pre_social_login(self.request, login)
        login.connect.assert_not_called()
        self.assertFalse(address.verified)

    def test_explicit_connect_does_not_select_owner_by_email(self):
        login = self.login("google", {"email": self.owner.email, "email_verified": True, "hd": "example.test"})
        login.state = {"process": "connect"}
        self.adapter.pre_social_login(self.request, login)
        login.connect.assert_not_called()

    def test_missing_email_or_local_user_does_not_link(self):
        for data in ({"email_verified": True}, {"email": "absent@example.test", "email_verified": True}):
            with self.subTest(data=data):
                login = self.login("google", data)
                self.adapter.pre_social_login(self.request, login)
                login.connect.assert_not_called()
