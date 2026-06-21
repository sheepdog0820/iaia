from django.core.management.base import BaseCommand

from accounts.billing import expire_promo_subscriptions


class Command(BaseCommand):
    help = '期限切れの運営コード由来プレミアム権限を失効します。'

    def handle(self, *args, **options):
        count = expire_promo_subscriptions()
        self.stdout.write(self.style.SUCCESS(f'expired_premium_access={count}'))
