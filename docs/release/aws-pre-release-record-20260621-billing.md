# AWS development release record - billing feature readiness

Do not write Secrets, real passwords, client secrets, or personal information in this file.

## Basic information

| Item | Value |
| --- | --- |
| Target environment | aws-pre |
| Date | 2026-06-21 |
| Branch | main |
| Commit | c7fad42 |
| Release decision | Conditional Go for aws-pre only if Stripe paid billing exposure remains test-mode controlled |

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Stripe Checkout monthly/yearly subscriptions | Implemented | Uses `STRIPE_PREMIUM_PRICE_ID` and `STRIPE_PREMIUM_YEARLY_PRICE_ID`. |
| Stripe Customer Portal | Implemented | Cancellation, payment method updates, invoice history are delegated to Stripe. |
| Stripe Webhook premium sync | Implemented | Checkout, subscription lifecycle, payment failure/recovery, refund, dispute events are handled. |
| Premium access code | Implemented | Operator-issued no-charge premium grants are available. |
| Manual premium grant | Preserved | Admin/manual grants remain valid without Stripe subscription. |
| Admin/audit visibility | Implemented | Premium subscription and audit evidence are available in admin/report commands. |
| Legal pages and billing runbook | Implemented | Commercial disclosure, premium features, and Stripe operations runbook are present. |
| External Stripe test verification | Not completed | Tracked by `ISSUE-077`. |

## Local verification completed

| Check | Result | Notes |
| --- | --- | --- |
| `python manage.py test accounts.test_billing tests.unit.test_release_documentation tests.unit.test_billing_legal_pages tests.unit.test_public_legal_pages tests.unit.test_production_settings --keepdb --noinput -v 1` | OK | 180 tests passed. |
| `python manage.py check` | OK | No issues. |
| `python manage.py makemigrations --check --dry-run` | OK | No model changes detected. |
| `python manage.py migrate --noinput` | OK | Local DB migrated through billing plan fields. |
| `python manage.py setup_billing_local --include-admin` | OK | Local users and premium code created. |
| `python manage.py billing_preflight` | Warnings | Stripe keys, webhook secret, legal seller details, public URL, and production mail backend are not configured locally. |

## Release conditions for aws-pre

- Configure aws-pre Secrets Manager with Stripe test-mode keys and Price IDs before exposing Checkout buttons.
- Use test mode monthly JPY 480 and yearly JPY 4,800 recurring Prices.
- Configure a Stripe test mode Webhook endpoint for the aws-pre `/api/billing/webhook/` URL.
- Run `billing_preflight --strict` and `billing_stripe_remote_check` in aws-pre.
- Complete `ISSUE-077` before treating paid premium access as verified.

## Residual tickets

| Ticket | Impact | Release handling |
| --- | --- | --- |
| ISSUE-077 | Stripe paid billing is implemented but not externally verified in aws-pre. | Keep open; conditional Go only if paid billing is test-mode controlled or hidden until verification. |
| ISSUE-070 | Final AWS environment apply approval. | Existing P0 Go/No-Go item. |
| ISSUE-073 | aws-pre environment settings and smoke test. | Existing P0 post-deploy validation. |
| ISSUE-074 | Operations, monitoring, and legal final values. | Existing P0 before public production release. |

## Next commands in aws-pre

```bash
python manage.py check
python manage.py billing_preflight --strict
python manage.py billing_stripe_remote_check --require-recent-events --recent-hours 72
python manage.py billing_status_report --json
```
