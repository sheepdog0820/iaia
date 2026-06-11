# Tableno AWS設定ガイド（ECS / 新規VPC / RDS & Redis新規）

最終更新: 2026-06-12

## 1. 目的

- 本番とプレ環境を安全に分離し、`APP_ENV` で確実に切り替える
- SSHしない運用（ECS再デプロイで復旧）
- Secrets/OAuth/TLS証明書をマネージドで管理
- 将来のIaC化（Terraform/CDK）へ移行しやすい構成にする

## 2. アーキテクチャ方針

- 実行基盤: ECS Fargate
- L7入口: ALB（TLS終端 + Host-based routing）
- DNS: Route53
- 証明書: ACM（ALBと同一リージョン）
- DB: RDS MySQL（プライベートサブネット）
- Cache: ElastiCache Redis（プライベートサブネット）
- 機密値: Secrets Manager（必要に応じてSSM）
- 監視: CloudWatch Logs / Metrics / Alarm

## 3. 環境分離ポリシー（必須）

- ECS Serviceを `prod` と `stg` で分離する
- Task Definitionを `prod` と `stg` で分離する
- DB/Redisは原則 `prod` と `stg` で分離する
- 最低でも `DB名` `DBユーザー` `Secrets` は完全分離する
- コンテナイメージは共通化し、差分は環境変数とSecretsで吸収する

## 4. APP_ENV運用ルール

- prod: `APP_ENV=aws-prod`
- stg: `APP_ENV=aws-pre`
- `DJANGO_SETTINGS_MODULE` は `tableno.runtime_env` が自動設定する
- ECSでは `ENV_FILE` を設定しない
- 注意: `ENV_FILE` を設定した場合、指定ファイルが存在しないと起動失敗する

## 5. 命名規則（推奨）

- VPC: `vpc-tableno`
- ALB: `alb-tableno`
- ECS Cluster: `ecs-tableno`
- ECS Service: `svc-tableno-prod`, `svc-tableno-stg`
- Task Definition: `task-tableno-prod`, `task-tableno-stg`
- RDS: `rds-tableno-prod`, `rds-tableno-stg`
- Redis: `redis-tableno-prod`, `redis-tableno-stg`
- Secrets: `tableno/aws-prod/*`, `tableno/aws-pre/*`

## 6. ネットワーク設計（新規VPC）

- VPC CIDR例: `10.40.0.0/16`
- Public Subnet（2AZ以上）: ALBのみ配置
- Private App Subnet（2AZ以上）: ECSタスク配置
- Private Data Subnet（2AZ以上）: RDS/Redis配置
- ECSタスクの外向き通信:
  - 推奨: NAT Gateway
  - 代替: VPC Endpoint中心 + 最小NAT

## 7. セキュリティグループ設計（最小許可）

- `sg-alb`
  - Inbound: `80/tcp` `443/tcp` from `0.0.0.0/0`
  - Outbound: `8000/tcp` to `sg-ecs`
- `sg-ecs`
  - Inbound: `8000/tcp` from `sg-alb`
  - Outbound: `3306/tcp` to `sg-rds`, `6379/6380` to `sg-redis`, `443/tcp` to internet
- `sg-rds`
  - Inbound: `3306/tcp` from `sg-ecs`
- `sg-redis`
  - Inbound: `6379/tcp` or `6380/tcp` from `sg-ecs`

## 8. ドメイン / 証明書 / ALB

対象ドメイン:

- `tableno.jp`
- `www.tableno.jp`
- `stg.tableno.jp`

設定:

- ACM証明書（SAN）に上記3ドメインを登録し、DNS検証で発行
- ALB `443` リスナーで証明書をアタッチ
- Host-based routing:
  - `tableno.jp`, `www.tableno.jp` -> `tg-tableno-prod`
  - `stg.tableno.jp` -> `tg-tableno-stg`
- `80` は `443` へリダイレクト

## 9. Route53

- Hosted Zone: `tableno.jp`
- Alias Aレコード:
  - `tableno.jp` -> ALB
  - `www.tableno.jp` -> ALB
  - `stg.tableno.jp` -> ALB

## 10. RDS / Redis設定

### RDS MySQL

- インスタンスは `prod` と `stg` を分離
- 自動バックアップ有効化（7日以上推奨）
- Multi-AZは本番で有効化推奨
- 接続先はSecretsで注入:
  - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- SSL利用推奨:
  - `DB_SSL_MODE=VERIFY_IDENTITY`（または要件に応じて）
  - `DB_SSL_CA`（必要時）

### ElastiCache Redis

- `prod` と `stg` を分離
- 本番は冗長化（Multi-AZ / Auto-failover）推奨
- TLS有効化推奨（`rediss://`）
- 接続先はSecretsで注入:
  - `REDIS_URL=rediss://...`
  - 必要時 `REDIS_SSL_CERT_REQS=required`

## 11. Secrets Manager設計

### 11.1 例: Secretキー体系

- `tableno/aws-prod/SECRET_KEY`
- `tableno/aws-prod/DB_PASSWORD`
- `tableno/aws-prod/REDIS_URL`
- `tableno/aws-prod/OAUTH_GOOGLE_CLIENT_SECRET`
- `tableno/aws-pre/SECRET_KEY`
- `tableno/aws-pre/DB_PASSWORD`
- `tableno/aws-pre/REDIS_URL`
- `tableno/aws-pre/OAUTH_GOOGLE_CLIENT_SECRET`

### 11.2 ECSへの注入方法

- 推奨: Task Definition `secrets` に個別キーをマッピング
- 代替: JSON Secretを `AWS_SECRETS_JSON` または `AWS_SECRETS_FILE` で注入

## 12. ECS設定（Cluster -> Task Definition -> Service）

### 12.1 Task Definition（prod/stg共通方針）

- Launch type: Fargate
- Log driver: awslogs（CloudWatch Logsへ送信）
- Port mapping: container `8000`
- Health check path: ALBで `/health/ready`
- 必須平文環境変数:
  - `APP_ENV`（prod=`aws-prod`, stg=`aws-pre`）
  - `ENVIRONMENT`（prod=`production`, stg=`staging`）
  - `ALLOWED_HOSTS`
  - `CSRF_TRUSTED_ORIGINS`
  - `SITE_ID`
  - `DB_ENGINE=mysql`
  - `DB_HOST`
  - `DB_PORT=3306`
  - `DB_NAME`
  - `DB_USER`
  - `LOG_TO_STDOUT=True`
- 必須Secrets:
  - `SECRET_KEY`
  - `DB_PASSWORD`
  - `REDIS_URL`

### 12.2 Service（prod/stg）

- Serviceは環境別に2つ作成:
  - `svc-tableno-prod`
  - `svc-tableno-stg`
- それぞれ別Target Groupを関連付け
- Desired count:
  - stg: 1（開始時）
  - prod: 2以上推奨

## 13. アプリ設定（このリポジトリの実装前提）

- `manage.py` / `tableno/wsgi.py` / `tableno/asgi.py` で `APP_ENV` を読み取り
- `APP_ENV=aws-pre/aws-prod` は `tableno.settings_production` を使用
- `/health/live` と `/health/ready` が実装済み
- `settings_production.py` で本番必須設定を検証（未設定はfail-fast）

## 14. OAuth設定

OAuth Provider側に環境別Redirect URIを登録する:

- prod: `https://tableno.jp/...`
- stg: `https://stg.tableno.jp/...`

`prod` と `stg` でOAuth Clientを分離することを推奨。

## 15. CloudWatch運用

- ECSタスクログをCloudWatch Logsへ集約
- 最低限のAlarm:
  - ALB `HTTPCode_Target_5XX_Count`
  - ECS `CPUUtilization`, `MemoryUtilization`
  - RDS `CPUUtilization`, `FreeStorageSpace`
- 復旧基準:
  - `/health/live` が `200`
  - `/health/ready` が `200`

## 16. 実行順（推奨）

1. 新規VPC（public/private subnet）
2. SG作成（ALB/ECS/RDS/Redis）
3. RDS作成 -> エンドポイント控える
4. Redis作成 -> エンドポイント控える
5. Route53 Hosted Zone / NS反映
6. ACM発行（DNS検証）
7. ALB作成 -> Listener/TargetGroup/Host routing
8. Secrets Manager登録 -> Task Role権限付与
9. ECS（cluster -> task definition -> prod/stg service）
10. Route53でA(Alias)割当（`tableno.jp` / `www.tableno.jp` / `stg.tableno.jp`）
11. OAuth側Redirect URIをprod/stg登録
12. healthチェックとログイン検証

## 17. 受け入れチェックリスト

- `https://tableno.jp/health/live` が `200`
- `https://tableno.jp/health/ready` が `200`
- `https://stg.tableno.jp/health/live` が `200`
- `https://stg.tableno.jp/health/ready` が `200`
- prod/stgで異なるDB・Redisを参照している
- CloudWatchで起動失敗理由が追跡できる
