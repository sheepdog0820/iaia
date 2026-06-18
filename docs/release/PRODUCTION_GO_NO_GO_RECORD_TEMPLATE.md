# 本番 Go/No-Go 記録テンプレート

最終更新: 2026-06-18

このテンプレートは実AWS環境への apply 判断を残すための記録用です。Secrets、実Client Secret、実パスワードは記載しません。

## 判定

| 項目 | 記録 |
| --- | --- |
| 対象環境 | aws-prod |
| 判定日時 | 運営者が確定する項目 |
| 判定 | Go / No-Go / 条件付きGo |
| 判定者 | 運営者が確定する項目 |
| apply担当者 | 運営者が確定する項目 |
| 実施時間帯 | 運営者が確定する項目 |
| メンテナンス告知 | 実施 / 不要 / 未定 |

## aws-pre / aws-prod 差分意図

| 項目 | aws-pre | aws-prod | 承認 |
| --- | --- | --- | --- |
| domain | stg.tableno.jp | tableno.jp / www.tableno.jp | 未確認 |
| desired_count | 検証用 | 本番冗長化 | 未確認 |
| secure_ssl_redirect | 有効化予定 | true | 未確認 |
| deletion_protection | 検証方針 | true | 未確認 |
| monthly_budget_usd | 検証予算 | 本番予算 | 未確認 |
| backup_retention | 検証保持 | 本番保持 | 未確認 |

## 実値承認チェック

| 項目 | 確認内容 | 状態 |
| --- | --- | --- |
| DNS | Route 53 hosted zone と `tableno.jp` / `www.tableno.jp` の向き先 | 未確認 |
| ACM | `tableno.jp` / `www.tableno.jp` の証明書とALB関連付け | 未確認 |
| Secrets | SECRET_KEY、DB、Redis、Google、Discord、XのSecret登録 | 未確認 |
| 予算 | AWS Budget金額と通知先 | 未確認 |
| バックアップ | RDS保持期間、復旧試験日、RPO/RTO | 未確認 |
| 監視通知 | CloudWatch Alarm通知先、SNS購読確認 | 未確認 |

## Terraform確認

| コマンド | 結果 | 記録者 |
| --- | --- | --- |
| `terraform -chdir=infrastructure/terraform fmt -check -recursive` | 未実施 |  |
| `terraform -chdir=infrastructure/terraform validate` | 未実施 |  |
| `terraform -chdir=infrastructure/terraform plan -input=false -lock=false -var-file=environments/aws-prod.tfvars` | 未実施 |  |
| 実AWS状態参照の `terraform plan` | 実資格情報が必要なため別工程 |  |

## ロールバック判断

| 項目 | 基準 |
| --- | --- |
| ALB health | `/health/ready` が継続失敗 |
| ECS | 新taskの起動失敗または再起動ループ |
| DB/Redis | 接続失敗またはmigration失敗 |
| OAuth | 本番callbackが復旧不能 |
| 判断者 | 運営者が確定する項目 |

## Go/No-Go結論

- 結論: 未記録
- 条件:
- 次アクション:
