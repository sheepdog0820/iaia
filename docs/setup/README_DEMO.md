# タブレノ - デモログイン機能

## 概要
開発・テスト環境でソーシャル認証の実装を確認するため、疑似的なソーシャルログイン機能を実装しました。実際のGoogleやTwitterのOAuth認証を行わずに、ソーシャルログインの流れを体験できます。

## 利用方法

### 1. デモログインページにアクセス
```
http://localhost:8000/accounts/demo/
```

### 2. 通常ログインページからアクセス
通常のログインページ（`/accounts/login/`）の下部に「デモログインはこちら」リンクが表示されます。

## 機能詳細

### デモアカウント

#### Google Demo Account
- **Name:** Google User
- **Email:** demo.google@example.com
- **Nickname:** Google Demo User
- **Avatar:** 自動生成プレースホルダー

#### Twitter Demo Account
- **Name:** Twitter User
- **Email:** demo.twitter@example.com
- **Handle:** @TwitterDemo
- **Avatar:** 自動生成プレースホルダー

### 実装内容

1. **疑似認証処理**
   - 実際のOAuth APIを呼び出さない
   - 予め定義されたデモデータを使用
   - リアルタイムでユーザーアカウントを作成

2. **データベース連携**
   - `CustomUser`モデルでユーザー作成
   - `SocialAccount`モデルでソーシャル連携情報を保存
   - 既存ユーザーの場合は再ログイン

3. **認証フロー**
   - 通常のソーシャル認証と同じ流れ
   - ダッシュボードへリダイレクト
   - セッション管理
   - メッセージ表示

## セキュリティ

### 開発環境のみ
- `DEBUG=True` の場合のみ利用可能
- 本番環境では無効化される
- デモモードの明確な表示

### 制限事項
- 固定されたデモデータのみ使用
- 実際のAPIキーやシークレットは不要
- ネットワーク通信なし

## URL構成

```
/accounts/demo/                     # デモログインページ
/accounts/mock-social/google/       # Google疑似認証
/accounts/mock-social/twitter/      # Twitter疑似認証
```

## ファイル構成

```
accounts/
├── views.py                        # mock_social_login, demo_login_page
├── urls.py                         # デモURL定義
└── templates/account/
    └── demo_login.html            # デモログインページ

templates/account/
└── login.html                     # デモリンク追加
```

## 使用例

### 1. 新規ユーザーとしてログイン
1. デモページでGoogleボタンをクリック
2. 新しいユーザーアカウントが作成される
3. ダッシュボードにリダイレクト
4. 成功メッセージ: "Googleアカウントでアカウントを作成し、ログインしました！ (デモモード)"

### 2. 既存ユーザーとしてログイン
1. 同じプロバイダーのボタンを再クリック
2. 既存アカウントでログイン
3. 成功メッセージ: "Googleアカウントでログインしました！ (デモモード)"

## 実際のソーシャル認証への移行

デモ機能から実際のソーシャル認証に移行する場合：

1. **OAuth アプリ設定**
   - Google Cloud Console でOAuthアプリ作成
   - Twitter Developer Portal でアプリ作成

2. **環境変数更新**
   ```bash
   GOOGLE_CLIENT_ID=actual-google-client-id
   GOOGLE_CLIENT_SECRET=actual-google-client-secret
   TWITTER_CLIENT_ID=actual-twitter-client-id
   TWITTER_CLIENT_SECRET=actual-twitter-client-secret
   ```

3. **設定更新**
   - `settings.py` の `SOCIALACCOUNT_PROVIDERS` を実際の値に更新
   - データベースの `SocialApp` レコードを更新

## トラブルシューティング

### デモボタンが表示されない
- `DEBUG=True` が設定されているか確認
- サーバーの再起動を試す

### ログインエラーが発生する
- データベースのマイグレーションを確認
- `accounts.models` の `CustomUser` モデルが正しく設定されているか確認

### 重複ユーザーエラー
- デモ用のメールアドレスが既に使用されている場合
- データベースをリセットするか、別のデモデータを使用