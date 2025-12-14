# Google OAuth API認証ガイド

## 概要

このガイドでは、フロントエンドアプリケーション（React/Vue/Angular等）からGoogle OAuth認証を使用してArkham Nexus APIにアクセスする方法を説明します。

## 認証フロー

### 1. Google Sign-In実装

フロントエンドでGoogle Sign-Inを実装します。

#### HTML
```html
<!-- Google Sign-In ライブラリ -->
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

#### JavaScript (React例)
```jsx
import { useEffect } from 'react';

function GoogleLoginButton() {
  useEffect(() => {
    // Google Sign-In初期化
    window.google.accounts.id.initialize({
      client_id: '456958275505-lgu362m6pl0seeqb8geuom5jf86c1ucn.apps.googleusercontent.com',
      callback: handleCredentialResponse
    });

    // ボタンレンダリング
    window.google.accounts.id.renderButton(
      document.getElementById("googleSignInButton"),
      { 
        theme: "outline", 
        size: "large",
        text: "signin_with"
      }
    );
  }, []);

  const handleCredentialResponse = async (response) => {
    // IDトークンを取得
    const idToken = response.credential;
    
    // バックエンドAPIに送信
    try {
      const apiResponse = await fetch('http://127.0.0.1:8000/api/auth/google/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_token: idToken
        })
      });

      const data = await apiResponse.json();
      
      if (apiResponse.ok) {
        // 認証成功
        console.log('認証成功:', data);
        
        // トークンを保存
        localStorage.setItem('authToken', data.token);
        
        // ユーザー情報を保存/表示
        console.log('ユーザー:', data.user);
        console.log('新規ユーザー:', data.created);
      } else {
        // エラー処理
        console.error('認証エラー:', data.error);
      }
    } catch (error) {
      console.error('通信エラー:', error);
    }
  };

  return <div id="googleSignInButton"></div>;
}
```

### 2. 認証方式

APIは3つの認証方式をサポートしています：

#### A. IDトークン方式（推奨）
```javascript
// Google Sign-Inから取得したIDトークンを使用
const response = await fetch('http://127.0.0.1:8000/api/auth/google/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    id_token: 'eyJhbGciOiJSUzI1NiIsImtpZCI6...' // Google IDトークン
  })
});
```

#### B. アクセストークン方式
```javascript
// Google OAuth Playgroundなどで取得したアクセストークンを使用
const response = await fetch('http://127.0.0.1:8000/api/auth/google/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    access_token: 'ya29.a0ARrdaM...' // Googleアクセストークン
  })
});
```

#### C. 認証コード方式
```javascript
// OAuth2認証フローで取得した認証コードを使用
const response = await fetch('http://127.0.0.1:8000/api/auth/google/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    code: '4/0AX4XfWh...',  // 認証コード
    redirect_uri: 'http://localhost:3000'  // フロントエンドのリダイレクトURI
  })
});
```

### 3. レスポンス形式

成功時のレスポンス：
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@gmail.com",
    "nickname": "Test User",
    "first_name": "Test",
    "last_name": "User"
  },
  "created": true  // true: 新規ユーザー, false: 既存ユーザー
}
```

エラー時のレスポンス：
```json
{
  "error": "エラーメッセージ",
  "detail": "詳細情報（デバッグ時のみ）"
}
```

## 認証後のAPI利用

### 現在のユーザー情報取得

```javascript
const token = localStorage.getItem('authToken');

const response = await fetch('http://127.0.0.1:8000/api/auth/user/', {
  headers: {
    'Authorization': `Token ${token}`
  }
});

const userData = await response.json();
console.log('現在のユーザー:', userData);
```

### 他のAPIエンドポイントへのアクセス

```javascript
// キャラクターシート一覧取得
const response = await fetch('http://127.0.0.1:8000/api/accounts/character-sheets/', {
  headers: {
    'Authorization': `Token ${token}`
  }
});

// グループ一覧取得
const response = await fetch('http://127.0.0.1:8000/api/accounts/groups/', {
  headers: {
    'Authorization': `Token ${token}`
  }
});
```

### ログアウト

```javascript
const response = await fetch('http://127.0.0.1:8000/api/auth/logout/', {
  method: 'POST',
  headers: {
    'Authorization': `Token ${token}`
  }
});

if (response.ok) {
  // トークンを削除
  localStorage.removeItem('authToken');
  console.log('ログアウトしました');
}
```

## CORS設定

開発環境でCORSエラーが発生する場合は、`settings.py`に以下を追加：

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React
    "http://localhost:8080",  # Vue
    "http://localhost:4200",  # Angular
]

# または開発時のみ
CORS_ALLOW_ALL_ORIGINS = True  # 本番環境では使用しない
```

## トラブルシューティング

### 1. "IDトークンの検証に失敗しました"
- Google Client IDが正しいか確認
- IDトークンの有効期限を確認（通常1時間）

### 2. "メールアドレスが取得できませんでした"
- Googleアカウントのプライバシー設定を確認
- スコープに`email`が含まれているか確認

### 3. CORSエラー
- Django側のCORS設定を確認
- `django-cors-headers`がインストールされているか確認

### 4. 401 Unauthorized
- Authorizationヘッダーの形式を確認（`Token`の後にスペース必要）
- トークンが正しく保存されているか確認

## セキュリティ注意事項

1. **本番環境では必ずHTTPSを使用**
2. **Client SecretはフロントエンドにコミットしないでID トークン方式を使用**
3. **トークンの適切な管理**（localStorage vs sessionStorage vs Cookie）
4. **CORS設定は必要最小限に**

## 実装例

完全な実装例は以下のリポジトリを参照：
- React: `examples/react-google-auth/`
- Vue: `examples/vue-google-auth/`
- Angular: `examples/angular-google-auth/`