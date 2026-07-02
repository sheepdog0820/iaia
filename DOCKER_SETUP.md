# Docker Setup

TablenoのDocker起動手順です。Pythonランタイムは `Dockerfile` とCIに合わせて Python 3.11 に統一しています。

## 前提

- Docker / Docker Compose
- `.env.*.example` から作成した環境ファイル
- 開発用はSQLiteまたはComposeのDB、本番/ステージング相当は `docker-compose.mysql.yml` のMySQL構成

## 開発用Compose

```bash
cp .env.compose.example .env.compose
cp .env.docker.example .env.docker
# 必要に応じて .env.compose の ENV_FILE を .env.development などへ変更します
docker compose --env-file .env.compose up --build
```

起動後に必要な管理コマンドを実行します。

```bash
docker compose --env-file .env.compose exec web python manage.py migrate --noinput
docker compose --env-file .env.compose exec web python create_admin.py
docker compose --env-file .env.compose exec web python manage.py create_sample_data
```

## ステージング/本番相当Compose

`docker-compose.mysql.yml` はMySQL、Redis、Nginx、Celeryを含む構成です。アプリ起動前にマイグレーションと静的ファイル収集を明示的に実行します。

```bash
# Staging
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml run --rm web python manage.py migrate --noinput
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml run --rm web python manage.py collectstatic --noinput
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d

# Production
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml run --rm web python manage.py migrate --noinput
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml run --rm web python manage.py collectstatic --noinput
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d
```

## よく使うコマンド

```bash
# ログ確認
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml logs -f web

# 停止
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml down

# Django shell
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml exec web python manage.py shell

# collectstatic
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml exec web python manage.py collectstatic --noinput
```

## 注意事項

- `.env.*` の実値はコミットしないでください。
- Composeの `.env.compose` とDjangoが読む `ENV_FILE` は用途が異なります。
- `SECRET_KEY` などに `$` を含める場合、Composeの変数展開対象になるファイルでは `$$` にエスケープしてください。
- `APP_ENV=aws-pre` / `APP_ENV=aws-prod` は `tableno.settings_production` を使います。
- 本番/ステージング相当では、Web/Celeryコンテナ起動時に自動で `migrate` や `collectstatic` を実行しない前提です。
