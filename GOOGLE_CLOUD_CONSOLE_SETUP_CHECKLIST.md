# Google Cloud Console 設定チェックリスト

## 🎯 現在のエラー

**エラー 400: redirect_uri_mismatch**

アプリケーションが送信しているリダイレクトURI:
```
http://127.0.0.1:8000/accounts/google/login/callback/
```

このURIがGoogle Cloud Consoleに正確に登録されていない場合、このエラーが発生します。

## ✅ 設定手順

### ステップ1: Google Cloud Console にアクセス

1. [Google Cloud Console](https://console.cloud.google.com/) を開く
2. 正しいプロジェクト（Arkham Nexus）が選択されているか確認

### ステップ2: 認証情報ページへ移動

1. 左側のメニューから「APIとサービス」→「認証情報」をクリック
2. OAuth 2.0 クライアントIDのセクションを確認

### ステップ3: OAuth 2.0 クライアントIDを編集

1. 既存のOAuth 2.0 クライアントIDをクリック（名前: Arkham Nexus Web Client など）
2. または、新規作成する場合は「+ 認証情報を作成」→「OAuth クライアント ID」を選択

### ステップ4: 設定内容を確認・修正

#### アプリケーションの種類
- ✅ **ウェブ アプリケーション** を選択

#### 承認済みのJavaScript生成元
以下を**正確に**入力してください：
```
http://127.0.0.1:8000
```

⚠️ **削除する項目**:
- `http://localhost:8000`
- `http://localhost:3000`
- その他のlocalhost関連のURL

#### 承認済みのリダイレクトURI
以下を**正確に**入力してください（末尾のスラッシュを含む）：
```
http://127.0.0.1:8000/accounts/google/login/callback/
```

⚠️ **削除する項目**:
- `http://localhost:8000/accounts/google/login/callback/`
- その他のlocalhost関連のコールバックURL

### ステップ5: 設定を保存

1. 「保存」ボタンをクリック
2. 設定が反映されるまで数分待つ（通常は即座ですが、最大5分程度かかる場合があります）

## 🔍 設定確認のポイント

### 必ず確認すべき項目

1. **プロトコル**: `http://` （開発環境のため）
2. **ホスト**: `127.0.0.1` （localhostではない）
3. **ポート**: `:8000` （必須）
4. **パス**: `/accounts/google/login/callback/` （django-allauth標準）
5. **末尾のスラッシュ**: `/` （必須）

### よくある間違い

❌ `http://localhost:8000/accounts/google/login/callback/` - localhost使用
❌ `http://127.0.0.1:8000/accounts/google/login/callback` - 末尾のスラッシュなし
❌ `https://127.0.0.1:8000/accounts/google/login/callback/` - httpsプロトコル
❌ `http://127.0.0.1/accounts/google/login/callback/` - ポート番号なし

✅ `http://127.0.0.1:8000/accounts/google/login/callback/` - 正解！

## 🧪 動作確認

### 1. ブラウザでテスト

```
http://127.0.0.1:8000/accounts/login/
```

⚠️ 注意: `localhost:8000` ではなく `127.0.0.1:8000` でアクセスしてください

### 2. ログインフローのテスト

1. 「Googleでログイン」ボタンをクリック
2. Googleのログイン画面に遷移することを確認
3. Googleアカウントでログイン
4. アプリケーションへのアクセス許可を承認
5. アプリケーション（ダッシュボード）にリダイレクトされることを確認

### 3. エラーが発生する場合

#### シークレット/プライベートモードで試す
- ブラウザのキャッシュやCookieの影響を排除

#### ブラウザの開発者ツールで確認
1. F12キーを押して開発者ツールを開く
2. Networkタブを選択
3. 「Googleでログイン」ボタンをクリック
4. リダイレクトURLを確認し、Google Cloud Consoleの設定と完全一致するか確認

## 📋 設定完了後の確認事項

### Google Cloud Console 側

- [ ] JavaScript生成元: `http://127.0.0.1:8000` のみ
- [ ] リダイレクトURI: `http://127.0.0.1:8000/accounts/google/login/callback/` のみ
- [ ] localhost関連のURLをすべて削除済み
- [ ] 設定を保存済み

### Django アプリケーション側

- [ ] サーバーが `http://127.0.0.1:8000` で起動している
- [ ] `.env` ファイルに正しいGOOGLE_CLIENT_IDとGOOGLE_CLIENT_SECRETが設定されている
- [ ] Django管理画面でSocialAppが設定されている（Provider: Google）
- [ ] Siteのdomain nameが `127.0.0.1:8000` に設定されている

## 🚀 本番環境への移行時の注意

本番環境では以下のように変更する必要があります：

### JavaScript生成元
```
https://yourdomain.com
```

### リダイレクトURI
```
https://yourdomain.com/accounts/google/login/callback/
```

- HTTPSプロトコルを使用
- ポート番号は不要（443がデフォルト）
- 実際のドメイン名を使用

## 📞 サポート

問題が解決しない場合は、以下のドキュメントも参照してください：

- [docs/OAUTH_REGISTRATION_GUIDE.md](docs/OAUTH_REGISTRATION_GUIDE.md) - OAuth登録の詳細手順
- [docs/GOOGLE_OAUTH_REDIRECT_URI_FIX.md](docs/GOOGLE_OAUTH_REDIRECT_URI_FIX.md) - リダイレクトURI問題の詳細
- [docs/GOOGLE_CLOUD_CONSOLE_CHECK.md](docs/GOOGLE_CLOUD_CONSOLE_CHECK.md) - Console設定チェックリスト
- [GOOGLE_OAUTH_REDIRECT_URI_SETUP.md](GOOGLE_OAUTH_REDIRECT_URI_SETUP.md) - リダイレクトURI設定ガイド
