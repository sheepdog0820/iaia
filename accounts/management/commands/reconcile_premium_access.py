from django.core.management.base import BaseCommand

from accounts.billing import create_premium_audit_log, expire_promo_subscriptions
from accounts.models import PremiumSubscription


class Command(BaseCommand):
    help = '課金レコードを正としてユーザーのプレミアム権限を再同期します。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='変更せず、同期対象件数だけ表示します。',
        )
        parser.add_argument(
            '--skip-expire',
            action='store_true',
            help='期限切れ運営コード由来プレミアムの失効処理をスキップします。',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        expired_count = 0
        if not options['skip_expire'] and not dry_run:
            expired_count = expire_promo_subscriptions()

        checked = 0
        changed = 0
        records = PremiumSubscription.objects.select_related('user').order_by('pk')
        for record in records:
            checked += 1
            expected = record.expected_user_premium_access
            current = record.user.is_premium
            if expected == current:
                continue

            changed += 1
            self.stdout.write(
                f'{record.user.username}: is_premium {current} -> {expected} '
                f'({record.access_source}:{record.subscription_status})'
            )
            if dry_run:
                continue

            record.user.is_premium = expected
            record.user.save(update_fields=['is_premium'])
            create_premium_audit_log(
                record.user,
                action='granted' if expected else 'revoked',
                source=record.access_source,
                reason='Premium access reconciled from billing record',
                metadata={
                    'subscription_id': record.pk,
                    'subscription_status': record.subscription_status,
                    'dry_run': False,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'reconcile_premium_access=ok checked={checked} changed={changed} expired={expired_count}'
            )
        )
