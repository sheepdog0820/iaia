from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from django.utils import timezone

from accounts.billing import get_stripe
from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS

RECENT_OPERATIONAL_EVENT_TYPES = (
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
    "invoice.payment_succeeded",
    "charge.refunded",
    "charge.dispute.created",
    "charge.dispute.closed",
)


class Command(BaseCommand):
    help = "Stripe API上のPriceとWebhook endpoint設定を確認します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-webhook",
            action="store_true",
            help="Webhook endpoint登録確認をスキップします。",
        )
        parser.add_argument(
            "--skip-portal",
            action="store_true",
            help="Customer Portal設定確認をスキップします。",
        )
        parser.add_argument(
            "--webhook-url",
            default="",
            help="確認対象のWebhook URL。省略時は PUBLIC_SITE_URL + /api/billing/webhook/ を使います。",
        )

        parser.add_argument(
            "--require-recent-events",
            action="store_true",
            help="Stripe Events APIで直近の実イベント発生を確認します。",
        )
        parser.add_argument(
            "--recent-hours",
            type=int,
            default=72,
            help="--require-recent-eventsで確認する直近イベントの時間幅です。",
        )

    def handle(self, *args, **options):
        if not settings.STRIPE_PREMIUM_PRICE_ID:
            raise CommandError("STRIPE_PREMIUM_PRICE_ID is required")

        expected_livemode = get_expected_livemode()
        stripe = get_stripe()
        price = stripe.Price.retrieve(settings.STRIPE_PREMIUM_PRICE_ID)
        price_errors = validate_price(
            price,
            expected_livemode=expected_livemode,
            expected_interval="month",
            expected_currency=getattr(settings, "STRIPE_PREMIUM_EXPECTED_CURRENCY", ""),
            expected_unit_amount=get_expected_unit_amount("STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT"),
        )
        if price_errors:
            raise CommandError("Stripe price check failed: " + ", ".join(price_errors))
        self.stdout.write(self.style.SUCCESS("OK stripe price monthly"))

        yearly_price_id = getattr(settings, "STRIPE_PREMIUM_YEARLY_PRICE_ID", "")
        if yearly_price_id:
            yearly_price = stripe.Price.retrieve(yearly_price_id)
            yearly_price_errors = validate_price(
                yearly_price,
                expected_livemode=expected_livemode,
                expected_interval="year",
                expected_currency=getattr(settings, "STRIPE_PREMIUM_EXPECTED_CURRENCY", ""),
                expected_unit_amount=get_expected_unit_amount("STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT"),
            )
            if yearly_price_errors:
                raise CommandError("Stripe yearly price check failed: " + ", ".join(yearly_price_errors))
            self.stdout.write(self.style.SUCCESS("OK stripe price yearly"))

        if options["skip_portal"]:
            self.stdout.write(self.style.WARNING("SKIP stripe customer portal"))
        else:
            portal_configurations = stripe.billing_portal.Configuration.list(limit=100)
            portal_errors = validate_portal_configurations(
                portal_configurations,
                expected_livemode=expected_livemode,
                expected_configuration_id=getattr(
                    settings,
                    "STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID",
                    "",
                ),
            )
            if portal_errors:
                raise CommandError("Stripe customer portal check failed: " + ", ".join(portal_errors))
            self.stdout.write(self.style.SUCCESS("OK stripe customer portal"))

        if options["skip_webhook"]:
            self.stdout.write(self.style.WARNING("SKIP stripe webhook endpoint"))
            self.stdout.write(self.style.SUCCESS("billing_stripe_remote_check=ok"))
            return

        webhook_url = options["webhook_url"] or build_default_webhook_url()
        endpoints = stripe.WebhookEndpoint.list(limit=100)
        endpoint_errors = validate_webhook_endpoints(
            endpoints,
            webhook_url,
            expected_livemode=expected_livemode,
        )
        if endpoint_errors:
            raise CommandError("Stripe webhook check failed: " + ", ".join(endpoint_errors))
        self.stdout.write(self.style.SUCCESS(f"OK stripe webhook endpoint {webhook_url}"))
        if options["require_recent_events"]:
            created_gte = int((timezone.now() - timezone.timedelta(hours=options["recent_hours"])).timestamp())
            recent_events = stripe.Event.list(
                limit=100,
                created={"gte": created_gte},
                types=list(RECENT_OPERATIONAL_EVENT_TYPES),
            )
            recent_event_errors = validate_recent_operational_events(
                recent_events,
                expected_livemode=expected_livemode,
            )
            if recent_event_errors:
                raise CommandError("Stripe recent event check failed: " + ", ".join(recent_event_errors))
            for line in summarize_recent_operational_events(recent_events):
                self.stdout.write(line)
            self.stdout.write(
                self.style.SUCCESS(f'OK stripe recent operational events last {options["recent_hours"]}h')
            )
        self.stdout.write(self.style.SUCCESS("billing_stripe_remote_check=ok"))


def build_default_webhook_url():
    site_url = getattr(settings, "PUBLIC_SITE_URL", "").rstrip("/")
    if not site_url:
        raise CommandError("PUBLIC_SITE_URL is required or pass --webhook-url")
    return f'{site_url}{reverse("billing-webhook")}'


def get_expected_unit_amount(setting_name):
    raw_value = str(getattr(settings, setting_name, "") or "").strip()
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError as exc:
        raise CommandError(f"{setting_name} must be an integer minor-unit amount") from exc


def get_expected_livemode():
    secret_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    environment = getattr(settings, "ENVIRONMENT", "").strip().lower()
    if secret_key.startswith("sk_live_"):
        if environment != "production":
            raise CommandError("STRIPE_SECRET_KEY live key cannot be used outside production")
        return True
    if secret_key.startswith("sk_test_"):
        if environment == "production":
            raise CommandError("STRIPE_SECRET_KEY test key cannot be used in production")
        return False
    raise CommandError("STRIPE_SECRET_KEY must start with sk_test_ or sk_live_")


def validate_price(
    price,
    expected_livemode=None,
    expected_interval="month",
    expected_currency="",
    expected_unit_amount=None,
):
    errors = []
    if not _get(price, "active", False):
        errors.append("price is not active")
    if _get(price, "type") != "recurring":
        errors.append("price type is not recurring")
    recurring = _get(price, "recurring", {}) or {}
    if _get(recurring, "interval") != expected_interval:
        errors.append(f"price interval is not {expected_interval}")
    if expected_currency:
        currency = str(_get(price, "currency", "") or "").lower()
        if currency != expected_currency.lower():
            errors.append(f'price currency mismatch: expected {expected_currency.lower()}, got {currency or "unknown"}')
    if expected_unit_amount is not None:
        unit_amount = _get(price, "unit_amount")
        if unit_amount != expected_unit_amount:
            errors.append(f"price unit_amount mismatch: expected {expected_unit_amount}, got {unit_amount}")
    livemode = _get(price, "livemode")
    if expected_livemode is not None and livemode is not None and livemode != expected_livemode:
        expected = "live" if expected_livemode else "test"
        actual = "live" if livemode else "test"
        errors.append(f"price livemode mismatch: expected {expected}, got {actual}")
    return errors


def validate_webhook_endpoints(endpoints, webhook_url, expected_livemode=None):
    endpoint = None
    for candidate in _get(endpoints, "data", []) or []:
        if _get(candidate, "url") == webhook_url:
            endpoint = candidate
            break
    if endpoint is None:
        return [f"webhook endpoint not found: {webhook_url}"]

    endpoint_status = _get(endpoint, "status")
    if endpoint_status and endpoint_status != "enabled":
        return [f"webhook endpoint is not enabled: {endpoint_status}"]

    livemode = _get(endpoint, "livemode")
    if expected_livemode is not None and livemode is not None and livemode != expected_livemode:
        expected = "live" if expected_livemode else "test"
        actual = "live" if livemode else "test"
        return [f"webhook endpoint livemode mismatch: expected {expected}, got {actual}"]

    enabled_events = set(_get(endpoint, "enabled_events", []) or [])
    if "*" in enabled_events:
        return []
    missing = [event for event in REQUIRED_WEBHOOK_EVENTS if event not in enabled_events]
    if missing:
        return ["missing webhook events: " + ", ".join(missing)]
    return []


def validate_portal_configurations(
    configurations,
    expected_livemode=None,
    expected_configuration_id="",
):
    configuration_data = _get(configurations, "data", []) or []
    if expected_configuration_id:
        matching_configurations = [
            configuration
            for configuration in configuration_data
            if _get(configuration, "id") == expected_configuration_id
        ]
        if not matching_configurations:
            return [f"customer portal configuration not found: {expected_configuration_id}"]
        active_configurations = [
            configuration for configuration in matching_configurations if _get(configuration, "active", False)
        ]
        if not active_configurations:
            return [f"customer portal configuration is not active: {expected_configuration_id}"]
    else:
        active_configurations = [
            configuration for configuration in configuration_data if _get(configuration, "active", False)
        ]
    if not active_configurations:
        return ["active customer portal configuration not found"]
    known_mode_configurations = [
        configuration for configuration in active_configurations if _get(configuration, "livemode") is not None
    ]
    if expected_livemode is not None and known_mode_configurations:
        matching_configurations = [
            configuration
            for configuration in known_mode_configurations
            if _get(configuration, "livemode") == expected_livemode
        ]
        if not matching_configurations:
            expected = "live" if expected_livemode else "test"
            actual_modes = {
                "live" if _get(configuration, "livemode") else "test" for configuration in known_mode_configurations
            }
            return ["customer portal livemode mismatch: " f'expected {expected}, got {", ".join(sorted(actual_modes))}']
    feature_errors = []
    feature_requirements = {
        "payment_method_update": "payment method update",
        "subscription_cancel": "subscription cancellation",
        "invoice_history": "invoice history",
    }
    for feature_key, label in feature_requirements.items():
        if not any(portal_feature_enabled(configuration, feature_key) for configuration in active_configurations):
            feature_errors.append(f"customer portal {label} is not enabled")
    if feature_errors:
        return feature_errors
    return []


def portal_feature_enabled(configuration, feature_key):
    features = _get(configuration, "features", {}) or {}
    feature = _get(features, feature_key, {}) or {}
    return bool(_get(feature, "enabled", False))


def validate_recent_operational_events(events, expected_livemode=None):
    data = _get(events, "data", []) or []
    found_types = {_get(event, "type") for event in data}
    missing = [event_type for event_type in RECENT_OPERATIONAL_EVENT_TYPES if event_type not in found_types]
    errors = []
    if missing:
        errors.append("missing recent events: " + ", ".join(missing))

    if expected_livemode is not None:
        mismatched = [
            _get(event, "id", _get(event, "type", "unknown"))
            for event in data
            if _get(event, "livemode") is not None and _get(event, "livemode") != expected_livemode
        ]
        if mismatched:
            expected = "live" if expected_livemode else "test"
            errors.append(f'recent event livemode mismatch: expected {expected}, events {", ".join(mismatched)}')

    canceling_subscription_events = [
        event
        for event in data
        if _get(event, "type") == "customer.subscription.updated"
        and _get(_get(_get(event, "data", {}) or {}, "object", {}) or {}, "cancel_at_period_end") is True
    ]
    if not canceling_subscription_events:
        errors.append("missing recent customer.subscription.updated with cancel_at_period_end=true")
    return errors


def summarize_recent_operational_events(events):
    data = _get(events, "data", []) or []
    event_ids_by_type = {}
    canceling_event_ids = []
    for event in data:
        event_type = _get(event, "type")
        event_id = _get(event, "id", "")
        if event_type in RECENT_OPERATIONAL_EVENT_TYPES and event_type not in event_ids_by_type:
            event_ids_by_type[event_type] = event_id
        if (
            event_type == "customer.subscription.updated"
            and _get(_get(_get(event, "data", {}) or {}, "object", {}) or {}, "cancel_at_period_end") is True
        ):
            canceling_event_ids.append(event_id)

    lines = ["recent_event_ids:"]
    for event_type in RECENT_OPERATIONAL_EVENT_TYPES:
        lines.append(f'- {event_type}: {event_ids_by_type.get(event_type, "-")}')
    lines.append(
        "recent_cancel_at_period_end_event_ids: " + (", ".join(canceling_event_ids) if canceling_event_ids else "-")
    )
    return lines


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
