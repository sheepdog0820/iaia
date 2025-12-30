# Docker セットアップガイド

本番環境想定のDocker設定です。PostgreSQL + gunicorn で動作します。

## 📋 必要なファイル

以下のファイルが追加されています：

- `Dockerfile` - Django アプリケーションのコンテナ定義
- `docker-compose.yml` - マルチコンテナ構成（web + db）
- `docker/entrypoint.sh` - 起動スクリプト（migration + collectstatic + gunicorn）
- `.env.docker` - Docker環境用の環境変数テンプレート
- `.dockerignore` - イメージビルド時の除外設定

## 🚀 クイックスタート

### 1. 環境変数の設定

`.env.docker` をコピーして `.env` を作成：

```bash
cp .env.docker .env
```

`.env` を編集して必要な値を設定：

```env
# 本番環境では必ず変更
SECRET_KEY=your-secret-key-here-change-in-production

# Google OAuth設定
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# データベースパスワード（変更推奨）
POSTGRES_PASSWORD=secure-password-here
```

### 2. Dockerコンテナをビルド＆起動

```bash
docker compose build
docker compose up
```

または、バックグラウンドで起動：

```bash
docker compose up -d
```

### 3. アクセス確認

ブラウザで以下にアクセス：

```
http://127.0.0.1:8000/
```

## 📁 プロジェクト構造

```
プロジェクト名: arkham_nexus
Settings Module: arkham_nexus.settings
WSGI Module: arkham_nexus.wsgi
```

## 🔧 主要コマンド

### コンテナの起動・停止

```bash
# ビルドして起動
docker compose build
docker compose up

# バックグラウンドで起動
docker compose up -d

# ログを確認
docker compose logs -f web

# 停止
docker compose down

# 停止＋ボリューム削除（データベース含む）
docker compose down -v
```

### Django管理コマンドの実行

```bash
# マイグレーション
docker compose exec web python manage.py migrate

# スーパーユーザー作成
docker compose exec web python create_admin.py

# Djangoシェル
docker compose exec web python manage.py shell

# 静的ファイル収集
docker compose exec web python manage.py collectstatic --noinput
```

### テスト実行

```bash
# コンテナ起動済みの場合
docker compose exec web python manage.py test accounts.test_group_features

# 使い捨てコンテナで実行する場合
docker compose run --rm web python manage.py test accounts.test_group_features
```

### データベース操作

```bash
# PostgreSQLに接続
docker compose exec db psql -U iaia -d iaia

# データベースのバックアップ
docker compose exec db pg_dump -U iaia iaia > backup.sql

# バックアップからリストア
docker compose exec -T db psql -U iaia iaia < backup.sql
```

## 🏗️ 構成詳細

### サービス構成

#### web（Djangoアプリケーション）
- **イメージ**: カスタムビルド（Dockerfile使用）
- **ポート**: 8000
- **起動コマンド**: gunicorn（entrypoint.sh経由）
- **環境変数**: `.env` から読み込み

#### db（PostgreSQL 16）
- **イメージ**: postgres:16
- **ポート**: 5432
- **データ永続化**: `postgres_data` ボリューム
- **デフォルトDB**: iaia
- **デフォルトユーザー**: iaia

### ボリューム

```yaml
postgres_data:    # PostgreSQLデータ
static_volume:    # 静的ファイル
media_volume:     # メディアファイル
```

### 環境変数

`.env` ファイルで設定可能な主要な環境変数：

| 変数名 | 説明 | デフォルト値 |
|--------|------|--------------|
| `DJANGO_SETTINGS_MODULE` | Django設定モジュール | `arkham_nexus.settings` |
| `DJANGO_WSGI_MODULE` | WSGIモジュール | `arkham_nexus.wsgi` |
| `DEBUG` | デバッグモード | `0` (本番は必ず0) |
| `SECRET_KEY` | Django秘密鍵 | _(変更必須)_ |
| `ALLOWED_HOSTS` | 許可ホスト | `127.0.0.1,localhost` |
| `DATABASE_URL` | DB接続URL | `postgres://iaia:iaia@db:5432/iaia` |
| `GUNICORN_WORKERS` | Gunicornワーカー数 | `2` |
| `GUNICORN_TIMEOUT` | リクエストタイムアウト（秒） | `60` |
| `POSTGRES_DB` | PostgreSQL DB名 | `iaia` |
| `POSTGRES_USER` | PostgreSQL ユーザー名 | `iaia` |
| `POSTGRES_PASSWORD` | PostgreSQL パスワード | `iaia` _(変更推奨)_ |

## 🔐 本番環境への移行

### 必須変更項目

1. **SECRET_KEY の変更**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

2. **DEBUG を無効化**
   ```env
   DEBUG=0
   ```

3. **ALLOWED_HOSTS の設定**
   ```env
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```

4. **データベースパスワードの変更**
   ```env
   POSTGRES_PASSWORD=secure-random-password-here
   DATABASE_URL=postgres://iaia:secure-random-password-here@db:5432/iaia
   ```

5. **Google OAuth リダイレクトURI**
   - Google Cloud Consoleで本番環境のURLを登録
   - 例: `https://yourdomain.com/accounts/google/login/callback/`

### 推奨設定

1. **HTTPSの有効化**
   - Nginx等のリバースプロキシでSSL終端
   - `SECURE_SSL_REDIRECT = True` の設定

2. **静的ファイルの配信**
   - Nginx等で直接配信（gunicornを経由しない）
   - CDNの活用

3. **ログの管理**
   - ボリュームマウントでログを永続化
   - ログローテーションの設定

4. **バックアップ**
   - 定期的なデータベースバックアップ
   - メディアファイルのバックアップ

## 🐛 トラブルシューティング

### コンテナが起動しない

```bash
# ログを確認
docker compose logs web

# コンテナの状態を確認
docker compose ps

# イメージを再ビルド
docker compose build --no-cache
```

### データベース接続エラー

```bash
# dbコンテナが起動しているか確認
docker compose ps db

# dbコンテナのログを確認
docker compose logs db

# 接続テスト
docker compose exec web python manage.py dbshell
```

### 静的ファイルが表示されない

```bash
# 静的ファイルを再収集
docker compose exec web python manage.py collectstatic --noinput

# 静的ファイルボリュームを確認
docker compose exec web ls -la /app/staticfiles
```

### マイグレーションエラー

```bash
# マイグレーションの状態を確認
docker compose exec web python manage.py showmigrations

# 手動でマイグレーション実行
docker compose exec web python manage.py migrate

# マイグレーションをリセット（開発環境のみ）
docker compose down -v
docker compose up -d
```

## 📝 開発モードでの実行

開発時はローカルコード変更が即座に反映されるよう、`docker-compose.yml` で以下のボリュームマウントを設定済み：

```yaml
volumes:
  - .:/app  # ローカルコードをマウント
```

ただし、以下の場合は再起動が必要：

- `requirements.txt` の変更時 → `docker compose build` して再起動
- 環境変数の変更時 → `docker compose restart web`
- Djangoのsettings.py変更時 → `docker compose restart web`

## 🔗 関連ドキュメント

- [Google OAuth設定ガイド](GOOGLE_CLOUD_CONSOLE_SETUP_CHECKLIST.md)
- [ソーシャルログイン設定](SOCIAL_LOGIN_SETUP.md)
- [プロジェクト仕様書](SPECIFICATION.md)

## 💡 Tips

### SQLiteで動かしたい場合

データベースを軽量にしたい場合は、`docker-compose.yml` から `db` サービスを削除し、`.env` で以下のように設定：

```env
# DATABASE_URL を削除またはコメントアウト
# DATABASE_URL=postgres://iaia:iaia@db:5432/iaia
```

`settings.py` でSQLiteを使用する設定に変更してください。

### gunicornワーカー数の調整

CPUコア数に応じて調整（推奨：`(CPUコア数 × 2) + 1`）：

```env
GUNICORN_WORKERS=5  # 2コアの場合
```

### 本番環境でのベストプラクティス

1. **.envファイルの管理**
   - `.env` は `.gitignore` に追加済み
   - 本番環境では環境変数を安全に管理（AWS Secrets Manager等）

2. **ログの監視**
   - Sentry等の監視ツールを導入（requirements.txtに含まれています）

3. **スケーリング**
   - webサービスのレプリカ数を増やす
   - ロードバランサーを前段に配置

4. **セキュリティ**
   - ファイアウォールの設定
   - 定期的なセキュリティアップデート
   - 不要なポートを閉じる
