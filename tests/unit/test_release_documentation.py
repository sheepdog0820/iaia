from pathlib import Path

from django.test import SimpleTestCase


class ReleaseDocumentationTestCase(SimpleTestCase):
    ROOT = Path(__file__).resolve().parents[2]
    SECRET_PATTERNS = [
        'arkham' + '_admin_2024',
        'admin / ' + 'arkham' + '_admin_2024',
        'azathoth_gm / ' + 'arkham' + '2024',
        'Password: ' + 'arkham' + '_admin_2024',
        'パスワード: ' + 'arkham' + '_admin_2024',
    ]

    def test_readme_does_not_publish_test_account_passwords(self):
        content = (self.ROOT / 'README.md').read_text(encoding='utf-8')

        for value in self.SECRET_PATTERNS:
            self.assertNotIn(value, content)

        self.assertIn('### テストアカウント', content)
        self.assertIn('ローカル環境で作成してください。', content)
        self.assertIn('python create_admin.py', content)

    def test_release_documents_do_not_publish_fixed_admin_password(self):
        checked_paths = [
            'AGENTS.md',
            'CLAUDE.md',
            'SPECIFICATION.md',
            'SESSION_TEST_DATA_SPECIFICATION.md',
            'TEST_DATA_MANAGEMENT.md',
            'TEST_DATA_README.md',
            'accounts/views/dev_login_view.py',
            'create_admin.py',
            'schedules/management/commands/create_session_test_data.py',
            'schedules/management/commands/reset_dev_session_data.py',
            'server.sh',
            'templates/accounts/dev_login.html',
        ]

        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding='utf-8')
            for value in self.SECRET_PATTERNS:
                self.assertNotIn(value, content, f'{relative_path} publishes {value!r}')

    def test_django_version_is_documented_as_52_series(self):
        readme = (self.ROOT / 'README.md').read_text(encoding='utf-8')
        requirements = (self.ROOT / 'requirements.txt').read_text(encoding='utf-8')

        self.assertIn('Django 5.2', readme)
        self.assertIn('Django>=5.2.0,<5.3', requirements)
        self.assertNotIn('Django ' + '4.2+', readme)
        self.assertNotIn('Django>=' + '4.2.0,<5.0', requirements)

    def test_stripe_billing_verification_record_template_exists(self):
        template = (
            self.ROOT
            / 'docs'
            / 'runbooks'
            / 'STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md'
        ).read_text(encoding='utf-8')
        pre_release_record = (
            self.ROOT
            / 'docs'
            / 'release'
            / 'AWS_PRE_RELEASE_RECORD_TEMPLATE.md'
        ).read_text(encoding='utf-8')

        self.assertIn('Stripe課金確認記録テンプレート', template)
        self.assertIn('checkout.session.completed', template)
        self.assertIn('invoice.payment_failed', template)
        self.assertIn('invoice.payment_succeeded', template)
        self.assertIn('charge.refunded', template)
        self.assertIn('charge.dispute.created', template)
        self.assertIn('charge.dispute.closed', template)
        self.assertIn('Monthly Price ID', template)
        self.assertIn('Yearly Price ID', template)
        self.assertIn('billing_intervals', template)
        self.assertIn('stripe_price_id', template)
        self.assertIn('billing_interval', template)
        self.assertIn('last_webhook_event_id', template)
        self.assertIn('last_webhook_processed_at', template)
        self.assertIn('failed_webhook_events=0', template)
        self.assertIn('stale_processing_webhook_events=0', template)
        self.assertIn('promo_expiring_soon_records', template)
        self.assertIn('--require-recent-events', template)
        self.assertIn('Secrets、実カード情報、顧客の個人情報', template)
        self.assertIn('STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md', pre_release_record)

    def test_stripe_cli_webhook_runbook_documents_trigger_commands(self):
        runbook = (
            self.ROOT
            / 'docs'
            / 'runbooks'
            / 'STRIPE_BILLING_OPERATIONS.md'
        ).read_text(encoding='utf-8')
        template = (
            self.ROOT
            / 'docs'
            / 'runbooks'
            / 'STRIPE_BILLING_VERIFICATION_RECORD_TEMPLATE.md'
        ).read_text(encoding='utf-8')
        trigger_commands = [
            'stripe trigger checkout.session.completed',
            'stripe trigger customer.subscription.created',
            'stripe trigger customer.subscription.updated',
            'stripe trigger customer.subscription.deleted',
            'stripe trigger invoice.payment_failed',
            'stripe trigger invoice.payment_succeeded',
            'stripe trigger charge.refunded',
            'stripe trigger charge.dispute.created',
            'stripe trigger charge.dispute.closed',
        ]

        self.assertIn('stripe listen --forward-to http://127.0.0.1:8000/api/billing/webhook/', runbook)
        self.assertIn('Set-Location C:\\Users\\endke\\Workspace\\iaia', runbook)
        self.assertIn('python manage.py runserver 127.0.0.1:8000', runbook)
        self.assertIn('C:\\WINDOWS\\system32', runbook)
        self.assertIn('STRIPE_WEBHOOK_SECRET', runbook)
        self.assertNotIn('PREMIUM_PRICE_LABEL`r', runbook)
        self.assertIn('fixtureイベント', runbook)
        self.assertIn('実Checkout/Stripe Dashboard操作', template)
        for command in trigger_commands:
            self.assertIn(command, runbook)
            self.assertIn(command, template)

    def test_billing_legal_environment_variables_are_documented(self):
        required_keys = [
            'STRIPE_REVOKE_ON_REFUND_OR_DISPUTE',
            'STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID',
            'EMAIL_BACKEND',
            'DEFAULT_FROM_EMAIL',
            'PREMIUM_PRICE_LABEL',
            'PREMIUM_MONTHLY_PRICE_LABEL',
            'PREMIUM_MONTHLY_PRICE_DESCRIPTION',
            'PREMIUM_YEARLY_PRICE_LABEL',
            'PREMIUM_YEARLY_PRICE_DESCRIPTION',
            'LEGAL_PAYMENT_METHOD',
            'LEGAL_PAYMENT_TIMING',
            'LEGAL_SERVICE_DELIVERY_TIMING',
            'LEGAL_CANCELLATION_METHOD',
            'LEGAL_CANCELLATION_EFFECT',
            'LEGAL_REFUND_POLICY',
            'LEGAL_SELLER_NAME',
            'LEGAL_SELLER_ADDRESS',
            'LEGAL_SELLER_PHONE',
            'CONTACT_EMAIL',
        ]
        checked_paths = [
            'docs/DEPLOYMENT_GUIDE.md',
            'docs/release/AWS_PRE_RELEASE_CHECKLIST.md',
            'docs/runbooks/STRIPE_BILLING_OPERATIONS.md',
        ]

        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding='utf-8')
            for key in required_keys:
                self.assertIn(key, content, f'{relative_path} does not document {key}')

    def test_env_example_documents_billing_settings_one_key_per_line(self):
        env_example = (self.ROOT / '.env.example').read_text(encoding='utf-8')
        required_keys = [
            'STRIPE_SECRET_KEY',
            'STRIPE_WEBHOOK_SECRET',
            'STRIPE_PREMIUM_PRICE_ID',
            'STRIPE_PREMIUM_YEARLY_PRICE_ID',
            'STRIPE_PUBLISHABLE_KEY',
            'STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID',
            'STRIPE_REVOKE_ON_REFUND_OR_DISPUTE',
            'PREMIUM_PRICE_LABEL',
            'PREMIUM_MONTHLY_PRICE_LABEL',
            'PREMIUM_MONTHLY_PRICE_DESCRIPTION',
            'PREMIUM_YEARLY_PRICE_LABEL',
            'PREMIUM_YEARLY_PRICE_DESCRIPTION',
            'LEGAL_PAYMENT_METHOD',
            'LEGAL_PAYMENT_TIMING',
            'LEGAL_SERVICE_DELIVERY_TIMING',
            'LEGAL_CANCELLATION_METHOD',
            'LEGAL_CANCELLATION_EFFECT',
            'LEGAL_REFUND_POLICY',
            'LEGAL_SELLER_NAME',
            'LEGAL_SELLER_ADDRESS',
            'LEGAL_SELLER_PHONE',
            'PUBLIC_SITE_URL',
            'CONTACT_EMAIL',
            'DEFAULT_FROM_EMAIL',
        ]
        lines = env_example.splitlines()

        for key in required_keys:
            matching_lines = [line for line in lines if line.startswith(f'{key}=')]
            self.assertEqual(
                len(matching_lines),
                1,
                f'.env.example must contain exactly one {key}= line',
            )
            self.assertNotIn('LEGAL_', matching_lines[0].split('=', 1)[1])
            self.assertNotIn('STRIPE_', matching_lines[0].split('=', 1)[1])

    def test_stripe_key_mode_is_documented(self):
        checked_paths = [
            'docs/DEPLOYMENT_GUIDE.md',
            'docs/runbooks/STRIPE_BILLING_OPERATIONS.md',
        ]

        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding='utf-8')
            self.assertIn('sk_live_', content, f'{relative_path} does not document live Stripe keys')
            self.assertIn('sk_test_', content, f'{relative_path} does not document test Stripe keys')

        runbook = (self.ROOT / 'docs/runbooks/STRIPE_BILLING_OPERATIONS.md').read_text(encoding='utf-8')
        self.assertIn('livemode', runbook)
        self.assertIn('Customer Portal', runbook)
        self.assertIn('支払い方法更新', runbook)
        self.assertIn('サブスクリプション解約', runbook)
        self.assertIn('請求履歴', runbook)
        self.assertIn('recent_event_ids', runbook)
        self.assertIn('recent_cancel_at_period_end_event_ids', runbook)
        self.assertIn('STRIPE_PREMIUM_YEARLY_PRICE_ID', runbook)
        self.assertIn('year', runbook)
        self.assertIn('billing_intervals', runbook)

    def test_manual_premium_grant_audit_is_documented(self):
        runbook = (self.ROOT / 'docs/runbooks/STRIPE_BILLING_OPERATIONS.md').read_text(encoding='utf-8')

        self.assertIn('set_premium_user', runbook)
        self.assertIn('source=manual', runbook)
        self.assertIn('metadata.command=set_premium_user', runbook)

    def test_refund_or_dispute_review_audit_is_documented(self):
        runbook = (self.ROOT / 'docs/runbooks/STRIPE_BILLING_OPERATIONS.md').read_text(encoding='utf-8')

        self.assertIn('refund_or_dispute_active_records', runbook)
        self.assertIn('action=reviewed', runbook)
        self.assertIn('Premium source', runbook)
        self.assertIn('課金レコードなしの手動付与', runbook)
        self.assertIn('charge_id', runbook)
        self.assertIn('auto_revoked', runbook)
        self.assertIn('access_revoked', runbook)
        self.assertIn('access_restored', runbook)
        self.assertIn('failed_webhook_events', runbook)
        self.assertIn('processing_status=failed', runbook)
        self.assertIn('stale_processing_webhook_events', runbook)
        self.assertIn('stripe_subscription_id', runbook)
        self.assertIn('stripe_price_id', runbook)
        self.assertIn('billing_interval', runbook)
        self.assertIn('cancel_at_period_end', runbook)

    def test_low_cost_manual_jobs_include_premium_expiration(self):
        checked_paths = [
            'docs/DEPLOYMENT_GUIDE.md',
            'docs/AWS_ECS_SETUP_GUIDE.md',
            'docs/runbooks/AWS_INCIDENT_RESPONSE.md',
            'docs/release/AWS_PRE_RELEASE_CHECKLIST.md',
        ]

        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding='utf-8')
            self.assertIn(
                'expire_premium_access',
                content,
                f'{relative_path} does not document premium expiration maintenance',
            )
