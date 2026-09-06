# Docker Setup

TablenoのDocker起動手順です。Pythonランタイムは `Dockerfile` とCIに合わせて Python 3.11+ に統一しています。

アプリイメージは既定でUID/GID `10001`の非rootユーザー`tableno`として動作します。LinuxやNASで`staticfiles`、`media`、`logs`をbind mountする場合は、ホスト側ディレクトリを同じUID/GIDから書き込み可能にしてください。環境に合わせる場合は`APP_UID`と`APP_GID`をビルド引数で指定します。

Python依存はイメージのビルド時に固定ロックから導入し、`pip check`成功後にpip・setuptools・wheelを除去します。稼働コンテナにはこれらのパッケージ管理ツールがないため、依存の追加・更新はロックを更新してイメージを再ビルドしてください。Django管理コマンドは引き続き実行できます。

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

```bash
docker compose build --build-arg APP_UID=10001 --build-arg APP_GID=10001
```

起動後に必要な管理コマンドを実行します。

```bash
docker compose --env-file .env.compose exec web python manage.py migrate --noinput
docker compose --env-file .env.compose exec web python scripts/dev/create_admin.py
docker compose --env-file .env.compose exec web python manage.py create_sample_data
```

## ステージング/本番相当Compose

`docker-compose.mysql.yml` はMySQL、Redis、Nginx、Celeryを含む構成です。アプリ起動前にマイグレーションと静的ファイル収集を明示的に実行します。

```bash
# Staging
MYSQL_APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml run --rm web python manage.py migrate --noinput
MYSQL_APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml run --rm web python manage.py collectstatic --noinput
MYSQL_APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d

# Production
MYSQL_APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml run --rm web python manage.py migrate --noinput
MYSQL_APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml run --rm web python manage.py collectstatic --noinput
MYSQL_APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d
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
- 開発用Composeは `.env.compose` から `ENV_FILE` を渡し、Django側のサンプルenvとして `.env.docker.example` を使います。
- Composeの `env_file` 側で `SECRET_KEY` などに `$` を含める場合、Composeの変数展開対象になるファイルでは `$$` にエスケープしてください。
- `MYSQL_APP_ENV=aws-pre` / `MYSQL_APP_ENV=aws-prod` はコンテナ内の`APP_ENV`へ渡され、`tableno.settings_production`を使います。
- 本番/ステージング相当では、Web/Celeryコンテナ起動時に自動で `migrate` や `collectstatic` を実行しない前提です。
