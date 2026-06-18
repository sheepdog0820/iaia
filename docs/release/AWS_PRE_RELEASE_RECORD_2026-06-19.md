# AWS開発環境リリース記録

作成日: 2026-06-19
対象環境: `aws-pre`

## 基本情報

| 項目 | 値 |
| --- | --- |
| 対象環境 | `aws-pre` |
| AWS region | `ap-northeast-1` |
| ドメイン | `stg.tableno.jp` |
| リリースコミット | `e20a404` |
| ECR image | `083773015316.dkr.ecr.ap-northeast-1.amazonaws.com/tableno:aws-pre-e20a404` |
| リリース結果 | リリース済み |
| 判定 | Go |

## 事前確認

| 確認項目 | 結果 | メモ |
| --- | --- | --- |
| `git status --short --branch` | OK | `main...origin/main [ahead 40]` |
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
| AWS CLI | OK | `AWS_PROFILE=tableno-pre` で確認 |
| `aws sts get-caller-identity` | OK | Account `083773015316` |
| Docker daemon | OK | Docker Desktop起動後にserver情報を取得 |
| ECR repository | OK | `083773015316.dkr.ecr.ap-northeast-1.amazonaws.com/tableno` |
| ECR login | OK | `Login Succeeded` |
| ECR image push | OK | digest `sha256:d461645cde9d1c01cdeec97ecd9604215bfad8836c2375b3d0669430254f203f` |

## Terraform

| 確認項目 | 結果 | メモ |
| --- | --- | --- |
| `terraform fmt -check -recursive` | OK | 通過 |
| `terraform init` | OK | `AWS_PROFILE=tableno-pre` でS3 backend初期化成功 |
| 実AWS `terraform plan` | OK | `3 to add, 3 to change, 3 to destroy`。ECS task definition更新のみ |
| `terraform apply` | OK | web/worker/beatを新task definitionへ更新 |

## リリース後確認

| 確認項目 | 結果 | メモ |
| --- | --- | --- |
| ECS web stable | OK | desired `1` / running `1` / pending `0` |
| ECS worker stable | OK | desired `1` / running `1` / pending `0` |
| ECS beat stable | OK | desired `1` / running `1` / pending `0` |
| web task definition | OK | `tableno-aws-pre:10` |
| worker task definition | OK | `tableno-aws-pre-worker:9` |
| beat task definition | OK | `tableno-aws-pre-beat:9` |
| image反映 | OK | web/worker/beatすべて `aws-pre-e20a404` |
| `/health/live/` | OK | HTTP 200 |
| `/health/ready/` | OK | HTTP 200、database/cacheともにOK |
| `/` | OK | HTTP 302、`/accounts/login/?next=/` へ遷移 |
| CloudWatch logs | 要観察 | 起動、migration、collectstatic、worker/beat稼働はOK。外部または古いクライアント由来と見られる `/v2/ws/public` の未定義WebSocket接続エラーあり |

## 残課題

- `/v2/ws/public` はリポジトリ内の正規WebSocket URLではない。正規URLは `/ws/notifications/`。継続して発生する場合、ALB/外部監視/古いクライアント設定を確認する。
- Celery worker/beatログでRedis TLSの `ssl_cert_reqs=CERT_NONE` 警告が出ている。開発環境では許容し、本番前に証明書検証設定を確認する。

## 最終判断

`aws-pre` へのリリースは成功。ヘルスチェック、ECS安定化、ECR image反映は確認済み。
