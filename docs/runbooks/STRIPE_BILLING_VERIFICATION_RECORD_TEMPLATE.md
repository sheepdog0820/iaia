# Stripe課金確認記録テンプレート

Secrets、実カード情報、顧客の個人情報、Webhook signing secretは記載しないでください。

## 基本情報

| 項目 | 値 |
| --- | --- |
| 確認日 |  |
| 確認者 |  |
| 環境 | local / aws-pre / aws-prod |
| base URL |  |
| Stripe mode | test / live |
| Monthly Price ID |  |
| Yearly Price ID |  |
| Webhook endpoint URL |  |
| リリース/commit |  |

## 事前チェック

| 確認項目 | コマンドまたは確認先 | 結果 | メモ |
| --- | --- | --- | --- |
| Django check | `python manage.py check` | 未実行 |  |
| 課金preflight | `python manage.py billing_preflight --strict` | 未実行 |  |
| Billing status report | `python manage.py billing_status_report` | 未実行 | `last_webhook_event_id` / `last_webhook_event_type` / `last_webhook_processed_at` をStripe Dashboardのイベントと照合する。`billing_intervals` includes month/year/blank counts. `failed_webhook_events=0`、`stale_processing_webhook_events=0` を確認する。 |
| Stripe remote check | `python manage.py billing_stripe_remote_check` | 未実行 |  |
| Stripe recent events check | `python manage.py billing_stripe_remote_check --require-recent-events --recent-hours 72` | 未実行 | 実Checkout/Stripe Dashboard操作後に `checkout.session.completed`、`customer.subscription.created/updated/deleted`、`invoice.payment_failed/succeeded`、`charge.refunded`、`charge.dispute.created/closed`、`cancel_at_period_end=true` を確認。出力された `recent_event_ids` と `recent_cancel_at_period_end_event_ids` をこの記録へ転記 |
| ローカル状態遷移スモーク | `python manage.py billing_webhook_smoke` | 未実行 |  |
| 特商法ページ | `/commercial-disclosure/` | 未確認 | 料金、解約、返金、提供時期、事業者情報 |
| プレミアム機能ページ | `/premium/` | 未確認 | 無料/有料差分 |
| 課金管理ページ | `/accounts/billing/` | 未確認 | 加入、管理、コード適用導線 |

## Stripe Webhook確認

### Stripe CLI trigger

`stripe trigger` はfixtureイベントの疎通確認として使います。既存ユーザーとの紐付けが必要な権限更新は、次の「実Checkout/Stripe Dashboard操作」で確認してください。

| コマンド | 期待結果 | 結果 | Stripe event ID | アプリ側確認 |
| --- | --- | --- | --- | --- |
| `stripe trigger checkout.session.completed` | 署名検証後に2xx応答、event記録 | 未確認 |  | `StripeWebhookEvent` |
| `stripe trigger customer.subscription.created` | 署名検証後に2xx応答、未知customerでも失敗しない | 未確認 |  | `StripeWebhookEvent` |
| `stripe trigger customer.subscription.updated` | 署名検証後に2xx応答、未知customerでも失敗しない | 未確認 |  | `StripeWebhookEvent` |
| `stripe trigger customer.subscription.deleted` | 署名検証後に2xx応答、未知customerでも失敗しない | 未確認 |  | `StripeWebhookEvent` |
| `stripe trigger invoice.payment_failed` | 署名検証後に2xx応答、未知customerでも失敗しない | 未確認 |  | `StripeWebhookEvent` |
| `stripe trigger invoice.payment_succeeded` | 署名検証後に2xx応答、未知customerでも失敗しない | 未確認 |  | `StripeWebhookEvent` |
| `stripe trigger charge.refunded` | 署名検証後に2xx応答、未知charge/customerでも失敗しない | 未確認 |  | `StripeWebhookEvent` |
| `stripe trigger charge.dispute.created` | 署名検証後に2xx応答、未知charge/customerでも失敗しない | 未確認 |  | `StripeWebhookEvent` |
| `stripe trigger charge.dispute.closed` | 署名検証後に2xx応答、未知charge/customerでも失敗しない | 未確認 |  | `StripeWebhookEvent` |
| 同一event ID再送 | duplicateとして2xx応答し、処理本体は二重実行されない | 未確認 |  | `StripeWebhookEvent`、監査ログ |

### 実Checkout/Stripe Dashboard操作

| イベント | 期待結果 | 結果 | Stripe event ID | アプリ側確認 |
| --- | --- | --- | --- | --- |
| `checkout.session.completed` | customer/subscriptionがユーザー課金レコードへ紐付く | 未確認 |  | `PremiumSubscription` |
| `customer.subscription.created` | `active` / `trialing` なら `is_premium=True` | 未確認 |  | ユーザー詳細、監査ログ |
| `customer.subscription.updated` | 解約予定なら `cancel_at_period_end=True`、期間終了までは有効 | 未確認 |  | 課金画面、管理画面 |
| `customer.subscription.updated` | `unpaid` なら `is_premium=False` | 未確認 |  | ユーザー詳細、監査ログ |
| `customer.subscription.deleted` | `canceled` として権限失効 | 未確認 |  | ユーザー詳細、監査ログ |
| `invoice.payment_failed` | 支払い失敗日時を保存し、課金画面とメールでカード更新を案内 | 未確認 |  | メール、課金画面 |
| `invoice.payment_succeeded` | 支払い失敗日時を解除し、課金画面のカード更新案内が消える | 未確認 |  | 課金画面、監査ログ |
| `charge.refunded` | 監査ログを残し、設定に応じて権限停止。自動停止後は `customer.subscription.updated` が `active` でも自動復旧しない | 未確認 |  | 監査ログ、ユーザー詳細 |
| `charge.dispute.created` | 監査ログを残し、設定に応じて権限停止。自動停止後は `customer.subscription.updated` が `active` でも自動復旧しない | 未確認 |  | 監査ログ、ユーザー詳細 |
| `charge.dispute.closed` | `status=lost` / `warning_closed` は権限停止。`status=won` はチャージバック由来の自動停止を復旧し、停止されていないユーザーは監査ログのみで権限維持 | 未確認 |  | 監査ログ、ユーザー詳細 |
| duplicate event | 同じevent IDの再送で二重処理しない | 未確認 |  | `StripeWebhookEvent` |

## 運営コード確認

| 確認項目 | 期待結果 | 結果 | メモ |
| --- | --- | --- | --- |
| コード発行 | `issue_premium_code --campaign` でキャンペーン名付きコードを発行できる | 未確認 |  |
| 一括発行CSV | `--count` と `--output-csv` でキャンペーン名を含むCSV出力ができる | 未確認 |  |
| コード適用 | `/accounts/billing/` で入力するとプレミアム化 | 未確認 |  |
| 期限付きコード | `premium_expires_at` に期限が入り、期限切れ後に失効 | 未確認 |  |
| 自動失効 | Celery beatまたは `expire_premium_access` で失効 | 未確認 |  |
| 7日以内に失効するコード | `billing_status_report` の `promo_expiring_soon_records` で把握できる | 未確認 |  |
| キャンペーン別コード内訳 | `billing_status_report` の `promo_campaigns` でキャンペーン別に total / active / expired / expiring_soon / indefinite を把握できる | 未確認 |  |
| 解約予定 | `billing_status_report` の `cancel_at_period_end_records` で把握でき、期間終了までは有効 | 未確認 |  |
| 管理画面停止 | 選択したコードを停止できる | 未確認 |  |
| 管理画面CSV | キャンペーン名と利用状況CSVを出力でき、raw codeは含まない | 未確認 |  |

## 管理画面・監査ログ

| 確認項目 | 期待結果 | 結果 | メモ |
| --- | --- | --- | --- |
| ユーザー詳細 | 課金レコード、コード利用履歴、監査ログが見える | 未確認 |  |
| Premium subscriptions | Stripe ID、ステータス、期限、失効理由、返金/チャージバック後の確認状態が見える | 未確認 |  |
| 手動付与保持 | 最新の手動ログが `source=manual/action=granted` のユーザーは自動失効やWebhook失効後も権限が保持される | 未確認 |  |
| 手動付与レポート | `billing_status_report` の `manual_override_users` / `manual_override_without_subscription` で手動付与ユーザーを把握できる | 未確認 |  |
| 管理画面復旧 | 失効状態解除アクションで管理者確認後に権限を復旧でき、actorが監査ログに残る | 未確認 |  |
| Premium access codes | 使用回数、期限、停止状態、利用者が見える | 未確認 |  |
| Premium audit logs | 付与、復旧、失効、支払い失敗、支払い復旧、返金、チャージバック、管理者操作actorが残る | 未確認 | Stripe subscription metadata includes `stripe_price_id` / `billing_interval`. |

## 判定

| 項目 | 値 |
| --- | --- |
| 判定 | Go / No-Go / 条件付きGo |
| 残課題 |  |
| 次の対応 |  |
