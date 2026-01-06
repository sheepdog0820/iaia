import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.conf import settings

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


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    カスタムソーシャルアカウントアダプター
    ソーシャルログイン時の処理をカスタマイズ
    """
    
    def is_open_for_signup(self, request, sociallogin):
        """
        ソーシャルアカウントからのサインアップを許可
        """
        return True
    
    def save_user(self, request, sociallogin, form=None):
        """
        ソーシャルログイン時のユーザー保存処理
        """
        user = super().save_user(request, sociallogin, form)
        
        # ソーシャルアカウントから取得した情報でプロフィールを更新
        extra_data = sociallogin.account.extra_data
        
        if sociallogin.account.provider == 'google':
            # Googleアカウントからの情報取得
            if 'name' in extra_data:
                names = extra_data['name'].split(' ', 1)
                user.first_name = names[0]
                if len(names) > 1:
                    user.last_name = names[1]
            
            if 'email' in extra_data and not user.email:
                user.email = extra_data['email']
                
            if 'picture' in extra_data:
                # プロフィール画像のURLを保存（実装は後で追加可能）
                pass
                
        elif sociallogin.account.provider == 'twitter_oauth2':
            # X (Twitter) アカウントからの情報取得
            if 'name' in extra_data:
                names = extra_data['name'].split(' ', 1)
                user.first_name = names[0]
                if len(names) > 1:
                    user.last_name = names[1]
                    
            username = extra_data.get('username') or extra_data.get('screen_name')
            if username and not user.nickname:
                user.nickname = username
        
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
        # メールアドレスが一致する既存ユーザーがいる場合は連携
        if sociallogin.account.provider == 'google':
            email = sociallogin.account.extra_data.get('email')
            if email:
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
        logger = logging.getLogger("allauth")
        provider_id = getattr(provider, "id", str(provider))

        def _mask(value, keep=6):
            if not value:
                return ""
            value = str(value)
            if len(value) <= keep:
                return "*" * len(value)
            return ("*" * (len(value) - keep)) + value[-keep:]

        host = None
        request_path = None
        try:
            host = request.get_host()
        except Exception:
            pass
        try:
            request_path = request.path
        except Exception:
            pass

        session_cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
        session_cookie = _mask(request.COOKIES.get(session_cookie_name)) if request else ""
        session_key = _mask(getattr(getattr(request, "session", None), "session_key", None)) if request else ""
        x_forwarded_host = request.META.get("HTTP_X_FORWARDED_HOST") if request else None
        x_forwarded_proto = request.META.get("HTTP_X_FORWARDED_PROTO") if request else None
        raw_host = request.META.get("HTTP_HOST") if request else None
        state = request.GET.get("state") if request else None
        get_params = dict(request.GET) if request else {}
        for sensitive_key in {
            "code",
            "access_token",
            "id_token",
            "oauth_token",
            "oauth_token_secret",
            "refresh_token",
            "token",
        }:
            if sensitive_key in get_params:
                get_params[sensitive_key] = ["<redacted>"]

        exc_info = None
        if exception is not None and getattr(exception, "__traceback__", None) is not None:
            exc_info = (type(exception), exception, exception.__traceback__)

        logger.warning(
            "Social authentication error: provider=%s code=%s host=%s raw_host=%s xf_host=%s xf_proto=%s path=%s state=%s session_cookie=%s session_key=%s GET=%s exception=%r",
            provider_id,
            error,
            host,
            raw_host,
            x_forwarded_host,
            x_forwarded_proto,
            request_path,
            state,
            session_cookie,
            session_key,
            get_params,
            exception,
            exc_info=exc_info,
        )
