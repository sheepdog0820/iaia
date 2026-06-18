# AWS Incident Response Runbook

## Alarm routing

CloudWatch alarms publish to the environment SNS topic. The on-call operator acknowledges the notification and records start time, environment and alarm state.

## First response

1. Check ALB target health and `/health/live`.
2. Check `/health/ready` to distinguish process health from DB/Redis failure.
3. Inspect ECS stopped-task reasons and `/ecs/tableno-<environment>` logs.
4. Review RDS connections/storage and ElastiCache health.
5. Roll back the latest task definition when the incident started after deployment.

## Alarm-specific actions

- ALB 5xx: inspect application exceptions, target health and DB saturation.
- ECS CPU/Memory: identify expensive endpoints/jobs, scale desired count, stop runaway jobs.
- RDS failure: fail over or restore according to `AWS_DATABASE_MIGRATION.md`.
- Media errors: verify IAM, bucket policy and CloudFront origin; use `AWS_MEDIA_MIGRATION.md` rollback.

## Closure

Confirm both health endpoints, error-rate recovery and successful login/session CRUD. Record timeline, cause, corrective action and follow-up issue.

## Verification records

Use this section to record operational checks without storing secrets or credentials.

| Check | Procedure | Latest result |
| --- | --- | --- |
| Backup | Confirm the latest automated RDS snapshot and retention period. | Not recorded |
| Restore | Restore a snapshot to a non-production DB and run `/health/ready`. | Not recorded |
| Alarm notification | Trigger or simulate a CloudWatch Alarm notification to the operational SNS subscriber. | Not recorded |
| Rollback | Deploy a previous ECS task definition in pre-production and verify login/session CRUD. | Not recorded |
