# Google Cloud Console設定確認チェックリスト

## 🔍 現在のエラーの原因

エラー `(invalid_client) Unauthorized` は以下の原因が考えられます：

1. OAuth 2.0クライアントIDが無効または削除されている
2. リダイレクトURIが一致していない
3. APIが有効化されていない

## ✅ 確認手順

### 1. Google Cloud Consoleにアクセス
[https://console.cloud.google.com/](https://console.cloud.google.com/)

### 2. 正しいプロジェクトを選択
- 上部のプロジェクトセレクターで正しいプロジェクトを選択

### 3. OAuth 2.0クライアントIDの確認

1. 左メニューから「APIとサービス」→「認証情報」
2. OAuth 2.0 クライアント IDセクションを確認
3. クライアントID `456958275505-lgu362m6pl0seeqb8geuom5jf86c1ucn.apps.googleusercontent.com` が存在することを確認

### 4. クライアント設定の確認

クライアントIDをクリックして詳細を確認：

#### ✅ アプリケーションの種類
- [ ] 「ウェブ アプリケーション」になっているか

#### ✅ 承認済みのJavaScript生成元
以下が登録されているか確認：
- [ ] `http://localhost:3000`
- [ ] `http://localhost:8000`（必要に応じて）

#### ✅ 承認済みのリダイレクトURI
以下が**正確に**登録されているか確認：
- [ ] `http://localhost:3000/auth/callback`

⚠️ **重要**: 末尾のスラッシュの有無も含めて完全一致する必要があります

### 5. APIの有効化確認

1. 「APIとサービス」→「有効なAPI」
2. 以下のAPIが有効になっているか確認：
   - [ ] Google+ API（または Google Identity API）
   - [ ] Google OAuth2 API

### 6. OAuth同意画面の設定

1. 「APIとサービス」→「OAuth同意画面」
2. 以下を確認：
   - [ ] アプリケーション名が設定されている
   - [ ] ユーザーサポートメールが設定されている
   - [ ] 承認済みドメインに `localhost` が含まれている（開発環境の場合）

## 🔧 修正が必要な場合

### リダイレクトURIを追加する場合
1. クライアントIDの編集画面を開く
2. 「承認済みのリダイレクトURI」セクション
3. 「+ URIを追加」をクリック
4. `http://localhost:3000/auth/callback` を追加
5. 「保存」をクリック

### 新しいクライアントIDを作成する場合
1. 「認証情報を作成」→「OAuth クライアント ID」
2. アプリケーションの種類：「ウェブ アプリケーション」
3. 名前：`Arkham Nexus Development`
4. 承認済みのJavaScript生成元：`http://localhost:3000`
5. 承認済みのリダイレクトURI：`http://localhost:3000/auth/callback`
6. 作成後、新しいクライアントIDとシークレットを`.env.development`に更新

## 📝 デバッグ用テストコマンド

設定確認後、以下のコマンドでテスト：

```bash
# 1. 設定の再確認
python3 check_google_oauth_settings.py

# 2. 新しい認証コードを取得
python3 get_google_auth_code.py

# 3. APIテスト
python3 test_google_auth_api.py
```

## 🚨 それでも動作しない場合

1. **クライアントシークレットを再生成**
   - クライアントIDの詳細画面で「シークレットをリセット」
   - 新しいシークレットを`.env.development`に更新

2. **ブラウザのキャッシュをクリア**
   - Googleアカウントからログアウト
   - ブラウザのキャッシュとCookieをクリア
   - 再度認証を試行

3. **別のGoogleアカウントで試す**
   - 権限の問題を排除するため

4. **アクセストークン方式でテスト**
   - OAuth Playgroundでアクセストークンを取得してテスト