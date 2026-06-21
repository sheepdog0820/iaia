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
現在確認できているAWS構成と今後の低コスト構成方針は `docs/specifications/AWS_INFRASTRUCTURE_CONFIGURATION.md` を参照してください。

`aws-pre` は低コスト構成として運用できます。この場合、web service は public subnet + public IP で常時1タスクのみ稼働し、NAT Gateway、ElastiCache Redis、worker/beat service は作成しません。Redis 無効時は `USE_REDIS_CACHE=False`、DB session、LocMemCache、in-memory channel layer を使用し、WebSocket通知とCelery定期実行は無効です。定期処理は必要時に `publish_scheduled_handouts`、`expire_async_jobs`、`expire_premium_access`、`sync_japanese_holidays` management command を手動実行します。期限付きプレミアムコードを発行している環境では、`expire_premium_access` を少なくとも日次で実行し、実行後に `billing_status_report --fail-on-issues` で期限切れ権限が残っていないことを確認します。

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
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PREMIUM_PRICE_ID / STRIPE_PREMIUM_YEARLY_PRICE_ID`
- `STRIPE_REVOKE_ON_REFUND_OR_DISPUTE`
- `PUBLIC_SITE_URL`
- `EMAIL_BACKEND`
- `DEFAULT_FROM_EMAIL`
- `STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID`
- PREMIUM_PRICE_LABEL`r
- `PREMIUM_MONTHLY_PRICE_LABEL`
- `PREMIUM_MONTHLY_PRICE_DESCRIPTION`
- `PREMIUM_YEARLY_PRICE_LABEL`
- `PREMIUM_YEARLY_PRICE_DESCRIPTION`
- `LEGAL_PAYMENT_METHOD`
- `LEGAL_PAYMENT_TIMING`
- `LEGAL_SERVICE_DELIVERY_TIMING`
- `LEGAL_CANCELLATION_METHOD`
- `LEGAL_CANCELLATION_EFFECT`
- `LEGAL_REFUND_POLICY`
- `LEGAL_SELLER_NAME`
- `LEGAL_SELLER_ADDRESS`
- `LEGAL_SELLER_PHONE`
- `CONTACT_EMAIL`

本番設定では未設定値を起動時に検出して失敗します。OAuthのIDとSecretは必ず対で設定します。

課金機能を有効にする環境では、Stripe Dashboardで作成した月額Price IDとWebhook signing secretを設定します。`ENVIRONMENT=production` では `STRIPE_SECRET_KEY` に `sk_live_` で始まる本番キーのみ許可され、staging/local の検証では `sk_test_` を使用します。`invoice.payment_failed` でカード更新依頼メールを送るため、`EMAIL_BACKEND` は console/dummy/locmem ではない実配送backendを使い、`DEFAULT_FROM_EMAIL` を設定します。料金、支払方法、支払時期、提供時期、解約方法、返金条件、問い合わせ先は特商法ページとプレミアム機能ページに表示されます。`STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=True` は返金/チャージバック検知時にプレミアム権限を自動停止し、`False` は監査ログだけ残して管理者確認に回します。`LEGAL_SELLER_NAME`、`LEGAL_SELLER_ADDRESS`、`LEGAL_SELLER_PHONE`、`CONTACT_EMAIL` は本番ではプレースホルダーではなく実際の事業者情報を設定してください。デプロイ前に `python manage.py billing_preflight --strict` を実行し、Stripe URL、特商法表示、返金時の権限停止方針、プレミアムコード失効ジョブの設定を確認します。

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
