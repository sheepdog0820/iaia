from datetime import timedelta
from datetime import timezone as datetime_timezone

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.conf import settings
from django.utils import timezone
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Public OAuth endpoint URL, not a credential.
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"  # nosec B105


def get_google_access_token(user):
    token = (
        SocialToken.objects.filter(
            account__user=user,
            account__provider="google",
        )
        .select_related("account")
        .order_by("-id")
        .first()
    )
    if not token:
        raise ValueError("Googleのアクセストークンを確認できません。Googleを再連携してください。")

    refresh_margin = timezone.now() + timedelta(minutes=2)
    if token.expires_at and token.expires_at > refresh_margin:
        return token.token

    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    if not token.token_secret or not client_id or not client_secret:
        raise ValueError("Googleの更新トークンを確認できません。Googleを再連携してください。")

    original = {
        "pk": token.pk,
        "account_id": token.account_id,
        "app_id": token.app_id,
        "token": token.token,
        "token_secret": token.token_secret,
        "expires_at": token.expires_at,
    }
    matching_accounts = SocialAccount.objects.filter(
        pk=token.account_id, user_id=user.pk, provider="google", uid=token.account.uid
    ).values("pk")

    credentials = Credentials(
        token=token.token,
        refresh_token=token.token_secret,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
    )
    try:
        credentials.refresh(Request())
    except (RefreshError, TransportError):
        raise ValueError(
            "Google認可の更新に失敗しました。時間をおいて再試行し、解消しない場合はGoogleを再連携してください。"
        ) from None

    updates = {
        "token": credentials.token,
        "token_secret": credentials.refresh_token or token.token_secret,
        "expires_at": token.expires_at,
    }
    if credentials.expiry:
        expiry = credentials.expiry
        if timezone.is_naive(expiry):
            expiry = timezone.make_aware(expiry, datetime_timezone.utc)
        updates["expires_at"] = expiry
    # Keep credential comparisons on the UPDATE target, not in a joined snapshot subquery.
    if SocialToken.objects.filter(account_id__in=matching_accounts, **original).update(**updates) != 1:
        raise ValueError(
            "Googleの認証情報が更新中に変更されました。もう一度操作し、必要に応じてGoogleを再連携してください。"
        )
    return updates["token"]
