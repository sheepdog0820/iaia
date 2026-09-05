import uuid

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.authtoken.models import Token


class GoogleIdentityError(Exception):
    def __init__(self, message, status=400, confirmation=False):
        self.status = status
        self.data = {"error": message}
        if confirmation:
            self.data.update(
                code="google_link_confirmation_required",
                login_url=reverse("account_login"),
                signup_url=reverse("account_login"),
                connections_url=reverse("socialaccount_connections"),
            )
        super().__init__(message)


def google_email_is_authoritative(claims):
    verified = claims.get("email_verified", claims.get("verified_email", False))
    email = claims.get("email")
    hosted_domain = claims.get("hd")
    return (
        verified is True
        and isinstance(email, str)
        and "@" in email
        and (
            email.rsplit("@", 1)[1].lower() == "gmail.com"
            or (isinstance(hosted_domain, str) and bool(hosted_domain.strip()))
        )
    )


def _confirmation_required():
    return GoogleIdentityError(
        "メールアドレスの追加確認が必要です。初めての方はブラウザのログイン画面でGoogleを選び、"
        "メール確認を完了してください。登録済みの方は既存の方法でログインした後、"
        "ソーシャルアカウント連携画面からGoogleを連携し、再度お試しください。",
        status=409,
        confirmation=True,
    )


def complete_google_login(claims, acting_user, *, link=False):
    """Resolve a verified Google identity without transferring accounts by email."""
    uid = claims.get("sub")
    if not isinstance(uid, str) or not uid or len(uid) > SocialAccount._meta.get_field("uid").max_length:
        raise GoogleIdentityError("Googleアカウントの識別情報が取得できませんでした。")
    if not isinstance(link, bool):
        raise GoogleIdentityError("連携方法の指定が正しくありません。")
    if link and not getattr(acting_user, "is_authenticated", False):
        raise GoogleIdentityError("Googleを連携するには先にログインしてください。", status=401)

    user_model = get_user_model()
    authoritative = google_email_is_authoritative(claims)
    email = claims.get("email")
    for attempt in range(2):
        try:
            with transaction.atomic():
                account = SocialAccount.objects.select_for_update().filter(provider="google", uid=uid).first()
                created = False
                if account:
                    user = user_model.objects.select_for_update().get(pk=account.user_id)
                    if link and user.pk != acting_user.pk:
                        raise GoogleIdentityError("このGoogleアカウントは別の利用者に連携されています。", status=409)
                elif link:
                    user = user_model.objects.select_for_update().get(pk=acting_user.pk)
                else:
                    if not email or claims.get("email_verified") is not True:
                        raise GoogleIdentityError("確認済みのメールアドレスが取得できませんでした。")
                    if not authoritative:
                        raise _confirmation_required()
                    matches = list(user_model.objects.select_for_update().filter(email__iexact=email)[:2])
                    if len(matches) > 1:
                        raise _confirmation_required()
                    if matches:
                        user = matches[0]
                    else:
                        user = user_model.objects.create_user(
                            username=f"google_{uuid.uuid4().hex}", email=email.lower()
                        )
                        created = True
                if not user.is_active:
                    raise GoogleIdentityError("このアカウントではログインできません。", status=403)
                if not account:
                    SocialAccount.objects.create(user=user, provider="google", uid=uid, extra_data=claims)
                # A changed claim must not verify or replace another mailbox.
                if authoritative and email.casefold() == user.email.casefold():
                    EmailAddress.objects.filter(user=user, primary=True).exclude(email=user.email).update(primary=False)
                    EmailAddress.objects.update_or_create(
                        user=user, email=user.email, defaults={"verified": True, "primary": True}
                    )
                if not link and not EmailAddress.objects.filter(user=user, verified=True).exists():
                    raise _confirmation_required()
                updated = []
                for field, claim in (("nickname", "name"), ("first_name", "given_name"), ("last_name", "family_name")):
                    value = claims.get(claim)
                    if not getattr(user, field) and isinstance(value, str) and value:
                        setattr(user, field, value[: user_model._meta.get_field(field).max_length])
                        updated.append(field)
                if updated:
                    user.save(update_fields=updated)
                token, _ = Token.objects.get_or_create(user=user)
                return user, created, token
        except IntegrityError:
            # Retry after rollback: a competing request may have created this UID.
            if attempt:
                raise GoogleIdentityError("認証処理が競合しました。もう一度お試しください。", status=503) from None
