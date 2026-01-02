# 必要設定チェックリスト（Local / Stg / Prod）

手作業で設定が必要な項目をまとめています。

## 共通（全環境）

- 例ファイルから env を作成して必須値を埋める
  - Local: `.env.development`
  - Stg: `.env.staging`
  - Prod: `.env.production`
- 各 env ファイルに必須のキー:
  - `SECRET_KEY`
  - `ALLOWED_HOSTS`
  - `CSRF_TRUSTED_ORIGINS`
  - `SITE_ID`
  - `DB_ENGINE` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT`
- Django Sites を使う場合、環境ごとに Site レコードを分ける

## ローカル（Dev）

- `.env.development`
  - `ALLOWED_HOSTS=localhost,127.0.0.1`
  - `CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000`
  - `SITE_ID=1`（またはローカルの Site ID）
  - DBは必要に応じて設定（SQLiteを使うなら最小限でOK）
- 起動: `ENV_FILE=.env.development python manage.py runserver`

## ステージング（stg.tableno.jp）

- `.env.staging`
  - `ALLOWED_HOSTS=stg.tableno.jp`
  - `CSRF_TRUSTED_ORIGINS=https://stg.tableno.jp`
  - `SITE_ID=2`（またはステージングの Site ID）
  - DB（ComposeのMySQL / RDSなどの接続先）
- stgインスタンスの `nginx.conf`:
  - `server_name stg.tableno.jp;`

## 本番（app.tableno.jp）

- `.env.production`
  - `ALLOWED_HOSTS=app.tableno.jp`
  - `CSRF_TRUSTED_ORIGINS=https://app.tableno.jp`
  - `SITE_ID=1`（または本番の Site ID）
  - DB（ComposeのMySQL / RDSなどの接続先）
- prodインスタンスの `nginx.conf`:
  - `server_name app.tableno.jp;`

## DNS（環境別）

- `app.tableno.jp` -> prod Lightsail の固定IP
- `stg.tableno.jp` -> stg Lightsail の固定IP

## SSL（環境別）

- 証明書の配置先:
  - `./ssl/fullchain.pem`
  - `./ssl/privkey.pem`
- 実行: `ENV_FILE=.env.staging ./scripts/renew_certbot.sh`（または `.env.production`）

## Compose（環境別）

- Stg: `ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d --build`
- Prod: `ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d --build`
