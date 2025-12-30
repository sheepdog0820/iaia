# OAuth アプリケーション登録ガイド

## 📌 Google OAuth2.0 登録手順

### 1. Google Cloud Console へアクセス
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. Googleアカウントでログイン

### 2. プロジェクトの作成
1. 上部のプロジェクト選択ドロップダウンをクリック
2. 「新しいプロジェクト」をクリック
3. プロジェクト情報を入力：
   - プロジェクト名: `Arkham Nexus`
   - 組織: （個人の場合は「組織なし」）
4. 「作成」をクリック

### 3. OAuth同意画面の設定
1. 左側メニューから「APIとサービス」→「OAuth同意画面」を選択
2. ユーザータイプを選択：
   - **外部**: 一般公開アプリの場合（推奨）
   - **内部**: G Suite組織内のみの場合
3. 「作成」をクリック
4. アプリ情報を入力：
   - **アプリ名**: `Arkham Nexus`
   - **ユーザーサポートメール**: あなたのメールアドレス
   - **アプリのロゴ**: （オプション）
   - **アプリケーションホームページ**: `http://127.0.0.1:8000`（開発用）
   - **アプリケーションプライバシーポリシー**: （本番環境では必須）
   - **アプリケーション利用規約**: （本番環境では必須）
   - **承認済みドメイン**: `localhost`（開発用）
   - **デベロッパーの連絡先情報**: あなたのメールアドレス
5. 「保存して次へ」

### 4. スコープの設定
1. 「スコープを追加または削除」をクリック
2. 以下のスコープを選択：
   - `.../auth/userinfo.email` - メールアドレスの取得
   - `.../auth/userinfo.profile` - プロフィール情報の取得
3. 「更新」→「保存して次へ」

### 5. テストユーザー（開発中のみ）
1. 「ADD USERS」をクリック
2. テストに使用するGoogleアカウントのメールアドレスを追加
3. 「保存して次へ」

### 6. OAuth2.0 クライアントIDの作成
1. 左側メニューから「APIとサービス」→「認証情報」を選択
2. 「+ 認証情報を作成」→「OAuth クライアント ID」を選択
3. アプリケーションの種類: **ウェブアプリケーション**
4. 名前: `Arkham Nexus Web Client`
5. 承認済みの JavaScript 生成元:
   ```
   http://127.0.0.1:8000
   http://127.0.0.1:8000
   ```
6. 承認済みのリダイレクト URI:
   ```
   http://127.0.0.1:8000/accounts/google/login/callback/
   http://127.0.0.1:8000/accounts/google/login/callback/
   ```
7. 「作成」をクリック
8. 表示される**クライアントID**と**クライアントシークレット**をメモ

### 7. APIの有効化
1. 「APIとサービス」→「有効なAPI」
2. 「+ APIとサービスの有効化」
3. 「Google+ API」を検索して有効化（ユーザー情報取得に必要）

---

## 📌 X (Twitter) OAuth2.0 登録手順

### 1. Twitter Developer Portal へアクセス
1. [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) にアクセス
2. Twitterアカウントでログイン

### 2. 開発者アカウントの申請（初回のみ）
1. 「Sign up」をクリック
2. 開発者アカウント申請フォームを記入：
   - **What's your use case?**: `Student` または `Hobbyist`
   - **Will you make Twitter content available to government?**: No
   - **用途の説明**: アプリケーションの説明を英語で記入
3. 利用規約に同意して送信
4. メールアドレスを確認

### 3. プロジェクトとアプリの作成
1. Developer Portalで「+ Create Project」をクリック
2. プロジェクト情報を入力：
   - **Project name**: `Arkham Nexus Project`
   - **Use case**: `Exploring the API`
   - **Project description**: TRPG session management application
3. 「Next」をクリック
4. アプリ情報を入力：
   - **App name**: `ArkhamNexus`（一意である必要があります）
   - **App environment**: `Development`
5. API Keyが表示されるので保存（後で再生成可能）

### 4. OAuth2.0 の設定
1. プロジェクトのアプリ設定ページへ移動
2. 「User authentication settings」の「Set up」をクリック
3. 以下を設定：

#### App permissions（アプリの権限）
- ✅ **Read**: ユーザー情報の読み取り
- ❌ Write: 不要
- ❌ Direct Messages: 不要

#### Type of App（アプリタイプ）
- 🔘 **Web App, Automated App or Bot**

#### App info（アプリ情報）
- **Callback URI / Redirect URL**:
  ```
  http://127.0.0.1:8000/accounts/twitter_oauth2/login/callback/
  http://127.0.0.1:8000/accounts/twitter_oauth2/login/callback/
  ```
- **Website URL**: `http://127.0.0.1:8000`
- **Terms of service**: （本番環境では必須）
- **Privacy policy**: （本番環境では必須）

4. 「Save」をクリック

### 5. Client ID と Client Secret の取得
1. 「Keys and tokens」タブに移動
2. 「OAuth 2.0 Client ID and Client Secret」セクション
3. 「Regenerate」をクリックしてClient Secretを生成
4. **Client ID**と**Client Secret**をメモ

### 6. Elevated Access の申請（必要な場合）
基本的なユーザー情報取得には不要ですが、より詳細な情報が必要な場合：
1. 「Products」→「Twitter API v2」
2. 「Elevated」タブ
3. 申請フォームを記入

---

## 🔧 Django プロジェクトへの設定

### 1. 環境変数の設定
`.env` ファイルに取得した認証情報を設定：

```bash
# Google OAuth2
GOOGLE_CLIENT_ID=取得したクライアントID
GOOGLE_CLIENT_SECRET=取得したクライアントシークレット

# X (Twitter) OAuth2
TWITTER_CLIENT_ID=取得したClient ID
TWITTER_CLIENT_SECRET=取得したClient Secret
```

### 2. Django管理画面での設定

1. スーパーユーザーでログイン：
   ```bash
   python manage.py createsuperuser
   ```

2. `http://127.0.0.1:8000/admin/` にアクセス

3. **Sites** の設定：
   - 「Sites」をクリック
   - `example.com` を編集
   - Domain name: `127.0.0.1:8000`
   - Display name: `Arkham Nexus Local`
   - 保存

4. **Social Applications** の追加：

#### Google の設定
1. 「Social applications」→「追加」
2. 入力内容：
   - Provider: `Google`
   - Name: `Google Login`
   - Client id: `.env`のGOOGLE_CLIENT_ID
   - Secret key: `.env`のGOOGLE_CLIENT_SECRET
   - Key: （空欄でOK）
3. 「Available sites」から`127.0.0.1:8000`を選択して「Chosen sites」に移動
4. 保存

#### Twitter の設定
1. 「Social applications」→「追加」
2. 入力内容：
   - Provider: `Twitter`
   - Name: `Twitter Login`
   - Client id: `.env`のTWITTER_CLIENT_ID
   - Secret key: `.env`のTWITTER_CLIENT_SECRET
3. 「Available sites」から`127.0.0.1:8000`を選択して「Chosen sites」に移動
4. 保存

---

## ✅ 動作確認

### 1. 開発サーバーの起動
```bash
python manage.py runserver
```

### 2. ログインページへアクセス
`http://127.0.0.1:8000/login/` にアクセス

### 3. ソーシャルログインのテスト
- 「Googleでログイン」ボタンをクリック
  - Googleの認証画面が表示される
  - アプリへのアクセスを許可
  - アプリケーションに戻る

- 「X (Twitter)でログイン」ボタンをクリック
  - Twitterの認証画面が表示される
  - アプリを認証
  - アプリケーションに戻る

---

## ⚠️ よくある問題と解決方法

### Google OAuth

#### エラー: "Error 400: redirect_uri_mismatch"
- **原因**: リダイレクトURIが一致しない
- **解決**: Google Cloud ConsoleでリダイレクトURIを確認し、完全一致させる
- スラッシュ（/）の有無に注意

#### エラー: "Access blocked: This app's request is invalid"
- **原因**: OAuth同意画面が未設定
- **解決**: OAuth同意画面の設定を完了させる

### Twitter OAuth

#### エラー: "Callback URL not approved"
- **原因**: Callback URLが登録されていない
- **解決**: Developer PortalでCallback URLを追加

#### エラー: "Desktop applications only support the oauth_callback value 'oob'"
- **原因**: アプリタイプの設定ミス
- **解決**: 「Web App」タイプを選択

### Django 側

#### プロバイダーが表示されない
- **原因**: Social Applicationが未設定
- **解決**: Django管理画面で設定を確認

#### ログイン後にエラー
- **原因**: Siteの設定ミス
- **解決**: SITE_IDとDomain nameを確認

---

## 🚀 本番環境への移行

### 1. HTTPS の設定
- SSL証明書を取得（Let's Encryptなど）
- すべてのURLを`https://`に変更

### 2. リダイレクトURIの更新
Google/Twitter両方で本番環境のURLを追加：
```
https://yourdomain.com/accounts/google/login/callback/
https://yourdomain.com/accounts/twitter_oauth2/login/callback/
```

### 3. 環境変数の更新
本番環境用の`.env`ファイルを作成

### 4. Djangoの設定
- `ALLOWED_HOSTS`に本番ドメインを追加
- `Site`のdomain nameを本番ドメインに変更
- `DEBUG = False`に設定

### 5. プライバシーポリシーと利用規約
- 両サービスとも本番環境では必須
- URLを各サービスの設定に追加
