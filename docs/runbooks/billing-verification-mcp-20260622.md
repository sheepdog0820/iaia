# Stripe MCP verification record - 2026-06-22

Do not write Secrets, real passwords, client secrets, customer personal information, or Webhook signing secrets in this file.

## Summary

| Item | Value |
| --- | --- |
| Checked date | 2026-06-22 |
| Target | Stripe MCP connector |
| Stripe account ID | acct_1TkMqJHdY1p3WlN0 |
| Purpose | ISSUE-077 external Stripe verification for aws-pre paid billing |
| Result | Not accepted as complete test-mode verification |

## MCP Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Account info | Observed | `_get_stripe_account_info` returned `acct_1TkMqJHdY1p3WlN0`. |
| Product search | Observed | Search for `products:name:'Tableno Premium'` returned `prod_UkNyUXGrQIln9L`, `prod_UkFVj0t5DW9v69`, and `prod_Uk2J3frLwl4lCk`. |
| Price search for `prod_UkNyUXGrQIln9L` | No Prices found | Search for `prices:product:'prod_UkNyUXGrQIln9L'` returned an empty result set. |
| Price search for `prod_UkFVj0t5DW9v69` | No Prices found | Search for `prices:product:'prod_UkFVj0t5DW9v69'` returned an empty result set. |
| Price search for `prod_Uk2J3frLwl4lCk` | No Prices found | Search for `prices:product:'prod_Uk2J3frLwl4lCk'` returned an empty result set. |
| `livemode=false` proof | Missing | MCP fetch output did not expose `livemode`, so the result cannot prove test-mode readiness. |
| Product/Price creation | Not performed | The available MCP tools in this session are search/fetch/planning/documentation tools only. Creation was intentionally not attempted. |

## 2026-06-22 follow-up read-only check

| Check | Result | Evidence |
| --- | --- | --- |
| Account info | Observed | `_get_stripe_account_info` returned `acct_1TkMqJHdY1p3WlN0`. |
| Product `prod_UkFVj0t5DW9v69` fetch | No default Price | `_fetch` returned `default_price=null`; `livemode` was not exposed. |
| Product `prod_Uk2J3frLwl4lCk` fetch | No default Price | `_fetch` returned `default_price=null`; `livemode` was not exposed. |
| Price search for `prod_UkFVj0t5DW9v69` | No Prices found | `prices: product:'prod_UkFVj0t5DW9v69'` returned an empty result set. |
| Price search for `prod_Uk2J3frLwl4lCk` | No Prices found | `prices: product:'prod_Uk2J3frLwl4lCk'` returned an empty result set. |

This follow-up read-only check still does not satisfy ISSUE-077 because there is no `livemode=false` proof, no monthly/yearly test Price IDs, and no real Stripe test-mode event IDs.

## 2026-06-22 post-commit read-only check

| Check | Result | Evidence |
| --- | --- | --- |
| Account info | Observed | `_get_stripe_account_info` returned `acct_1TkMqJHdY1p3WlN0`. |
| Product search | Observed | `products: name:'Tableno Premium'` returned `prod_UkNyUXGrQIln9L`, `prod_UkFVj0t5DW9v69`, and `prod_Uk2J3frLwl4lCk`. |
| Product `prod_UkNyUXGrQIln9L` fetch | No default Price | `_fetch` returned `default_price=null`; `livemode` was not exposed. |
| Product `prod_UkFVj0t5DW9v69` fetch | No default Price | `_fetch` returned `default_price=null`; `livemode` was not exposed. |
| Product `prod_Uk2J3frLwl4lCk` fetch | No default Price | `_fetch` returned `default_price=null`; `livemode` was not exposed. |
| Price search for `prod_UkNyUXGrQIln9L` | No Prices found | `prices: product:'prod_UkNyUXGrQIln9L'` returned an empty result set. |
| Price search for `prod_UkFVj0t5DW9v69` | No Prices found | `prices: product:'prod_UkFVj0t5DW9v69'` returned an empty result set. |
| Price search for `prod_Uk2J3frLwl4lCk` | No Prices found | `prices: product:'prod_Uk2J3frLwl4lCk'` returned an empty result set. |

This post-commit read-only check still does not satisfy ISSUE-077 because there is no `livemode=false` proof, no monthly/yearly test Price IDs, and no real Stripe test-mode event IDs.

## Decision

This record does not satisfy ISSUE-077. It only proves that the connector can read the account and that the visible `Tableno Premium` Products do not currently expose matching Prices through MCP search.

Do not expose paid Checkout buttons in aws-pre as externally verified until all of the following are recorded in a later verification file:

- Stripe Dashboard or connector output proves `livemode: false`.
- Test Product `Tableno Premium` has recurring Prices for JPY 480 monthly and JPY 4,800 yearly.
- aws-pre Secrets use `sk_test_...`, `pk_test_...`, test `price_...`, and the aws-pre Webhook `whsec_...`.
- `billing_preflight --strict` passes in aws-pre.
- `billing_stripe_remote_check --require-recent-events --recent-hours 72` passes after real test events exist.
- Real test-mode Stripe event IDs are recorded for Checkout, subscription update/delete, payment failure/recovery, refund, dispute, and cancel-at-period-end flows.

## Next Actions

1. In Stripe Dashboard, switch explicitly to test mode.
2. Create or confirm the test Product and recurring monthly/yearly Prices.
3. Copy the test Price IDs into aws-pre Secrets and `.env.development` as needed.
4. Configure the test-mode Webhook endpoint for `/api/billing/webhook/`.
5. Generate the final verification record with `python manage.py billing_verification_record --environment aws-pre --stripe-mode test --require-recent-events`.
