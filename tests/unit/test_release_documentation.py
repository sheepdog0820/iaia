from pathlib import Path

from django.test import SimpleTestCase
from django.urls import Resolver404, resolve


class ReleaseDocumentationTestCase(SimpleTestCase):
    ROOT = Path(__file__).resolve().parents[2]
    SECRET_PATTERNS = [
        "arkham" + "_admin_2024",
        "admin / " + "arkham" + "_admin_2024",
        "azathoth_gm / " + "arkham" + "2024",
        "Password: " + "arkham" + "_admin_2024",
        "パスワード: " + "arkham" + "_admin_2024",
    ]

    def test_readme_does_not_publish_test_account_passwords(self):
        content = (self.ROOT / "README.md").read_text(encoding="utf-8")

        for value in self.SECRET_PATTERNS:
            self.assertNotIn(value, content)

        self.assertIn("### テストアカウント", content)
        self.assertIn("ローカル環境で作成してください。", content)
        self.assertIn("python create_admin.py", content)

    def test_release_documents_do_not_publish_fixed_admin_password(self):
        checked_paths = [
            "AGENTS.md",
            "CLAUDE.md",
            "SPECIFICATION.md",
            "SESSION_TEST_DATA_SPECIFICATION.md",
            "TEST_DATA_MANAGEMENT.md",
            "TEST_DATA_README.md",
            "accounts/views/dev_login_view.py",
            "create_admin.py",
            "schedules/management/commands/create_session_test_data.py",
            "schedules/management/commands/reset_dev_session_data.py",
            "server.sh",
            "templates/accounts/dev_login.html",
        ]

        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding="utf-8")
            for value in self.SECRET_PATTERNS:
                self.assertNotIn(value, content, f"{relative_path} publishes {value!r}")

    def test_django_version_is_documented_as_52_series(self):
        readme = (self.ROOT / "README.md").read_text(encoding="utf-8")
        requirements = (self.ROOT / "requirements.txt").read_text(encoding="utf-8")

        self.assertIn("Django 5.2", readme)
        self.assertIn("Django>=5.2.0,<5.3", requirements)
        self.assertNotIn("Django " + "4.2+", readme)
        self.assertNotIn("Django>=" + "4.2.0,<5.0", requirements)

    def test_x_oauth_callback_url_resolves_only_for_configured_provider(self):
        resolved = resolve("/accounts/twitter_oauth2/login/callback/")

        self.assertIn("twitter_oauth2", resolved.route)
        with self.assertRaises(Resolver404):
            resolve("/accounts/twitter/login/callback/")

    def test_x_oauth_design_uses_configured_allauth_provider(self):
        design = (self.ROOT / "docs/X_OAUTH_LINKING_DESIGN.md").read_text(encoding="utf-8")

        self.assertIn("allauth.socialaccount.providers.twitter_oauth2", design)
        self.assertIn("provider: `twitter_oauth2`", design)
        self.assertIn("TWITTER_CLIENT_ID", design)
        self.assertIn("TWITTER_REDIRECT_URI", design)
        self.assertNotIn("allauth.socialaccount.providers.twitter`", design)
        self.assertNotIn("provider: `twitter`", design)
        self.assertNotIn("`X_CLIENT_ID`", design)
        self.assertNotIn("`X_REDIRECT_URI`", design)

    def test_public_release_oauth_callbacks_match_allauth_provider_paths(self):
        public_tasks = (self.ROOT / "docs/release/PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")
        staging_env = (self.ROOT / ".env.staging.example").read_text(encoding="utf-8")
        production_env = (self.ROOT / ".env.production.example").read_text(encoding="utf-8")

        expected_callbacks = [
            "https://stg.tableno.jp/accounts/google/login/callback/",
            "https://tableno.jp/accounts/google/login/callback/",
            "https://stg.tableno.jp/accounts/discord/login/callback/",
            "https://tableno.jp/accounts/discord/login/callback/",
            "https://stg.tableno.jp/accounts/twitter_oauth2/login/callback/",
            "https://tableno.jp/accounts/twitter_oauth2/login/callback/",
        ]

        for callback in expected_callbacks:
            self.assertIn(callback, public_tasks)
        self.assertIn(
            "TWITTER_REDIRECT_URI=https://stg.tableno.jp/accounts/twitter_oauth2/login/callback/", staging_env
        )
        self.assertIn("TWITTER_REDIRECT_URI=https://tableno.jp/accounts/twitter_oauth2/login/callback/", production_env)
        self.assertNotIn("/accounts/twitter/login/callback/", public_tasks)

    def test_stripe_billing_verification_record_template_exists(self):
        template = (self.ROOT / "docs" / "runbooks" / "STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md").read_text(
            encoding="utf-8"
        )
        pre_release_record = (self.ROOT / "docs" / "release" / "AWS_PRE_RELEASE_RECORD_TEMPLATE.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Stripe課金確認記録テンプレート", template)
        self.assertIn("checkout.session.completed", template)
        self.assertIn("invoice.payment_failed", template)
        self.assertIn("invoice.payment_succeeded", template)
        self.assertIn("charge.refunded", template)
        self.assertIn("charge.dispute.created", template)
        self.assertIn("charge.dispute.closed", template)
        self.assertIn("Monthly Price ID", template)
        self.assertIn("Yearly Price ID", template)
        self.assertIn("billing_intervals", template)
        self.assertIn("stripe_price_id", template)
        self.assertIn("billing_interval", template)
        self.assertIn("last_webhook_event_id", template)
        self.assertIn("last_webhook_processed_at", template)
        self.assertIn("failed_webhook_events=0", template)
        self.assertIn("stale_processing_webhook_events=0", template)
        self.assertIn("promo_expiring_soon_records", template)
        self.assertIn("--require-recent-events", template)
        self.assertIn("Secrets、実カード情報、顧客の個人情報", template)
        self.assertIn("STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md", pre_release_record)

    def test_stripe_cli_webhook_runbook_documents_trigger_commands(self):
        runbook = (self.ROOT / "docs" / "runbooks" / "STRIPE_BILLING_OPERATIONS.md").read_text(encoding="utf-8")
        template = (self.ROOT / "docs" / "runbooks" / "STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md").read_text(
            encoding="utf-8"
        )
        trigger_commands = [
            "stripe trigger checkout.session.completed",
            "stripe trigger customer.subscription.created",
            "stripe trigger customer.subscription.updated",
            "stripe trigger customer.subscription.deleted",
            "stripe trigger invoice.payment_failed",
            "stripe trigger invoice.payment_succeeded",
            "stripe trigger charge.refunded",
            "stripe trigger charge.dispute.created",
            "stripe trigger charge.dispute.closed",
        ]

        self.assertIn("stripe listen --forward-to http://127.0.0.1:8000/api/billing/webhook/", runbook)
        self.assertIn("Set-Location C:\\Users\\endke\\Workspace\\iaia", runbook)
        self.assertIn("python manage.py runserver 127.0.0.1:8000", runbook)
        self.assertIn("C:\\WINDOWS\\system32", runbook)
        self.assertIn("STRIPE_WEBHOOK_SECRET", runbook)
        self.assertNotIn("PREMIUM_PRICE_LABEL`r", runbook)
        self.assertIn("fixtureイベント", runbook)
        self.assertIn("実Checkout/Stripe Dashboard操作", template)
        for command in trigger_commands:
            self.assertIn(command, runbook)
            self.assertIn(command, template)

    def test_billing_release_gate_is_documented(self):
        runbook = (self.ROOT / "docs/runbooks/STRIPE_BILLING_OPERATIONS.md").read_text(encoding="utf-8")
        deployment_guide = (self.ROOT / "docs/DEPLOYMENT_GUIDE.md").read_text(encoding="utf-8")

        for content in (runbook, deployment_guide):
            self.assertIn("billing_release_gate", content)
            self.assertIn("STRIPE_CHECKOUT_ENABLED=False", content)
            self.assertIn("real Stripe test-mode event IDs", content)
        self.assertIn("paid Checkout exposure guard", runbook)
        self.assertIn("STRIPE_CHECKOUT_ENABLED=False", runbook)
        self.assertIn("Checkout disabled", deployment_guide)
        self.assertIn("Checkout enabled", deployment_guide)

    def test_billing_legal_environment_variables_are_documented(self):
        required_keys = [
            "STRIPE_PREMIUM_EXPECTED_CURRENCY",
            "STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT",
            "STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT",
            "STRIPE_REVOKE_ON_REFUND_OR_DISPUTE",
            "STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID",
            "EMAIL_BACKEND",
            "DEFAULT_FROM_EMAIL",
            "PREMIUM_PRICE_LABEL",
            "PREMIUM_MONTHLY_PRICE_LABEL",
            "PREMIUM_MONTHLY_PRICE_DESCRIPTION",
            "PREMIUM_YEARLY_PRICE_LABEL",
            "PREMIUM_YEARLY_PRICE_DESCRIPTION",
            "LEGAL_PAYMENT_METHOD",
            "LEGAL_PAYMENT_TIMING",
            "LEGAL_SERVICE_DELIVERY_TIMING",
            "LEGAL_CANCELLATION_METHOD",
            "LEGAL_CANCELLATION_EFFECT",
            "LEGAL_REFUND_POLICY",
            "LEGAL_SELLER_NAME",
            "LEGAL_SELLER_ADDRESS",
            "LEGAL_SELLER_PHONE",
            "CONTACT_EMAIL",
        ]
        checked_paths = [
            "docs/DEPLOYMENT_GUIDE.md",
            "docs/release/AWS_PRE_RELEASE_CHECKLIST.md",
            "docs/runbooks/STRIPE_BILLING_OPERATIONS.md",
        ]

        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding="utf-8")
            for key in required_keys:
                self.assertIn(key, content, f"{relative_path} does not document {key}")

    def test_env_example_documents_billing_settings_one_key_per_line(self):
        env_example = (self.ROOT / ".env.example").read_text(encoding="utf-8")
        required_keys = [
            "STRIPE_CHECKOUT_ENABLED",
            "STRIPE_SECRET_KEY",
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_PREMIUM_PRICE_ID",
            "STRIPE_PREMIUM_YEARLY_PRICE_ID",
            "STRIPE_PREMIUM_EXPECTED_CURRENCY",
            "STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT",
            "STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT",
            "STRIPE_PUBLISHABLE_KEY",
            "STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID",
            "STRIPE_REVOKE_ON_REFUND_OR_DISPUTE",
            "PREMIUM_PRICE_LABEL",
            "PREMIUM_MONTHLY_PRICE_LABEL",
            "PREMIUM_MONTHLY_PRICE_DESCRIPTION",
            "PREMIUM_YEARLY_PRICE_LABEL",
            "PREMIUM_YEARLY_PRICE_DESCRIPTION",
            "LEGAL_PAYMENT_METHOD",
            "LEGAL_PAYMENT_TIMING",
            "LEGAL_SERVICE_DELIVERY_TIMING",
            "LEGAL_CANCELLATION_METHOD",
            "LEGAL_CANCELLATION_EFFECT",
            "LEGAL_REFUND_POLICY",
            "LEGAL_SELLER_NAME",
            "LEGAL_SELLER_ADDRESS",
            "LEGAL_SELLER_PHONE",
            "PUBLIC_SITE_URL",
            "CONTACT_EMAIL",
            "DEFAULT_FROM_EMAIL",
        ]
        lines = env_example.splitlines()

        for key in required_keys:
            matching_lines = [line for line in lines if line.startswith(f"{key}=")]
            self.assertEqual(
                len(matching_lines),
                1,
                f".env.example must contain exactly one {key}= line",
            )
            self.assertNotIn("LEGAL_", matching_lines[0].split("=", 1)[1])
            self.assertNotIn("STRIPE_", matching_lines[0].split("=", 1)[1])

    def test_aws_env_examples_keep_checkout_disabled_and_mail_configured(self):
        common_required_lines = [
            "STRIPE_CHECKOUT_ENABLED=False",
            "STRIPE_SECRET_KEY=sk_test_or_live_replace_me",
            "STRIPE_WEBHOOK_SECRET=whsec_replace_me",
            "STRIPE_PREMIUM_PRICE_ID=price_monthly_replace_me",
            "STRIPE_PREMIUM_YEARLY_PRICE_ID=price_yearly_replace_me",
            "STRIPE_PREMIUM_EXPECTED_CURRENCY=jpy",
            "STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT=480",
            "STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT=4800",
            "STRIPE_PUBLISHABLE_KEY=pk_test_or_live_replace_me",
            "STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID=bpc_replace_me",
            "STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=True",
            "PREMIUM_PRICE_LABEL=Monthly 480 JPY / Yearly 4,800 JPY",
            "LEGAL_PAYMENT_METHOD=Credit card and other payment methods available through Stripe Checkout.",
            "LEGAL_PAYMENT_TIMING=Charged when the subscription starts and renewed on each billing cycle.",
            "LEGAL_SELLER_NAME=Tableno operations",
            "EMAIL_HOST=smtp.gmail.com",
            "EMAIL_PORT=587",
            "EMAIL_USE_TLS=True",
            "EMAIL_HOST_USER=your-email@gmail.com",
            "EMAIL_HOST_PASSWORD=your-email-password",
            "DEFAULT_FROM_EMAIL=noreply@tableno.jp",
            "SERVER_EMAIL=noreply@tableno.jp",
            "CONTACT_EMAIL=support@tableno.jp",
            "SUPPORT_EMAIL=support@tableno.jp",
        ]
        env_specific_lines = {
            ".env.staging.example": "PUBLIC_SITE_URL=https://stg.tableno.jp",
            ".env.production.example": "PUBLIC_SITE_URL=https://tableno.jp",
        }

        for env_name, public_site_url in env_specific_lines.items():
            with self.subTest(env_name=env_name):
                content = (self.ROOT / env_name).read_text(encoding="utf-8")
                for line in [*common_required_lines, public_site_url]:
                    self.assertIn(line, content)

    def test_development_env_example_documents_local_billing_settings(self):
        env_example = (self.ROOT / ".env.development.example").read_text(encoding="utf-8")
        required_lines = [
            "APP_ENV=local",
            "ENVIRONMENT=development",
            "PUBLIC_SITE_URL=http://127.0.0.1:8000",
            "STRIPE_CHECKOUT_ENABLED=False",
            "STRIPE_SECRET_KEY=",
            "STRIPE_WEBHOOK_SECRET=",
            "STRIPE_PREMIUM_PRICE_ID=",
            "STRIPE_PREMIUM_YEARLY_PRICE_ID=",
            "STRIPE_PREMIUM_EXPECTED_CURRENCY=jpy",
            "STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT=480",
            "STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT=4800",
            "STRIPE_PUBLISHABLE_KEY=",
            "STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID=",
            "STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=True",
            "PREMIUM_PRICE_LABEL=\u6708\u984d480\u5186 / \u5e74\u984d4,800\u5186",
            "PREMIUM_MONTHLY_PRICE_DESCRIPTION=480\u5186/\u6708",
            "PREMIUM_YEARLY_PRICE_DESCRIPTION=4,800\u5186/\u5e74",
            "LEGAL_PAYMENT_TIMING=\u521d\u56de\u7533\u3057\u8fbc\u307f\u6642\u306b\u8ab2\u91d1\u3055\u308c\u3001\u4ee5\u5f8c\u306f\u9078\u629e\u3057\u305f\u6708\u984d\u307e\u305f\u306f\u5e74\u984d\u30b5\u30d6\u30b9\u30af\u30ea\u30d7\u30b7\u30e7\u30f3\u3068\u3057\u3066\u81ea\u52d5\u66f4\u65b0\u3055\u308c\u307e\u3059\u3002",
        ]

        for line in required_lines:
            self.assertIn(line, env_example)

        self.assertIn("Use Stripe test keys and test Price IDs", env_example)
        self.assertIn("Do not put live keys here", env_example)
        self.assertNotIn("sk_live_", env_example)
        self.assertNotIn("pk_live_", env_example)

    def test_stripe_key_mode_is_documented(self):
        checked_paths = [
            "docs/DEPLOYMENT_GUIDE.md",
            "docs/runbooks/STRIPE_BILLING_OPERATIONS.md",
        ]

        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("sk_live_", content, f"{relative_path} does not document live Stripe keys")
            self.assertIn("sk_test_", content, f"{relative_path} does not document test Stripe keys")

        for relative_path in [
            "docs/DEPLOYMENT_GUIDE.md",
            "docs/release/AWS_PRE_RELEASE_CHECKLIST.md",
        ]:
            content = (self.ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("`PREMIUM_PRICE_LABEL`", content)
            self.assertNotIn("PREMIUM_PRICE_LABEL`r", content)

        runbook = (self.ROOT / "docs/runbooks/STRIPE_BILLING_OPERATIONS.md").read_text(encoding="utf-8")
        self.assertIn("livemode", runbook)
        self.assertIn("Customer Portal", runbook)
        self.assertIn("支払い方法更新", runbook)
        self.assertIn("サブスクリプション解約", runbook)
        self.assertIn("請求履歴", runbook)
        self.assertIn("recent_event_ids", runbook)
        self.assertIn("recent_cancel_at_period_end_event_ids", runbook)
        self.assertIn("STRIPE_CHECKOUT_ENABLED", runbook)
        self.assertIn("STRIPE_PREMIUM_YEARLY_PRICE_ID", runbook)
        self.assertIn("year", runbook)
        self.assertIn("billing_intervals", runbook)
        self.assertIn("stripe_checkout_enabled", runbook)
        self.assertIn("Stripe test mode safety checklist", runbook)
        self.assertIn("MCP or connector result must show `livemode: false`", runbook)
        self.assertIn("If MCP or connector output shows `livemode: true`", runbook)
        self.assertIn("do not create test Product/Price objects", runbook)
        self.assertIn("billing_preflight --strict", runbook)
        self.assertIn("JPY 480 monthly", runbook)
        self.assertIn("JPY 4,800 yearly", runbook)
        self.assertIn("STRIPE_PREMIUM_EXPECTED_CURRENCY", runbook)
        self.assertIn("STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT", runbook)
        self.assertIn("STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT", runbook)
        self.assertIn("local 480 JPY monthly / 4,800 JPY yearly test plan", runbook)
        self.assertIn("billing_development_check", runbook)
        self.assertIn("create_stripe_development_prices", runbook)
        self.assertIn("refuses `sk_live_...`", runbook)
        self.assertIn("livemode=false", runbook)
        self.assertIn("stripe_price_id=price_smoke_monthly", runbook)
        self.assertIn("billing_interval=month", runbook)
        self.assertIn("stripe_price_id=price_smoke_yearly", runbook)
        self.assertIn("billing_interval=year", runbook)

        template = (self.ROOT / "docs" / "runbooks" / "STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Expected Stripe Price currency", template)
        self.assertIn("Expected monthly unit amount", template)
        self.assertIn("Expected yearly unit amount", template)
        self.assertIn("Stripe Checkout enabled", template)
        self.assertIn("stripe_checkout_enabled", template)
        self.assertIn("Stripe publishable key configured", template)
        self.assertIn("Customer Portal configuration ID", template)
        self.assertIn("stripe_price_id=price_smoke_monthly", template)
        self.assertIn("billing_interval=month", template)
        self.assertIn("stripe_price_id=price_smoke_yearly", template)
        self.assertIn("billing_interval=year", template)

    def test_public_release_tasks_records_current_full_test_evidence(self):
        release_tasks = (self.ROOT / "docs/release/PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")

        self.assertIn("manage.py test --noinput", release_tasks)
        self.assertIn("billing_release_gate", release_tasks)
        self.assertIn("1120件 OK", release_tasks)
        self.assertIn("skipped=3", release_tasks)
        self.assertIn("tests.unit.test_production_settings", release_tasks)
        self.assertIn("manage.py check --deploy", release_tasks)
        self.assertIn("Python 3.11.1", release_tasks)
        self.assertIn(".python-version", release_tasks)
        self.assertIn("manage.py check", release_tasks)
        self.assertIn("migrate --check", release_tasks)
        self.assertIn("runserver --noreload", release_tasks)
        self.assertIn("/health/live/", release_tasks)
        self.assertIn("/health/ready/", release_tasks)
        self.assertIn("/accounts/login/", release_tasks)
        self.assertIn("timeout 扱い", release_tasks)
        self.assertNotIn("1092件", release_tasks)
        self.assertNotIn("1099件", release_tasks)

    def test_external_integrations_are_documented_as_beta_gated(self):
        readme = (self.ROOT / "README.md").read_text(encoding="utf-8")
        features = (self.ROOT / "docs/CURRENT_WEBAPP_FEATURES.md").read_text(encoding="utf-8")
        specification = (self.ROOT / "SPECIFICATION.md").read_text(encoding="utf-8")

        for content in (readme, features, specification):
            self.assertIn("docs/release/PUBLIC_RELEASE_TASKS.md", content)
            self.assertIn("real external-service verification", content)
            self.assertIn("Google Calendar/Sheets", content)
            self.assertIn("advanced Discord", content)
            self.assertIn("WebSocket", content)

    def test_password_reset_verification_guard_is_documented(self):
        release_tasks = (self.ROOT / "docs/release/PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")
        features = (self.ROOT / "docs/CURRENT_WEBAPP_FEATURES.md").read_text(encoding="utf-8")

        self.assertIn("未確認メールへのリセットメール抑止", release_tasks)
        self.assertIn("ACCOUNT_FORMS.reset_password=accounts.forms.CustomPasswordResetForm", release_tasks)
        self.assertIn("未確認メールへのパスワードリセット送信も抑止", release_tasks)
        self.assertIn("確認済みメールのみ送信", features)

    def test_account_deletion_billing_guard_is_documented(self):
        release_tasks = (self.ROOT / "docs/release/PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")
        features = (self.ROOT / "docs/CURRENT_WEBAPP_FEATURES.md").read_text(encoding="utf-8")
        runbook = (self.ROOT / "docs/runbooks/STRIPE_BILLING_OPERATIONS.md").read_text(encoding="utf-8")

        for content in (release_tasks, features):
            self.assertIn("有効なStripe購読", content)
            self.assertIn("課金管理", content)
            self.assertIn("ブロック", content)
        self.assertIn("Account deletion safety", runbook)
        self.assertIn("active Stripe subscription", runbook)
        self.assertIn("/accounts/billing/", runbook)
        self.assertIn("blocks deletion", runbook)

    def test_stripe_temporary_outage_guard_is_documented(self):
        release_tasks = (self.ROOT / "docs/release/PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")
        runbook = (self.ROOT / "docs/runbooks/STRIPE_BILLING_OPERATIONS.md").read_text(encoding="utf-8")

        self.assertIn("Stripe一時障害時は汎用503", release_tasks)
        self.assertIn("Stripe outage safety", runbook)
        self.assertIn("Checkout and Customer Portal API failures", runbook)
        self.assertIn("Stripe service is temporarily unavailable", runbook)
        self.assertIn("does not expose exception details", runbook)

    def test_public_release_beta_scope_keeps_core_small_and_explicit(self):
        release_tasks = (self.ROOT / "docs/release/PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")

        core_markers = [
            "| ログイン | 必須 |",
            "| グループ | 必須 |",
            "| セッション管理 | 必須 |",
            "参加者管理",
            "| Character sheets | Required |",
            "| 秘匿HO | 必須 |",
            "| 画像アップロード | 必須 |",
            "| 最低限のプレミアム判定 | 条件付き |",
            "Stripe CheckoutはISSUE-077完了まで非表示またはテストモード限定",
        ]
        deferred_markers = [
            "| Google Sheets連携 | 後回し可 |",
            "| Google Calendar同期 | 後回し可 |",
            "| Discord高度通知 | 後回し可 |",
            "| WebSocket通知 | 後回し可 |",
            "| 複雑な自動公開条件 | 後回し可 |",
            "| 高度な統計/年間プレイ時間集計 | 後回し可 |",
        ]

        self.assertIn("## β公開スコープ", release_tasks)
        for marker in core_markers:
            self.assertIn(marker, release_tasks)
        for marker in deferred_markers:
            self.assertIn(marker, release_tasks)

    def test_fixed_session_share_url_pattern_resolves_to_fixed_share_view(self):
        uuid_path = "00000000-0000-0000-0000-000000000001"

        fixed_url = resolve(f"/share/sessions/{uuid_path}/view/")

        self.assertEqual(fixed_url.url_name, "fixed-shared-session-view")

    def test_current_features_documents_fixed_session_share_url(self):
        features = (self.ROOT / "docs/CURRENT_WEBAPP_FEATURES.md").read_text(encoding="utf-8")
        specification = (self.ROOT / "SPECIFICATION.md").read_text(encoding="utf-8")

        for content in (features, specification):
            self.assertIn("/share/sessions/<uuid:share_token>/view/", content)
            self.assertIn("visibility='link'", content)
            self.assertIn("visibility='public'", content)

    def test_handout_attachment_direct_url_guard_is_documented(self):
        release_tasks = (self.ROOT / "docs/release/PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")

        self.assertIn("秘匿HO添付の直URL DELETE", release_tasks)
        self.assertIn("stale or misdirected secret handout notifications", release_tasks)
        self.assertIn("割当外ユーザーへ404で存在秘匿", release_tasks)
        self.assertIn("閲覧可能だが削除権限がない参加者は403", release_tasks)
        self.assertIn("schedules.test_handout_permissions", release_tasks)

    def test_public_release_go_no_go_matrix_covers_final_release_gates(self):
        release_tasks = (self.ROOT / "docs/release/PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")

        required_evidence = [
            "README",
            "Docker",
            "GitHub Actions",
            "production deploy check",
            "schedules.test_handout_permissions",
            "schedules.test_session_visibility",
            "schedules.test_group_links_and_guests.GuestInvitationClaimTestCase.test_guest_claim_requires_invitation_token",
            "scenarios.test_scenarios.ScenarioAPITestCase.test_scenario_public_view_mode_is_readable_without_login",
            "accounts.tests.BasicAccountsTestCase.test_fixed_character_share_view_requires_shareable_scope",
            "accounts.tests.BasicAccountsTestCase.test_access_scope_private_update_closes_fixed_share_view",
            "accounts.test_group_features.GroupMemberCharactersAPITestCase.test_member_characters_only_include_public_scope",
            "accounts.test_billing",
            "SENTRY_DSN",
            "CloudWatch/SNS Runbook",
            "docs/backup.md",
            "AWS_DATABASE_MIGRATION.md",
            "BillingAdminTestCase",
            "tests.unit.test_public_legal_pages",
            "tests.unit.test_billing_legal_pages",
            "billing_preflight --strict",
            "/commercial-disclosure/",
        ]
        external_pending_markers = [
            "Docker daemon",
            "リモート実行は未確認",
            "外部Stripe確認は未完",
            "実SNS購読/通知試験は未完",
            "実RDS復旧リハーサルは未完",
            "実aws-pre目視確認は未完",
            "新規環境での再現確認は未完",
            "正式法務レビュー、運営者実値、問い合わせ先実配送確認は未完",
        ]

        self.assertIn("## β公開 Go/No-Go", release_tasks)
        for marker in required_evidence:
            self.assertIn(marker, release_tasks)
        for marker in external_pending_markers:
            self.assertIn(marker, release_tasks)

    def test_production_go_no_go_template_records_public_release_gates(self):
        template = (self.ROOT / "docs/release/PRODUCTION_GO_NO_GO_RECORD_TEMPLATE.md").read_text(encoding="utf-8")

        required_markers = [
            "## 本番公開ゲート",
            "Google / Discord / X",
            "/terms/",
            "/privacy/",
            "/contact/",
            "/commercial-disclosure/",
            "問い合わせ配送",
            "STRIPE_CHECKOUT_ENABLED=False",
            "実Stripe test-mode event IDs",
            "billing_release_gate",
            "billing-verification-YYYYMMDD.md",
            "Webhook event IDs",
            "CloudWatch Alarmから実SNS購読者へ通知",
            "RPO/RTO",
            "PRODUCTION_SMOKE_TEST_CHECKLIST.md",
        ]

        for marker in required_markers:
            self.assertIn(marker, template)

    def test_production_smoke_checklist_covers_public_release_gates(self):
        checklist = (self.ROOT / "docs/release/PRODUCTION_SMOKE_TEST_CHECKLIST.md").read_text(encoding="utf-8")

        required_markers = [
            "https://tableno.jp/health/live",
            "Google OAuth",
            "Discord OAuth",
            "X OAuth",
            "/terms/",
            "/privacy/",
            "/contact/",
            "/commercial-disclosure/",
            "本番実値で正式レビュー済み",
            "問い合わせ配送",
            "STRIPE_CHECKOUT_ENABLED=False",
            "billing_release_gate --verification-record docs/runbooks/billing-verification-YYYYMMDD.md",
            "実Stripe test-mode event IDs",
            "PRODUCTION_GO_NO_GO_RECORD_TEMPLATE.md",
            "OAuth/SNS/RDS/法務/Stripe",
        ]

        for marker in required_markers:
            self.assertIn(marker, checklist)

    def test_manual_premium_grant_audit_is_documented(self):
        runbook = (self.ROOT / "docs/runbooks/STRIPE_BILLING_OPERATIONS.md").read_text(encoding="utf-8")

        self.assertIn("set_premium_user", runbook)
        self.assertIn("source=manual", runbook)
        self.assertIn("metadata.command=set_premium_user", runbook)

    def test_stripe_billing_runbook_is_not_mojibake(self):
        runbook = (self.ROOT / "docs/runbooks/STRIPE_BILLING_OPERATIONS.md").read_text(encoding="utf-8")

        required_japanese = [
            "\u0053tripe\u8ab2\u91d1\u904b\u7528\u624b\u9806",
            "\u5fc5\u9808\u74b0\u5883\u5909\u6570",
            "\u7279\u5546\u6cd5\u30da\u30fc\u30b8\u3068\u30d7\u30ec\u30df\u30a2\u30e0\u6a5f\u80fd\u30da\u30fc\u30b8\u306b\u8868\u793a\u3059\u308b\u6599\u91d1\u6587\u8a00",
            "\u89e3\u7d04\u65b9\u6cd5",
            "\u8fd4\u91d1\u6761\u4ef6",
            "\u30ed\u30fc\u30ab\u30ebWebhook\u78ba\u8a8d",
            "\u904b\u55b6\u30b3\u30fc\u30c9",
            "\u76e3\u67fb",
        ]
        mojibake_markers = [
            "???",
            "\u7e3a",
            "\u7e5d",
            "\u8b5b",
            "\u96b1",
            "\u8709",
            "\u879f",
            "\u9a55",
            "\u8b07",
        ]

        for phrase in required_japanese:
            self.assertIn(phrase, runbook)

        checked_paths = [
            "docs/runbooks/STRIPE_BILLING_OPERATIONS.md",
            "docs/runbooks/STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md",
            "docs/release/aws-pre-release-record-20260621-billing.md",
            "ISSUES.md",
            "templates/account/billing.html",
            "templates/premium/features.html",
            "tableno/legal_views.py",
            "accounts/admin.py",
            "accounts/management/commands/expire_premium_access.py",
            "accounts/management/commands/reconcile_premium_access.py",
            ".env.development.example",
        ]
        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding="utf-8")
            for marker in mojibake_markers:
                self.assertNotIn(marker, content, f"{relative_path} contains mojibake marker {marker!r}")

    def test_refund_or_dispute_review_audit_is_documented(self):
        runbook = (self.ROOT / "docs/runbooks/STRIPE_BILLING_OPERATIONS.md").read_text(encoding="utf-8")

        self.assertIn("refund_or_dispute_active_records", runbook)
        self.assertIn("action=reviewed", runbook)
        self.assertIn("Premium source", runbook)
        self.assertIn("課金レコードなしの手動付与", runbook)
        self.assertIn("charge_id", runbook)
        self.assertIn("auto_revoked", runbook)
        self.assertIn("access_revoked", runbook)
        self.assertIn("access_restored", runbook)
        self.assertIn("failed_webhook_events", runbook)
        self.assertIn("processing_status=failed", runbook)
        self.assertIn("stale_processing_webhook_events", runbook)
        self.assertIn("stripe_subscription_id", runbook)
        self.assertIn("stripe_price_id", runbook)
        self.assertIn("billing_interval", runbook)
        self.assertIn("cancel_at_period_end", runbook)

    def test_low_cost_manual_jobs_include_premium_expiration(self):
        checked_paths = [
            "docs/DEPLOYMENT_GUIDE.md",
            "docs/AWS_ECS_SETUP_GUIDE.md",
            "docs/runbooks/AWS_INCIDENT_RESPONSE.md",
            "docs/release/AWS_PRE_RELEASE_CHECKLIST.md",
        ]

        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn(
                "expire_premium_access",
                content,
                f"{relative_path} does not document premium expiration maintenance",
            )

        billing_runbook = (self.ROOT / "docs/runbooks/STRIPE_BILLING_OPERATIONS.md").read_text(encoding="utf-8")
        self.assertIn("expire_premium_access --dry-run", billing_runbook)
        self.assertIn(
            "\u30e6\u30fc\u30b6\u30fc\u6a29\u9650\u3084\u76e3\u67fb\u30ed\u30b0\u3092\u5909\u66f4\u3057\u307e\u305b\u3093",
            billing_runbook,
        )

    def test_issue_077_tracks_stripe_external_verification_scope(self):
        issues = (self.ROOT / "ISSUES.md").read_text(encoding="utf-8")

        self.assertIn("ISSUE-077: Stripe billing aws-pre verification before paid feature exposure", issues)
        self.assertIn("231 tests passed", issues)
        self.assertIn("tests.unit.test_local_settings", issues)
        self.assertIn("billing_development_check", issues)
        self.assertIn("billing_development_check --require-stripe", issues)
        self.assertIn("STRIPE_CHECKOUT_ENABLED", issues)
        self.assertIn("stripe_checkout_enabled", issues)
        self.assertIn("480 JPY monthly and 4,800 JPY yearly test plan", issues)
        self.assertIn("real Stripe test keys and Price IDs remain intentionally blank", issues)
        self.assertIn("live keys are rejected outside production", issues)
        self.assertIn("livemode: true", issues)
        self.assertIn("billing_stripe_remote_check --require-recent-events --recent-hours 72", issues)
        self.assertIn("real test-mode Stripe event IDs", issues)
        self.assertIn("docs/runbooks/billing-verification-YYYYMMDD.md", issues)

    def test_mcp_stripe_verification_record_keeps_issue_077_open(self):
        record = (self.ROOT / "docs" / "runbooks" / "billing-verification-mcp-20260622.md").read_text(encoding="utf-8")
        issues = (self.ROOT / "ISSUES.md").read_text(encoding="utf-8")
        release_record = (self.ROOT / "docs" / "release" / "aws-pre-release-record-20260621-billing.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("acct_1TkMqJHdY1p3WlN0", record)
        self.assertIn("prod_UkNyUXGrQIln9L", record)
        self.assertIn("prod_UkFVj0t5DW9v69", record)
        self.assertIn("prod_Uk2J3frLwl4lCk", record)
        self.assertIn("No Prices found", record)
        self.assertIn("livemode=false` proof | Missing", record)
        self.assertIn("does not satisfy ISSUE-077", record)
        self.assertIn("follow-up read-only check", record)
        self.assertIn("post-commit read-only check", record)
        self.assertIn("default_price=null", record)
        self.assertIn("Product/Price creation | Not performed", record)
        self.assertIn("billing-verification-mcp-20260622.md", issues)
        self.assertIn("no `livemode=false` proof", issues)
        self.assertIn("not acceptance evidence", release_record)

    def test_aws_pre_checklist_includes_billing_release_gate(self):
        checklist = (self.ROOT / "docs" / "release" / "AWS_PRE_RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

        self.assertIn("Billing release gate", checklist)
        self.assertIn("BILLING_READINESS_MATRIX_2026-06-22.md", checklist)
        self.assertIn("python manage.py billing_status_report --json", checklist)
        self.assertIn("stripe_checkout_enabled", checklist)
        self.assertIn("Keep it `false` until ISSUE-077 is complete", checklist)
        self.assertIn("python manage.py billing_preflight --strict", checklist)
        self.assertIn(
            "python manage.py billing_stripe_remote_check --require-recent-events --recent-hours 72", checklist
        )
        self.assertIn(
            "python manage.py billing_verification_record --environment aws-pre --stripe-mode test", checklist
        )
        self.assertIn("python manage.py billing_release_gate --verification-record", checklist)
        self.assertIn("real Stripe test-mode event IDs", checklist)

    def test_billing_readiness_matrix_maps_goal_to_evidence(self):
        matrix = (self.ROOT / "docs" / "release" / "BILLING_READINESS_MATRIX_2026-06-22.md").read_text(encoding="utf-8")
        release_record = (self.ROOT / "docs" / "release" / "aws-pre-release-record-20260621-billing.md").read_text(
            encoding="utf-8"
        )
        issues = (self.ROOT / "ISSUES.md").read_text(encoding="utf-8")

        required_items = [
            "Commercial disclosure and pricing pages",
            "Monthly and yearly premium pricing",
            "Local development billing configuration",
            "Stripe Checkout subscription flow",
            "Customer Portal for cancellation",
            "Stripe Webhook signature verification and idempotency",
            "`checkout.session.completed` subscription linkage",
            "`customer.subscription.created/updated/deleted` premium sync",
            "Payment failure and recovery handling",
            "Code-granted premium expiration policy",
            "Automatic expiration batch for time-limited code grants",
            "Admin visibility for Stripe IDs",
            "Refund and dispute handling policy",
            "Premium feature comparison page",
            "Premium access code management",
            "Audit logs for premium grant/revoke/recovery/payment/refund/dispute/admin actor",
            "Test-mode operating runbook",
        ]
        for item in required_items:
            self.assertIn(item, matrix)

        self.assertIn("ISSUE-077 remains open", matrix)
        self.assertIn("STRIPE_CHECKOUT_ENABLED=False", matrix)
        self.assertIn("billing_release_gate", matrix)
        self.assertIn("billing-verification-local-20260622.md", matrix)
        self.assertIn("billing-verification-mcp-20260622.md", matrix)
        self.assertIn("billing_development_check", matrix)
        self.assertIn("setup_billing_local --include-admin", matrix)
        self.assertIn("tests.unit.test_local_settings", matrix)
        self.assertIn("BILLING_READINESS_MATRIX_2026-06-22.md", release_record)
        self.assertIn("BILLING_READINESS_MATRIX_2026-06-22.md", issues)
        self.assertIn("billing_release_gate", issues)
        public_tasks = (self.ROOT / "docs" / "release" / "PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")
        self.assertIn("CI billing_release_gate runs with STRIPE_CHECKOUT_ENABLED=False", public_tasks)

    def test_public_release_tasks_documents_monitoring_and_backup_evidence(self):
        checklist = (self.ROOT / "docs" / "release" / "PUBLIC_RELEASE_TASKS.md").read_text(encoding="utf-8")
        backup_runbook = (self.ROOT / "docs" / "backup.md").read_text(encoding="utf-8")
        incident_runbook = (self.ROOT / "docs" / "runbooks" / "AWS_INCIDENT_RESPONSE.md").read_text(encoding="utf-8")
        migration_runbook = (self.ROOT / "docs" / "runbooks" / "AWS_DATABASE_MIGRATION.md").read_text(encoding="utf-8")
        production_settings = (self.ROOT / "tableno" / "settings_production.py").read_text(encoding="utf-8")

        self.assertIn("SENTRY_DSN", checklist)
        self.assertIn("CloudWatch/SNS Runbook", checklist)
        self.assertIn("実SNS購読/通知試験は未完", checklist)
        self.assertIn("docs/backup.md", checklist)
        self.assertIn("AWS_DATABASE_MIGRATION.md", checklist)
        self.assertIn("実RDS復旧リハーサルは未完", checklist)
        self.assertIn("SENTRY_DSN", production_settings)
        self.assertIn("send_default_pii=False", production_settings)
        self.assertIn("RDS自動バックアップ有効化", backup_runbook)
        self.assertIn("手動スナップショットからの復元", backup_runbook)
        self.assertIn("Alarm notification", incident_runbook)
        self.assertIn("Restore", incident_runbook)
        self.assertIn("Backup and restore drill", migration_runbook)

    def test_local_billing_verification_record_is_documented(self):
        record = (self.ROOT / "docs" / "runbooks" / "billing-verification-local-20260622.md").read_text(
            encoding="utf-8"
        )
        release_record = (self.ROOT / "docs" / "release" / "aws-pre-release-record-20260621-billing.md").read_text(
            encoding="utf-8"
        )
        issues = (self.ROOT / "ISSUES.md").read_text(encoding="utf-8")

        self.assertIn("Stripe\u8ab2\u91d1\u78ba\u8a8d\u8a18\u9332", record)
        self.assertIn("| \u74b0\u5883 | local |", record)
        self.assertIn("| Stripe mode | test |", record)
        self.assertIn("| Expected monthly unit amount | 480 |", record)
        self.assertIn("| Expected yearly unit amount | 4800 |", record)
        self.assertIn("| Stripe Checkout enabled | yes |", record)
        self.assertIn("billing_webhook_smoke=ok", record)
        self.assertIn("stripe_checkout_enabled=true", record)
        self.assertIn("remote check not run or produced no output", record)
        self.assertIn("billing-verification-local-20260622.md", release_record)
        self.assertIn("does not satisfy ISSUE-077", release_record)
        self.assertIn("billing-verification-local-20260622.md", issues)

    def test_billing_release_record_documents_premium_expiration(self):
        record = (self.ROOT / "docs" / "release" / "aws-pre-release-record-20260621-billing.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Local development billing configuration", record)
        self.assertIn("billing_development_check", record)
        self.assertIn("setup_billing_local --include-admin", record)
        self.assertIn("Stripe Checkout exposure switch", record)
        self.assertIn("STRIPE_CHECKOUT_ENABLED", record)
        self.assertIn("billing_status_report", record)
        self.assertIn("stripe_checkout_enabled", record)
        self.assertIn(".env.development", record)
        self.assertIn("Premium access expiration", record)
        self.assertIn("expire_premium_access", record)
        self.assertIn("schedules.tasks.expire_premium_access", record)
        self.assertIn("manual overrides are preserved", record)
        self.assertIn("tests.unit.test_local_settings", record)
        self.assertIn("231 tests passed", record)
        self.assertIn("ISSUE-077 Stripe external verification scope", record)
        self.assertIn("livemode: false", record)
        self.assertIn("Tableno Premium", record)
        self.assertIn("JPY 480 monthly", record)
        self.assertIn("JPY 4,800 yearly", record)
        self.assertIn("sk_test_", record)
        self.assertIn("billing_stripe_remote_check --require-recent-events --recent-hours 72", record)
        self.assertIn("customer.subscription.updated` with `cancel_at_period_end=true", record)
        self.assertIn("charge.dispute.closed", record)
        self.assertIn("StripeWebhookEvent", record)
        self.assertIn("Premium audit logs", record)
