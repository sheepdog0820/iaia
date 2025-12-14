# Google OAuth認証 クイックスタートガイド

## 🚀 最速で認証コードを取得する方法

### ステップ1: 認証URLを生成して開く
```bash
python3 get_google_auth_code.py
```

### ステップ2: ブラウザでの操作
1. 自動的にブラウザが開きます
2. Googleアカウントでログイン
3. アプリへのアクセスを許可

### ステップ3: 認証コードを取得
リダイレクト後のURL例：
```
http://localhost:3000/auth/callback?code=4/0AX4XfWi8TnG9...&scope=email%20profile...
```

**認証コード**: `4/0AX4XfWi8TnG9...`（`code=`から`&`まで）

### ステップ4: APIをテスト
```bash
python3 test_google_auth_api.py
# オプション1を選択し、認証コードを貼り付け
```

## 🔧 トラブルシューティング

### "このサイトにアクセスできません" エラー
これは**正常**です！URLバーを見てください。認証コードが含まれています。

### "Error 400: redirect_uri_mismatch"
Google Cloud Consoleで承認済みのリダイレクトURIに以下を追加：
- `http://localhost:3000/auth/callback`

### 認証コードが無効
- 認証コードは**一度だけ**使用可能
- 有効期限は**数分**
- 新しいコードを取得してください

## 📝 手動でURLを作成する場合

以下のURLをブラウザで開く：
```
https://accounts.google.com/o/oauth2/v2/auth?client_id=456958275505-lgu362m6pl0seeqb8geuom5jf86c1ucn.apps.googleusercontent.com&redirect_uri=http://localhost:3000/auth/callback&response_type=code&scope=openid%20email%20profile&access_type=offline&prompt=consent
```

## 🎯 成功時のレスポンス例
```json
{
  "token": "a1b2c3d4e5f6...",
  "user": {
    "id": 1,
    "username": "user",
    "email": "user@gmail.com",
    "nickname": "User Name",
    "first_name": "User",
    "last_name": "Name"
  },
  "created": true
}
```