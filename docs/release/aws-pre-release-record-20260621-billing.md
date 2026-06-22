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

## Readiness matrix

See `docs/release/BILLING_READINESS_MATRIX_2026-06-22.md` for requirement-by-requirement billing readiness, evidence, and remaining external verification.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Stripe Checkout monthly/yearly subscriptions | Implemented | Uses `STRIPE_PREMIUM_PRICE_ID` and `STRIPE_PREMIUM_YEARLY_PRICE_ID`. |
| Stripe Checkout exposure switch | Implemented | `STRIPE_CHECKOUT_ENABLED` must be explicitly enabled before paid Checkout buttons/API are exposed in aws-pre/aws-prod; `billing_status_report` and verification records include the current exposure state. |
| Local development billing configuration | Implemented | `.env.development` is ignored, `.env.development.example` documents test-mode Stripe placeholders, `billing_development_check` validates local test-mode safety, and `setup_billing_local --include-admin` creates local billing users/codes for verification. |
| Stripe Customer Portal | Implemented | Cancellation, payment method updates, invoice history are delegated to Stripe. |
| Stripe Webhook premium sync | Implemented | Checkout, subscription lifecycle, payment failure/recovery, refund, dispute events are handled. |
| Premium access code | Implemented | Operator-issued no-charge premium grants are available. |
| Premium access expiration | Implemented | Time-limited code grants expire through `expire_premium_access` / `schedules.tasks.expire_premium_access`; manual overrides are preserved. |
| Manual premium grant | Preserved | Admin/manual grants remain valid without Stripe subscription. |
| Admin/audit visibility | Implemented | Premium subscription and audit evidence are available in admin/report commands. |
| Billing admin/operator labels | Implemented | Admin actions and `issue_premium_code --help` show readable Japanese labels. |
| Legal pages and billing runbook | Implemented | Commercial disclosure, premium features, and Stripe operations runbook are present. |
| External Stripe test verification | Not completed | Tracked by `ISSUE-077`; the read-only MCP check is recorded in `docs/runbooks/billing-verification-mcp-20260622.md` but is not acceptance evidence. |

## Local verification completed

| Check | Result | Notes |
| --- | --- | --- |
| `python manage.py test accounts.test_billing tests.unit.test_release_documentation tests.unit.test_production_settings tests.unit.test_local_settings tests.unit.test_billing_legal_pages tests.unit.test_public_legal_pages --keepdb --noinput -v 1` | OK | 231 tests passed. |
| `python manage.py check` | OK | No issues. |
| `python manage.py makemigrations --check --dry-run` | OK | No model changes detected. |
| `python manage.py migrate --noinput` | OK | Local DB migrated through billing plan fields. |
| `python manage.py setup_billing_local --include-admin` | OK | Local users and premium code created; `.env.development` is prepared for the development 480 JPY monthly / 4,800 JPY yearly plan with Stripe key and Price ID placeholders left blank. |
| `python manage.py billing_preflight` | Warnings | Stripe keys, webhook secret, legal seller details, public URL, and production mail backend are not configured locally. |
| `python manage.py billing_verification_record --environment local --stripe-mode test --run-smoke --output docs/runbooks/billing-verification-local-20260622.md` | OK | Local-only evidence generated; this does not satisfy ISSUE-077 because no real Stripe test-mode event IDs are recorded. |

## Release conditions for aws-pre

- Configure aws-pre Secrets Manager with Stripe test-mode keys and Price IDs, and keep `STRIPE_CHECKOUT_ENABLED=False` until verification is complete.
- Use test mode monthly JPY 480 and yearly JPY 4,800 recurring Prices.
- Configure a Stripe test mode Webhook endpoint for the aws-pre `/api/billing/webhook/` URL.
- Run `billing_preflight --strict` and `billing_stripe_remote_check` in aws-pre.
- Complete `ISSUE-077` before treating paid premium access as verified.

## ISSUE-077 Stripe external verification scope

Keep this ticket open until all of the following are proven in Stripe test mode and recorded with real Stripe event IDs. Do not use live-mode Stripe objects for this verification.

- Stripe Dashboard or connector confirms `livemode: false` before Product/Price creation. The 2026-06-22 MCP check did not expose this proof.
- Test Product `Tableno Premium` exists with recurring Prices: JPY 480 monthly and JPY 4,800 yearly.
- aws-pre uses only `sk_test_...`, `pk_test_...`, test `price_...`, and the aws-pre Webhook `whsec_...`.
- `billing_preflight --strict` passes in aws-pre.
- `billing_stripe_remote_check --require-recent-events --recent-hours 72` passes in aws-pre.
- The verification record captures real IDs for `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated` with `cancel_at_period_end=true`, `customer.subscription.deleted`, `invoice.payment_failed`, `invoice.payment_succeeded`, `charge.refunded`, `charge.dispute.created`, and `charge.dispute.closed`.
- Django admin and `billing_status_report --json` confirm the matching `StripeWebhookEvent`, `PremiumSubscription`, and `Premium audit logs` state.

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
python manage.py billing_status_report --json  # confirm stripe_checkout_enabled before exposing Checkout
```
