"""Persist Google's token response only for an authenticated integration connect."""

from allauth.socialaccount.models import SocialAccount, SocialToken
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView
from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.contrib.auth import get_user_model
from django.db import transaction
from django.dispatch import receiver
from django.utils import timezone

from schedules.models import GoogleIntegration


class IntegrationGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    def complete_login(self, request, app, token, **kwargs):
        login = super().complete_login(request, app, token, **kwargs)
        raw_scopes = kwargs["response"].get("scope")
        # Only the server-to-server token response establishes granted scopes.
        login.google_integration_scopes = sorted(set(raw_scopes.split())) if isinstance(raw_scopes, str) else []
        return login


oauth2_callback = OAuth2CallbackView.adapter_view(IntegrationGoogleOAuth2Adapter)


@receiver(social_account_added, dispatch_uid="tableno.google.integration.added")
@receiver(social_account_updated, dispatch_uid="tableno.google.integration.updated")
def store_google_integration_grant(sender, request, sociallogin, **kwargs):
    scopes = getattr(sociallogin, "google_integration_scopes", None)
    if (
        scopes is None
        or sociallogin.account.provider != "google"
        or sociallogin.state.get("process") != "connect"
        or not request.user.is_authenticated
        or request.user.pk != sociallogin.account.user_id
        or not sociallogin.token
    ):
        return
    with transaction.atomic():
        # Serialize different Google accounts connecting to the same Tableno user.
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        account = SocialAccount.objects.select_for_update().get(pk=sociallogin.account.pk, user_id=request.user.pk)
        token = sociallogin.token
        app = token.app if token.app_id else None
        stored, _ = SocialToken.objects.get_or_create(account=account, app=app)
        stored.token = token.token
        # Google does not return a new refresh token on every consent response.
        if token.token_secret:
            stored.token_secret = token.token_secret
        stored.expires_at = token.expires_at
        stored.save(update_fields=["token", "token_secret", "expires_at"])
        # There is one active integration per user; keep its credential unambiguous.
        SocialToken.objects.filter(account__user=request.user, account__provider="google").exclude(
            pk=stored.pk
        ).delete()
        integration, _ = GoogleIntegration.objects.select_for_update().get_or_create(user=account.user)
        integration.scopes = scopes
        integration.calendar_enabled = integration.calendar_enabled and integration.REQUIRED_CALENDAR_SCOPE in scopes
        integration.sheets_enabled = integration.sheets_enabled and integration.REQUIRED_SHEETS_SCOPE in scopes
        integration.connected_at = timezone.now()
        integration.save(update_fields=["scopes", "calendar_enabled", "sheets_enabled", "connected_at", "updated_at"])
