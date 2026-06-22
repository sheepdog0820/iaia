# Stripe課金運用手順

## 必須環境変数

- `STRIPE_CHECKOUT_ENABLED`: Checkout exposure switch. Keep `False` in aws-pre/aws-prod until Stripe test-mode Product/Price, Webhook, and real event verification are complete. Set `True` only when paid Checkout buttons may be exposed.
- `STRIPE_SECRET_KEY`: Stripe secret key. `ENVIRONMENT=production` では `sk_live_` で始まる本番キーのみ許可されます。staging/local の検証では `sk_test_` を使用してください。
- `STRIPE_WEBHOOK_SECRET`: Webhook署名検証用secret
- `STRIPE_PREMIUM_PRICE_ID / STRIPE_PREMIUM_YEARLY_PRICE_ID`: 月額/年額プレミアムのStripe Price ID
- `STRIPE_PREMIUM_EXPECTED_CURRENCY`, `STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT`, `STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT`: optional Stripe remote check guards for currency and minor-unit amounts. For the local test plan use `jpy`, `480`, and `4800`.
- `STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID`: Stripe Customer Portal configuration ID。設定時は `billing_stripe_remote_check` がこの設定IDのactive状態、支払い方法更新、サブスクリプション解約、請求履歴を確認します
- `STRIPE_REVOKE_ON_REFUND_OR_DISPUTE`: 返金/チャージバック検知時に権限停止するか。既定は `True`
- `PREMIUM_PRICE_LABEL`: Displayed combined monthly/yearly price label
- `PREMIUM_MONTHLY_PRICE_LABEL`
- `PREMIUM_MONTHLY_PRICE_DESCRIPTION`
- `PREMIUM_YEARLY_PRICE_LABEL`
- `PREMIUM_YEARLY_PRICE_DESCRIPTION`: 特商法ページとプレミアム機能ページに表示する料金文言
- `LEGAL_PAYMENT_METHOD`: 支払方法
- `LEGAL_PAYMENT_TIMING`: 支払時期
- `LEGAL_SERVICE_DELIVERY_TIMING`: プレミアム機能の提供時期
- `LEGAL_CANCELLATION_METHOD`: 解約方法
- `LEGAL_CANCELLATION_EFFECT`: 解約後の権限終了タイミング
- `LEGAL_REFUND_POLICY`: 返金条件
- `LEGAL_SELLER_NAME`, `LEGAL_SELLER_ADDRESS`, `LEGAL_SELLER_PHONE`, `CONTACT_EMAIL`: 事業者情報と問い合わせ先
- `PUBLIC_SITE_URL`: 支払い失敗メールなどに記載する公開URL
- `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`: `invoice.payment_failed` 時のカード更新依頼メールを実配送するため、本番では console/dummy/locmem ではないメールbackendと送信元を設定する

## 本番前チェック

```bash
python manage.py check
python manage.py billing_development_check
python manage.py billing_preflight --strict
python manage.py billing_stripe_remote_check
python manage.py billing_stripe_remote_check --require-recent-events --recent-hours 72
python manage.py billing_webhook_smoke
python manage.py billing_verification_record --strict-preflight --run-remote-check --run-smoke --output docs/runbooks/billing-verification-YYYYMMDD.md
python manage.py billing_release_gate --verification-record docs/runbooks/billing-verification-YYYYMMDD.md
```


Stripe実確認を開始する前に、ローカル端末で以下を確認します。

```powershell
stripe --version
python manage.py billing_development_check
python manage.py billing_preflight
python manage.py billing_status_report --json
python manage.py billing_webhook_smoke
```

`stripe --version` が失敗する場合はStripe CLIをインストールし、`stripe login` で対象Stripeアカウントへ接続してください。`billing_preflight` が `STRIPE_SECRET_KEY`、`STRIPE_WEBHOOK_SECRET`、`STRIPE_PREMIUM_PRICE_ID / STRIPE_PREMIUM_YEARLY_PRICE_ID`、`PUBLIC_SITE_URL` を警告する場合は、テスト環境では `sk_test_...`、`whsec_...`、月額recurring Price ID、ローカル確認用URLを設定してから再実行します。`STRIPE_WEBHOOK_SECRET` は `stripe listen --forward-to http://127.0.0.1:8000/api/billing/webhook/` が表示する `whsec_...` に合わせます。

`billing_development_check` validates that `.env.development` is git-ignored, uses the local JPY 480 monthly / JPY 4,800 yearly expected amounts, and contains no live Stripe key prefixes without printing secrets. Before Stripe Product/Price creation, blank `STRIPE_SECRET_KEY` and `STRIPE_PREMIUM_PRICE_ID` values are warnings. Add `--require-stripe` to fail when test keys or test Price IDs are still blank.

`billing_preflight --strict` はStripeキー、料金表示、解約/返金条件、事業者情報、公開URL、Webhook URL、期限切れコード失効ジョブを確認し、不足があれば失敗します。

`billing_stripe_remote_check` validates Stripe remote settings. `STRIPE_PREMIUM_PRICE_ID` must be an active monthly recurring Price. `STRIPE_PREMIUM_YEARLY_PRICE_ID`, when configured, must be an active yearly recurring Price. If `STRIPE_PREMIUM_EXPECTED_CURRENCY` or expected unit amounts are set, it also verifies the Stripe Price currency and minor-unit amount, so the local 480 JPY monthly / 4,800 JPY yearly test plan cannot accidentally point at the wrong Price. It also verifies matching `livemode` across the secret key, Price, Customer Portal, and Webhook endpoint; Customer Portal support for payment method updates, subscription cancellation, and invoice history; required Webhook event subscriptions; and recent Stripe Events when `--require-recent-events` is used. Copy `recent_event_ids` and `recent_cancel_at_period_end_event_ids` into the verification record and compare Stripe Dashboard events with local `StripeWebhookEvent` records.

`billing_webhook_smoke` はローカルDB上で `checkout.session.completed`、`active`、`cancel_at_period_end`、`invoice.payment_failed`、`invoice.payment_succeeded`、`unpaid`、`deleted/canceled`、`charge.refunded`、`charge.dispute.created`、`charge.dispute.closed status=won` 相当の状態遷移を実行し、Stripe customer/subscriptionの紐付け、プレミアム権限、支払い失敗日時、監査ログが更新されることを確認します。返金/チャージバックで自動停止したレコードは、後続の `customer.subscription.updated` が `active` でも管理者が失効状態を解除するまで再付与されません。チャージバック勝訴時は、チャージバック由来の自動停止が解除されることも確認します。 It also verifies subscription Price synchronization for `stripe_price_id=price_smoke_monthly` with `billing_interval=month` and `stripe_price_id=price_smoke_yearly` with `billing_interval=year`.

`billing_release_gate` is the paid Checkout exposure guard. If `STRIPE_CHECKOUT_ENABLED=False`, it passes because paid Checkout is hidden. If `STRIPE_CHECKOUT_ENABLED=True`, it requires a final aws-pre verification record with real Stripe test-mode event IDs, recent-event output, cancel-at-period-end evidence, and no unfinished placeholders.

`billing_verification_record` writes the checked timestamp, environment, monthly Price ID, yearly Price ID, expected Stripe currency/unit amounts, Webhook URL, `check`, `billing_preflight`, optional `billing_stripe_remote_check`, optional `billing_webhook_smoke`, and manual Stripe/Django admin verification items to Markdown. Add real Stripe event IDs and screen verification notes to the generated file.

## StripeテストPrice作成

テスト確認ではStripe Dashboardをテスト環境に切り替え、同一Productに以下2つのrecurring Priceを作成します。

| プラン | 金額 | 通貨 | 請求周期 | 環境変数 |
| --- | ---: | --- | --- | --- |
| 月額 | 480 | JPY | monthly | `STRIPE_PREMIUM_PRICE_ID` |
| 年額 | 4,800 | JPY | yearly | `STRIPE_PREMIUM_YEARLY_PRICE_ID` |

作成後、ローカルPowerShellでは以下を設定します。

```powershell
$env:STRIPE_SECRET_KEY="sk_test_..."
$env:STRIPE_PREMIUM_PRICE_ID="price_monthly_test_..."
$env:STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_test_..."
$env:STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy"
$env:STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480"
$env:STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT="4800"
$env:PREMIUM_PRICE_LABEL="月額480円 / 年額4,800円"
```

MCP接続が `livemode: true` の場合は、テスト目的のProduct/PriceをMCPから作成しないでください。テストPriceはStripe Dashboardのテスト環境、またはテストキーで認証したStripe CLI/APIから作成します。

## Stripe test mode safety checklist

Before creating Product or Price objects for verification, confirm all of the following.

- Stripe Dashboard test mode is enabled.
- Any MCP or connector result must show `livemode: false` before creating Product/Price objects.
- If MCP or connector output shows `livemode: true`, do not create test Product/Price objects through that connection.
- Use only `sk_test_...`, `pk_test_...`, test `price_...`, and the `whsec_...` from `stripe listen` for local or aws-pre verification.
- Keep `STRIPE_PREMIUM_PRICE_ID` and `STRIPE_PREMIUM_YEARLY_PRICE_ID` empty until real test mode Price IDs exist.
- Run `python manage.py billing_preflight --strict` after setting environment variables. It fails when `sk_live_...` is used outside production.

For the initial test plan, create one Product named `Tableno Premium` in Stripe test mode with two recurring Prices: JPY 480 monthly and JPY 4,800 yearly. Copy the monthly Price ID to `STRIPE_PREMIUM_PRICE_ID` and the yearly Price ID to `STRIPE_PREMIUM_YEARLY_PRICE_ID`.

If you have a `sk_test_...` key locally, you can create the development Product and both Prices through Django instead of MCP:

```powershell
Set-Location C:\Users\endke\Workspace\iaia
$env:STRIPE_SECRET_KEY="sk_test_..."
python manage.py create_stripe_development_prices
```

The command refuses `sk_live_...`, refuses `ENVIRONMENT=production`, verifies the Product response has `livemode=false`, and stops before Price creation if Stripe returns a live-mode object. Copy the printed `STRIPE_PREMIUM_PRICE_ID` and `STRIPE_PREMIUM_YEARLY_PRICE_ID` values into `.env.development`.

## Windows PowerShell quick start

PowerShell is often opened in `C:\WINDOWS\system32`. Always move to the project root before running `manage.py`.

```powershell
Set-Location C:\Users\endke\Workspace\iaia
$env:STRIPE_SECRET_KEY="sk_test_..."
$env:STRIPE_PREMIUM_PRICE_ID="price_monthly_test_..."
$env:STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_test_..."
$env:STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy"
$env:STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480"
$env:STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT="4800"
$env:PREMIUM_PRICE_LABEL="Monthly 480 JPY / Yearly 4,800 JPY"
python manage.py setup_billing_local --include-admin
python manage.py runserver 127.0.0.1:8000
```

Open another PowerShell window for Stripe CLI webhook forwarding, and keep the Django server running.

```powershell
Set-Location C:\Users\endke\Workspace\iaia
stripe login
stripe listen --forward-to http://127.0.0.1:8000/api/billing/webhook/
```

Copy the displayed `whsec_...` value into `STRIPE_WEBHOOK_SECRET`, restart Django, and retry Checkout from `http://127.0.0.1:8000/accounts/billing/`.

## ローカル画面確認用データ

```bash
python manage.py setup_billing_local --include-admin
```

作成されるユーザーの既定パスワードは `password123` です。

- `billing-free`: 未加入ユーザー。Checkout導線の確認用
- `billing-premium`: 手動付与済みプレミアムユーザー。管理ポータル導線や権限表示の確認用
- `billing-code`: 運営発行コード適用の確認用
- `billing-admin`: `--include-admin` 指定時のみ作成される管理画面確認用スーパーユーザー

コマンド出力に `premium code: ...` として表示されるコードを `/accounts/billing/` で入力すると、`billing-code` を課金なしでプレミアム化できます。出力される `Local verification URLs` から、課金管理ページ、プレミアム機能ページ、特商法ページ、管理画面を順に開いて表示を確認します。

## ローカルWebhook確認

1. Stripe CLIにログインする。

   ```bash
   stripe login
   ```

2. Webhookをローカルへ転送する。

   ```bash
   stripe listen --forward-to http://127.0.0.1:8000/api/billing/webhook/
   ```

3. 表示された `whsec_...` を `STRIPE_WEBHOOK_SECRET` に設定してDjangoを再起動する。

4. Stripe Checkoutのテスト決済を実行し、以下を確認する。

   - `checkout.session.completed` 後に `PremiumSubscription` がStripe customer/subscriptionへ紐付く
   - `customer.subscription.updated` の `active` / `trialing` で `is_premium=True`
   - `customer.subscription.updated` の解約予定で `cancel_at_period_end=True` になり、期間終了までは有効
   - `customer.subscription.deleted` や `unpaid` で `is_premium=False`
   - `invoice.payment_failed` で課金管理画面に支払い失敗の警告が表示され、メールが送信される
   - `invoice.payment_succeeded` で支払い失敗の警告が解除される
   - `charge.refunded` / `charge.dispute.created` で監査ログが残り、既定では権限が停止される
   - `charge.dispute.closed` は `status=lost` / `warning_closed` の場合に権限停止対象、`status=won` の場合はチャージバック由来の自動停止を復旧し、停止されていないユーザーは監査ログのみで権限を維持する
   - 返金/チャージバックで停止したユーザーは、後続の `customer.subscription.updated` が `active` でも自動復旧しない

Stripe CLIでWebhook処理だけを発火する場合は、Djangoサーバーと `stripe listen` を起動したまま別ターミナルで実行します。

```bash
stripe trigger checkout.session.completed
stripe trigger customer.subscription.created
stripe trigger customer.subscription.updated
stripe trigger customer.subscription.deleted
stripe trigger invoice.payment_failed
stripe trigger invoice.payment_succeeded
stripe trigger charge.refunded
stripe trigger charge.dispute.created
stripe trigger charge.dispute.closed
```

`stripe trigger` はStripe側のfixtureイベントを送るため、アプリ内の既存ユーザーや既存 `PremiumSubscription` と紐付かない場合があります。その場合はWebhook署名検証、HTTP 2xx応答、`StripeWebhookEvent` の記録、未知customerを無視して失敗しないことを確認し、ユーザー権限の実更新はCheckoutテスト決済または `billing_webhook_smoke` で確認してください。同じStripe event IDの再送は最初の1回だけ処理され、同時再送で一意制約に当たったリクエストはduplicateとして2xx応答します。

実ユーザーとの紐付きを含めて確認する場合は、`billing-free` で `/accounts/billing/` からCheckoutのテスト決済を完了し、Stripe Dashboardのサブスクリプション画面からキャンセル予約、支払い失敗相当のテスト、返金/Disputeのテストイベントを発生させます。Stripe event ID、アプリ側の `StripeWebhookEvent`、`Premium audit logs`、課金画面の表示を照合してください。

確認結果は `docs/runbooks/STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md` をコピーして記録します。Stripe secret、実カード情報、顧客の個人情報は記載しないでください。

確認記録を自動生成する場合:

```bash
python manage.py billing_verification_record \
  --environment aws-pre \
  --stripe-mode test \
  --confirmed-by "your-name" \
  --commit "$(git rev-parse --short HEAD)" \
  --strict-preflight \
  --run-remote-check \
  --remote-require-recent-events \
  --remote-recent-hours 72 \
  --run-smoke \
  --output docs/runbooks/billing-verification-YYYYMMDD.md
```

Customer PortalやWebhook endpointを一時的に別手順で確認する場合は、`--remote-skip-portal` または `--remote-skip-webhook` を付けてください。`--base-url` を指定すると、remote checkのWebhook URLにも同じbase URLが使われます。

## 本番Webhookイベント

Stripe DashboardのWebhook endpointに以下を登録します。

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_failed`
- `invoice.payment_succeeded`
- `charge.refunded`
- `charge.dispute.created`
- `charge.dispute.closed`

## 運営コード

単発発行:

```bash
python manage.py issue_premium_code \
  --label support-comp \
  --campaign-name support \
  --max-uses 1 \
  --expires-in-days 30
```

一括発行とCSV出力:

```bash
python manage.py issue_premium_code \
  --label trial-campaign \
  --campaign-name winter-trial \
  --count 100 \
  --max-uses 1 \
  --expires-in-days 30 \
  --output-csv premium-codes.csv
```

コード本体は発行時にのみ表示されます。DBにはSHA-256 digestのみ保存します。`--output-csv` のCSVには配布用のコード本体に加えて、`campaign_name`、`status`、`use_count`、`remaining_uses`、`expires_at` が含まれます。配布後の利用状況確認や利用者一覧の確認は、raw codeを含まない管理画面CSVを使います。

`--expires-in-days` を指定したコードは、コード入力期限と付与後のプレミアム期限を兼ねます。ユーザーが期限付きコードを入力すると、`PremiumSubscription.premium_expires_at` に同じ日時が保存され、期限到達後は失効バッチで `is_premium=False` になります。`--expires-in-days` を指定しないコードは無期限付与として扱い、管理画面の失効操作または `reconcile_premium_access` で明示的に停止するまで有効です。

期限切れコード由来プレミアムの失効:

```bash
python manage.py expire_premium_access --dry-run
python manage.py expire_premium_access
```

`--dry-run` は失効対象件数だけを出力し、ユーザー権限や監査ログを変更しません。AWS手動実行時は先にdry-runで件数を確認してから本実行してください。Celery beatが有効な環境では `schedules.tasks.expire_premium_access` が1時間ごとに実行されます。

Webhook遅延、手動修正、バッチ停止などで `CustomUser.is_premium` と課金レコードの状態がずれた場合は、まずdry-runで確認してから再同期します。

```bash
python manage.py billing_status_report
python manage.py billing_status_report --json
python manage.py billing_status_report --fail-on-issues
python manage.py billing_status_report --fail-on-issues --include-payment-issues
python manage.py reconcile_premium_access --dry-run
python manage.py reconcile_premium_access
```

`billing_status_report` prints subscription status counts, active access counts, manual override counts, manual overrides without billing records, cancel_at_period_end records, payment failures, refund/dispute records, refund_or_dispute_active_records, expired promo records, indefinite promo records, expiring promo records, promo campaign breakdowns, stale user flags, last processed Stripe Webhook event details, failed_webhook_events, processing_status=failed, and stale_processing_webhook_events. `--fail-on-issues` fails on stale access or expired promo records. `--include-payment-issues` also fails on payment failures, refund/dispute review items, failed Webhook events, and stale processing Webhook events. JSON includes `stripe_checkout_enabled`, `billing_intervals` with `month`, `year`, and blank interval counts, plus `expected_stripe_price_currency`, `expected_monthly_unit_amount`, and `expected_yearly_unit_amount` for Stripe Price verification.

個別ユーザーへ運営判断で手動付与・解除する場合は、理由を付けて実行します。状態が変わった場合は `Premium audit logs` に `source=manual`、`action=granted` または `revoked`、指定した理由、`metadata.command=set_premium_user` が記録されます。最新の手動ログが `source=manual/action=granted` のユーザーは、Stripe購読の失効、返金/チャージバック自動停止、期限付きコードの自動失効、`reconcile_premium_access` の再同期ではプレミアム権限を保持します。手動付与を終了する場合は `set_premium_user --off` または管理画面で明示的に解除してください。

```bash
python manage.py set_premium_user username --on --reason "support comp until migration"
python manage.py set_premium_user username --off --reason "support comp ended"
```

## 監査

Django管理画面で以下を確認します。

- `Users`: 一覧の `Premium source` フィルタでStripe購読、運営コード、手動付与、課金レコードなしの手動付与、プレミアムなしを切り分けます。ユーザー詳細には課金レコード、コード利用履歴、監査ログがインライン表示されます
- `Premium subscriptions`: ユーザーごとのStripe ID、Stripe DashboardへのCustomer/Subscriptionリンク、権限ソース、期限、失効理由、返金/チャージバック検知後の手動確認状態。手動付与が有効なユーザーは、課金レコードがinactiveでも `manual: active override` として表示されます。選択した課金レコードは管理アクションで手動停止、失効状態の解除、ユーザー権限再同期、返金/チャージバック検知の確認済み化ができます。返金/チャージバックで自動停止した権限を再付与する場合は、Stripe Dashboardの状態を確認したうえで失効状態の解除アクションを使います。`STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=False` の手動確認運用では、Stripe Dashboardで返金/Disputeの扱いを確認したあと、確認済み化アクションで `refund_or_dispute_active_records` の対応待ちから外します
- `Premium access codes`: 発行コードのキャンペーン名、状態（active / expired / exhausted / revoked）、使用回数、残り使用可能数、期限、失効状態。選択したコードは管理アクションで停止、付与済みコード由来プレミアムの失効、またはCSV出力ができます。管理画面CSVにはraw codeを含めず、キャンペーン名、状態、利用者一覧が含まれます
- `Premium audit logs`: コード利用、期限切れ失効、管理画面からのコード由来権限失効では `access_code_id`、`access_code_label`、`access_code_campaign_name` を確認できます
- `Premium access code redemptions`: コード利用者
- `Stripe webhook events`: Stripe event ID、event type、`processing_status`、`error_message`、処理時刻。`failed` はStripe Dashboardから再送し、成功後に `succeeded` へ変わることを確認します
- `Premium audit logs`: 付与、復旧、失効、支払い失敗、支払い復旧、返金、チャージバック、確認済み化の履歴。管理画面の手動停止・復旧・同期・返金/チャージバック確認済み化は実行者を `actor` に保存し、Webhookやバッチ由来のログは `actor` なしのシステム処理として扱います。支払い失敗ログは `invoice_id` と `email_sent` をmetadataに保存し、支払い復旧ログは `invoice_id` をmetadataに保存します。返金/チャージバックログは `event_type`、`object_id`、`charge_id`、`invoice_id`、`payment_intent_id`、`amount`、`currency`、`auto_revoked`、`access_revoked`、`access_restored` をmetadataに保存するため、Stripe DashboardのCharge/Invoice/PaymentIntentと照合してください。`access_revoked` はユーザーのプレミアム権限が実際に停止した場合にのみ `true` です。手動付与で権限が保持された場合、課金レコードが失効しても `access_revoked=false` になります。返金/チャージバック確認済み化ログは `action=reviewed` として、最後に検知した時刻をmetadataに保存します Stripe subscription grant/revoke metadata includes `stripe_subscription_id`, `stripe_price_id`, `billing_interval`, and `cancel_at_period_end`.



