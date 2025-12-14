# Google OAuth リダイレクトURI設定ガイド（127.0.0.1統一版）

## エラー: redirect_uri_mismatch の解決方法

### 1. Google Cloud Console での設定（127.0.0.1に統一）

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) を開く
2. 該当のOAuth 2.0 クライアントIDをクリック
3. 「承認済みのリダイレクトURI」セクションで以下のURIを追加:

```
http://127.0.0.1:8000/accounts/google/login/callback/
```

4. 「承認済みのJavaScript生成元」セクションで以下を追加:

```
http://127.0.0.1:8000
```

**重要**: `localhost` を使用したURIは削除してください（127.0.0.1に統一）

### 2. 重要な注意点

- **末尾のスラッシュ**: 必ず含める（`/accounts/google/login/callback/`）
- **HTTPプロトコル**: 開発環境では `http://` を使用（`https://` ではない）
- **ポート番号**: `:8000` を必ず含める
- **127.0.0.1を使用**: `localhost` ではなく `127.0.0.1` を使用
- **django-allauth形式**: `/accounts/google/login/callback/` を使用

### 3. エラーの原因

アプリケーションは以下のリダイレクトURIを使用しています：
- `http://127.0.0.1:8000/accounts/google/login/callback/`

このURIがGoogle Cloud Consoleに正確に登録されていない場合、`redirect_uri_mismatch`エラーが発生します。

### 4. 確認方法

1. ブラウザで `http://127.0.0.1:8000/accounts/login/` にアクセス（`localhost`ではなく`127.0.0.1`を使用）
2. 「Googleでログイン」ボタンをクリック
3. エラーページのURLを確認し、`redirect_uri`パラメータの値を確認

### 5. トラブルシューティング

- 設定変更後、数分待つ（Google側の反映に時間がかかる場合があります）
- ブラウザのキャッシュをクリア
- シークレット/プライベートブラウジングモードで試す
- 正しいGoogle Cloudプロジェクトを編集しているか確認

### 6. 本番環境への移行時

本番環境では以下のようなURIに変更する必要があります：
```
https://yourdomain.com/accounts/google/callback/
```