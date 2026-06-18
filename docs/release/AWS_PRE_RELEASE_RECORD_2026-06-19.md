# AWS開発環境リリース記録

作成日: 2026-06-19
対象環境: `aws-pre`

## 基本情報

| 項目 | 値 |
| --- | --- |
| 対象環境 | `aws-pre` |
| AWS region | `ap-northeast-1` |
| ドメイン | `stg.tableno.jp` |
| リリース結果 | 未リリース |
| 判定 | No-Go |

## 事前確認

| 確認項目 | 結果 | メモ |
| --- | --- | --- |
| `git status --short --branch` | 確認済み | `main...origin/main [ahead 39]`。リリース手順書とテスト修正の差分あり |
| `python manage.py check` | OK | `System check identified no issues` |
| `python manage.py check --deploy` | OK | `APP_ENV=aws-pre` とダミー必須環境変数で確認 |
| リリース関連ユニットテスト | OK | `tests.unit.test_release_documentation`、`tests.unit.test_production_settings` |
| 画像アップロード系テスト | OK | `scenarios.test_scenario_images`、`schedules.test_session_images` |
| E2Eリリース主要フロー | OK | Playwright chromium 9件成功 |
| Unitテスト | OK | `tests.unit` 42件成功 |
| Integrationテスト | OK | `tests.integration` 56件成功、2件skip |
| Systemテスト | OK | `tests.system` 17件成功、1件skip |
| 全体テスト | 未完了 | 15分でタイムアウトしたためカテゴリ別に分割して確認 |

## AWS設定確認

| 確認項目 | 結果 | メモ |
| --- | --- | --- |
| `aws-pre.tfvars` 実値 | OK | `infrastructure/terraform/environments/aws-pre.tfvars` が存在 |
| AWS CLI | NG | `Unable to locate credentials` |
| `aws sts get-caller-identity` | NG | 認証情報未設定 |
| Docker daemon | NG | Docker Desktop/daemon未起動 |
| ECR image push | 未実施 | Docker daemonとAWS認証が必要 |
| Secrets Manager確認 | 未実施 | AWS認証が必要 |

## Terraform

| 確認項目 | 結果 | メモ |
| --- | --- | --- |
| `terraform fmt -check -recursive` | OK | 通過 |
| `terraform init` | NG | S3 backend認証情報なし |
| `terraform validate` | OK | backendを除いた一時コピーで通過 |
| offline `terraform plan` | OK | backendを除いた一時コピーで `56 to add, 0 to change, 0 to destroy` |
| 実AWS `terraform plan` | 未実施 | AWS認証が必要 |
| `terraform apply` | 未実施 | AWS認証、Docker/ECR image pushが必要 |

## リリース後確認

未実施。AWSへの実リリースが未完了のため、ECS安定化、`/health/live`、`/health/ready`、ログ確認、画像アップロード確認は実施していない。

## No-Go理由

- AWS CLIに認証情報が設定されていない。
- Terraform S3 backendを初期化できない。
- Docker daemonが起動しておらず、ECRへリリースイメージをpushできない。

## 次回再開条件

1. AWS認証情報を設定し、`aws sts get-caller-identity` が成功すること。
2. Docker daemonを起動し、`docker version` がserver情報まで取得できること。
3. `docs/release/AWS_PRE_RELEASE_RUNBOOK.md` のECR pushから再開すること。
