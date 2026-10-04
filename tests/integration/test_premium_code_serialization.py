from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from accounts.billing import PremiumCodeRedeemError, handle_checkout_completed, redeem_premium_access_code
from accounts.models import PremiumAccessCode, PremiumAccessCodeRedemption, PremiumAuditLog, PremiumSubscription


class PremiumCodeFreshAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="promo-fresh-user")
        self.code, self.raw_code = PremiumAccessCode.issue(label="fresh-state")

    def test_stale_free_user_does_not_replace_current_stripe_access(self):
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=True)
        record = PremiumSubscription.objects.create(
            user=self.user,
            access_source="stripe",
            subscription_status="active",
            stripe_customer_id="cus_fresh_state",
            stripe_subscription_id="sub_fresh_state",
            current_period_end=timezone.now(),
        )
        original_end = record.current_period_end

        code, redeemed = redeem_premium_access_code(self.user, self.raw_code)

        self.assertEqual(code.pk, self.code.pk)
        self.assertFalse(redeemed)
        self.assertTrue(self.user.has_premium_access)
        record.refresh_from_db()
        self.assertEqual(record.access_source, "stripe")
        self.assertEqual(record.subscription_status, "active")
        self.assertEqual(record.current_period_end, original_end)
        self.assertUnusedCode(self.code)

    def test_two_preloaded_requests_do_not_spend_two_codes(self):
        stale_request_user = get_user_model().objects.get(pk=self.user.pk)
        second_code, second_raw = PremiumAccessCode.issue(label="second-code")

        self.assertTrue(redeem_premium_access_code(self.user, self.raw_code)[1])
        self.assertFalse(redeem_premium_access_code(stale_request_user, second_raw)[1])

        self.assertTrue(stale_request_user.has_premium_access)
        self.assertUnusedCode(second_code)
        self.assertEqual(PremiumAccessCodeRedemption.objects.count(), 1)
        self.assertEqual(PremiumAuditLog.objects.filter(action="granted", source="promo_code").count(), 1)

    def test_access_granted_after_initial_check_is_not_replaced(self):
        record = PremiumSubscription.objects.create(user=self.user)

        def grant_before_record_lock(user):
            get_user_model().objects.filter(pk=user.pk).update(is_premium=True)
            PremiumSubscription.objects.filter(pk=record.pk).update(
                access_source="stripe", subscription_status="active"
            )
            return record

        with patch("accounts.billing.get_or_create_subscription_record", side_effect=grant_before_record_lock):
            self.assertFalse(redeem_premium_access_code(self.user, self.raw_code)[1])

        self.assertTrue(self.user.has_premium_access)
        self.assertUnusedCode(self.code)
        record.refresh_from_db()
        self.assertEqual(record.access_source, "stripe")
        self.assertEqual(record.subscription_status, "active")

    def test_repeat_redemption_refreshes_response_access_without_spending_again(self):
        stale_request_user = get_user_model().objects.get(pk=self.user.pk)
        self.assertTrue(redeem_premium_access_code(self.user, self.raw_code)[1])

        self.assertFalse(redeem_premium_access_code(stale_request_user, self.raw_code)[1])

        self.assertTrue(stale_request_user.has_premium_access)
        self.code.refresh_from_db()
        self.assertEqual(self.code.use_count, 1)
        self.assertEqual(PremiumAccessCodeRedemption.objects.count(), 1)

    def test_code_expiring_during_billing_lock_wait_is_not_spent(self):
        before = timezone.now()
        clock = [before]
        self.code.expires_at = before + timedelta(seconds=1)
        self.code.save(update_fields=["expires_at"])
        record = PremiumSubscription.objects.create(user=self.user)

        def finish_wait(user):
            clock[0] = before + timedelta(seconds=2)
            return record

        with (
            patch("accounts.billing.timezone.now", side_effect=lambda: clock[0]),
            patch("accounts.billing.get_or_create_subscription_record", side_effect=finish_wait),
            self.assertRaisesMessage(PremiumCodeRedeemError, "このコードは利用できません。"),
        ):
            redeem_premium_access_code(self.user, self.raw_code)

        self.assertUnusedCode(self.code)
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_premium_access)
        record.refresh_from_db()
        self.assertEqual(record.access_source, "manual")

    def test_newly_revoked_user_can_redeem_despite_stale_premium_flag(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=False)

        self.assertTrue(redeem_premium_access_code(self.user, self.raw_code)[1])

        record = PremiumSubscription.objects.get(user=self.user)
        self.assertEqual(record.access_source, "promo_code")
        self.assertTrue(record.is_promo_active)
        self.assertTrue(self.user.has_premium_access)

    def test_current_staff_and_superuser_access_does_not_spend_code(self):
        for field in ("is_staff", "is_superuser"):
            with self.subTest(field=field):
                stale_request_user = get_user_model().objects.create_user(username=f"promo-{field}")
                get_user_model().objects.filter(pk=stale_request_user.pk).update(**{field: True})
                role_code, role_raw = PremiumAccessCode.issue(label=field)

                self.assertFalse(redeem_premium_access_code(stale_request_user, role_raw)[1])
                self.assertTrue(stale_request_user.has_premium_access)
                self.assertUnusedCode(role_code)
                self.assertFalse(PremiumSubscription.objects.filter(user=stale_request_user).exists())

    def test_invalid_code_does_not_create_billing_record(self):
        with self.assertRaisesMessage(PremiumCodeRedeemError, "コードが見つかりません。"):
            redeem_premium_access_code(self.user, "NOT-AN-ISSUED-CODE")
        self.assertFalse(PremiumSubscription.objects.filter(user=self.user).exists())
        self.assertUnusedCode(self.code)

    def assertUnusedCode(self, code):
        code.refresh_from_db()
        self.assertEqual(code.use_count, 0)
        self.assertFalse(PremiumAccessCodeRedemption.objects.filter(access_code=code).exists())


@skipUnlessDBFeature("has_select_for_update")
class PremiumCodeConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="promo-parallel-user")
        PremiumSubscription.objects.create(user=self.user)

    def redeemTogether(self, pairs):
        barrier = Barrier(2)

        def redeem(user_id, raw_code):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                barrier.wait(timeout=10)
                try:
                    return redeem_premium_access_code(user, raw_code)[1]
                except PremiumCodeRedeemError:
                    return "unavailable"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(redeem, user_id, raw_code) for user_id, raw_code in pairs]
            return [future.result(timeout=15) for future in futures]

    def assertSingleRedemptionFromDifferentCodes(self):
        first, first_raw = PremiumAccessCode.issue(label="parallel-first")
        second, second_raw = PremiumAccessCode.issue(label="parallel-second")

        results = self.redeemTogether([(self.user.pk, first_raw), (self.user.pk, second_raw)])

        self.assertCountEqual(results, [True, False])
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.use_count + second.use_count, 1)
        self.assertEqual(PremiumAccessCodeRedemption.objects.count(), 1)
        self.assertEqual(PremiumAuditLog.objects.filter(action="granted", source="promo_code").count(), 1)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

    def test_parallel_different_codes_for_one_user_spend_only_one(self):
        self.assertSingleRedemptionFromDifferentCodes()

    def test_parallel_first_redemptions_create_only_one_billing_record(self):
        PremiumSubscription.objects.filter(user=self.user).delete()
        self.assertSingleRedemptionFromDifferentCodes()
        self.assertEqual(PremiumSubscription.objects.filter(user=self.user).count(), 1)

    def test_parallel_users_cannot_exceed_shared_code_limit(self):
        other = get_user_model().objects.create_user(username="promo-parallel-other")
        PremiumSubscription.objects.create(user=other)
        code, raw_code = PremiumAccessCode.issue(max_uses=1, label="single-use-parallel")

        results = self.redeemTogether([(self.user.pk, raw_code), (other.pk, raw_code)])

        self.assertCountEqual(results, [True, "unavailable"])
        code.refresh_from_db()
        self.assertEqual(code.use_count, 1)
        self.assertEqual(PremiumAccessCodeRedemption.objects.count(), 1)
        self.assertEqual(get_user_model().objects.filter(pk__in=[self.user.pk, other.pk], is_premium=True).count(), 1)

    def test_waiting_redemption_preserves_checkout_handler_grant(self):
        code, raw_code = PremiumAccessCode.issue(label="checkout-race")
        checkout_locked = Event()
        redemption_waiting = Event()
        current = {"id": "sub_promo_race", "customer": "cus_promo_race", "status": "active"}
        stripe = Mock()

        def retrieve_current(subscription_id):
            self.assertEqual(subscription_id, current["id"])
            checkout_locked.set()
            self.assertTrue(redemption_waiting.wait(timeout=10))
            return current

        stripe.v1.subscriptions.retrieve.side_effect = retrieve_current

        def deliver_checkout():
            close_old_connections()
            try:
                return handle_checkout_completed(
                    {
                        "client_reference_id": str(self.user.pk),
                        "customer": current["customer"],
                        "subscription": current["id"],
                    },
                    event_id="evt_promo_race",
                ).pk
            finally:
                connections.close_all()

        def redeem_while_checkout_holds_lock():
            close_old_connections()
            try:
                self.assertTrue(checkout_locked.wait(timeout=10))
                user = get_user_model().objects.get(pk=self.user.pk)
                self.assertFalse(user.has_premium_access)

                def observe_lock(execute, sql, params, many, context):
                    if "FOR UPDATE" in sql and "accounts_premiumsubscription" in sql:
                        redemption_waiting.set()
                    return execute(sql, params, many, context)

                with connections["default"].execute_wrapper(observe_lock):
                    return redeem_premium_access_code(user, raw_code)[1]
            finally:
                connections.close_all()

        with patch("accounts.billing.get_stripe", return_value=stripe), ThreadPoolExecutor(max_workers=2) as pool:
            checkout = pool.submit(deliver_checkout)
            redemption = pool.submit(redeem_while_checkout_holds_lock)
            checkout.result(timeout=15)
            self.assertFalse(redemption.result(timeout=15))

        code.refresh_from_db()
        self.assertEqual(code.use_count, 0)
        self.assertFalse(PremiumAccessCodeRedemption.objects.exists())
        record = PremiumSubscription.objects.get(user=self.user)
        self.assertEqual(record.access_source, "stripe")
        self.assertEqual(record.stripe_subscription_id, current["id"])
        self.assertEqual(record.subscription_status, "active")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
