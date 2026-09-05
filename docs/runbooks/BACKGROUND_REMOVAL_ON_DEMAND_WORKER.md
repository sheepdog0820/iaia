# On-demand background removal worker

The web task must never run `rembg`. It persists a `BackgroundRemovalJob` and launches one Fargate task with:

```text
python manage.py process_background_removal_job <job UUID>
```

## Terraform configuration

`infrastructure/terraform` creates the dedicated task definition, task role, S3
policy, and least-privilege launcher policy. The task defaults to `1 vCPU` and
`2 GB` memory and has no ECS service or desired count, so it is billed only
while a submitted job is running.

Terraform injects these values into the web task automatically:

- `BACKGROUND_REMOVAL_ECS_CLUSTER`
- `BACKGROUND_REMOVAL_TASK_DEFINITION`
- `BACKGROUND_REMOVAL_CONTAINER_NAME`
- `BACKGROUND_REMOVAL_SUBNETS`
- `BACKGROUND_REMOVAL_SECURITY_GROUPS`
- `BACKGROUND_REMOVAL_ASSIGN_PUBLIC_IP`
- `BACKGROUND_REMOVAL_JOB_TIMEOUT_SECONDS`
- `BACKGROUND_REMOVAL_DAILY_LIMIT`（既定: 1ユーザー1日10回、JST午前0時リセット）
- `BACKGROUND_REMOVAL_RESULT_RETENTION_HOURS`（既定: 24時間）
- `BACKGROUND_REMOVAL_JOB_RETENTION_DAYS`（既定: 7日）

完了画像と完了・失敗ジョブはCelery beatの`cleanup-background-removal-jobs`で1時間ごとに整理されます。この処理は、設定時間を超えたpending/runningジョブを先にfailedへ移してソース画像を削除します。手動確認では次の管理コマンドを使用します。

```bash
python manage.py cleanup_background_removal_jobs --dry-run
python manage.py cleanup_background_removal_jobs
```

Private subnets and no public IP are used when the NAT gateway is enabled. In
the low-cost public-subnet configuration, Terraform enables the task public IP
so it can retrieve the container image and rembg model. The worker receives the
same application environment and secrets as the other application tasks, but
uses a dedicated task role limited to the media bucket. It exits after exactly
one job.

## 推論モデル（2026-09-06更新）

`accounts/background_removal.py` は `u2net` と `CPUExecutionProvider` を明示する。
rembgの既定モデルに依存しない。固定依存rembg 2.0.81の既定はBRIA RMBG-2.0であり、
[提供元のモデルカード](https://huggingface.co/briaai/RMBG-2.0)は商用利用に別契約が必要と説明している。
このタスクでは契約・購入をしていない。

U²-Netの[公式リポジトリ](https://github.com/xuebinqin/U-2-Net)と
[Apache-2.0ライセンス](https://github.com/xuebinqin/U-2-Net/blob/master/LICENSE)を参照する。
モデルは起動時にrembgの取得処理でダウンロードするため、実環境での取得経路・初回時間・
代表的な立ち絵での品質検証を公開前に行う。実行に失敗しても別の既定モデルに切り替えない。

## Verification

```powershell
terraform -chdir=infrastructure/terraform fmt -check
terraform -chdir=infrastructure/terraform validate
terraform -chdir=infrastructure/terraform plan -var-file=environments/aws-pre.tfvars
```

After applying, confirm that a premium-user request returns `202`, one
`background-removal` task starts, the status endpoint transitions from
`pending`/`running` to a PNG response, and no ECS service was created for this
worker.

Jobs left in `pending` or `running` for 15 minutes are marked failed on the
next status check or submission. This prevents a stopped Fargate task from
blocking that user permanently.
