# Billing readiness matrix - 2026-06-22

This matrix maps the premium billing release goal to current evidence. Do not write Secrets, real card data, customer personal information, or Webhook signing secrets in this file.

## Decision

| Item | Status | Release handling |
| --- | --- | --- |
| Local implementation readiness | Ready for aws-pre deployment with Checkout hidden or test-mode controlled | Local tests and smoke checks pass. |
| Paid Checkout exposure | External verification required | Keep `STRIPE_CHECKOUT_ENABLED=False` in aws-pre/aws-prod until ISSUE-077 is complete; `billing_release_gate` blocks enabled Checkout without final evidence. |
| Public production launch | Not ready | Requires real legal seller values, live Stripe setup, and production Go/No-Go evidence. |

## Requirement Matrix

| Requirement | Current status | Evidence | Remaining release action |
| --- | --- | --- | --- |
| Commercial disclosure and pricing pages include price, cancellation, refund, service delivery timing, and seller information | Implemented locally | `tableno/legal_views.py`, `templates/legal/commercial_disclosure.html`, `templates/premium/features.html`, `tests.unit.test_billing_legal_pages`, `billing_preflight --strict` | Set production `LEGAL_SELLER_NAME`, `LEGAL_SELLER_ADDRESS`, `LEGAL_SELLER_PHONE`, `CONTACT_EMAIL`, and final legal copy before public production. |
| Monthly and yearly premium pricing | Implemented locally | `.env.development.example`, `.env.development`, `STRIPE_PREMIUM_PRICE_ID`, `STRIPE_PREMIUM_YEARLY_PRICE_ID`, expected JPY 480 / JPY 4,800 checks | Create or confirm Stripe test-mode Product/Prices and copy real test Price IDs into aws-pre Secrets. |
| Local development billing configuration | Implemented locally | `.env.development.example`, ignored `.env.development`, `billing_development_check`, `setup_billing_local --include-admin`, `tests.unit.test_local_settings` | Keep real Stripe test keys and Price IDs out of git; fill `.env.development` only after test-mode Stripe objects are confirmed. |
| Stripe Checkout subscription flow | Implemented | `accounts/billing.py`, `accounts/views/billing_views.py`, `accounts.test_billing` | Complete real test Checkout for both monthly and yearly plans in aws-pre. |
| Customer Portal for cancellation, payment method update, and invoice history | Implemented | `portal-session` API, `billing_stripe_remote_check` Customer Portal checks, runbook | Confirm test-mode Customer Portal configuration in Stripe and aws-pre. |
| Stripe Webhook signature verification and idempotency | Implemented locally | `StripeWebhookView`, `StripeWebhookEvent`, `accounts.test_billing`, `billing_webhook_smoke` | Record real Stripe test-mode event IDs and local DB evidence in `docs/runbooks/billing-verification-YYYYMMDD.md`. |
| `checkout.session.completed` subscription linkage | Implemented locally | Webhook tests and local smoke record | Confirm with real test Checkout event ID in aws-pre. |
| `customer.subscription.created/updated/deleted` premium sync | Implemented locally | Webhook tests, `billing_webhook_smoke`, `PremiumSubscription.sync_user_premium_access` | Confirm active/trialing, cancel-at-period-end, deleted/canceled, and unpaid behavior with real Stripe test events. |
| Payment failure and recovery handling | Implemented locally | `invoice.payment_failed`, `invoice.payment_succeeded`, billing page warning, console email evidence in local verification record | Confirm mail delivery backend in aws-pre and real test failure/recovery events. |
| Code-granted premium expiration policy | Implemented | Time-limited code grants copy `expires_at` into `PremiumSubscription.premium_expires_at`; no-expiry codes remain active until explicit revoke | Maintain daily `expire_premium_access` job or manual run while beat is disabled. |
| Automatic expiration batch for time-limited code grants | Implemented | `expire_premium_access`, `schedules.tasks.expire_premium_access`, docs, tests | Confirm scheduler/manual job in aws-pre operations. |
| Admin visibility for Stripe IDs, code redemption history, and current access reason | Implemented | `accounts/admin.py`, admin tests, runbook audit section | Perform visual admin confirmation in aws-pre and record screenshots/notes without secrets. |
| Refund and dispute handling policy | Implemented with env-controlled behavior | `STRIPE_REVOKE_ON_REFUND_OR_DISPUTE`, refund/dispute webhook handlers, admin review action, audit logs | Confirm chosen policy in aws-pre and record `charge.refunded` / `charge.dispute.*` event IDs. |
| Premium feature comparison page | Implemented | `/premium/`, `tableno/legal_views.py`, `tests.unit.test_billing_legal_pages` | Visual check in aws-pre. |
| Premium access code management | Implemented | `issue_premium_code`, bulk CSV, campaign name, expiry, admin CSV without raw code, redemption list | Confirm operator flow in admin/aws-pre. |
| Audit logs for premium grant/revoke/recovery/payment/refund/dispute/admin actor | Implemented | `PremiumAuditLog`, admin tests, Webhook tests, runbook | Confirm audit evidence after real Stripe test events. |
| Test-mode operating runbook | Implemented | `docs/runbooks/STRIPE_BILLING_OPERATIONS.md`, `STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md`, local/MCP verification records | Use the template for final aws-pre verification after real Stripe events exist. |

## Open External Verification

ISSUE-077 remains open. The following are still required before paid Checkout is treated as verified in aws-pre:

- Prove Stripe test mode with `livemode: false` before Product/Price creation.
- Create or confirm `Tableno Premium` with JPY 480 monthly and JPY 4,800 yearly recurring Prices.
- Configure aws-pre Secrets with only `sk_test_...`, `pk_test_...`, test `price_...`, and the aws-pre `whsec_...`.
- Run `billing_preflight --strict`, `billing_stripe_remote_check --require-recent-events --recent-hours 72`, and `billing_release_gate --verification-record docs/runbooks/billing-verification-YYYYMMDD.md` in aws-pre.
- Complete monthly and yearly Checkout from `/accounts/billing/` and record real Stripe event IDs.
- Confirm Customer Portal cancellation sets `cancel_at_period_end=True` and access remains through the paid period.
- Confirm payment failure/recovery, refund/dispute, admin visibility, and audit logs with real test events.

## Local Evidence

- `docs/runbooks/billing-verification-local-20260622.md`: local-only smoke evidence, not ISSUE-077 acceptance evidence.
- `docs/runbooks/billing-verification-mcp-20260622.md`: read-only MCP evidence, not ISSUE-077 acceptance evidence because `livemode=false` proof and Prices are missing.
- `docs/release/aws-pre-release-record-20260621-billing.md`: aws-pre release decision record and residual ticket list.
