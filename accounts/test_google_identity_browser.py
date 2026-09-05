"""Exercise allauth's real signup/connect flow with isolated provider claims."""

import json

from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import path

from tableno.urls import urlpatterns as application_patterns


def isolated_google_callback(request):
    claims = json.loads(request.body)
    provider = get_adapter().get_provider(request, "google")
    sociallogin = provider.sociallogin_from_response(request, claims)
    sociallogin.state = {"process": claims.get("process", "login")}
    return complete_social_login(request, sociallogin)


urlpatterns = [path("isolated-google-callback/", isolated_google_callback), *application_patterns]


@override_settings(
    ROOT_URLCONF=__name__,
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SOCIALACCOUNT_PROVIDERS={"google": {"APP": {"client_id": "isolated", "secret": "fixture"}}},
)
class GoogleBrowserIdentityTests(TestCase):
    def callback(self, **claims):
        return self.client.post("/isolated-google-callback/", claims, content_type="application/json")

    def test_third_party_signup_requires_email_verification(self):
        response = self.callback(sub="new-id", email="new@example.test", email_verified=True)
        self.assertEqual(response.status_code, 302)
        self.assertIn("confirm-email", response.url)
        account = SocialAccount.objects.get(provider="google", uid="new-id")
        self.assertFalse(EmailAddress.objects.get(user=account.user).verified)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_existing_uid_with_changed_email_logs_in_original_owner(self):
        original = get_user_model().objects.create_user(username="original", email="original@example.test")
        other = get_user_model().objects.create_user(username="other", email="other@example.test")
        EmailAddress.objects.create(user=original, email=original.email, verified=True, primary=True)
        SocialAccount.objects.create(user=original, provider="google", uid="stable-id")
        response = self.callback(sub="stable-id", email=other.email, email_verified=True)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(original.pk))
        self.assertFalse(EmailAddress.objects.filter(user=other, verified=True).exists())

    def test_connect_uses_authenticated_owner_even_when_email_matches_someone_else(self):
        original = get_user_model().objects.create_user(username="original", email="original@example.test")
        other = get_user_model().objects.create_user(username="other", email="other@gmail.com")
        EmailAddress.objects.create(user=original, email=original.email, verified=True, primary=True)
        self.client.force_login(original)
        response = self.callback(sub="new-id", email=other.email, email_verified=True, process="connect")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SocialAccount.objects.get(provider="google", uid="new-id").user_id, original.pk)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(original.pk))

    def test_connections_buttons_request_connect_process(self):
        user = get_user_model().objects.create_user(username="connections", email="connections@example.test")
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        self.client.force_login(user)
        response = self.client.get("/accounts/3rdparty/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "process=connect")

    @override_settings(SOCIALACCOUNT_EMAIL_AUTHENTICATION=True)
    def test_third_party_email_cannot_authenticate_existing_mailbox_owner(self):
        owner = get_user_model().objects.create_user(username="mailbox", email="owner@example.test")
        EmailAddress.objects.create(user=owner, email=owner.email, verified=True, primary=True)
        response = self.callback(sub="unlinked-id", email=owner.email, email_verified=True)
        self.assertIn(response.status_code, (200, 302))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(SocialAccount.objects.filter(user=owner, uid="unlinked-id").exists())

    def test_explicit_connect_cannot_transfer_existing_identity(self):
        owner = get_user_model().objects.create_user(username="owner", email="owner@example.test")
        other = get_user_model().objects.create_user(username="other", email="other@example.test")
        EmailAddress.objects.create(user=other, email=other.email, verified=True, primary=True)
        SocialAccount.objects.create(user=owner, provider="google", uid="owned-id")
        self.client.force_login(other)
        response = self.callback(sub="owned-id", email=owner.email, email_verified=True, process="connect")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SocialAccount.objects.get(uid="owned-id", provider="google").user_id, owner.pk)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(other.pk))
