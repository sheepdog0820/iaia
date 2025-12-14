# Google OAuth 8000番ポート統一版セットアップガイド

## 概要
このガイドでは、8000番ポートのみを使用してGoogle OAuth認証を実装する方法を説明します。

## 🔧 Google Cloud Console設定

### 1. リダイレクトURIの更新

Google Cloud Consoleで以下のリダイレクトURIを設定してください：

```
http://127.0.0.1:8000/accounts/google/callback/
```

**重要な注意事項：**
- ✅ HTTPを使用（HTTPSではない）
- ✅ ポート番号は8000
- ✅ 末尾のスラッシュ（/）を含める
- ✅ 完全一致が必要

### 2. 設定手順

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 「APIとサービス」→「認証情報」
3. OAuth 2.0 クライアントIDをクリック
4. 「承認済みのリダイレクトURI」セクション
5. 既存のURIを削除または編集：
   - 削除: `http://localhost:3000/auth/callback`
   - 追加: `http://127.0.0.1:8000/accounts/google/callback/`
6. 「保存」をクリック

## 🚀 使用方法

### 1. サーバーを起動
```bash
python3 manage.py runserver
```

### 2. テストページにアクセス
```
http://127.0.0.1:8000/accounts/google/test/
```

### 3. 認証フロー

#### 方法A: Webベース認証（推奨）
1. 「Google認証を開始」ボタンをクリック
2. Googleアカウントでログイン
3. アプリへのアクセスを許可
4. 自動的にリダイレクトされ、成功ページが表示

#### 方法B: API認証テスト
1. 手動で認証コードを取得
2. テストページのフォームに入力
3. APIレスポンスを確認

## 📍 利用可能なURL

| URL | 説明 |
|-----|------|
| `/accounts/google/test/` | テストページ |
| `/accounts/google/login/` | Google認証開始 |
| `/accounts/google/callback/` | 認証コールバック（自動） |
| `/accounts/google/success/` | 認証成功ページ |

## 🔑 認証成功後

認証成功後は以下の情報が表示されます：

1. **ユーザー情報**
   - ユーザー名
   - メールアドレス
   - ニックネーム

2. **APIトークン**
   - Django REST FrameworkのTokenが自動生成
   - コピーボタンで簡単にコピー可能

3. **APIテスト例**
   - curlコマンドの使用例が表示

## 🛠️ トラブルシューティング

### "redirect_uri_mismatch" エラー
- Google Cloud ConsoleのリダイレクトURIが正確に一致しているか確認
- 末尾のスラッシュを含めているか確認
- HTTPを使用しているか確認（HTTPSではない）

### "invalid_client" エラー
- クライアントIDとシークレットが正しいか確認
- `.env.development`ファイルを確認

### 認証後にエラーページが表示される
- セッションが有効か確認
- Cookieが有効になっているか確認

## 📝 開発時の注意

1. **セキュリティ**
   - この設定は開発環境専用
   - 本番環境では必ずHTTPSを使用

2. **ポート番号**
   - 8000番ポートが他のプロセスで使用されていないか確認
   - 必要に応じて別のポートを使用可能

3. **ブラウザ**
   - プライベートモードでのテストを推奨
   - キャッシュクリアが必要な場合あり