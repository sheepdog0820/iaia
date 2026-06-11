# タブレノ デプロイメントガイド

最終更新: 2026-06-12

## 1. 構成方針

正規のAWS本番構成は次のとおりです。

- ECS Fargate
- ALB + ACM
- Route 53
- RDS MySQL
- ElastiCache Redis
- S3 + CloudFront
- Secrets Manager / SSM
- CloudWatch Logs / Metrics / Alarm

詳細なAWSリソース作成手順は `docs/AWS_ECS_SETUP_GUIDE.md` を参照してください。

`docker-compose.mysql.yml` と `nginx.conf` は、ローカル本番相当検証または既存Lightsail運用の互換手段です。AWS/ECSではコンテナ内Nginxとcertbotを使用せず、ALBでTLSを終端します。

## 2. 環境選択

| 環境 | APP_ENV | 設定 |
| --- | --- | --- |
| ローカル | `local` | `tableno.settings` |
| AWSプレ環境 | `aws-pre` | `tableno.settings_production` |
| AWS本番 | `aws-prod` | `tableno.settings_production` |

`manage.py`、WSGI、ASGIは`tableno.runtime_env`を通して設定を選択します。AWS/ECSでは`ENV_FILE`を設定せず、Task Definitionの環境変数とSecretsを使用します。

## 3. 必須設定

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

本番設定では未設定値を起動時に検出して失敗します。OAuthのIDとSecretは必ず対で設定します。

## 4. AWS Secrets

推奨方式はECS Task Definitionの`secrets`による個別注入です。

```bash
AWS_SECRETS_JSON={"SECRET_KEY":"...","DB_PASSWORD":"...","REDIS_URL":"..."}
AWS_SECRETS_FILE=/run/secrets/tableno.json
```

ローテーション手順は`docs/SECRETS_ROTATION_RUNBOOK.md`を参照してください。

## 5. RDS / ElastiCache

```bash
DB_ENGINE=mysql
DB_HOST=database.example.ap-northeast-1.rds.amazonaws.com
DB_PORT=3306
DB_SSL_MODE=VERIFY_IDENTITY
DB_SSL_CA=/app/certs/rds-ca.pem

REDIS_URL=rediss://cache.example.cache.amazonaws.com:6379/1
REDIS_SSL_CERT_REQS=required
```

## 6. S3 / CloudFront

```bash
USE_S3_STORAGE=True
AWS_STORAGE_BUCKET_NAME=tableno-prod-assets
AWS_S3_REGION_NAME=ap-northeast-1
AWS_S3_CUSTOM_DOMAIN=assets.tableno.jp
AWS_STATIC_LOCATION=static
AWS_MEDIA_LOCATION=media
```

## 7. ALB / ACM

- ALBの80番は443番へリダイレクト
- ACM証明書を443番リスナーへ設定
- Host-based routingでprod/stgを分離
- Djangoは`SECURE_PROXY_SSL_HEADER`と`USE_X_FORWARDED_HOST`を使用
- `ALLOWED_HOSTS`と`CSRF_TRUSTED_ORIGINS`は環境別に限定

| 項目 | 値 |
| --- | --- |
| Path | `/health/ready` |
| Success code | `200` |
| Interval | `30s` |
| Timeout | `5s` |
| Healthy threshold | `2` |
| Unhealthy threshold | `3` |

`/health/live`はプロセス生存確認、`/health/ready`はDBとCacheの疎通確認です。

## 8. ECS起動

```text
APP_ENV=aws-prod
ENVIRONMENT=production
LOG_TO_STDOUT=True
ENABLE_FILE_LOGGING=False
```

`docker/entrypoint.sh`がマイグレーションと静的ファイル収集を行い、Gunicornを起動します。

## 9. Compose互換運用

```bash
# プレ環境
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d --build

# 本番相当
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d --build
```

Composeでは`APP_ENV`をコンテナへ渡し、`DJANGO_SETTINGS_MODULE`は固定しません。

## 10. リリース確認

```bash
curl -f https://tableno.jp/health/live
curl -f https://tableno.jp/health/ready
```

- マイグレーション成功
- static/media表示成功
- 通常ログインとOAuthログイン成功
- DB/Redis接続エラーなし
- CloudWatchへアプリログが出力される
