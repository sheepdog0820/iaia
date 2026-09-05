import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.shortcuts import redirect

from .auth_redirects import consume_auth_next
from .google_identity import google_email_is_authoritative

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    カスタムアカウントアダプター
    ソーシャルログインのみを許可する設定

    方針: このアプリケーションはソーシャルログイン専用
    - 通常のメール/パスワードサインアップは無効
    - Googleなどのソーシャルアカウントのみでサインアップ可能
    - 開発環境は /accounts/dev-login/ で直接ログイン可能
    """

    def is_open_for_signup(self, request):
        """
        通常のサインアップを無効化
        ソーシャルアカウントからのみサインアップを許可

        Returns:
            False: 通常のメール/パスワードサインアップは常に拒否
        """
        return False

    def get_login_redirect_url(self, request):
        return consume_auth_next(request) or super().get_login_redirect_url(request)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    カスタムソーシャルアカウントアダプター
    ソーシャルログイン時の処理をカスタマイズ
    """

    def can_authenticate_by_email(self, login, email):
        if login.account.provider == "google" and (
            not google_email_is_authoritative(login.account.extra_data) or login.state.get("process") == "connect"
        ):
            return False
        return super().can_authenticate_by_email(login, email)

    def is_open_for_signup(self, request, sociallogin):
        """
        ソーシャルアカウントからのサインアップを許可
        """
        return True

    def save_user(self, request, sociallogin, form=None):
        try:
            with transaction.atomic():
                return self._save_social_user(request, sociallogin, form)
        except IntegrityError:
            messages.warning(request, "登録処理が競合しました。もう一度ログインをお試しください。")
            raise ImmediateHttpResponse(redirect("account_login")) from None

    def _save_social_user(self, request, sociallogin, form=None):
        """
        ソーシャルログイン時のユーザー保存処理
        """
        user = super().save_user(request, sociallogin, form)

        # ソーシャルアカウントから取得した情報でプロフィールを更新
        extra_data = sociallogin.account.extra_data

        if sociallogin.account.provider == "google":
            # Googleアカウントからの情報取得
            if "name" in extra_data:
                names = extra_data["name"].split(" ", 1)
                user.first_name = names[0]
                if len(names) > 1:
                    user.last_name = names[1]

            if "email" in extra_data and not user.email:
                user.email = extra_data["email"]

            if "picture" in extra_data:
                # プロフィール画像のURLを保存（実装は後で追加可能）
                pass

        elif sociallogin.account.provider == "twitter_oauth2":
            # X (Twitter) アカウントからの情報取得
            if "name" in extra_data:
                names = extra_data["name"].split(" ", 1)
                user.first_name = names[0]
                if len(names) > 1:
                    user.last_name = names[1]

            username = extra_data.get("username") or extra_data.get("screen_name")
            if username and not user.nickname:
                user.nickname = username
        elif sociallogin.account.provider == "discord":
            display_name = extra_data.get("global_name") or extra_data.get("username")
            if display_name:
                user.first_name = display_name
            if extra_data.get("email") and extra_data.get("verified", False) and not user.email:
                user.email = extra_data["email"]
            if display_name and not user.nickname:
                user.nickname = display_name

        # ニックネームが設定されていない場合はユーザー名を使用
        if not user.nickname:
            user.nickname = user.username

        user.save()
        return user

    def pre_social_login(self, request, sociallogin):
        """
        ソーシャルログイン前の処理
        既存のユーザーとの紐付けなどを行う
        """
        if sociallogin.account.provider == "google" and not google_email_is_authoritative(
            sociallogin.account.extra_data
        ):
            for address in getattr(sociallogin, "email_addresses", []):
                address.verified = False
        if sociallogin.is_existing or getattr(sociallogin, "state", {}).get("process") == "connect":
            return

        # 確認済みメールが一致する場合だけ既存ユーザーへ連携する。
        if sociallogin.account.provider in ("google", "discord"):
            extra_data = sociallogin.account.extra_data
            email = extra_data.get("email")
            if sociallogin.account.provider == "google":
                verified = google_email_is_authoritative(extra_data)
            else:
                verified = extra_data.get("verified", False)
            if email and verified is True:
                try:
                    existing_user = User.objects.get(email=email)
                    sociallogin.connect(request, existing_user)
                except User.DoesNotExist:
                    pass

    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        provider_id = getattr(provider, "id", provider if isinstance(provider, str) else None)
        if provider_id not in ("google", "discord", "twitter_oauth2"):
            provider_id = "unknown"
        error_code = error if error in ("unknown", "cancelled", "denied") else "unknown"
        # Callback parameters, cookies and exception text can contain credentials.
        logging.getLogger("allauth").warning(
            "Social authentication error: provider=%s code=%s exception_type=%s",
            provider_id,
            error_code,
            type(exception).__name__ if exception is not None else "none",
        )
