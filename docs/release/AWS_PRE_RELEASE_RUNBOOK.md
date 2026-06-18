# AWS開発環境リリース手順

対象環境: `aws-pre`

この手順は、AWS開発環境へアプリケーションをリリースするための標準手順です。確認項目は `docs/release/AWS_PRE_RELEASE_CHECKLIST.md` を使用します。

## 前提

- AWS CLIで対象AWSアカウントへ認証済み。
- Dockerが利用可能。
- Terraform backendはAWS開発環境用に設定済み。
- `infrastructure/terraform/environments/aws-pre.tfvars` が実値で作成済み。
- ECR repositoryが作成済み。
- 実SecretsはAWS Secrets Managerで管理し、リポジトリやリリース記録へ書かない。
- リリース記録を作成済み。

## 変数

PowerShell例:

```powershell
$env:AWS_REGION = "ap-northeast-1"
$env:AWS_PROFILE = "<aws-profile>"
$env:AWS_ACCOUNT_ID = "<account-id>"
$env:AWS_PRE_DOMAIN = "stg.tableno.jp"
$env:ECR_REPOSITORY = "tableno"
$env:RELEASE_SHA = (git rev-parse --short HEAD)
$env:IMAGE_URI = "$env:AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com/$env:ECR_REPOSITORY:aws-pre-$env:RELEASE_SHA"
```

Bash例:

```bash
export AWS_REGION=ap-northeast-1
export AWS_PROFILE=<aws-profile>
export AWS_ACCOUNT_ID=<account-id>
export AWS_PRE_DOMAIN=stg.tableno.jp
export ECR_REPOSITORY=tableno
export RELEASE_SHA="$(git rev-parse --short HEAD)"
export IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:aws-pre-${RELEASE_SHA}"
```

Terraform上のリソース名は `project_name=tableno`、`environment=aws-pre` の場合、次を想定します。

- ECS cluster: `tableno-aws-pre`
- ECS service: `tableno-aws-pre`
- ECS worker service: `tableno-aws-pre-worker`
- ECS beat service: `tableno-aws-pre-beat`
- CloudWatch log group: `/ecs/tableno-aws-pre`
- Secrets Manager secret: `tableno-aws-pre/app`

## 1. リリース前チェック

`docs/release/AWS_PRE_RELEASE_CHECKLIST.md` の「1. 事前確認」と「2. AWS設定確認」をすべて実施します。

最低限のコマンド:

```powershell
git status --short --branch
git rev-parse --short HEAD
python manage.py check
python manage.py test tests.unit.test_release_documentation tests.unit.test_production_settings --noinput --keepdb
python manage.py test scenarios.test_scenario_images schedules.test_session_images --noinput --keepdb
terraform -chdir=infrastructure/terraform fmt -check -recursive
terraform -chdir=infrastructure/terraform validate
aws sts get-caller-identity
```

## 2. コンテナイメージ作成

ECRログイン:

```powershell
aws ecr get-login-password --region $env:AWS_REGION |
  docker login --username AWS --password-stdin "$env:AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com"
```

イメージ作成:

```powershell
docker build -t $env:IMAGE_URI .
```

必要に応じてローカルでコンテナ起動確認:

```powershell
docker run --rm $env:IMAGE_URI python manage.py check
```

ECRへpush:

```powershell
docker push $env:IMAGE_URI
```

push確認:

```powershell
aws ecr describe-images `
  --repository-name $env:ECR_REPOSITORY `
  --image-ids imageTag="aws-pre-$env:RELEASE_SHA" `
  --region $env:AWS_REGION
```

## 3. Terraform plan

`container_image` はtfvarsを書き換えるか、apply時に `-var` で渡します。リリースごとの値を明確に残すため、ここでは `-var` を推奨します。

```powershell
terraform -chdir=infrastructure/terraform init

terraform -chdir=infrastructure/terraform plan `
  -input=false `
  -var-file=environments/aws-pre.tfvars `
  -var "container_image=$env:IMAGE_URI" `
  -out=tfplan.aws-pre
```

plan確認:

- `aws-prod` リソースが含まれない。
- RDS、S3、Secretsの削除や再作成がない。
- ECS task definition/service更新が想定通り。
- `container_image` が今回の `$env:IMAGE_URI` になっている。

## 4. Terraform apply

```powershell
terraform -chdir=infrastructure/terraform apply tfplan.aws-pre
```

apply後、outputを控えます。

```powershell
terraform -chdir=infrastructure/terraform output
```

## 5. ECSデプロイ監視

```powershell
aws ecs describe-services `
  --cluster tableno-aws-pre `
  --services tableno-aws-pre tableno-aws-pre-worker tableno-aws-pre-beat `
  --region $env:AWS_REGION
```

web serviceの安定化待ち:

```powershell
aws ecs wait services-stable `
  --cluster tableno-aws-pre `
  --services tableno-aws-pre `
  --region $env:AWS_REGION
```

worker/beatも確認:

```powershell
aws ecs wait services-stable `
  --cluster tableno-aws-pre `
  --services tableno-aws-pre-worker tableno-aws-pre-beat `
  --region $env:AWS_REGION
```

失敗時はイベントと停止理由を確認します。

```powershell
aws ecs describe-services `
  --cluster tableno-aws-pre `
  --services tableno-aws-pre `
  --query "services[0].events[0:10]" `
  --region $env:AWS_REGION
```

```powershell
aws ecs list-tasks `
  --cluster tableno-aws-pre `
  --desired-status STOPPED `
  --region $env:AWS_REGION
```

## 6. リリース後確認

```powershell
$env:AWS_PRE_BASE_URL = "https://$env:AWS_PRE_DOMAIN"
curl.exe -f "$env:AWS_PRE_BASE_URL/health/live"
curl.exe -f "$env:AWS_PRE_BASE_URL/health/ready"
```

CloudWatch Logs:

```powershell
aws logs tail /ecs/tableno-aws-pre `
  --since 30m `
  --region $env:AWS_REGION
```

`docs/release/AWS_PRE_RELEASE_CHECKLIST.md` の「4. リリース後スモークテスト」を実施します。

画像アップロード負荷プローブ:

```powershell
python tests/performance/image_upload_load.py `
  --base-url "$env:AWS_PRE_BASE_URL" `
  --username "$env:TABLENO_USERNAME" `
  --password "$env:TABLENO_PASSWORD" `
  --concurrency 4 `
  --requests-per-target 9
```

## 7. ロールバック手順

### 7.1 直前イメージへ戻す

直前の動作確認済みimage URIを確認します。

```powershell
aws ecs describe-task-definition `
  --task-definition tableno-aws-pre `
  --query "taskDefinition.containerDefinitions[?name=='web'].image" `
  --region $env:AWS_REGION
```

直前image URIを `ROLLBACK_IMAGE_URI` として設定します。

```powershell
$env:ROLLBACK_IMAGE_URI = "<previous-good-image-uri>"

terraform -chdir=infrastructure/terraform plan `
  -input=false `
  -var-file=environments/aws-pre.tfvars `
  -var "container_image=$env:ROLLBACK_IMAGE_URI" `
  -out=tfplan.aws-pre-rollback

terraform -chdir=infrastructure/terraform apply tfplan.aws-pre-rollback
```

ECS安定化待ちとスモークテストを再実施します。

### 7.2 migration起因の失敗

`docker/entrypoint.sh` は起動時に `python manage.py migrate --noinput` を実行します。migration失敗または後方互換性がないmigrationの場合、単純なimageロールバックだけでは復旧できない場合があります。

対応順:

1. `/health/ready` とCloudWatch Logsで失敗箇所を確認する。
2. DB変更の影響範囲を確認する。
3. 開発環境であれば、必要に応じてRDSスナップショットから復旧する。
4. 復旧後に旧imageへ戻す。
5. `docs/backup.md` と `docs/runbooks/AWS_DATABASE_MIGRATION.md` に沿って復旧結果を記録する。

### 7.3 緊急停止

開発環境で影響を止める必要がある場合のみ、desired countを一時的に0へ下げます。

```powershell
aws ecs update-service --cluster tableno-aws-pre --service tableno-aws-pre --desired-count 0 --region $env:AWS_REGION
aws ecs update-service --cluster tableno-aws-pre --service tableno-aws-pre-worker --desired-count 0 --region $env:AWS_REGION
aws ecs update-service --cluster tableno-aws-pre --service tableno-aws-pre-beat --desired-count 0 --region $env:AWS_REGION
```

復旧時はtfvarsのdesired countに戻し、Terraform applyで状態を揃えます。

## 8. 完了条件

- ECS web/worker/beatがstable。
- `/health/live` と `/health/ready` が200。
- CloudWatch Logsに起動エラー、migrationエラー、DB/Redis接続エラーがない。
- ログイン、セッション作成、キャラシ作成、画像アップロードが成功。
- リリース記録に、commit、image URI、plan/apply結果、確認結果、残課題が記録済み。
