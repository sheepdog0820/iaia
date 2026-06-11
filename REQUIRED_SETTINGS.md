# 必須設定

最終更新: 2026-06-12

## 環境プロファイル

- ローカル: `APP_ENV=local`
- AWSプレ環境: `APP_ENV=aws-pre`
- AWS本番: `APP_ENV=aws-prod`

`APP_ENV`未指定時は`local`です。`DJANGO_SETTINGS_MODULE`は通常、直接指定しません。

## ローカル

```bash
APP_ENV=local ENV_FILE=.env.development python manage.py runserver
```

SQLiteを使う場合、DB接続値は不要です。

## AWSプレ・本番

必須値:

- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `SITE_ID`
- `DB_ENGINE`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `REDIS_URL`

| 項目 | プレ環境 | 本番 |
| --- | --- | --- |
| `APP_ENV` | `aws-pre` | `aws-prod` |
| `ENVIRONMENT` | `staging` | `production` |
| `ALLOWED_HOSTS` | `stg.tableno.jp` | `tableno.jp,www.tableno.jp` |
| `CSRF_TRUSTED_ORIGINS` | `https://stg.tableno.jp` | `https://tableno.jp,https://www.tableno.jp` |
| `SITE_ID` | `2` | `1` |

## Secrets

ECS Task Definitionの`secrets`で個別注入する方式を推奨します。JSON形式を使用する場合は`AWS_SECRETS_JSON`または`AWS_SECRETS_FILE`を設定します。

## RDS

- MySQL: `DB_ENGINE=mysql`
- PostgreSQL: `DB_ENGINE=postgresql`
- TLS: `DB_SSL_MODE`, `DB_SSL_CA`

ComposeのMySQLを使用する場合のみ`DB_ROOT_PASSWORD`も必要です。

## Redis

- 非TLS: `redis://...`
- TLS: `rediss://...`
- 証明書検証: `REDIS_SSL_CERT_REQS=required`

## S3 / CloudFront

`USE_S3_STORAGE=True`の場合:

- `AWS_STORAGE_BUCKET_NAME`
- `AWS_S3_REGION_NAME`
- `AWS_S3_CUSTOM_DOMAIN`（CloudFront利用時）
- `AWS_STATIC_LOCATION`
- `AWS_MEDIA_LOCATION`

## ログ

AWS/ECS:

```text
LOG_TO_STDOUT=True
ENABLE_FILE_LOGGING=False
```

## ヘルスチェック

- Liveness: `/health/live`
- Readiness: `/health/ready`

ReadinessはDBまたはCacheの障害時に`503`を返します。
