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

Private subnets and no public IP are used when the NAT gateway is enabled. In
the low-cost public-subnet configuration, Terraform enables the task public IP
so it can retrieve the container image and rembg model. The worker receives the
same application environment and secrets as the other application tasks, but
uses a dedicated task role limited to the media bucket. It exits after exactly
one job.

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
