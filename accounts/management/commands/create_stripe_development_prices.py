from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.billing import get_stripe


class Command(BaseCommand):
    help = "Create Stripe test-mode Product and monthly/yearly Prices for local billing verification."

    def add_arguments(self, parser):
        parser.add_argument(
            "--product-name",
            default="Tableno Premium Development",
            help="Stripe Product name to create in test mode.",
        )
        parser.add_argument(
            "--monthly-amount",
            type=int,
            default=480,
            help="Monthly amount in minor currency units. For JPY this is yen.",
        )
        parser.add_argument(
            "--yearly-amount",
            type=int,
            default=4800,
            help="Yearly amount in minor currency units. For JPY this is yen.",
        )
        parser.add_argument(
            "--currency",
            default="jpy",
            help="Lowercase Stripe currency code.",
        )

    def handle(self, *args, **options):
        self._validate_safety(options)
        stripe = get_stripe()

        product = stripe.Product.create(
            name=options["product_name"],
            description="Development/test-mode premium subscription for Tableno local verification.",
            active=True,
            type="service",
            metadata={
                "app": "tableno",
                "environment": "development",
                "managed_by": "django_command",
                "purpose": "local_billing_verification",
            },
        )
        if _get(product, "livemode") is not False:
            product_id = _get(product, "id", "")
            try:
                if product_id:
                    stripe.Product.modify(
                        product_id,
                        active=False,
                        metadata={
                            "app": "tableno",
                            "environment": "development",
                            "managed_by": "django_command",
                            "purpose": "local_billing_verification",
                            "disabled_reason": "unexpected_live_mode_response",
                        },
                    )
            finally:
                raise CommandError(
                    "Stripe Product response was not test mode; disabled Product and stopped before Price creation"
                )

        monthly_price = self._create_price(
            stripe,
            product_id=_get(product, "id"),
            nickname="Tableno Premium monthly development",
            amount=options["monthly_amount"],
            currency=options["currency"],
            interval="month",
        )
        yearly_price = self._create_price(
            stripe,
            product_id=_get(product, "id"),
            nickname="Tableno Premium yearly development",
            amount=options["yearly_amount"],
            currency=options["currency"],
            interval="year",
        )

        self.stdout.write(self.style.SUCCESS("stripe_development_prices=ok"))
        self.stdout.write(f'product_id={_get(product, "id")}')
        self.stdout.write(f'STRIPE_PREMIUM_PRICE_ID={_get(monthly_price, "id")}')
        self.stdout.write(f'STRIPE_PREMIUM_YEARLY_PRICE_ID={_get(yearly_price, "id")}')
        self.stdout.write(f'STRIPE_PREMIUM_EXPECTED_CURRENCY={options["currency"]}')
        self.stdout.write(f'STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT={options["monthly_amount"]}')
        self.stdout.write(f'STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT={options["yearly_amount"]}')

    def _validate_safety(self, options):
        secret_key = getattr(settings, "STRIPE_SECRET_KEY", "")
        environment = getattr(settings, "ENVIRONMENT", "").strip().lower()
        currency = options["currency"].strip().lower()
        if not secret_key.startswith("sk_test_"):
            raise CommandError("STRIPE_SECRET_KEY must be a test key starting with sk_test_")
        if environment == "production":
            raise CommandError("create_stripe_development_prices cannot run in production")
        if currency != options["currency"] or len(currency) != 3 or not currency.isalpha():
            raise CommandError("currency must be a lowercase 3-letter code")
        if options["monthly_amount"] <= 0 or options["yearly_amount"] <= 0:
            raise CommandError("monthly and yearly amounts must be positive")

    def _create_price(self, stripe, *, product_id, nickname, amount, currency, interval):
        price = stripe.Price.create(
            product=product_id,
            nickname=nickname,
            unit_amount=amount,
            currency=currency,
            recurring={"interval": interval},
            metadata={
                "app": "tableno",
                "environment": "development",
                "managed_by": "django_command",
                "billing_interval": interval,
                "purpose": "local_billing_verification",
            },
        )
        if _get(price, "livemode") is not False:
            raise CommandError(f"Stripe {interval} Price response was not test mode")
        return price


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
