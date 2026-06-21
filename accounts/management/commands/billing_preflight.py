from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.test import Client
from django.urls import NoReverseMatch, reverse



LEGAL_PAGE_REQUIRED_TEXT = {
    'commercial_disclosure': (
        '\u7279\u5b9a\u5546\u53d6\u5f15\u6cd5\u306b\u57fa\u3065\u304f\u8868\u8a18',
        '\u8ca9\u58f2\u4e8b\u696d\u8005',
        '\u8ca9\u58f2\u4fa1\u683c',
        '\u652f\u6255\u65b9\u6cd5',
        '\u652f\u6255\u6642\u671f',
        '\u63d0\u4f9b\u6642\u671f',
        '\u89e3\u7d04\u65b9\u6cd5',
        '\u8fd4\u54c1\u30fb\u30ad\u30e3\u30f3\u30bb\u30eb\u30fb\u8fd4\u91d1',
    ),
    'premium_features': (
        '\u30d7\u30ec\u30df\u30a2\u30e0\u6a5f\u80fd',
        '\u6599\u91d1',
        '\u30b7\u30ca\u30ea\u30aa\u30a2\u30fc\u30ab\u30a4\u30d6',
        '\u6708\u984d\u6599\u91d1',
        '\u8fd4\u91d1\u6761\u4ef6',
        '\u4e8b\u696d\u8005\u60c5\u5831',
    ),
}

MOJIBAKE_MARKERS = (
    '\u7e5d',
    '\u8b5b',
    '\u8711',
    '\u90e2\uff67',
    '\u90b5\uff7a',
    '\u96b4\ufffd',
    '\u9aeb\uff71',
    '\u9b2e\uff6f',
)

REQUIRED_WEBHOOK_EVENTS = (
    'checkout.session.completed',
    'customer.subscription.created',
    'customer.subscription.updated',
    'customer.subscription.deleted',
    'invoice.payment_failed',
    'invoice.payment_succeeded',
    'charge.refunded',
    'charge.dispute.created',
    'charge.dispute.closed',
)


class Command(BaseCommand):
    help = 'Stripe課金とプレミアム権限付与に必要な本番設定を検査します。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='警告がある場合もエラー終了します。',
        )

    def handle(self, *args, **options):
        strict = options['strict']
        warnings = []

        checks = [
            self._setting_check('STRIPE_SECRET_KEY', required_prefix='sk_'),
            self._setting_check('STRIPE_WEBHOOK_SECRET', required_prefix='whsec_'),
            self._setting_check('STRIPE_PREMIUM_PRICE_ID', required_prefix='price_'),
            self._optional_setting_check('STRIPE_PREMIUM_YEARLY_PRICE_ID', required_prefix='price_'),
            self._refund_or_dispute_policy_check(),
            self._setting_check(
                'PREMIUM_PRICE_LABEL',
                reject_fragments=('Stripe Checkout', 'Checkout画面に表示'),
                reject_message='本番では月額料金を具体的に設定してください。',
            ),
            self._setting_check('LEGAL_PAYMENT_METHOD'),
            self._setting_check('LEGAL_PAYMENT_TIMING'),
            self._setting_check('LEGAL_SERVICE_DELIVERY_TIMING'),
            self._setting_check('LEGAL_CANCELLATION_METHOD'),
            self._setting_check('LEGAL_CANCELLATION_EFFECT'),
            self._setting_check('LEGAL_REFUND_POLICY'),
            self._setting_check(
                'LEGAL_SELLER_NAME',
                reject_fragments=('タブレノ運営',),
                reject_message='本番では実際の販売事業者名を設定してください。',
            ),
            self._setting_check('LEGAL_SELLER_ADDRESS', reject_disclosure_placeholder=True),
            self._setting_check('LEGAL_SELLER_PHONE', reject_disclosure_placeholder=True),
            self._contact_email_check(),
            self._setting_check('PUBLIC_SITE_URL', required_prefix='https://'),
            self._email_delivery_check(),
            self._url_check('billing-webhook'),
            self._url_check('billing-checkout-session'),
            self._url_check('billing-portal-session'),
            self._url_check('billing-redeem-code'),
            self._url_check('commercial_disclosure'),
            self._url_check('premium_features'),
            self._url_check('billing'),
            self._page_contains_check(
                'commercial_disclosure',
                (
                    'LEGAL_SELLER_NAME',
                    'LEGAL_SELLER_ADDRESS',
                    'LEGAL_SELLER_PHONE',
                    'CONTACT_EMAIL',
                    'PREMIUM_PRICE_LABEL',
                    'LEGAL_PAYMENT_METHOD',
                    'LEGAL_PAYMENT_TIMING',
                    'LEGAL_SERVICE_DELIVERY_TIMING',
                    'LEGAL_CANCELLATION_METHOD',
                    'LEGAL_CANCELLATION_EFFECT',
                    'LEGAL_REFUND_POLICY',
                ),
            ),
            self._page_quality_check('commercial_disclosure'),
            self._page_contains_check(
                'premium_features',
                (
                    'PREMIUM_PRICE_LABEL',
                    'LEGAL_PAYMENT_TIMING',
                    'LEGAL_SERVICE_DELIVERY_TIMING',
                    'LEGAL_CANCELLATION_METHOD',
                    'LEGAL_CANCELLATION_EFFECT',
                    'LEGAL_REFUND_POLICY',
                ),
            ),
            self._page_quality_check('premium_features'),
            self._celery_expiration_check(),
        ]

        for name, ok, message in checks:
            if ok:
                suffix = f': {message}' if message else ''
                self.stdout.write(self.style.SUCCESS(f'OK {name}{suffix}'))
            else:
                warnings.append(f'{name}: {message}')
                self.stdout.write(self.style.WARNING(f'WARN {name}: {message}'))

        self.stdout.write('Required Stripe webhook events:')
        for event_name in REQUIRED_WEBHOOK_EVENTS:
            self.stdout.write(f'- {event_name}')

        if warnings:
            if strict:
                raise CommandError('billing_preflight failed: ' + '; '.join(warnings))
            self.stdout.write(self.style.WARNING('billing_preflight=warnings'))
            return

        self.stdout.write(self.style.SUCCESS('billing_preflight=ok'))

    def _optional_setting_check(self, name, required_prefix=None):
        value = getattr(settings, name, '')
        if not value:
            return name, True, 'not configured'
        if required_prefix and not str(value).startswith(required_prefix):
            return name, False, f'set a value starting with {required_prefix}'
        return name, True, ''

    def _setting_check(
        self,
        name,
        required_prefix=None,
        reject_disclosure_placeholder=False,
        reject_fragments=(),
        reject_message='本番では具体的な値を設定してください。',
    ):
        value = getattr(settings, name, '')
        if not value:
            return name, False, '値が設定されていません。'
        if required_prefix and not str(value).startswith(required_prefix):
            return name, False, f'set a value starting with {required_prefix}'
        if reject_disclosure_placeholder and '請求があった場合' in str(value):
            return name, False, '本番では実際の事業者情報を設定してください。'
        if any(fragment in str(value) for fragment in reject_fragments):
            return name, False, reject_message
        return name, True, ''

    def _url_check(self, name):
        try:
            reverse(name)
        except NoReverseMatch as exc:
            return f'url:{name}', False, str(exc)
        return f'url:{name}', True, ''

    def _page_contains_check(self, url_name, setting_names):
        try:
            url = reverse(url_name)
        except NoReverseMatch as exc:
            return f'page:{url_name}', False, str(exc)
        response = Client().get(url)
        if response.status_code != 200:
            return f'page:{url_name}', False, f'HTTP {response.status_code}'
        html = response.content.decode(response.charset or 'utf-8', errors='replace')
        missing = [
            setting_name
            for setting_name in setting_names
            if str(getattr(settings, setting_name, '')) not in html
        ]
        if missing:
            return (
                f'page:{url_name}',
                False,
                '設定値が画面に表示されていません: ' + ', '.join(missing),
            )
        return f'page:{url_name}', True, ''


    def _page_quality_check(self, url_name):
        try:
            url = reverse(url_name)
        except NoReverseMatch as exc:
            return f'page-quality:{url_name}', False, str(exc)
        response = Client().get(url)
        if response.status_code != 200:
            return f'page-quality:{url_name}', False, f'HTTP {response.status_code}'
        html = response.content.decode(response.charset or 'utf-8', errors='replace')
        mojibake_found = [marker for marker in MOJIBAKE_MARKERS if marker in html]
        missing_required_text = [
            text
            for text in LEGAL_PAGE_REQUIRED_TEXT.get(url_name, ())
            if text not in html
        ]
        issues = []
        if mojibake_found:
            issues.append('mojibake marker found: ' + ', '.join(mojibake_found))
        if missing_required_text:
            issues.append('required legal text missing: ' + ', '.join(missing_required_text))
        if issues:
            return f'page-quality:{url_name}', False, '; '.join(issues)
        return f'page-quality:{url_name}', True, ''

    def _refund_or_dispute_policy_check(self):
        auto_revoke = getattr(settings, 'STRIPE_REVOKE_ON_REFUND_OR_DISPUTE', True)
        policy = 'auto revoke' if auto_revoke else 'manual review'
        return 'STRIPE_REVOKE_ON_REFUND_OR_DISPUTE', True, policy

    def _email_delivery_check(self):
        backend = getattr(settings, 'EMAIL_BACKEND', '')
        disabled_backends = (
            'django.core.mail.backends.console.EmailBackend',
            'django.core.mail.backends.dummy.EmailBackend',
            'django.core.mail.backends.locmem.EmailBackend',
        )
        if backend in disabled_backends:
            return (
                'EMAIL_BACKEND',
                False,
                '支払い失敗通知を送るため、本番では実配送できるメールbackendを設定してください。',
            )
        if not getattr(settings, 'DEFAULT_FROM_EMAIL', ''):
            return 'DEFAULT_FROM_EMAIL', False, '支払い失敗通知の送信元を設定してください。'
        return 'EMAIL_BACKEND', True, backend

    def _contact_email_check(self):
        value = getattr(settings, 'CONTACT_EMAIL', '')
        if not value:
            return 'CONTACT_EMAIL', False, '特商法ページの問い合わせ先メールを設定してください。'
        try:
            validate_email(value)
        except ValidationError:
            return 'CONTACT_EMAIL', False, '有効な問い合わせ先メールアドレスを設定してください。'
        return 'CONTACT_EMAIL', True, value

    def _celery_expiration_check(self):
        schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
        entry = schedule.get('expire-premium-access', {})
        task = entry.get('task')
        if task != 'schedules.tasks.expire_premium_access':
            return (
                'celery:expire-premium-access',
                False,
                'schedules.tasks.expire_premium_access がCelery beatに登録されていません。',
            )
        interval = entry.get('schedule')
        if isinstance(interval, timedelta):
            interval_seconds = interval.total_seconds()
        elif isinstance(interval, (int, float)):
            interval_seconds = float(interval)
        else:
            interval_seconds = None
        if interval_seconds is not None and interval_seconds > 3600:
            return (
                'celery:expire-premium-access',
                False,
                '期限付きプレミアムコードの失効ジョブは1時間以内の間隔で実行してください。',
            )
        return 'celery:expire-premium-access', True, ''

