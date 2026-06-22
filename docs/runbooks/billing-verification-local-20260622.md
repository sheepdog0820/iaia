# Stripe課金確認記録

Secrets、実カード情報、顧客の個人情報、Webhook signing secretは記載しない。

## 基本情報

| 項目 | 値 |
| --- | --- |
| 確認日 | 2026-06-22 07:36:09 JST |
| 確認者 | Codex |
| 環境 | local |
| base URL | http://127.0.0.1:8000 |
| Stripe mode | test |
| Monthly Price ID | 未設定 |
| Yearly Price ID | 未設定 |
| Expected Stripe Price currency | jpy |
| Expected monthly unit amount | 480 |
| Expected yearly unit amount | 4800 |
| Stripe Checkout enabled | yes |
| Stripe publishable key configured | no |
| Customer Portal configuration ID | 未設定 |
| Webhook endpoint URL | http://127.0.0.1:8000/api/billing/webhook/ |
| リリース/commit | c6b6f81 |

## 事前チェック

| 確認項目 | コマンドまたは確認先 | 結果 | メモ |
| --- | --- | --- | --- |
| Django check | `python manage.py check` | OK | System check identified no issues (0 silenced). |
| 課金preflight | `python manage.py billing_preflight` | WARN | billing_preflight=warnings |
| Billing status report | `python manage.py billing_status_report` | OK | stripe_checkout_enabled=true, expected_stripe_price_currency=jpy, expected_monthly_unit_amount=480, expected_yearly_unit_amount=4800, last_webhook_event_id=(none), last_webhook_event_type=(none), last_webhook_processed_at=(none), failed_webhook_events=0, stale_processing_webhook_events=0, last_failed_webhook_event_id=(none), last_stale_processing_webhook_event_id=(none); Check billing_intervals for month/year/blank counts. |
| Stripe remote check | `python manage.py billing_stripe_remote_check` | 未実行 | 必要に応じて--run-remote-checkを指定 |
| ローカル状態遷移スモーク | `python manage.py billing_webhook_smoke` | OK | billing_webhook_smoke=ok user=billing-smoke-user audits=36 |
| 特商法ページ | /commercial-disclosure/ | 要画面確認 | 料金、解約、返金、提供時期、事業者情報 |
| プレミアム機能ページ | /premium/ | 要画面確認 | 無料/有料差分 |
| 課金管理ページ | /accounts/billing/ | 要画面確認 | 加入、管理、コード適用導線 |

## Stripe recent event IDs

```text
remote check not run or produced no output
```

## Stripe Webhook確認

| イベント | 期待結果 | 結果 | アプリ側確認 |
| --- | --- | --- | --- |
| `checkout.session.completed` | customer/subscriptionがユーザー課金レコードへ紐付く | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |
| `customer.subscription.created` | active/trialingならis_premium=True | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |
| `customer.subscription.updated` | 解約予定、active、unpaidの状態が同期される | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |
| `customer.subscription.deleted` | canceledとして権限失効 | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |
| `invoice.payment_failed` | 支払い失敗日時を保存し、画面とメールでカード更新を案内 | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |
| `invoice.payment_succeeded` | 支払い失敗日時を解除し、画面のカード更新案内を消す | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |
| `charge.refunded` | 監査ログを残し、設定に応じて権限停止。自動停止後はactive更新だけで復旧しない | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |
| `charge.dispute.created` | 監査ログを残し、設定に応じて権限停止。自動停止後はactive更新だけで復旧しない | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |
| `charge.dispute.closed` | status=lost/warning_closedは権限停止、status=wonはチャージバック由来の自動停止を復旧 | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |
| 同一event ID再送 | duplicateとして2xx応答し、処理本体は二重実行されない | 要確認 | StripeWebhookEvent、監査ログ |

## 運営コード確認

| 確認項目 | 期待結果 | 結果 | メモ |
| --- | --- | --- | --- |
| コード発行 | issue_premium_code --campaignでキャンペーン名付きコードを発行できる | 要確認 |  |
| 一括発行CSV | --count と --output-csv でキャンペーン名を含むCSV出力ができる | 要確認 |  |
| コード適用 | /accounts/billing/ で入力するとプレミアム化 | 要確認 |  |
| 期限付きコード | premium_expires_atに期限が入り、期限切れ後に失効 | 要確認 |  |
| 自動失効 | Celery beatまたはexpire_premium_accessで失効 | 要確認 | billing_status_reportのexpired_promo_recordsを確認 |
| 無期限コード | expires_atなしのコードは明示停止まで有効 | 要確認 | billing_status_reportのpromo_indefinite_recordsを確認 |
| 期限付き有効コード | 期限前のコード由来プレミアムを把握できる | 要確認 | billing_status_reportのpromo_expiring_active_recordsを確認 |
| 7日以内に失効するコード | 直近で失効するコード由来プレミアムを把握できる | 要確認 | billing_status_reportのpromo_expiring_soon_recordsを確認 |
| キャンペーン別コード内訳 | キャンペーン別のコード由来プレミアムを把握できる | 要確認 | billing_status_reportのpromo_campaignsを確認 |
| 解約予定 | 解約予定ユーザーを把握でき、期間終了までは有効 | 要確認 | billing_status_reportのcancel_at_period_end_recordsを確認 |
| 管理画面CSV | キャンペーン名と利用状況CSVを出力でき、raw codeは含まない | 要確認 |  |

## 管理画面・監査ログ

| 確認項目 | 期待結果 | 結果 | メモ |
| --- | --- | --- | --- |
| ユーザー詳細 | 課金レコード、コード利用履歴、監査ログが見える | 要確認 |  |
| Premium subscriptions | Stripe IDs, Price ID, billing interval, status, period end, revoke reason, and refund/dispute review state are visible | Needs confirmation | stripe_price_id / billing_interval |
| 手動付与保持 | 最新の手動ログがsource=manual/action=grantedのユーザーは自動失効やWebhook失効後も権限が保持される | 要確認 |  |
| 手動付与レポート | billing_status_reportのmanual_override_users / manual_override_without_subscriptionで手動付与ユーザーを把握できる | 要確認 |  |
| 管理画面復旧 | 失効状態解除アクションで管理者確認後に権限を復旧でき、actorが監査ログに残る | 要確認 |  |
| 返金/チャージバック手動確認 | 自動停止しない設定ではbilling_status_reportのrefund_or_dispute_active_recordsで把握できる | 要確認 |  |
| Premium access codes | 使用回数、期限、停止状態、利用者が見える | 要確認 |  |
| Premium audit logs | Grant, restore, revoke, payment failure/recovery, refund, dispute, and admin actor history are visible | Needs confirmation | Stripe subscription metadata includes stripe_price_id / billing_interval |

## 判定

| 項目 | 値 |
| --- | --- |
| 判定 | Go / No-Go / 条件付きGo |
| 残課題 |  |
| 次の対応 |  |
