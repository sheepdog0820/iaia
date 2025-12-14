# Google OAuth redirect_uri_mismatch エラーの解決方法

## エラーの原因
Google OAuth認証で「エラー 400: redirect_uri_mismatch」が発生するのは、アプリケーションが使用しているリダイレクトURIが、Google Cloud Consoleに登録されているURIと一致しないためです。

## 解決手順

### 1. Google Cloud Consoleにアクセス
1. [Google Cloud Console](https://console.cloud.google.com/)にログイン
2. プロジェクト「Arkham Nexus」を選択
3. 左側メニューから「APIとサービス」→「認証情報」を選択

### 2. OAuth 2.0 クライアントIDを編集
1. 作成済みのOAuthクライアント「Arkham Nexus API Client」をクリック
2. 以下の設定を確認・更新します：

#### 承認済みのJavaScript生成元
以下のURLをすべて追加してください：
```
http://localhost:8000
http://localhost:3000
http://127.0.0.1:8000
http://127.0.0.1:3000
```

#### 承認済みのリダイレクトURI
以下のURLをすべて追加してください：
```
http://localhost:8000/accounts/google/login/callback/
http://localhost:8000/auth/google/callback/
http://localhost:3000/auth/google/callback
http://127.0.0.1:8000/accounts/google/login/callback/
http://127.0.0.1:8000/auth/google/callback/
http://127.0.0.1:3000/auth/google/callback
```

### 3. 設定の保存
「保存」ボタンをクリックして設定を保存します。

## 重要な注意事項

### リダイレクトURIの形式
- **末尾のスラッシュ（/）に注意**: 一部のURIは末尾にスラッシュが必要です
- **httpとhttps**: 開発環境ではhttpを使用しますが、本番環境では必ずhttpsを使用してください
- **ポート番号**: localhostの場合はポート番号も含めて完全一致する必要があります

### django-allauthを使用している場合
現在のシステムはdjango-allauthを使用しているため、標準的なリダイレクトURIは以下の形式になります：
- `/accounts/google/login/callback/`

### テスト方法
1. ブラウザのシークレットモード/プライベートモードを使用
2. キャッシュとCookieをクリア
3. Google認証を最初からやり直す

## トラブルシューティング

### それでもエラーが続く場合
1. **実際のリダイレクトURIを確認**
   - ブラウザの開発者ツール（F12）を開く
   - Networkタブで実際のリダイレクトURLを確認
   - そのURLをGoogle Cloud Consoleに追加

2. **URLエンコーディングの確認**
   - 特殊文字が含まれていないか確認
   - URLが正しくエンコードされているか確認

3. **OAuth同意画面の確認**
   - 「APIとサービス」→「OAuth同意画面」
   - アプリケーションが「テスト」状態になっているか確認
   - テストユーザーが追加されているか確認（必要な場合）

### 本番環境への移行時
本番環境では以下の点に注意：
- HTTPSを使用
- 実際のドメイン名を使用
- 適切なリダイレクトURIを設定

例：
```
https://your-domain.com/accounts/google/login/callback/
https://your-domain.com/api/auth/google/callback
```