# AWSリリース作業計画

最終更新: 2026-06-12

## 目的

ECS/Fargateを中心とするAWS本番構成について、リポジトリ内で検証できる成果物と、AWSアカウント上で実施するリリース作業を分離して管理します。

Terraform、移行Runbook、障害一次対応Runbookは実装済みです。AWSへの実適用、監視通知先の確定、Go/No-Go承認は認証情報と運用判断を必要とする別工程です。

## ISSUE-051: Secrets・環境変数

- [x] `APP_ENV`による環境選択
- [x] 本番必須値のfail-fast検証
- [x] Secrets Manager/SSMの注入方式を文書化
- [x] JSON Secret読込
- [x] ローテーション手順
- [x] 単体テスト

## ISSUE-052: S3・CloudFront

- [x] `django-storages` / `boto3`
- [x] static/mediaのS3切替
- [x] CloudFrontカスタムドメイン
- [x] 設定単体テスト
- [x] 既存mediaの同期・差分確認・切替・ロールバック手順
- [ ] AWSプレ環境でのアップロード確認

## ISSUE-053: ALB・ACM・ヘルスチェック

- [x] `/health/live`と`/health/ready`
- [x] ALBヘルスチェック条件
- [x] `SECURE_PROXY_SSL_HEADER` / `USE_X_FORWARDED_HOST`
- [x] プロキシ設定単体テスト
- [x] ALB + ACMの構成手順
- [ ] AWSプレ環境でのHost/HTTPS/CSRF検証

## ISSUE-054: CloudWatch

- [x] アプリログの標準出力化
- [x] ECS `awslogs`利用方針
- [x] 最低限の監視対象をAWS設定ガイドへ記載
- [x] 環境別Log GroupのTerraform定義
- [x] 5xx、CPU、Memory、タスク再起動、RDSのAlarm定義
- [x] 障害一次対応Runbook
- [ ] 実環境の通知先設定と通知試験

## ISSUE-055: RDS・ElastiCache

- [x] RDS必須接続値
- [x] MySQL/PostgreSQL TLS設定
- [x] ElastiCache TLS設定
- [x] 設定単体テスト
- [x] 既存DBのdump/restore手順
- [x] 切替当日の停止・移行・再開・検証手順
- [x] RPO/RTO目標と復旧確認手順
- [ ] 実環境での定期リストア試験

## リポジトリ内完了条件

- [x] `aws-pre` / `aws-prod` の変数例
- [x] remote state bootstrap
- [x] VPC、ALB/ACM、ECS、RDS、ElastiCache、S3/CloudFront、Secrets、CloudWatch、BudgetのTerraform定義
- [x] media移行、DB移行、障害一次対応Runbook
- [x] `terraform fmt` と `terraform validate`
- [x] ダミー値と `offline_plan=true` による認証不要の `terraform plan`
- [x] 移行スクリプトのdry-run対応
- [ ] AWS認証情報と実在リソースを使う `terraform plan`

## AWS実環境の完了条件

- [ ] AWSプレ環境で総合リリーステスト完了
- [ ] media移行とDB移行のリハーサル完了
- [ ] CloudWatch Alarmの通知試験完了
- [ ] 本番Go/No-Go記録と承認

## 関連文書

- `docs/AWS_ECS_SETUP_GUIDE.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/SECRETS_ROTATION_RUNBOOK.md`
- `docs/runbooks/AWS_MEDIA_MIGRATION.md`
- `docs/runbooks/AWS_DATABASE_MIGRATION.md`
- `docs/runbooks/AWS_INCIDENT_RESPONSE.md`
- `infrastructure/terraform/`
- `REQUIRED_SETTINGS.md`
