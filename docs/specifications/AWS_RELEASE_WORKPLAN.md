# AWSリリース作業計画

最終更新: 2026-06-12

## 目的

`ISSUES.md`のISSUE-050から055に沿って、ECS/Fargateを中心とするAWS本番構成を完成させます。

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
- [ ] 既存mediaの同期・切替手順
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
- [ ] 環境別Log Groupの作成
- [ ] 5xx、CPU、Memory、タスク再起動、RDSのAlarm作成
- [ ] 通知先と一次対応Runbook

## ISSUE-055: RDS・ElastiCache

- [x] RDS必須接続値
- [x] MySQL/PostgreSQL TLS設定
- [x] ElastiCache TLS設定
- [x] 設定単体テスト
- [ ] 既存DBのdump/restore手順
- [ ] 切替当日の停止・移行・再開・検証手順
- [ ] RPO/RTOと定期リストア確認

## 完了条件

- [ ] AWSプレ環境で総合リリーステスト完了
- [ ] media移行とDB移行のRunbook完成
- [ ] CloudWatch Alarmと通知先設定
- [ ] 本番Go/No-Go記録と承認

## 関連文書

- `docs/AWS_ECS_SETUP_GUIDE.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/SECRETS_ROTATION_RUNBOOK.md`
- `REQUIRED_SETTINGS.md`
