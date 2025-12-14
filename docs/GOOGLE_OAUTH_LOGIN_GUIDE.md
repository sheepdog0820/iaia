# Google OAuth ログイン手順（開発環境）

## 事前準備

### 1. 開発サーバーの起動
```bash
cd /mnt/c/Users/endke/Workspace/iaia
python3 manage.py runserver
```
サーバーが `http://localhost:8000` で起動します。

### 2. 環境確認
- Google Cloud Consoleの設定が完了していること
- `.env`ファイルにGoogle認証情報が設定されていること

## ログイン方法

### 方法1: Webブラウザ経由（django-allauth使用）

1. **ブラウザでアクセス**
   ```
   http://localhost:8000/accounts/login/
   ```

2. **Googleログインボタンをクリック**
   - 「Google でログイン」ボタンが表示されます
   - クリックするとGoogleの認証画面にリダイレクトされます

3. **Googleアカウントを選択**
   - 使用するGoogleアカウントを選択
   - 初回は権限の許可を求められるので「許可」をクリック

4. **ログイン完了**
   - 自動的に `http://localhost:8000/accounts/dashboard/` にリダイレクトされます
   - ログインが成功すると、ダッシュボード画面が表示されます

### 方法2: API経由（フロントエンド開発用）

#### ステップ1: Google OAuth認証フローの実装

フロントエンド（React/Vue/Angular等）で以下を実装：

1. **Google Sign-In ライブラリの導入**
   ```html
   <script src="https://accounts.google.com/gsi/client" async defer></script>
   ```

2. **認証ボタンの実装**
   ```javascript
   // Google認証の初期化
   google.accounts.id.initialize({
     client_id: '456958275505-lgu362m6pl0seeqb8geuom5jf86c1ucn.apps.googleusercontent.com',
     callback: handleCredentialResponse
   });

   // 認証レスポンスの処理
   function handleCredentialResponse(response) {
     // response.credential にIDトークンが含まれる
     sendTokenToBackend(response.credential);
   }
   ```

3. **バックエンドAPIへトークン送信**
   ```javascript
   async function sendTokenToBackend(idToken) {
     const response = await fetch('http://localhost:8000/api/auth/google/', {
       method: 'POST',
       headers: {
         'Content-Type': 'application/json',
       },
       body: JSON.stringify({
         code: idToken  // IDトークンを送信
       })
     });

     const data = await response.json();
     if (data.token) {
       // DRFトークンを保存
       localStorage.setItem('authToken', data.token);
       console.log('ログイン成功:', data.user);
     }
   }
   ```

#### ステップ2: 認証後のAPIアクセス

```javascript
// 認証が必要なAPIへのアクセス
async function fetchUserData() {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch('http://localhost:8000/api/auth/user/', {
    headers: {
      'Authorization': `Token ${token}`
    }
  });
  
  const userData = await response.json();
  return userData;
}
```

### 方法3: テスト用コマンドライン（開発用）

1. **Google OAuth Playgroundでアクセストークンを取得**
   - https://developers.google.com/oauthplayground/ にアクセス
   - Google OAuth2 API v2 を選択
   - スコープ: `https://www.googleapis.com/auth/userinfo.email` と `https://www.googleapis.com/auth/userinfo.profile`
   - 認証してアクセストークンを取得

2. **curlコマンドでテスト**
   ```bash
   # Google認証
   curl -X POST http://localhost:8000/api/auth/google/ \
     -H "Content-Type: application/json" \
     -d '{"access_token": "YOUR_ACCESS_TOKEN_HERE"}'
   
   # レスポンス例
   {
     "token": "abcd1234567890...",
     "user": {
       "id": 1,
       "username": "testuser",
       "email": "test@gmail.com",
       "nickname": "Test User"
     },
     "created": true
   }
   ```

3. **認証トークンを使用してAPIアクセス**
   ```bash
   curl -X GET http://localhost:8000/api/auth/user/ \
     -H "Authorization: Token abcd1234567890..."
   ```

## トラブルシューティング

### ログインできない場合

1. **ブラウザのキャッシュをクリア**
   - シークレット/プライベートモードで試す
   - Cookieとキャッシュを削除

2. **コンソールログを確認**
   ```bash
   # Djangoサーバーのログを確認
   python3 manage.py runserver
   ```

3. **設定を再確認**
   - `.env`ファイルの認証情報
   - Google Cloud ConsoleのリダイレクトURI設定

### よくあるエラー

1. **redirect_uri_mismatch**
   - Google Cloud ConsoleのリダイレクトURIを確認
   - 末尾のスラッシュ（/）に注意

2. **Invalid token**
   - アクセストークンの有効期限を確認
   - 正しいスコープで取得しているか確認

3. **CORS error**
   - `settings.py`のCORS設定を確認
   - フロントエンドのURLが許可されているか確認

## ログアウト

### Webブラウザ経由
```
http://localhost:8000/accounts/logout/
```

### API経由
```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

## 開発のヒント

1. **テストユーザーの作成**
   - 初回ログイン時に自動的にユーザーが作成されます
   - メールアドレスをキーとして管理されます

2. **トークンの管理**
   - DRFトークンは永続的です（有効期限なし）
   - セキュリティのため、定期的にトークンを更新することを推奨

3. **デバッグ情報**
   - Django管理画面（http://localhost:8000/admin/）でユーザーとトークンを確認可能
   - 管理者アカウント: admin / arkham_admin_2024