from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command, CommandError
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone

from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS


class Command(BaseCommand):
    help = 'Stripe課金の運用確認記録をMarkdownで生成します。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            help='生成した確認記録を書き出すファイルパス。未指定時は標準出力します。',
        )
        parser.add_argument(
            '--environment',
            default=getattr(settings, 'APP_ENV', 'local'),
            help='記録に残す確認環境名。例: local / aws-pre / aws-prod',
        )
        parser.add_argument(
            '--stripe-mode',
            default='test',
            choices=('test', 'live'),
            help='記録に残すStripe mode。',
        )
        parser.add_argument(
            '--confirmed-by',
            default='',
            help='確認者名。',
        )
        parser.add_argument(
            '--base-url',
            default='',
            help='確認対象のbase URL。未指定時はPUBLIC_SITE_URLを使います。',
        )
        parser.add_argument(
            '--commit',
            default='',
            help='確認対象のリリース名またはcommit。',
        )
        parser.add_argument(
            '--strict-preflight',
            action='store_true',
            help='billing_preflightを--strict付きで実行します。',
        )
        parser.add_argument(
            '--run-smoke',
            action='store_true',
            help='billing_webhook_smokeを実行して状態遷移結果を記録します。',
        )
        parser.add_argument(
            '--run-remote-check',
            action='store_true',
            help='billing_stripe_remote_checkを実行してStripe API側の設定確認結果を記録します。',
        )
        parser.add_argument(
            '--remote-skip-webhook',
            action='store_true',
            help='billing_stripe_remote_check実行時にWebhook endpoint確認を省略します。',
        )
        parser.add_argument(
            '--remote-skip-portal',
            action='store_true',
            help='billing_stripe_remote_check実行時にCustomer Portal確認を省略します。',
        )
        parser.add_argument(
            '--remote-require-recent-events',
            action='store_true',
            help='billing_stripe_remote_check実行時にStripe Events APIの直近実イベント確認も要求します。',
        )
        parser.add_argument(
            '--remote-recent-hours',
            type=int,
            default=72,
            help='--remote-require-recent-eventsで確認する直近イベントの時間幅です。',
        )
        parser.add_argument(
            '--skip-command-checks',
            action='store_true',
            help='Django checkと課金確認コマンドを実行せず、未実行として記録します。',
        )

    def handle(self, *args, **options):
        record = self._build_record(options)
        output = options.get('output')
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(record, encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'billing_verification_record={output_path}'))
            return
        self.stdout.write(record)

    def _build_record(self, options):
        base_url = (options['base_url'] or getattr(settings, 'PUBLIC_SITE_URL', '')).rstrip('/')
        webhook_url = f'{base_url}{reverse("billing-webhook")}' if base_url else reverse('billing-webhook')
        price_id = getattr(settings, 'STRIPE_PREMIUM_PRICE_ID', '')
        yearly_price_id = getattr(settings, 'STRIPE_PREMIUM_YEARLY_PRICE_ID', '')
        checkout_enabled = bool(getattr(settings, 'STRIPE_CHECKOUT_ENABLED', True))
        publishable_key_configured = bool(getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''))
        portal_configuration_id = getattr(
            settings,
            'STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID',
            '',
        )
        expected_currency = getattr(settings, 'STRIPE_PREMIUM_EXPECTED_CURRENCY', '')
        expected_monthly_amount = getattr(
            settings,
            'STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT',
            '',
        )
        expected_yearly_amount = getattr(
            settings,
            'STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT',
            '',
        )
        results = self._collect_command_results(options)

        lines = [
            '# Stripe課金確認記録',
            '',
            'Secrets、実カード情報、顧客の個人情報、Webhook signing secretは記載しない。',
            '',
            '## 基本情報',
            '',
            '| 項目 | 値 |',
            '| --- | --- |',
            f'| 確認日 | {timezone.localtime().strftime("%Y-%m-%d %H:%M:%S %Z")} |',
            f'| 確認者 | {options["confirmed_by"] or "未記入"} |',
            f'| 環境 | {options["environment"]} |',
            f'| base URL | {base_url or "未設定"} |',
            f'| Stripe mode | {options["stripe_mode"]} |',
            f'| Monthly Price ID | {price_id or "未設定"} |',
            f'| Yearly Price ID | {yearly_price_id or "未設定"} |',
            f'| Expected Stripe Price currency | {expected_currency or "未設定"} |',
            f'| Expected monthly unit amount | {expected_monthly_amount or "未設定"} |',
            f'| Expected yearly unit amount | {expected_yearly_amount or "未設定"} |',
            f'| Stripe Checkout enabled | {"yes" if checkout_enabled else "no"} |',
            f'| Stripe publishable key configured | {"yes" if publishable_key_configured else "no"} |',
            f'| Customer Portal configuration ID | {portal_configuration_id or "未設定"} |',
            f'| Webhook endpoint URL | {webhook_url} |',
            f'| リリース/commit | {options["commit"] or "未記入"} |',
            '',
            '## 事前チェック',
            '',
            '| 確認項目 | コマンドまたは確認先 | 結果 | メモ |',
            '| --- | --- | --- | --- |',
            self._result_row('Django check', 'python manage.py check', results['check']),
            self._result_row(
                '課金preflight',
                'python manage.py billing_preflight --strict'
                if options['strict_preflight']
                else 'python manage.py billing_preflight',
                results['preflight'],
            ),
            self._result_row(
                'Billing status report',
                'python manage.py billing_status_report',
                results['status_report'],
                memo='Check billing_intervals for month/year/blank counts.',
            ),
            self._result_row(
                'Stripe remote check',
                self._remote_check_command_label(options, webhook_url),
                results['remote'],
            ),
            self._result_row(
                'ローカル状態遷移スモーク',
                'python manage.py billing_webhook_smoke',
                results['smoke'],
            ),
            '| 特商法ページ | /commercial-disclosure/ | 要画面確認 | 料金、解約、返金、提供時期、事業者情報 |',
            '| プレミアム機能ページ | /premium/ | 要画面確認 | 無料/有料差分 |',
            '| 課金管理ページ | /accounts/billing/ | 要画面確認 | 加入、管理、コード適用導線 |',
            '',
            '## Stripe recent event IDs',
            '',
            '```text',
            self._recent_event_id_block(results['remote']),
            '```',
            '',
            '## Stripe Webhook確認',
            '',
            '| イベント | 期待結果 | 結果 | アプリ側確認 |',
            '| --- | --- | --- | --- |',
        ]
        lines.extend(self._webhook_rows())
        lines.extend([
            '| 同一event ID再送 | duplicateとして2xx応答し、処理本体は二重実行されない | 要確認 | StripeWebhookEvent、監査ログ |',
            '',
            '## 運営コード確認',
            '',
            '| 確認項目 | 期待結果 | 結果 | メモ |',
            '| --- | --- | --- | --- |',
            '| コード発行 | issue_premium_code --campaignでキャンペーン名付きコードを発行できる | 要確認 |  |',
            '| 一括発行CSV | --count と --output-csv でキャンペーン名を含むCSV出力ができる | 要確認 |  |',
            '| コード適用 | /accounts/billing/ で入力するとプレミアム化 | 要確認 |  |',
            '| 期限付きコード | premium_expires_atに期限が入り、期限切れ後に失効 | 要確認 |  |',
            '| 自動失効 | Celery beatまたはexpire_premium_accessで失効 | 要確認 | billing_status_reportのexpired_promo_recordsを確認 |',
            '| 無期限コード | expires_atなしのコードは明示停止まで有効 | 要確認 | billing_status_reportのpromo_indefinite_recordsを確認 |',
            '| 期限付き有効コード | 期限前のコード由来プレミアムを把握できる | 要確認 | billing_status_reportのpromo_expiring_active_recordsを確認 |',
            '| 7日以内に失効するコード | 直近で失効するコード由来プレミアムを把握できる | 要確認 | billing_status_reportのpromo_expiring_soon_recordsを確認 |',
            '| キャンペーン別コード内訳 | キャンペーン別のコード由来プレミアムを把握できる | 要確認 | billing_status_reportのpromo_campaignsを確認 |',
            '| 解約予定 | 解約予定ユーザーを把握でき、期間終了までは有効 | 要確認 | billing_status_reportのcancel_at_period_end_recordsを確認 |',
            '| 管理画面CSV | キャンペーン名と利用状況CSVを出力でき、raw codeは含まない | 要確認 |  |',
            '',
            '## 管理画面・監査ログ',
            '',
            '| 確認項目 | 期待結果 | 結果 | メモ |',
            '| --- | --- | --- | --- |',
            '| ユーザー詳細 | 課金レコード、コード利用履歴、監査ログが見える | 要確認 |  |',
            '| Premium subscriptions | Stripe IDs, Price ID, billing interval, status, period end, revoke reason, and refund/dispute review state are visible | Needs confirmation | stripe_price_id / billing_interval |',
            '| 手動付与保持 | 最新の手動ログがsource=manual/action=grantedのユーザーは自動失効やWebhook失効後も権限が保持される | 要確認 |  |',
            '| 手動付与レポート | billing_status_reportのmanual_override_users / manual_override_without_subscriptionで手動付与ユーザーを把握できる | 要確認 |  |',
            '| 管理画面復旧 | 失効状態解除アクションで管理者確認後に権限を復旧でき、actorが監査ログに残る | 要確認 |  |',
            '| 返金/チャージバック手動確認 | 自動停止しない設定ではbilling_status_reportのrefund_or_dispute_active_recordsで把握できる | 要確認 |  |',
            '| Premium access codes | 使用回数、期限、停止状態、利用者が見える | 要確認 |  |',
            '| Premium audit logs | Grant, restore, revoke, payment failure/recovery, refund, dispute, and admin actor history are visible | Needs confirmation | Stripe subscription metadata includes stripe_price_id / billing_interval |',
            '',
            '## 判定',
            '',
            '| 項目 | 値 |',
            '| --- | --- |',
            '| 判定 | Go / No-Go / 条件付きGo |',
            '| 残課題 |  |',
            '| 次の対応 |  |',
            '',
        ])
        return '\n'.join(lines)

    def _collect_command_results(self, options):
        if options['skip_command_checks']:
            skipped = {'status': '未実行', 'summary': 'skip-command-checks指定'}
            return {
                'check': skipped,
                'preflight': skipped,
                'status_report': skipped,
                'remote': skipped,
                'smoke': skipped,
            }

        results = {
            'check': self._run_command('check'),
            'preflight': self._run_command(
                'billing_preflight',
                *(['--strict'] if options['strict_preflight'] else []),
            ),
            'status_report': self._run_command('billing_status_report'),
        }
        if options['run_remote_check']:
            results['remote'] = self._run_command(
                'billing_stripe_remote_check',
                *self._remote_check_args(options),
            )
        else:
            results['remote'] = {
                'status': '未実行',
                'summary': '必要に応じて--run-remote-checkを指定',
            }
        if options['run_smoke']:
            results['smoke'] = self._run_command('billing_webhook_smoke')
        else:
            results['smoke'] = {'status': '未実行', 'summary': '必要に応じて--run-smokeを指定'}
        return results

    def _run_command(self, command_name, *args):
        stdout = StringIO()
        try:
            call_command(command_name, *args, stdout=stdout)
        except CommandError as exc:
            return {'status': 'NG', 'summary': str(exc)}
        except Exception as exc:
            return {'status': 'NG', 'summary': f'{exc.__class__.__name__}: {exc}'}

        output = stdout.getvalue().strip()
        if command_name == 'billing_preflight' and 'billing_preflight=warnings' in output:
            return {'status': 'WARN', 'summary': self._last_line(output), 'output': output}
        if command_name == 'billing_status_report':
            return {
                'status': 'OK',
                'summary': self._billing_status_summary(output),
                'output': output,
            }
        return {'status': 'OK', 'summary': self._last_line(output), 'output': output}

    def _result_row(self, label, command, result, memo=''):
        detail = result["summary"]
        if memo:
            detail = f'{detail}; {memo}' if detail else memo
        return f'| {label} | `{command}` | {result["status"]} | {detail} |'

    def _remote_check_args(self, options):
        args = []
        if options.get('remote_skip_webhook'):
            args.append('--skip-webhook')
        if options.get('remote_skip_portal'):
            args.append('--skip-portal')
        if options.get('remote_require_recent_events'):
            args.extend(['--require-recent-events', '--recent-hours', str(options['remote_recent_hours'])])
        base_url = (options.get('base_url') or '').rstrip('/')
        if base_url and not options.get('remote_skip_webhook'):
            args.extend(['--webhook-url', f'{base_url}{reverse("billing-webhook")}'])
        return args

    def _remote_check_command_label(self, options, webhook_url):
        parts = ['python manage.py billing_stripe_remote_check']
        if options.get('remote_skip_webhook'):
            parts.append('--skip-webhook')
        if options.get('remote_skip_portal'):
            parts.append('--skip-portal')
        if options.get('remote_require_recent_events'):
            parts.extend(['--require-recent-events', '--recent-hours', str(options['remote_recent_hours'])])
        base_url = (options.get('base_url') or '').rstrip('/')
        if base_url and not options.get('remote_skip_webhook'):
            parts.extend(['--webhook-url', webhook_url])
        return ' '.join(parts)

    def _webhook_rows(self):
        expectations = {
            'checkout.session.completed': 'customer/subscriptionがユーザー課金レコードへ紐付く',
            'customer.subscription.created': 'active/trialingならis_premium=True',
            'customer.subscription.updated': '解約予定、active、unpaidの状態が同期される',
            'customer.subscription.deleted': 'canceledとして権限失効',
            'invoice.payment_failed': '支払い失敗日時を保存し、画面とメールでカード更新を案内',
            'invoice.payment_succeeded': '支払い失敗日時を解除し、画面のカード更新案内を消す',
            'charge.refunded': '監査ログを残し、設定に応じて権限停止。自動停止後はactive更新だけで復旧しない',
            'charge.dispute.created': '監査ログを残し、設定に応じて権限停止。自動停止後はactive更新だけで復旧しない',
            'charge.dispute.closed': (
                'status=lost/warning_closedは権限停止、'
                'status=wonはチャージバック由来の自動停止を復旧'
            ),
        }
        return [
            f'| `{event_name}` | {expectations[event_name]} | 要Stripe確認 | StripeWebhookEvent / PremiumSubscription / Premium audit logs |'
            for event_name in REQUIRED_WEBHOOK_EVENTS
        ]

    def _last_line(self, output):
        if not output:
            return ''
        return output.splitlines()[-1][:200]

    def _billing_status_summary(self, output):
        keys = {
            'stripe_checkout_enabled',
            'expected_stripe_price_currency',
            'expected_monthly_unit_amount',
            'expected_yearly_unit_amount',
            'last_webhook_event_id',
            'last_webhook_event_type',
            'last_webhook_processed_at',
            'failed_webhook_events',
            'stale_processing_webhook_events',
            'last_failed_webhook_event_id',
            'last_stale_processing_webhook_event_id',
        }
        values = [
            line
            for line in output.splitlines()
            if line.split('=', 1)[0] in keys
        ]
        return ', '.join(values)[:500] if values else self._last_line(output)

    def _recent_event_id_block(self, result):
        output = result.get('output', '')
        if not output:
            return 'remote check not run or produced no output'

        lines = output.splitlines()
        try:
            start = lines.index('recent_event_ids:')
        except ValueError:
            return 'recent event ID output not available'

        collected = []
        for line in lines[start:]:
            if line == 'billing_stripe_remote_check=ok':
                break
            if line.startswith('OK stripe recent operational events'):
                break
            collected.append(line)
        return '\n'.join(collected) if collected else 'recent event ID output not available'
