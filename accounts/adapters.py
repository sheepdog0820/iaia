from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    カスタムアカウントアダプター
    ソーシャルログインのみを許可する設定
    """
    
    def is_open_for_signup(self, request):
        """
        通常のサインアップを無効化
        ソーシャルアカウントからのみサインアップを許可
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
                
        elif sociallogin.account.provider == 'twitter':
            # Twitterアカウントからの情報取得
            if 'name' in extra_data:
                names = extra_data['name'].split(' ', 1)
                user.first_name = names[0]
                if len(names) > 1:
                    user.last_name = names[1]
                    
            if 'screen_name' in extra_data and not user.nickname:
                user.nickname = extra_data['screen_name']
        
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