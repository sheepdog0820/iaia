from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.billing import sync_subscription_object
from accounts.models import PremiumSubscription


class StripePortalCancellationTests(TestCase):
    def test_portal_cancel_timestamp_and_reactivation(self):
        user = get_user_model().objects.create_user(username="portal-cancellation-test")
        PremiumSubscription.objects.create(user=user, stripe_customer_id="cus_portal")
        period_end = int(timezone.now().timestamp()) + 3600
        subscription = {
            "id": "sub_portal",
            "customer": "cus_portal",
            "status": "active",
            "cancel_at_period_end": False,
            "cancel_at": period_end,
            "items": {
                "data": [
                    {
                        "current_period_end": period_end,
                        "price": {"id": "price_portal", "recurring": {"interval": "month"}},
                    }
                ]
            },
        }
        record = sync_subscription_object(subscription)
        self.assertTrue(record.cancel_at_period_end)
        user.refresh_from_db()
        self.assertTrue(user.is_premium)

        subscription["cancel_at"] = None
        record = sync_subscription_object(subscription)
        self.assertFalse(record.cancel_at_period_end)
        user.refresh_from_db()
        self.assertTrue(user.is_premium)

    def test_other_or_unknown_period_is_not_reported_as_period_end_cancellation(self):
        user = get_user_model().objects.create_user(username="portal-other-period-test")
        PremiumSubscription.objects.create(user=user, stripe_customer_id="cus_other_period")
        for period_end, cancel_at in [(None, None), (None, 2000000000), (2000000000, 2000003600)]:
            with self.subTest(period_end=period_end, cancel_at=cancel_at):
                record = sync_subscription_object(
                    {
                        "id": "sub_other_period",
                        "customer": "cus_other_period",
                        "status": "active",
                        "current_period_end": period_end,
                        "cancel_at_period_end": False,
                        "cancel_at": cancel_at,
                    }
                )
                self.assertFalse(record.cancel_at_period_end)
