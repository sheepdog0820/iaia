# Docker セットアップガイド

本ドキュメントは **ステージング/本番（MySQL + Nginx）** を中心に説明します。
開発用は `docker-compose.yml`（PostgreSQL）を使用します。

## 前提条件

- Python 3.11+
- Docker / Docker Compose

## 📋 利用する Compose

- **開発**: `docker-compose.yml`（PostgreSQL）
- **Stg/Prod**: `docker-compose.mysql.yml`（MySQL + Redis + Nginx + Celery）

## 🚀 クイックスタート（Stg/Prod）

### 1. 環境変数の設定

```bash
cp .env.production.example .env.production
cp .env.staging.example .env.staging
```

※ `.env.*` は `ENV_FILE` で明示指定します（settings.py は自動読み込みしません）。
※ 実際に使う環境のファイルだけ用意すればOKです。
※ Docker Compose はカレントディレクトリの `.env` やサービスの `env_file` を変数展開にも使います。Compose 用 `.env` と Django 用 `ENV_FILE` を分けても、`ENV_FILE` 側の `SECRET_KEY` などに `$` を含める場合は `$$` にエスケープしてください。

### 2. デプロイ前処理

Stg/Prod では Web/Celery コンテナ起動時に migration や collectstatic を自動実行しません。
デプロイ手順で明示的に 1 回だけ実行してください。

```bash
# Stg
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml run --rm web python manage.py migrate --noinput
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml run --rm web python manage.py collectstatic --noinput

# Prod
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml run --rm web python manage.py migrate --noinput
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml run --rm web python manage.py collectstatic --noinput
```

### 3. 起動

```bash
# Stg
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d

# Prod
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d
```

### 4. 管理コマンド

```bash
# マイグレーション
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml exec web python manage.py migrate

# スーパーユーザー作成
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml exec web python manage.py createsuperuser

# collectstatic
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml exec web python manage.py collectstatic --noinput
```

## 🐳 開発環境（PostgreSQL）

```bash
cp .env.compose.example .env.compose
# サンプル起動は .env.docker.example を使用します。実開発値を使う場合は .env.compose の ENV_FILE を .env.development に変更します。
docker compose --env-file .env.compose up -d
```

`.env.compose` は Compose の補間用、`.env.docker.example` はサンプル起動用のDjangoアプリenvです。Django側の実開発秘密値を使う場合は `.env.development` に置き、`.env.compose` の `ENV_FILE` を `.env.development` に変更してください。
ただし、利用するComposeバージョンによっては `env_file` の中身も補間対象になります。`.env.development` や `.env.production` の値に `$` を含める場合は `$$` にエスケープしてください。

## 🔧 よく使うコマンド（Stg/Prod）

```bash
# ログ確認
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml logs -f web

# 停止
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml down
```

## 🗄️ MySQL 操作（Stg/Prod）

```bash
# MySQL に接続
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml exec db \
  sh -c 'mysql -u\"$DB_USER\" -p\"$DB_PASSWORD\" \"$DB_NAME\"'

# バックアップ
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml exec db \
  sh -c 'mysqldump -u\"$DB_USER\" -p\"$DB_PASSWORD\" \"$DB_NAME\"' > backup.sql
```

## 🔒 SSL（Nginx）

- `nginx.conf` の `server_name` は **環境ごとに** 設定してください。
- 証明書の配置は `./ssl/fullchain.pem` と `./ssl/privkey.pem` です。
- 詳細手順は `docs/DEPLOYMENT_GUIDE.md` を参照してください。
