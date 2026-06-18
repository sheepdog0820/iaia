# AWS開発環境リリース確認手順

対象環境: `aws-pre`

この手順は、AWS開発環境へリリースするたびに必ず実施します。確認結果は `docs/release/AWS_PRE_RELEASE_RECORD_TEMPLATE.md` を元に記録し、Secrets、実パスワード、Client Secret、個人情報は記録しません。

## リリース可否ルール

- すべての「必須」項目がOKになるまでリリースしない。
- 「条件付きOK」は、影響範囲、期限、担当者を記録した場合のみ許可する。
- DB migrationを含むリリースは、ロールバック可否を事前に判断する。
- `aws-pre`で未確認の変更を`aws-prod`へ進めない。

## 1. 事前確認

| 必須 | 確認項目 | コマンド/確認方法 | 期待結果 |
| --- | --- | --- | --- |
| 必須 | 作業ツリー | `git status --short --branch` | 対象ブランチが明確で未コミット差分がない |
| 必須 | リリース対象コミット | `git rev-parse --short HEAD` | リリース記録に記載 |
| 必須 | Python/Django基本チェック | `python manage.py check` | エラーなし |
| 必須 | 公開前ドキュメント検査 | `python manage.py test tests.unit.test_release_documentation --noinput --keepdb` | 成功 |
| 必須 | production設定検査 | `python manage.py test tests.unit.test_production_settings --noinput --keepdb` | 成功 |
| 必須 | 画像アップロード検査 | `python manage.py test scenarios.test_scenario_images schedules.test_session_images --noinput --keepdb` | 成功 |
| 推奨 | E2E | `node .\node_modules\playwright\cli.js test --project=chromium tests/e2e/flows/auth-flow.spec.ts tests/e2e/flows/session-management.spec.ts tests/e2e/flows/character-export.spec.ts tests/e2e/flows/mobile-responsive.spec.ts --reporter=line` | 成功 |
| 必須 | Terraform fmt | `terraform -chdir=infrastructure/terraform fmt -check -recursive` | 成功 |
| 必須 | Terraform validate | `terraform -chdir=infrastructure/terraform validate` | 成功 |
| 必須 | AWS認証先 | `aws sts get-caller-identity` | 想定AWSアカウント |

## 2. AWS設定確認

| 必須 | 確認項目 | コマンド/確認方法 | 期待結果 |
| --- | --- | --- | --- |
| 必須 | tfvars | `infrastructure/terraform/environments/aws-pre.tfvars` | 実値で存在し、exampleを直接使っていない |
| 必須 | domain | tfvarsの`domain_name` | AWS開発環境のドメイン |
| 必須 | hosted zone | tfvarsの`hosted_zone_id` | domainと一致するRoute 53 Hosted Zone |
| 必須 | container image | tfvarsまたは`-var container_image=...` | 今回pushしたECR image URI |
| 必須 | Secrets Manager | `aws secretsmanager get-secret-value --secret-id tableno-aws-pre/app --query SecretString --output text` | 必須キーが存在する。値は記録しない |
| 必須 | OAuth callback | Provider管理画面 | `https://<aws-pre-domain>/accounts/.../callback/` が登録済み |
| 必須 | CloudWatch Logs | AWS ConsoleまたはCLI | `/ecs/tableno-aws-pre` が存在する |
| 推奨 | Alarm通知 | SNS Subscription | 確認済みまたは開発環境では明示的に不要 |

必須Secretキー:

- `SECRET_KEY`
- `DB_PASSWORD`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `TWITTER_CLIENT_ID`
- `TWITTER_CLIENT_SECRET`
- `TWITTER_REDIRECT_URI`
- `DISCORD_CLIENT_ID`
- `DISCORD_CLIENT_SECRET`
- `DISCORD_REDIRECT_URI`

## 3. Terraform plan確認

| 必須 | 確認項目 | コマンド/確認方法 | 期待結果 |
| --- | --- | --- | --- |
| 必須 | plan作成 | `terraform -chdir=infrastructure/terraform plan -input=false -var-file=environments/aws-pre.tfvars -out=tfplan.aws-pre` | 成功 |
| 必須 | 変更内容 | plan出力 | `aws-prod`、本番ドメイン、本番Secretsを変更しない |
| 必須 | 破壊的変更 | plan出力 | RDS/S3/Secretsの削除・再作成がない。ある場合はNo-Go |
| 必須 | ECS更新 | plan出力 | web/worker/beatのtask definitionまたはservice更新が想定通り |
| 推奨 | 予算影響 | plan出力 | 開発環境の予算範囲内 |

## 4. リリース後スモークテスト

`AWS_PRE_BASE_URL=https://<aws-pre-domain>` を設定して実施します。

| 必須 | 確認項目 | コマンド/確認方法 | 期待結果 |
| --- | --- | --- | --- |
| 必須 | live health | `curl -f "$AWS_PRE_BASE_URL/health/live"` | 200 |
| 必須 | ready health | `curl -f "$AWS_PRE_BASE_URL/health/ready"` | 200 |
| 必須 | ALB target health | `aws elbv2 describe-target-health --target-group-arn <target-group-arn>` | healthy |
| 必須 | ECS services | `aws ecs describe-services --cluster tableno-aws-pre --services tableno-aws-pre tableno-aws-pre-worker tableno-aws-pre-beat` | desired/runningが一致 |
| 必須 | web logs | CloudWatch Logs | 起動エラー、migrationエラー、DB/Redis接続エラーなし |
| 必須 | 通常ログイン | ブラウザ | ログインできる |
| 必須 | セッション作成/編集 | ブラウザ | DBへ保存される |
| 必須 | キャラシ作成/編集 | ブラウザ | DBへ保存される |
| 必須 | 画像アップロード | ブラウザまたは負荷プローブ | S3/CloudFront経由で表示できる |
| 推奨 | OAuth | Google/Discord/X | callbackが成功する |
| 推奨 | 画像負荷プローブ | `python tests/performance/image_upload_load.py --base-url "$AWS_PRE_BASE_URL" --username "$TABLENO_USERNAME" --password "$TABLENO_PASSWORD" --concurrency 4 --requests-per-target 9` | 全probe成功 |

## 5. ロールバック判断

次のいずれかに該当する場合はロールバックします。

- `/health/ready` が5分以上失敗する。
- ECS taskが連続して再起動する。
- migration失敗またはDB接続失敗が出る。
- ログイン、セッション作成、キャラシ作成のいずれかが失敗する。
- 画像アップロードまたは表示が失敗し、S3/CloudFront設定起因と判断される。
- OAuth callbackが全Providerで失敗する。

ロールバック実施時は `docs/release/AWS_PRE_RELEASE_RUNBOOK.md` の「ロールバック手順」に従います。
