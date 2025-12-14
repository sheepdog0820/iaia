# Google/X ソーシャルログイン設定ガイド

## 現在の実装状況

### ✅ 実装済み
1. **django-allauth** インストール済み (v65.9.0)
2. **設定ファイル** 
   - `settings.py` に Google/Twitter プロバイダー設定済み
   - 環境変数による認証情報管理
3. **ログインテンプレート**
   - `/templates/account/login.html` でソーシャルログインボタン表示
4. **開発環境用モックログイン**
   - `/accounts/dev-login/` で開発用ログイン可能

### ⚠️ 設定が必要な部分

## 1. 環境変数の設定

`.env` ファイルを作成し、以下の情報を設定してください：

```bash
# Google OAuth2設定
GOOGLE_CLIENT_ID=your-actual-google-client-id
GOOGLE_CLIENT_SECRET=your-actual-google-client-secret

# X (Twitter) OAuth2設定  
TWITTER_CLIENT_ID=your-actual-twitter-client-id
TWITTER_CLIENT_SECRET=your-actual-twitter-client-secret
```

## 2. Google OAuth2 設定手順

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成または既存のプロジェクトを選択
3. 「APIとサービス」→「認証情報」に移動
4. 「認証情報を作成」→「OAuth クライアント ID」を選択
5. アプリケーションの種類：「ウェブアプリケーション」を選択
6. 以下の情報を設定：
   - 名前: `Arkham Nexus Development`
   - 承認済みの JavaScript 生成元:
     ```
     http://127.0.0.1:8000
     ```
   - 承認済みのリダイレクト URI:
     ```
     http://127.0.0.1:8000/accounts/google/login/callback/
     ```
7. 作成されたクライアントIDとシークレットを `.env` に設定

## 3. X (Twitter) OAuth2 設定手順

1. [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) にアクセス
2. アプリを作成または既存のアプリを選択
3. 「User authentication settings」を設定
4. OAuth 2.0を有効化し、以下を設定：
   - App permissions: `Read`
   - Type of App: `Web App`
   - Callback URI:
     ```
     http://127.0.0.1:8000/accounts/twitter/login/callback/
     ```
   - Website URL: `http://127.0.0.1:8000`
5. Client IDとClient Secretを `.env` に設定

## 4. Django管理画面での設定

1. Django管理画面にアクセス: `http://127.0.0.1:8000/admin/`
2. 「Sites」セクションで、ドメインを `127.0.0.1:8000` に変更
3. 「Social applications」セクションで新規作成：

### Google設定
- Provider: Google
- Name: Google OAuth2
- Client id: (環境変数から取得)
- Secret key: (環境変数から取得)
- Sites: 127.0.0.1:8000 を選択

### Twitter設定
- Provider: Twitter
- Name: Twitter OAuth2
- Client id: (環境変数から取得)
- Secret key: (環境変数から取得)
- Sites: 127.0.0.1:8000 を選択

## 5. 動作確認

1. ログインページにアクセス: `http://127.0.0.1:8000/accounts/login/`
2. 「Googleでログイン」または「X (Twitter)でログイン」ボタンをクリック
3. 各サービスの認証画面にリダイレクトされることを確認
4. 認証後、アプリケーションに戻ってくることを確認

## トラブルシューティング

### エラー: "redirect_uri_mismatch"
- Google/TwitterのOAuth設定でリダイレクトURIが正しく設定されているか確認
- `http://` と `https://` の違いに注意

### エラー: "Client authentication failed"
- Client IDとClient Secretが正しく設定されているか確認
- 環境変数が正しく読み込まれているか確認

### プロバイダーが表示されない
- Django管理画面でSocial applicationsが正しく設定されているか確認
- Siteの設定が正しいか確認

## 開発環境での簡易ログイン

開発環境では以下の方法でもログイン可能：

1. `/accounts/dev-login/` にアクセス
2. テスト用アカウントでログイン
3. または `/accounts/mock-social/google/` や `/accounts/mock-social/twitter/` でモックログイン

## 本番環境への移行時の注意点

1. HTTPSを使用すること
2. リダイレクトURIを本番環境のURLに変更
3. 環境変数を本番用に更新
4. Djangoの `ALLOWED_HOSTS` と `Site` 設定を更新