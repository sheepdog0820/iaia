from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections, transaction
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from accounts.admin import PremiumSubscriptionAdmin
from accounts.models import PremiumAuditLog, PremiumSubscription


class AdminAccessOperations:
    operations = ("revoke_selected_access", "restore_selected_access", "mark_refund_or_dispute_reviewed")

    def setUp(self):
        self.now = timezone.now()
        self.user = get_user_model().objects.create_user(username="admin-access-integrity", is_premium=True)
        self.actor = get_user_model().objects.create_user(username="admin-access-integrity-actor", is_staff=True)
        self.record = PremiumSubscription.objects.create(
            user=self.user,
            subscription_status="active",
            access_source="stripe",
            stripe_subscription_id="sub_admin_access_fixture",
            last_refund_or_dispute_at=self.now,
        )

    def runAction(self, operation, *, actor=True):
        admin = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        admin.message_user = Mock()
        request = SimpleNamespace(user=self.actor if actor else None)
        getattr(admin, operation)(request, PremiumSubscription.objects.filter(pk=self.record.pk))
        return admin.message_user.call_args.args[1]

    def snapshotThen(self, callback):
        original_iter = QuerySet.__iter__
        original_iterator = QuerySet.iterator
        captured = []

        def change(queryset, rows):
            if queryset.model is PremiumSubscription and not queryset.query.select_for_update and not captured:
                captured.append(True)
                callback()
            return iter(rows)

        def snapshot_iter(queryset):
            return change(queryset, list(original_iter(queryset)))

        def snapshot_iterator(queryset, *args, **kwargs):
            return change(queryset, list(original_iterator(queryset, *args, **kwargs)))

        return (
            captured,
            patch.object(QuerySet, "__iter__", new=snapshot_iter),
            patch.object(QuerySet, "iterator", new=snapshot_iterator),
        )


class AdminAccessIntegrityTests(AdminAccessOperations, TestCase):
    def assertRestoreUsesLatest(self, original_status, latest_status, latest_flag):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(
            subscription_status=original_status, revoked_at=self.now, revoked_reason="fixture revocation"
        )
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=latest_flag)
        captured, first, second = self.snapshotThen(
            lambda: PremiumSubscription.objects.filter(pk=self.record.pk).update(subscription_status=latest_status)
        )
        with first, second:
            message = self.runAction("restore_selected_access")
        self.assertEqual(captured, [True])
        self.user.refresh_from_db()
        self.record.refresh_from_db()
        self.assertEqual(self.user.is_premium, latest_flag)
        self.assertEqual(self.record.subscription_status, latest_status)
        self.assertIsNone(self.record.revoked_at)
        self.assertEqual(message, "0件のユーザー権限を復旧しました。")

    def test_restore_does_not_grant_subscription_canceled_after_snapshot(self):
        self.assertRestoreUsesLatest("active", "canceled", False)

    def test_restore_does_not_remove_subscription_activated_after_snapshot(self):
        self.assertRestoreUsesLatest("canceled", "active", True)

    def test_review_records_latest_detection_and_source(self):
        latest = self.now + timezone.timedelta(seconds=1)
        captured, first, second = self.snapshotThen(
            lambda: PremiumSubscription.objects.filter(pk=self.record.pk).update(
                last_refund_or_dispute_at=latest, access_source="promo_code"
            )
        )
        with first, second:
            message = self.runAction("mark_refund_or_dispute_reviewed")
        self.assertEqual(captured, [True])
        audit = PremiumAuditLog.objects.get()
        self.assertEqual(audit.metadata["last_refund_or_dispute_at"], latest.isoformat())
        self.assertEqual(audit.source, "promo_code")
        self.assertEqual(message, "1件の返金/チャージバック検知を確認済みにしました。")

    def test_review_skips_detection_cleared_after_snapshot(self):
        captured, first, second = self.snapshotThen(
            lambda: PremiumSubscription.objects.filter(pk=self.record.pk).update(last_refund_or_dispute_at=None)
        )
        with first, second:
            message = self.runAction("mark_refund_or_dispute_reviewed")
        self.assertEqual(captured, [True])
        self.assertFalse(PremiumAuditLog.objects.exists())
        self.assertEqual(message, "0件の返金/チャージバック検知を確認済みにしました。")

    def test_revoke_uses_latest_source_without_changing_stripe_identity(self):
        captured, first, second = self.snapshotThen(
            lambda: PremiumSubscription.objects.filter(pk=self.record.pk).update(
                access_source="promo_code", stripe_subscription_id="sub_new_admin_fixture"
            )
        )
        with first, second:
            self.runAction("revoke_selected_access")
        self.assertEqual(captured, [True])
        self.record.refresh_from_db()
        self.assertEqual(self.record.stripe_subscription_id, "sub_new_admin_fixture")
        self.assertEqual(PremiumAuditLog.objects.get().source, "promo_code")

    def test_audit_failure_rolls_back_every_action_and_never_reports_success(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                PremiumSubscription.objects.filter(pk=self.record.pk).update(
                    subscription_status="active",
                    revoked_at=self.now if operation == "restore_selected_access" else None,
                    revoked_reason="fixture revocation" if operation == "restore_selected_access" else "",
                    last_refund_or_dispute_at=self.now,
                )
                get_user_model().objects.filter(pk=self.user.pk).update(
                    is_premium=operation != "restore_selected_access"
                )
                before = PremiumSubscription.objects.filter(pk=self.record.pk).values().get()
                flag = get_user_model().objects.get(pk=self.user.pk).is_premium
                admin = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
                admin.message_user = Mock()
                with (
                    patch(
                        "accounts.admin.create_premium_audit_log", side_effect=RuntimeError("isolated audit failure")
                    ),
                    self.assertRaisesMessage(RuntimeError, "isolated audit failure"),
                ):
                    getattr(admin, operation)(SimpleNamespace(user=self.actor), PremiumSubscription.objects.all())
                self.assertEqual(PremiumSubscription.objects.filter(pk=self.record.pk).values().get(), before)
                self.user.refresh_from_db()
                self.assertEqual(self.user.is_premium, flag)
                self.assertFalse(PremiumAuditLog.objects.exists())
                admin.message_user.assert_not_called()

    def assertDeletedRecordIsSkipped(self, operation):
        def delete_current_record():
            self.assertTrue(PremiumSubscription.objects.filter(pk=self.record.pk).exists())
            PremiumSubscription.objects.filter(pk=self.record.pk).delete()

        captured, first, second = self.snapshotThen(delete_current_record)
        with first, second:
            message = self.runAction(operation)
        self.assertEqual(captured, [True])
        self.assertTrue(message.startswith("0件"))
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_revoke_skips_deleted_record(self):
        self.assertDeletedRecordIsSkipped("revoke_selected_access")

    def test_restore_skips_deleted_record(self):
        self.assertDeletedRecordIsSkipped("restore_selected_access")

    def test_review_skips_deleted_record(self):
        self.assertDeletedRecordIsSkipped("mark_refund_or_dispute_reviewed")

    def test_restore_does_not_reactivate_revoked_subscription_status(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(subscription_status="revoked", revoked_at=self.now)
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=False)
        self.assertEqual(self.runAction("restore_selected_access"), "0件のユーザー権限を復旧しました。")
        self.user.refresh_from_db()
        self.record.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertEqual(self.record.subscription_status, "revoked")
        self.assertIsNone(self.record.revoked_at)

    def test_restore_preserves_existing_manual_override_policy(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(
            subscription_status="canceled", revoked_at=self.now
        )
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=False)
        PremiumAuditLog.objects.create(user=self.user, action="granted", source="manual")
        self.assertEqual(self.runAction("restore_selected_access"), "1件のユーザー権限を復旧しました。")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(PremiumAuditLog.objects.latest("pk").action, "restored")

    def test_bulk_actions_commit_in_pk_order_and_roll_back_only_failed_record(self):
        other_user = get_user_model().objects.create_user(username="admin-access-integrity-second")
        other = PremiumSubscription.objects.create(user=other_user, subscription_status="active")
        for operation in self.operations:
            with self.subTest(operation=operation):
                PremiumAuditLog.objects.all().delete()
                PremiumSubscription.objects.all().update(
                    subscription_status="active", revoked_at=self.now, last_refund_or_dispute_at=self.now
                )
                get_user_model().objects.filter(pk__in=(self.user.pk, other_user.pk)).update(
                    is_premium=operation != "restore_selected_access"
                )
                before = PremiumSubscription.objects.filter(pk=other.pk).values().get()
                other_flag = get_user_model().objects.get(pk=other_user.pk).is_premium
                admin = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
                admin.message_user = Mock()
                attempted = []

                def audit_or_fail(user, **kwargs):
                    attempted.append(kwargs["metadata"]["subscription_id"])
                    if user.pk == other_user.pk:
                        raise RuntimeError("second audit failure")
                    return PremiumAuditLog.objects.create(user=user, **kwargs)

                with (
                    patch("accounts.admin.create_premium_audit_log", side_effect=audit_or_fail),
                    self.assertRaisesMessage(RuntimeError, "second audit failure"),
                ):
                    getattr(admin, operation)(
                        SimpleNamespace(user=self.actor), PremiumSubscription.objects.order_by("-pk")
                    )
                self.assertEqual(attempted, [self.record.pk, other.pk])
                self.assertEqual(PremiumSubscription.objects.filter(pk=other.pk).values().get(), before)
                other_user.refresh_from_db()
                self.assertEqual(other_user.is_premium, other_flag)
                self.assertEqual(PremiumAuditLog.objects.get().user_id, self.user.pk)
                self.record.refresh_from_db()
                self.user.refresh_from_db()
                if operation == "revoke_selected_access":
                    self.assertEqual(self.record.subscription_status, "revoked")
                    self.assertFalse(self.user.is_premium)
                elif operation == "restore_selected_access":
                    self.assertIsNone(self.record.revoked_at)
                    self.assertTrue(self.user.is_premium)
                else:
                    self.assertIsNone(self.record.last_refund_or_dispute_at)
                admin.message_user.assert_not_called()

    def test_success_preserves_actor_metadata_and_existing_repeat_semantics(self):
        for operation, action in zip(self.operations, ("revoked", "restored", "reviewed"), strict=True):
            with self.subTest(operation=operation):
                PremiumAuditLog.objects.all().delete()
                PremiumSubscription.objects.filter(pk=self.record.pk).update(
                    subscription_status="active",
                    revoked_at=self.now,
                    revoked_reason="fixture",
                    last_refund_or_dispute_at=self.now,
                    access_source="stripe",
                )
                get_user_model().objects.filter(pk=self.user.pk).update(is_premium=False)
                self.runAction(operation)
                audit = PremiumAuditLog.objects.get()
                self.assertEqual(audit.action, action)
                self.assertEqual(audit.actor, self.actor)
                self.assertEqual(audit.source, "stripe")
                self.assertEqual(audit.metadata["subscription_id"], self.record.pk)
                self.runAction(operation, actor=False)
                # Revoke/restore record explicit operator attempts; review does not
                # create a duplicate when the detection has already been cleared.
                self.assertEqual(PremiumAuditLog.objects.count(), 1 if action == "reviewed" else 2)
                if action != "reviewed":
                    self.assertIsNone(PremiumAuditLog.objects.latest("pk").actor)


@skipUnlessDBFeature("has_select_for_update")
class AdminAccessConcurrencyTests(AdminAccessOperations, TransactionTestCase):
    def assertActionWaitsForCurrentRecord(self, operation):
        locked = Event()
        action_waiting = Event()
        latest = self.now + timezone.timedelta(seconds=1)

        def writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    record = PremiumSubscription.objects.select_for_update().get(pk=self.record.pk)
                    locked.set()
                    self.assertTrue(action_waiting.wait(timeout=10), "admin action did not attempt the shared row lock")
                    record.subscription_status = "canceled"
                    record.access_source = "promo_code"
                    record.last_refund_or_dispute_at = latest
                    record.save(update_fields=["subscription_status", "access_source", "last_refund_or_dispute_at"])
                    get_user_model().objects.filter(pk=self.user.pk).update(is_premium=False)
            finally:
                connections.close_all()

        def action():
            close_old_connections()
            try:
                self.assertTrue(locked.wait(timeout=10))

                def observe_lock(execute, sql, params, many, context):
                    if "FOR UPDATE" in sql and "accounts_premiumsubscription" in sql:
                        action_waiting.set()
                    return execute(sql, params, many, context)

                with connections["default"].execute_wrapper(observe_lock):
                    return self.runAction(operation)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            mutation = pool.submit(writer)
            administration = pool.submit(action)
            mutation.result(timeout=15)
            message = administration.result(timeout=15)
        self.user.refresh_from_db()
        self.record.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertEqual(
            self.record.subscription_status, "revoked" if operation == "revoke_selected_access" else "canceled"
        )
        audit = PremiumAuditLog.objects.get()
        self.assertEqual(audit.source, "promo_code")
        if operation == "mark_refund_or_dispute_reviewed":
            self.assertEqual(audit.metadata["last_refund_or_dispute_at"], latest.isoformat())
            self.assertIsNone(self.record.last_refund_or_dispute_at)
        if operation == "restore_selected_access":
            self.assertEqual(message, "0件のユーザー権限を復旧しました。")

    def test_revoke_waits_for_shared_subscription_lock(self):
        self.assertActionWaitsForCurrentRecord("revoke_selected_access")

    def test_restore_waits_for_shared_subscription_lock(self):
        self.assertActionWaitsForCurrentRecord("restore_selected_access")

    def test_review_waits_for_shared_subscription_lock(self):
        self.assertActionWaitsForCurrentRecord("mark_refund_or_dispute_reviewed")
