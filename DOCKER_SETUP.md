# Docker セットアップガイド

本ドキュメントは **ステージング/本番（MySQL + Nginx）** を中心に説明します。
開発用は `docker-compose.yml`（PostgreSQL）を使用します。

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

### 2. 起動

```bash
# Stg
ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d

# Prod
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d
```

### 3. 管理コマンド

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
docker compose up -d
```

`.env` を利用する場合は `docker-compose.yml` に合わせて用意してください。

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
