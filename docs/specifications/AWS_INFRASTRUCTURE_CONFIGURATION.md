# AWS Infrastructure Configuration

Last updated: 2026-06-20

## Purpose

This document records the AWS infrastructure that was confirmed from the local
environment and the intended low-cost target configuration for the development
AWS environment.

## Currently Confirmed AWS Environment

The following state was confirmed with the locally available AWS profile and DNS
checks.

| Item | Confirmed value |
| --- | --- |
| AWS profile | `tableno-pre` |
| AWS account | `083773015316` |
| Region | `ap-northeast-1` |
| ECS cluster | `tableno-aws-pre` |
| ECS services | `tableno-aws-pre`, `tableno-aws-pre-worker`, `tableno-aws-pre-beat` |
| ALB | `tableno-aws-pre` |
| ALB DNS name | `tableno-aws-pre-654848595.ap-northeast-1.elb.amazonaws.com` |
| Route53 hosted zone | `tableno.jp` |
| Active web alias | `stg.tableno.jp` -> `tableno-aws-pre` ALB |

`tableno.jp` and `www.tableno.jp` do not currently have Web A/AAAA records in
the confirmed hosted zone. `tableno.jp` did not resolve as a public Web endpoint
from the local environment during the check.

No `aws-prod` ECS cluster or production ALB was visible from the available
`tableno-pre` profile. If production resources exist under a different AWS
account or profile, they must be checked separately with that profile.

## Current Terraform Design

The Terraform design in `infrastructure/terraform/` defines a production-grade
AWS layout:

- ECS Fargate for application runtime.
- ALB + ACM for HTTPS ingress.
- Route53 records for application domains.
- RDS for the relational database.
- ElastiCache Redis for cache, sessions, Channels, and Celery broker/result
  backend.
- S3 + CloudFront for static and media assets.
- NAT Gateway for outbound traffic from private ECS tasks.
- Always-on ECS services for web, worker, and beat.
- CloudWatch Logs, metrics, alarms, SNS, Secrets Manager, and a monthly budget.

This design favors managed services and availability, but it creates several
always-on cost sources in a development environment.

## Target Low-Cost `aws-pre` Configuration: Pattern 1

The development AWS environment should be moved toward a minimum-cost ECS-based
configuration while keeping `https://stg.tableno.jp` continuously available:

- Keep ECS Fargate as the runtime platform.
- Keep ALB, ACM, Route53, RDS, S3, CloudFront, Secrets Manager, CloudWatch Logs,
  and Budget.
- Keep one always-on web task with `web_cpu=256` and `web_memory=512`.
- Do not create always-on worker and beat services.
- Do not create ElastiCache Redis for `aws-pre`.
- Do not create NAT Gateway for `aws-pre`.
- Place the web ECS service in public subnets with `assign_public_ip=true`.
- Keep ECS inbound restricted to the ALB security group on the application port.
- Keep RDS in private subnets.
- Run scheduled/background tasks manually or through an explicit temporary task
  when needed.
- Set RDS to `db.t4g.micro`, 20 GB allocated storage, 20 GB max storage,
  Single-AZ, one-day backup retention, and Performance Insights disabled.
- Set CloudWatch Logs retention to 3 days.
- Set the monthly budget to 50 USD.

The low-cost `aws-pre` configuration accepts the following limitations:

- WebSocket notifications are disabled or limited.
- Celery periodic tasks do not run continuously.
- Cache/session behavior must fall back to non-Redis production-safe settings.
- Availability is lower than the production-oriented Terraform design.

Manual periodic maintenance commands:

```bash
python manage.py publish_scheduled_handouts
python manage.py expire_async_jobs
python manage.py sync_japanese_holidays
```

## `aws-prod` Policy

`aws-prod` is not part of the planned low-cost change. The production
configuration should remain unchanged unless a production AWS profile is provided
and a separate production-specific plan is approved.

If a production profile exists, confirm production state before any stop or
change operation:

```bash
aws sts get-caller-identity --profile <prod-profile>
aws ecs list-clusters --profile <prod-profile> --region ap-northeast-1
aws elbv2 describe-load-balancers --profile <prod-profile> --region ap-northeast-1
aws route53 list-resource-record-sets --hosted-zone-id <prod-hosted-zone-id> --profile <prod-profile>
```
