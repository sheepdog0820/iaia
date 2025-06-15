# ソーシャル認証セットアップガイド

## 概要
Arkham NexusでGoogleとTwitter/Xのソーシャル認証を設定するためのガイドです。

## 必要な手順

### 1. Google OAuth設定

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成または既存プロジェクトを選択
3. 「APIとサービス」→「認証情報」に移動
4. 「認証情報を作成」→「OAuth 2.0 クライアントID」を選択
5. アプリケーションタイプ：「ウェブアプリケーション」
6. 承認済みリダイレクトURIに以下を追加：
   - `http://localhost:8000/accounts/google/login/callback/`
   - `http://127.0.0.1:8000/accounts/google/login/callback/`
7. クライアントIDとクライアントシークレットを取得

### 2. Twitter/X OAuth設定

1. [Twitter Developer Portal](https://developer.twitter.com/)にアクセス
2. アプリを作成
3. App Settings → User authentication settings
4. OAuth 2.0を有効化
5. Callback URLに以下を追加：
   - `http://localhost:8000/accounts/twitter/login/callback/`
6. Client IDとClient Secretを取得

### 3. 環境変数設定

`.env`ファイルを作成し、取得した認証情報を設定：

```bash
# Django設定
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Twitter OAuth
TWITTER_CLIENT_ID=your-twitter-client-id
TWITTER_CLIENT_SECRET=your-twitter-client-secret
```

### 4. データベース更新

```bash
python3 manage.py shell -c "
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings

# サイト設定
site = Site.objects.get_current()
site.domain = 'localhost:8000'
site.name = 'Arkham Nexus'
site.save()

# Google設定更新
google_app = SocialApp.objects.get(provider='google')
google_app.client_id = 'YOUR_GOOGLE_CLIENT_ID'
google_app.secret = 'YOUR_GOOGLE_CLIENT_SECRET'
google_app.save()

# Twitter設定更新
twitter_app = SocialApp.objects.get(provider='twitter')
twitter_app.client_id = 'YOUR_TWITTER_CLIENT_ID'
twitter_app.secret = 'YOUR_TWITTER_CLIENT_SECRET'
twitter_app.save()

print('Social apps updated successfully!')
"
```

### 5. テスト

1. サーバーを起動: `python3 manage.py runserver`
2. `http://localhost:8000/accounts/login/`にアクセス
3. GoogleまたはTwitterボタンをクリック
4. 認証フローをテスト

## 実装済み機能

✅ **認証フロー**
- Google OAuth 2.0認証
- Twitter OAuth 2.0認証
- 自動アカウント作成
- メールアドレス連携

✅ **エラーハンドリング**
- 認証キャンセル処理
- 認証エラー処理
- ユーザーフレンドリーなエラーページ

✅ **ユーザー管理**
- プロフィール自動設定
- 複数ソーシャルアカウント連携
- アカウント連携解除

✅ **セキュリティ**
- CSRF保護
- セッション管理
- OAuth PKCEサポート

## 利用可能なURL

- ログイン: `/accounts/login/`
- ログアウト: `/accounts/logout/`
- ダッシュボード: `/accounts/dashboard/`
- アカウント連携: `/accounts/social/connections/`

## トラブルシューティング

### 認証エラーが発生する場合
1. OAuth設定のリダイレクトURIを確認
2. Client IDとSecretが正しく設定されているか確認
3. .envファイルが正しく読み込まれているか確認

### ローカル開発での注意点
- HTTPSが必要な場合は`localhost`ではなく`127.0.0.1`を使用
- ポート番号を含めたURLを設定
- 開発用と本番用で異なるOAuthアプリを作成推奨