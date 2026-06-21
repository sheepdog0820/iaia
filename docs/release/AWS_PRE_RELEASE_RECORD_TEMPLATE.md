# AWS開発環境リリース記録

Secrets、実パスワード、Client Secret、個人情報は記載しない。

## 基本情報

| 項目 | 値 |
| --- | --- |
| 対象環境 | aws-pre |
| 実施日 |  |
| 実施者 |  |
| 対象ブランチ |  |
| commit |  |
| image URI |  |
| AWS account alias/id |  |
| base URL |  |
| リリース判断 | Go / No-Go / 条件付きGo |

## 事前確認

| 確認項目 | 結果 | メモ |
| --- | --- | --- |
| `git status --short --branch` | 未実施 |  |
| `python manage.py check` | 未実施 |  |
| release documentation tests | 未実施 |  |
| production settings tests | 未実施 |  |
| billing preflight | 未実施 | `python manage.py billing_preflight --strict` |
| Stripe billing verification record | 未確認 | `docs/runbooks/STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md` を使用 |
| image upload tests | 未実施 |  |
| Playwright E2E | 未実施 |  |
| `terraform fmt -check -recursive` | 未実施 |  |
| `terraform validate` | 未実施 |  |
| `aws sts get-caller-identity` | 未実施 |  |

## AWS設定確認

| 確認項目 | 結果 | メモ |
| --- | --- | --- |
| `aws-pre.tfvars` 実値 | 未確認 |  |
| domain/hosted zone | 未確認 |  |
| ECR image push | 未確認 |  |
| Secrets必須キー | 未確認 | 値は記載しない |
| OAuth callback | 未確認 |  |
| CloudWatch Logs | 未確認 |  |
| Alarm/SNS | 未確認 |  |

## Terraform

| 確認項目 | 結果 | メモ |
| --- | --- | --- |
| plan作成 | 未実施 |  |
| plan内の対象環境 | 未確認 |  |
| 破壊的変更なし | 未確認 |  |
| apply | 未実施 |  |
| terraform output | 未確認 |  |

## リリース後確認

| 確認項目 | 期待結果 | 結果 | メモ |
| --- | --- | --- | --- |
| `/health/live` | 200 | 未確認 |  |
| `/health/ready` | 200 | 未確認 |  |
| ECS web stable | desired/running一致 | 未確認 |  |
| ECS worker stable | desired/running一致 | 未確認 |  |
| ECS beat stable | desired/running一致 | 未確認 |  |
| CloudWatch Logs | エラーなし | 未確認 |  |
| 通常ログイン | 成功 | 未確認 |  |
| セッション作成/編集 | 成功 | 未確認 |  |
| キャラシ作成/編集 | 成功 | 未確認 |  |
| 画像アップロード | 成功 | 未確認 |  |
| OAuth Google | 成功または対象外 | 未確認 |  |
| OAuth Discord | 成功または対象外 | 未確認 |  |
| OAuth X | 成功または対象外 | 未確認 |  |
| 画像負荷プローブ | 成功 | 未確認 |  |

## ロールバック情報

| 項目 | 値 |
| --- | --- |
| 直前の正常image URI |  |
| rollback plan作成可否 | 未確認 |
| DB migration有無 |  |
| RDS snapshot名 |  |
| ロールバック判断 | 不要 / 実施 / 保留 |

## 残課題

| 課題 | 影響 | 担当 | 期限 |
| --- | --- | --- | --- |
|  |  |  |  |

## 最終判断

- 判断: Go / No-Go / 条件付きGo
- 理由:
- 次の対応:
