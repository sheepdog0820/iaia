from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from accounts.admin import PremiumAccessCodeAdmin
from accounts.billing import expire_promo_subscriptions, handle_checkout_completed
from accounts.models import PremiumAccessCode, PremiumAccessCodeRedemption, PremiumAuditLog, PremiumSubscription


class PromoRevocationTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = get_user_model().objects.create_user(username="promo-revoke-user", is_premium=True)
        self.actor = get_user_model().objects.create_user(username="promo-revoke-admin", is_staff=True)
        self.old_code, _ = PremiumAccessCode.issue(label="old-grant")
        self.current_code, _ = PremiumAccessCode.issue(label="current-grant")
        PremiumAccessCodeRedemption.objects.create(
            user=self.user, access_code=self.old_code, redeemed_at=self.now - timedelta(hours=2)
        )
        PremiumAccessCodeRedemption.objects.create(
            user=self.user, access_code=self.current_code, redeemed_at=self.now - timedelta(hours=1)
        )
        self.record = PremiumSubscription.objects.create(
            user=self.user,
            access_source="promo_code",
            subscription_status="promo",
            premium_expires_at=self.now - timedelta(seconds=1),
        )
        self.admin = PremiumAccessCodeAdmin(PremiumAccessCode, AdminSite())
        self.admin.message_user = Mock()
        self.request = SimpleNamespace(user=self.actor)

    def revokeSelected(self, codes):
        self.admin.revoke_code_granted_access(self.request, PremiumAccessCode.objects.filter(pk__in=codes))

    def test_selecting_old_code_does_not_revoke_later_grant(self):
        self.revokeSelected([self.old_code.pk])

        self.assertActivePromo()
        self.admin.message_user.assert_called_once_with(self.request, "0件のコード由来プレミアム権限を失効しました。")
        self.assertFalse(PremiumAuditLog.objects.filter(action="revoked").exists())

    def test_selecting_both_codes_logs_current_grant_only_once(self):
        self.revokeSelected([self.old_code.pk, self.current_code.pk])

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        audit = PremiumAuditLog.objects.get(action="revoked")
        self.assertEqual(audit.actor, self.actor)
        self.assertEqual(audit.metadata["access_code_id"], self.current_code.pk)
        self.admin.message_user.assert_called_once_with(self.request, "1件のコード由来プレミアム権限を失効しました。")

    def test_equal_redemption_times_use_latest_primary_key(self):
        PremiumAccessCodeRedemption.objects.filter(user=self.user).update(redeemed_at=self.now)

        self.revokeSelected([self.old_code.pk])

        self.assertActivePromo()
        self.revokeSelected([self.current_code.pk])
        self.assertEqual(PremiumAuditLog.objects.get(action="revoked").metadata["access_code_id"], self.current_code.pk)

    def test_expiry_rechecks_state_after_candidate_snapshot(self):
        original_filter = QuerySet.filter
        changed = []

        def capture_then_grant(queryset, *args, **kwargs):
            result = original_filter(queryset, *args, **kwargs)
            if queryset.model is PremiumSubscription and "premium_expires_at__lte" in kwargs and not changed:
                list(result)
                changed.append(True)
                original_filter(PremiumSubscription.objects.all(), pk=self.record.pk).update(
                    access_source="stripe", subscription_status="active", stripe_subscription_id="sub_newer_grant"
                )
            return result

        with patch.object(QuerySet, "filter", new=capture_then_grant):
            self.assertEqual(expire_promo_subscriptions(now=self.now), 0)

        self.assertEqual(changed, [True])
        self.record.refresh_from_db()
        self.assertEqual(self.record.access_source, "stripe")
        self.assertEqual(self.record.subscription_status, "active")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertFalse(PremiumAuditLog.objects.filter(action="revoked").exists())

    def test_expiry_rechecks_new_expiration_after_candidate_snapshot(self):
        original_filter = QuerySet.filter
        changed = []

        def capture_then_extend(queryset, *args, **kwargs):
            result = original_filter(queryset, *args, **kwargs)
            if queryset.model is PremiumSubscription and "premium_expires_at__lte" in kwargs and not changed:
                list(result)
                changed.append(True)
                original_filter(PremiumSubscription.objects.all(), pk=self.record.pk).update(
                    premium_expires_at=self.now + timedelta(days=30)
                )
            return result

        with patch.object(QuerySet, "filter", new=capture_then_extend):
            self.assertEqual(expire_promo_subscriptions(now=self.now), 0)

        self.assertEqual(changed, [True])
        self.assertActivePromo()
        self.assertFalse(PremiumAuditLog.objects.filter(action="revoked").exists())

    def test_dry_run_does_not_change_access_or_audit(self):
        self.assertEqual(expire_promo_subscriptions(now=self.now, dry_run=True), 1)
        self.assertActivePromo()
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_deleted_redemption_after_lock_does_not_revoke_unattributed_access(self):
        original_first = QuerySet.first
        changed = []

        def lock_then_delete(queryset):
            result = original_first(queryset)
            if queryset.model is PremiumSubscription and result is not None and not changed:
                changed.append(True)
                PremiumAccessCodeRedemption.objects.filter(user=self.user).delete()
            return result

        with patch.object(QuerySet, "first", new=lock_then_delete):
            self.revokeSelected([self.current_code.pk])

        self.assertEqual(changed, [True])
        self.assertActivePromo()
        self.assertFalse(PremiumAuditLog.objects.filter(action="revoked").exists())

    def test_expiry_audit_failure_rolls_back_access_change(self):
        with (
            patch("accounts.billing.create_premium_audit_log", side_effect=RuntimeError("isolated audit failure")),
            self.assertRaisesMessage(RuntimeError, "isolated audit failure"),
        ):
            expire_promo_subscriptions(now=self.now)

        self.assertActivePromo()
        self.assertFalse(PremiumAuditLog.objects.filter(action="revoked").exists())

    def test_admin_audit_failure_rolls_back_access_change(self):
        with (
            patch("accounts.admin.create_premium_audit_log", side_effect=RuntimeError("isolated audit failure")),
            self.assertRaisesMessage(RuntimeError, "isolated audit failure"),
        ):
            self.revokeSelected([self.current_code.pk])

        self.assertActivePromo()
        self.assertFalse(PremiumAuditLog.objects.filter(action="revoked").exists())

    def test_expiry_preserves_manual_override_and_logs_once(self):
        PremiumAuditLog.objects.create(user=self.user, action="granted", source="manual")

        self.assertEqual(expire_promo_subscriptions(now=self.now), 1)
        self.assertEqual(expire_promo_subscriptions(now=self.now), 0)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(PremiumAuditLog.objects.get(action="revoked").metadata["access_code_id"], self.current_code.pk)

    def test_expiry_retains_legacy_metadata_without_redemption(self):
        PremiumAccessCodeRedemption.objects.filter(user=self.user).delete()

        self.assertEqual(expire_promo_subscriptions(now=self.now), 1)

        self.assertEqual(PremiumAuditLog.objects.get(action="revoked").metadata, {"subscription_id": self.record.pk})

    def assertActivePromo(self):
        self.user.refresh_from_db()
        self.record.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(self.record.access_source, "promo_code")
        self.assertEqual(self.record.subscription_status, "promo")
        self.assertIsNone(self.record.revoked_at)


@skipUnlessDBFeature("has_select_for_update")
class PromoRevocationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = get_user_model().objects.create_user(username="promo-revoke-parallel", is_premium=True)
        self.actor = get_user_model().objects.create_user(username="promo-revoke-parallel-admin", is_staff=True)
        self.code, _ = PremiumAccessCode.issue(label="parallel-revoke")
        PremiumAccessCodeRedemption.objects.create(user=self.user, access_code=self.code)
        self.record = PremiumSubscription.objects.create(
            user=self.user,
            access_source="promo_code",
            subscription_status="promo",
            premium_expires_at=self.now - timedelta(seconds=1),
        )

    def test_parallel_expiry_workers_revoke_and_log_once(self):
        barrier = Barrier(2)
        original_filter = QuerySet.filter

        def capture_candidates(queryset, *args, **kwargs):
            result = original_filter(queryset, *args, **kwargs)
            if queryset.model is PremiumSubscription and "premium_expires_at__lte" in kwargs:
                list(result)
                barrier.wait(timeout=10)
            return result

        def expire():
            close_old_connections()
            try:
                return expire_promo_subscriptions(now=self.now)
            finally:
                connections.close_all()

        with patch.object(QuerySet, "filter", new=capture_candidates), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(expire) for _ in range(2)]
            results = [future.result(timeout=15) for future in futures]

        self.assertCountEqual(results, [1, 0])
        self.assertEqual(PremiumAuditLog.objects.filter(action="revoked").count(), 1)

    def assertCheckoutWins(self, action):
        checkout_locked = Event()
        revocation_waiting = Event()
        stripe = Mock()
        current = {"id": "sub_revoke_race", "customer": "cus_revoke_race", "status": "active"}

        def retrieve_current(subscription_id):
            self.assertEqual(subscription_id, current["id"])
            checkout_locked.set()
            self.assertTrue(revocation_waiting.wait(timeout=10))
            return current

        stripe.v1.subscriptions.retrieve.side_effect = retrieve_current

        def checkout():
            close_old_connections()
            try:
                handle_checkout_completed(
                    {
                        "client_reference_id": str(self.user.pk),
                        "customer": current["customer"],
                        "subscription": current["id"],
                    },
                    event_id="evt_revoke_race",
                )
            finally:
                connections.close_all()

        def revoke():
            close_old_connections()
            try:
                self.assertTrue(checkout_locked.wait(timeout=10))

                def observe_lock(execute, sql, params, many, context):
                    if "FOR UPDATE" in sql and "accounts_premiumsubscription" in sql:
                        revocation_waiting.set()
                    return execute(sql, params, many, context)

                with connections["default"].execute_wrapper(observe_lock):
                    if action == "expiry":
                        self.assertEqual(expire_promo_subscriptions(now=self.now), 0)
                    else:
                        admin = PremiumAccessCodeAdmin(PremiumAccessCode, AdminSite())
                        admin.message_user = Mock()
                        request = SimpleNamespace(user=self.actor)
                        admin.revoke_code_granted_access(request, PremiumAccessCode.objects.filter(pk=self.code.pk))
                        admin.message_user.assert_called_once_with(
                            request, "0件のコード由来プレミアム権限を失効しました。"
                        )
            finally:
                connections.close_all()

        with patch("accounts.billing.get_stripe", return_value=stripe), ThreadPoolExecutor(max_workers=2) as pool:
            purchase = pool.submit(checkout)
            revocation = pool.submit(revoke)
            purchase.result(timeout=15)
            revocation.result(timeout=15)

        self.record.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.record.access_source, "stripe")
        self.assertEqual(self.record.subscription_status, "active")
        self.assertEqual(self.record.stripe_subscription_id, current["id"])
        self.assertTrue(self.user.is_premium)
        self.assertIsNone(self.record.revoked_at)
        self.assertFalse(PremiumAuditLog.objects.filter(action="revoked", source="promo_code").exists())

    def test_expiry_waiting_for_checkout_does_not_revoke_paid_access(self):
        self.assertCheckoutWins("expiry")

    def test_admin_revocation_waiting_for_checkout_does_not_revoke_paid_access(self):
        self.assertCheckoutWins("admin")
