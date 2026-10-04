from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Barrier, Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import close_old_connections, connections
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from accounts.admin import PremiumSubscriptionAdmin
from accounts.billing import handle_checkout_completed
from accounts.models import PremiumAuditLog, PremiumSubscription


class ReconciliationOperations:
    def runReconciliation(self, operation, *, dry_run=False):
        if operation == "command":
            output = StringIO()
            call_command("reconcile_premium_access", skip_expire=True, dry_run=dry_run, stdout=output)
            return output.getvalue()
        admin = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        admin.message_user = Mock()
        request = SimpleNamespace(user=self.actor)
        admin.sync_selected_user_access(request, PremiumSubscription.objects.filter(pk=self.record.pk))
        return admin.message_user.call_args.args[1]

    def setUpRecords(self):
        self.user = get_user_model().objects.create_user(username="reconcile-integrity")
        self.actor = get_user_model().objects.create_user(username="reconcile-integrity-admin", is_staff=True)
        self.record = PremiumSubscription.objects.create(
            user=self.user, access_source="stripe", subscription_status="active"
        )


class PremiumReconciliationTests(ReconciliationOperations, TestCase):
    def setUp(self):
        self.setUpRecords()

    def assertLatestSnapshotUsed(self, operation, original_status, latest_status, latest_flag):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(subscription_status=original_status)
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=latest_flag)
        original_iter = QuerySet.__iter__
        original_iterator = QuerySet.iterator
        captured = []

        def change_after_snapshot(queryset, result):
            if queryset.model is PremiumSubscription and not queryset.query.select_for_update and not captured:
                captured.append(True)
                PremiumSubscription.objects.filter(pk=self.record.pk).update(subscription_status=latest_status)
                get_user_model().objects.filter(pk=self.user.pk).update(is_premium=latest_flag)
            return iter(result)

        def snapshot_iter(queryset):
            return change_after_snapshot(queryset, list(original_iter(queryset)))

        def snapshot_iterator(queryset, *args, **kwargs):
            return change_after_snapshot(queryset, list(original_iterator(queryset, *args, **kwargs)))

        with (
            patch.object(QuerySet, "__iter__", new=snapshot_iter),
            patch.object(QuerySet, "iterator", new=snapshot_iterator),
        ):
            result = self.runReconciliation(operation)

        self.assertEqual(captured, [True])
        self.user.refresh_from_db()
        self.assertEqual(self.user.is_premium, latest_flag)
        self.assertFalse(PremiumAuditLog.objects.exists())
        self.assertIn("changed=0" if operation == "command" else "0件のユーザー権限を再同期しました。", result)

    def test_command_does_not_restore_subscription_canceled_after_snapshot(self):
        self.assertLatestSnapshotUsed("command", "active", "canceled", False)

    def test_admin_does_not_restore_subscription_canceled_after_snapshot(self):
        self.assertLatestSnapshotUsed("admin", "active", "canceled", False)

    def test_command_does_not_revoke_subscription_activated_after_snapshot(self):
        self.assertLatestSnapshotUsed("command", "canceled", "active", True)

    def test_admin_does_not_revoke_subscription_activated_after_snapshot(self):
        self.assertLatestSnapshotUsed("admin", "canceled", "active", True)

    def test_command_audit_failure_rolls_back_user_change(self):
        with (
            patch(
                "accounts.management.commands.reconcile_premium_access.create_premium_audit_log",
                side_effect=RuntimeError("isolated audit failure"),
            ),
            self.assertRaisesMessage(RuntimeError, "isolated audit failure"),
        ):
            self.runReconciliation("command")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_admin_audit_failure_rolls_back_user_change(self):
        with (
            patch("accounts.admin.create_premium_audit_log", side_effect=RuntimeError("isolated audit failure")),
            self.assertRaisesMessage(RuntimeError, "isolated audit failure"),
        ):
            self.runReconciliation("admin")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_deleted_candidate_is_not_reconciled(self):
        original_first = QuerySet.first

        def delete_candidate(queryset):
            if queryset.model is PremiumSubscription and queryset.query.select_for_update:
                PremiumSubscription.objects.filter(pk=self.record.pk).delete()
            return original_first(queryset)

        for operation in ("command", "admin"):
            with self.subTest(operation=operation), patch.object(QuerySet, "first", new=delete_candidate):
                self.assertIsNotNone(PremiumSubscription.objects.filter(pk=self.record.pk).first())
                result = self.runReconciliation(operation)
            self.user.refresh_from_db()
            self.assertFalse(self.user.is_premium)
            self.assertFalse(PremiumAuditLog.objects.exists())
            self.assertIn("changed=0" if operation == "command" else "0件のユーザー権限を再同期しました。", result)
            if operation == "command":
                self.record = PremiumSubscription.objects.create(
                    user=self.user, access_source="stripe", subscription_status="active"
                )

    def test_command_dry_run_never_locks_or_writes(self):
        with patch.object(QuerySet, "select_for_update", side_effect=AssertionError("dry run must not lock")):
            result = self.runReconciliation("command", dry_run=True)
        self.assertIn("checked=1 changed=1 expired=0", result)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_success_is_idempotent_and_retains_actor_and_metadata(self):
        for operation in ("command", "admin"):
            with self.subTest(operation=operation):
                get_user_model().objects.filter(pk=self.user.pk).update(is_premium=False)
                PremiumAuditLog.objects.all().delete()
                result = self.runReconciliation(operation)
                self.assertIn("changed=1" if operation == "command" else "1件のユーザー権限を再同期しました。", result)
                result = self.runReconciliation(operation)
                self.assertIn("changed=0" if operation == "command" else "0件のユーザー権限を再同期しました。", result)
                audit = PremiumAuditLog.objects.get()
                self.assertEqual(audit.action, "granted")
                self.assertEqual(audit.source, "stripe")
                self.assertEqual(audit.actor, self.actor if operation == "admin" else None)
                self.assertEqual(audit.metadata["subscription_id"], self.record.pk)


@skipUnlessDBFeature("has_select_for_update")
class PremiumReconciliationConcurrencyTests(ReconciliationOperations, TransactionTestCase):
    def setUp(self):
        self.setUpRecords()

    def assertCheckoutWins(self, operation):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(subscription_status="canceled")
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=True)
        checkout_locked = Event()
        reconciliation_waiting = Event()
        stripe = Mock()

        def retrieve_current(subscription_id):
            self.assertEqual(subscription_id, "sub_reconcile_race")
            checkout_locked.set()
            self.assertTrue(reconciliation_waiting.wait(timeout=10))
            return {"id": subscription_id, "customer": "cus_reconcile_race", "status": "active"}

        stripe.Subscription.retrieve.side_effect = retrieve_current

        def checkout():
            close_old_connections()
            try:
                handle_checkout_completed(
                    {
                        "client_reference_id": str(self.user.pk),
                        "customer": "cus_reconcile_race",
                        "subscription": "sub_reconcile_race",
                    },
                    event_id="evt_reconcile_race",
                )
            finally:
                connections.close_all()

        def reconcile():
            close_old_connections()
            try:
                self.assertTrue(checkout_locked.wait(timeout=10))

                def observe_lock(execute, sql, params, many, context):
                    if "FOR UPDATE" in sql and "accounts_premiumsubscription" in sql:
                        reconciliation_waiting.set()
                    return execute(sql, params, many, context)

                with connections["default"].execute_wrapper(observe_lock):
                    return self.runReconciliation(operation)
            finally:
                connections.close_all()

        with patch("accounts.billing.get_stripe", return_value=stripe), ThreadPoolExecutor(max_workers=2) as pool:
            purchase = pool.submit(checkout)
            maintenance = pool.submit(reconcile)
            purchase.result(timeout=15)
            result = maintenance.result(timeout=15)

        self.user.refresh_from_db()
        self.record.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(self.record.subscription_status, "active")
        self.assertIn("changed=0" if operation == "command" else "0件のユーザー権限を再同期しました。", result)
        self.assertFalse(PremiumAuditLog.objects.filter(action="revoked").exists())

    def test_command_waits_for_checkout_and_keeps_new_access(self):
        self.assertCheckoutWins("command")

    def test_admin_waits_for_checkout_and_keeps_new_access(self):
        self.assertCheckoutWins("admin")

    def test_parallel_reconciliation_logs_one_change(self):
        barrier = Barrier(2)
        original_iterator = QuerySet.iterator
        original_iter = QuerySet.__iter__

        def snapshot(queryset, result):
            if queryset.model is PremiumSubscription and not queryset.query.select_for_update:
                barrier.wait(timeout=10)
            return iter(result)

        def snapshot_iterator(queryset, *args, **kwargs):
            return snapshot(queryset, list(original_iterator(queryset, *args, **kwargs)))

        def snapshot_iter(queryset):
            return snapshot(queryset, list(original_iter(queryset)))

        def reconcile(operation):
            close_old_connections()
            try:
                return self.runReconciliation(operation)
            finally:
                connections.close_all()

        with (
            patch.object(QuerySet, "iterator", new=snapshot_iterator),
            patch.object(QuerySet, "__iter__", new=snapshot_iter),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            results = [pool.submit(reconcile, operation) for operation in ("command", "admin")]
            outputs = [future.result(timeout=15) for future in results]

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(PremiumAuditLog.objects.filter(action="granted").count(), 1)
        self.assertEqual(sum("changed=1" in result or "1件" in result for result in outputs), 1)
