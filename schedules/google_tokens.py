from datetime import timedelta
from datetime import timezone as datetime_timezone

from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'


def get_google_access_token(user):
    token = SocialToken.objects.filter(
        account__user=user,
        account__provider='google',
    ).order_by('-id').first()
    if not token:
        raise ValueError('Google access token is unavailable.')

    refresh_margin = timezone.now() + timedelta(minutes=2)
    if not token.expires_at or token.expires_at > refresh_margin:
        return token.token

    client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '')
    if not token.token_secret or not client_id or not client_secret:
        raise ValueError('Google refresh token is unavailable. Reconnect Google.')

    credentials = Credentials(
        token=token.token,
        refresh_token=token.token_secret,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
    )
    credentials.refresh(Request())

    token.token = credentials.token
    if credentials.refresh_token:
        token.token_secret = credentials.refresh_token
    if credentials.expiry:
        expiry = credentials.expiry
        if timezone.is_naive(expiry):
            expiry = timezone.make_aware(expiry, datetime_timezone.utc)
        token.expires_at = expiry
    token.save(update_fields=['token', 'token_secret', 'expires_at'])
    return token.token
