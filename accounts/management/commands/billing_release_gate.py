from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS


BLOCKING_RECORD_MARKERS = (
    'does not satisfy ISSUE-077',
    'not ISSUE-077 acceptance evidence',
    'remote check not run or produced no output',
    'Product/Price creation | Not performed',
    'livemode=false` proof | Missing',
    'No Prices found',
    'Missing',
    'Not run',
    'Needs confirmation',
    'not run',
    '未実行',
    '未確認',
    '要Stripe確認',
    '要確認',
)


class Command(BaseCommand):
    help = (
        'Fail the release when paid Stripe Checkout is exposed without a final '
        'external billing verification record.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--verification-record',
            default='',
            help='Final aws-pre billing verification record path.',
        )

    def handle(self, *args, **options):
        checkout_enabled = bool(getattr(settings, 'STRIPE_CHECKOUT_ENABLED', True))
        self.stdout.write(
            f'stripe_checkout_enabled={str(checkout_enabled).lower()}'
        )

        if not checkout_enabled:
            self.stdout.write(self.style.SUCCESS('billing_release_gate=ok checkout-disabled'))
            return

        record_path = options['verification_record']
        if not record_path:
            raise CommandError(
                'STRIPE_CHECKOUT_ENABLED is true; pass --verification-record with final '
                'aws-pre Stripe test-mode evidence before exposing paid Checkout'
            )

        path = Path(record_path)
        if not path.exists():
            raise CommandError(f'billing verification record not found: {path}')

        content = path.read_text(encoding='utf-8')
        issues = self._validate_record(content)
        if issues:
            raise CommandError(
                'billing verification record is not release-ready: '
                + '; '.join(issues)
            )

        self.stdout.write(self.style.SUCCESS('billing_release_gate=ok checkout-verified'))

    def _validate_record(self, content):
        issues = []

        for marker in BLOCKING_RECORD_MARKERS:
            if marker in content:
                issues.append(f'blocking marker found: {marker}')

        required_fragments = [
            '| Stripe mode | test |',
            '| Stripe Checkout enabled | yes |',
            '| Expected Stripe Price currency | jpy |',
            '| Expected monthly unit amount | 480 |',
            '| Expected yearly unit amount | 4800 |',
            'billing_stripe_remote_check=ok',
            'recent_event_ids:',
            'recent_cancel_at_period_end_event_ids',
            'StripeWebhookEvent',
            'PremiumSubscription',
            'Premium audit logs',
        ]
        for fragment in required_fragments:
            if fragment not in content:
                issues.append(f'missing required evidence: {fragment}')

        for event_name in REQUIRED_WEBHOOK_EVENTS:
            if event_name not in content:
                issues.append(f'missing webhook event evidence: {event_name}')

        if 'cancel_at_period_end=true' not in content:
            issues.append('missing cancel_at_period_end=true evidence')

        if 'evt_' not in content:
            issues.append('missing real Stripe event ID evidence')

        return issues
