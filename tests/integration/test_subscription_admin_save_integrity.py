from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.admin.models import LogEntry
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import close_old_connections, connections, transaction
from django.forms import BooleanField, MultiWidget
from django.http import Http404
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from accounts.admin import PremiumSubscriptionAdmin
from accounts.billing_admin_forms import REVISION_SALT, PremiumSubscriptionAdminForm
from accounts.models import PremiumAuditLog, PremiumSubscription


class SubscriptionAdminSetup:
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="subscription-admin-integrity")
        self.actor = get_user_model().objects.create_user(
            username="subscription-admin-actor", is_staff=True, is_superuser=True
        )
        self.record = PremiumSubscription.objects.create(
            user=self.user,
            access_source="stripe",
            subscription_status="active",
            stripe_customer_id="cus_admin_fixture",
            stripe_subscription_id="sub_admin_fixture",
        )

    def saveAdmin(self, record, fields):
        PremiumSubscriptionAdmin(PremiumSubscription, AdminSite()).save_model(
            SimpleNamespace(user=self.actor), record, SimpleNamespace(changed_data=fields), True
        )

    def adminPayload(self, record=None, *, add=False):
        self.client.force_login(self.actor)
        url = (
            reverse("admin:accounts_premiumsubscription_add")
            if add
            else reverse("admin:accounts_premiumsubscription_change", args=[(record or self.record).pk])
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context["adminform"].form
        data = {"_save": "Save"}
        for name, field in form.fields.items():
            value = form[name].value()
            if isinstance(field.widget, MultiWidget):
                for index, part in enumerate(field.widget.decompress(value)):
                    data[f"{name}_{index}"] = str(part) if part is not None else ""
            elif isinstance(field, BooleanField):
                if value:
                    data[name] = "on"
            else:
                data[name] = value if value is not None else ""
        return url, data, response


class SubscriptionAdminSaveIntegrityTests(SubscriptionAdminSetup, TestCase):
    def test_direct_save_preserves_unedited_webhook_columns(self):
        now = timezone.now()
        PremiumSubscription.objects.filter(pk=self.record.pk).update(
            subscription_status="canceled",
            stripe_price_id="price_latest_fixture",
            last_payment_failed_at=now,
            last_refund_or_dispute_at=now,
            last_webhook_event_id="evt_latest_fixture",
        )
        self.record.revoked_reason = "運営の記録"
        self.saveAdmin(self.record, ["revoked_reason"])
        self.record.refresh_from_db()
        self.assertEqual(self.record.subscription_status, "canceled")
        self.assertEqual(self.record.stripe_price_id, "price_latest_fixture")
        self.assertEqual(self.record.last_payment_failed_at, now)
        self.assertEqual(self.record.last_refund_or_dispute_at, now)
        self.assertEqual(self.record.last_webhook_event_id, "evt_latest_fixture")
        self.assertEqual(self.record.revoked_reason, "運営の記録")

    def test_no_change_does_not_write_stale_columns_or_updated_timestamp(self):
        now = timezone.now()
        PremiumSubscription.objects.filter(pk=self.record.pk).update(subscription_status="canceled", updated_at=now)
        self.saveAdmin(self.record, [])
        self.record.refresh_from_db()
        self.assertEqual(self.record.subscription_status, "canceled")
        self.assertEqual(self.record.updated_at, now)

    def test_deleted_direct_save_target_is_not_recreated(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).delete()
        self.record.revoked_reason = "削除後の変更"
        with self.assertRaisesMessage(Http404, "課金情報が見つかりません。"):
            self.saveAdmin(self.record, ["revoked_reason"])
        self.assertFalse(PremiumSubscription.objects.exists())

    def test_actual_form_contains_hidden_revision_without_exposing_billing_values(self):
        _, data, response = self.adminPayload()
        self.assertIn("billing_revision", data)
        self.assertTrue(response.context["adminform"].form.fields["billing_revision"].widget.is_hidden)
        self.assertNotIn(self.record.stripe_customer_id, data["billing_revision"])
        self.assertNotIn(self.record.stripe_subscription_id, data["billing_revision"])

    def test_actual_post_rejects_webhook_change_after_page_was_opened(self):
        url, data, _ = self.adminPayload()
        now = timezone.now()
        # Include a writer that does not update updated_at: timestamp alone is insufficient.
        PremiumSubscription.objects.filter(pk=self.record.pk).update(
            subscription_status="canceled", last_webhook_event_id="evt_after_get", last_payment_failed_at=now
        )
        before = PremiumSubscription.objects.filter(pk=self.record.pk).values().get()
        data["revoked_reason"] = "古い画面からの編集"
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "課金情報が変更されています。ページを再読み込みして、内容を確認してから保存してください。"
        )
        self.assertEqual(PremiumSubscription.objects.filter(pk=self.record.pk).values().get(), before)
        self.assertFalse(LogEntry.objects.exists())
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_actual_post_rejects_missing_or_tampered_revision(self):
        url, data, _ = self.adminPayload()
        before = PremiumSubscription.objects.filter(pk=self.record.pk).values().get()
        for token in (None, "invalid.fixture.signature"):
            with self.subTest(token=token):
                payload = dict(data, revoked_reason="不正な確認情報")
                if token is None:
                    payload.pop("billing_revision", None)
                else:
                    payload["billing_revision"] = token
                response = self.client.post(url, payload)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "更新確認情報が無効です。ページを再読み込みしてください。")
        self.assertEqual(PremiumSubscription.objects.filter(pk=self.record.pk).values().get(), before)
        self.assertFalse(LogEntry.objects.exists())

    def test_actual_post_rejects_revision_from_different_record(self):
        url, data, _ = self.adminPayload()
        other = get_user_model().objects.create_user(username="subscription-admin-other")
        second = PremiumSubscription.objects.create(user=other)
        _, other_data, _ = self.adminPayload(second)
        data["billing_revision"] = other_data.get("billing_revision", "other-record")
        data["revoked_reason"] = "別レコードの確認情報"
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "課金情報が変更されています。ページを再読み込みして、内容を確認してから保存してください。"
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.revoked_reason, "")

    def test_actual_fresh_form_preserves_explicit_edit_and_existing_sync_behavior(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        url, data, _ = self.adminPayload()
        data.update(revoked_reason="新しい記録", subscription_status="canceled")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.record.refresh_from_db()
        self.assertEqual(self.record.subscription_status, "canceled")
        self.assertEqual(self.record.revoked_reason, "新しい記録")
        self.user.refresh_from_db()
        # Record editing has never implicitly synchronized the user's flag.
        self.assertTrue(self.user.is_premium)
        self.assertFalse(PremiumAuditLog.objects.exists())
        log = LogEntry.objects.get()
        self.assertEqual(log.user, self.actor)
        self.assertIn("Subscription status", log.change_message)
        self.assertNotIn("billing_revision", log.change_message)

    def test_actual_post_rejects_microsecond_change_in_readonly_column(self):
        now = timezone.now()
        PremiumSubscription.objects.filter(pk=self.record.pk).update(last_payment_failed_at=now)
        url, data, _ = self.adminPayload()
        PremiumSubscription.objects.filter(pk=self.record.pk).update(
            last_payment_failed_at=now + timedelta(microseconds=1)
        )
        response = self.client.post(url, dict(data, revoked_reason="精度を落とさない"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "課金情報が変更されています。ページを再読み込みして、内容を確認してから保存してください。"
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.revoked_reason, "")

    def test_actual_unchanged_post_does_not_update_timestamp_or_log_revision(self):
        url, data, _ = self.adminPayload()
        before = PremiumSubscription.objects.filter(pk=self.record.pk).values().get()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PremiumSubscription.objects.filter(pk=self.record.pk).values().get(), before)
        self.assertEqual(LogEntry.objects.get().change_message, "[]")

    def test_actual_post_cannot_write_readonly_fields(self):
        url, data, _ = self.adminPayload()
        data.update(revoked_reason="正規の編集", last_webhook_event_id="evt_forged_readonly")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.record.refresh_from_db()
        self.assertEqual(self.record.revoked_reason, "正規の編集")
        self.assertEqual(self.record.last_webhook_event_id, "")

    def test_fresh_form_can_explicitly_clear_period_end_cancellation_checkbox(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(cancel_at_period_end=True)
        url, data, _ = self.adminPayload()
        self.assertEqual(data.pop("cancel_at_period_end"), "on")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.record.refresh_from_db()
        self.assertFalse(self.record.cancel_at_period_end)

    def test_form_validation_handles_deleted_target_without_recreation(self):
        _, data, _ = self.adminPayload()
        form_type = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite()).get_form(
            SimpleNamespace(user=self.actor)
        )
        form = form_type(data, instance=self.record)
        PremiumSubscription.objects.filter(pk=self.record.pk).delete()
        self.assertFalse(form.is_valid())
        self.assertIn(
            "課金情報が変更されています。ページを再読み込みして、内容を確認してから保存してください。",
            form.non_field_errors(),
        )
        self.assertFalse(PremiumSubscription.objects.exists())

    def test_save_rechecks_revision_if_validated_form_is_used_outside_admin_transaction(self):
        _, data, _ = self.adminPayload()
        admin = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        form_type = admin.get_form(SimpleNamespace(user=self.actor))
        form = form_type(data, instance=self.record)
        self.assertIsInstance(form, PremiumSubscriptionAdminForm)
        self.assertTrue(form.is_valid(), form.errors)
        PremiumSubscription.objects.filter(pk=self.record.pk).update(last_webhook_event_id="evt_after_validation")
        form.instance.revoked_reason = "検証後の古い保存"
        with self.assertRaisesMessage(Http404, "課金情報が変更されています。再読み込みしてください。"):
            admin.save_model(SimpleNamespace(user=self.actor), form.instance, form, True)
        self.record.refresh_from_db()
        self.assertEqual(self.record.revoked_reason, "")
        self.assertEqual(self.record.last_webhook_event_id, "evt_after_validation")

    def test_legacy_form_none_remains_explicit_full_save(self):
        self.record.revoked_reason = "従来の明示的保存"
        PremiumSubscriptionAdmin(PremiumSubscription, AdminSite()).save_model(
            SimpleNamespace(user=self.actor), self.record, None, True
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.revoked_reason, "従来の明示的保存")

    def test_authenticated_but_wrong_revision_payload_is_rejected(self):
        url, data, _ = self.adminPayload()
        data["billing_revision"] = signing.dumps(["wrong-fixture-shape"], salt=REVISION_SALT)
        response = self.client.post(url, dict(data, revoked_reason="不正な形式"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "課金情報が変更されています。ページを再読み込みして、内容を確認してから保存してください。"
        )
        self.assertFalse(LogEntry.objects.exists())

    def test_actual_post_rolls_back_if_admin_log_fails(self):
        url, data, _ = self.adminPayload()
        before = PremiumSubscription.objects.filter(pk=self.record.pk).values().get()
        data["revoked_reason"] = "監査失敗時は保存しない"
        with (
            patch.object(
                PremiumSubscriptionAdmin, "log_change", side_effect=RuntimeError("isolated admin log failure")
            ),
            self.assertRaisesMessage(RuntimeError, "isolated admin log failure"),
        ):
            self.client.post(url, data)
        self.assertEqual(PremiumSubscription.objects.filter(pk=self.record.pk).values().get(), before)
        self.assertFalse(LogEntry.objects.exists())

    def test_staff_without_change_permission_is_rejected(self):
        url, data, _ = self.adminPayload()
        self.actor.is_superuser = False
        self.actor.save(update_fields=["is_superuser"])
        self.client.force_login(self.actor)
        response = self.client.post(url, dict(data, revoked_reason="権限なし"))
        self.assertEqual(response.status_code, 403)
        self.record.refresh_from_db()
        self.assertEqual(self.record.revoked_reason, "")

    def test_actual_add_keeps_existing_behavior_without_revision_requirement(self):
        user = get_user_model().objects.create_user(username="subscription-admin-new")
        url, data, _ = self.adminPayload(add=True)
        data.update(user=str(user.pk), access_source="manual", subscription_status="", revoked_reason="新規記録")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PremiumSubscription.objects.get(user=user).revoked_reason, "新規記録")
        self.assertFalse(PremiumAuditLog.objects.exists())


@skipUnlessDBFeature("has_select_for_update")
class SubscriptionAdminSaveConcurrencyTests(SubscriptionAdminSetup, TransactionTestCase):
    def test_actual_post_waits_for_writer_then_rejects_stale_revision(self):
        url, data, _ = self.adminPayload()
        locked = Event()
        waiting = Event()

        def writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    record = PremiumSubscription.objects.select_for_update().get(pk=self.record.pk)
                    locked.set()
                    self.assertTrue(waiting.wait(timeout=10))
                    record.subscription_status = "canceled"
                    record.last_webhook_event_id = "evt_during_post"
                    record.save(update_fields=["subscription_status", "last_webhook_event_id", "updated_at"])
            finally:
                connections.close_all()

        def mutation():
            close_old_connections()
            try:
                self.assertTrue(locked.wait(timeout=10))

                def observe(execute, sql, params, many, context):
                    if "accounts_premiumsubscription" in sql and "FOR UPDATE" in sql:
                        waiting.set()
                    return execute(sql, params, many, context)

                with connections["default"].execute_wrapper(observe):
                    response = self.client.post(url, dict(data, revoked_reason="待機後の古い編集"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response, "課金情報が変更されています。ページを再読み込みして、内容を確認してから保存してください。"
                )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(writer)
            second = pool.submit(mutation)
            first.result(timeout=15)
            second.result(timeout=15)
        self.record.refresh_from_db()
        self.assertEqual(self.record.subscription_status, "canceled")
        self.assertEqual(self.record.last_webhook_event_id, "evt_during_post")
        self.assertEqual(self.record.revoked_reason, "")
        self.assertFalse(LogEntry.objects.exists())

    def test_actual_post_holds_billing_lock_through_admin_log_and_commit(self):
        url, data, _ = self.adminPayload()
        logging = Event()
        waiting = Event()
        original_log = PremiumSubscriptionAdmin.log_change

        def log_change(admin, request, obj, message):
            logging.set()
            self.assertTrue(waiting.wait(timeout=10))
            return original_log(admin, request, obj, message)

        def writer():
            close_old_connections()
            try:
                self.assertTrue(logging.wait(timeout=10))

                def observe(execute, sql, params, many, context):
                    if "accounts_premiumsubscription" in sql and "FOR UPDATE" in sql:
                        waiting.set()
                    return execute(sql, params, many, context)

                with transaction.atomic(), connections["default"].execute_wrapper(observe):
                    record = PremiumSubscription.objects.select_for_update().get(pk=self.record.pk)
                    self.assertEqual(record.revoked_reason, "commitまでロック")
                    self.assertTrue(LogEntry.objects.filter(object_id=str(record.pk)).exists())
                    record.last_webhook_event_id = "evt_after_admin_commit"
                    record.save(update_fields=["last_webhook_event_id", "updated_at"])
            finally:
                connections.close_all()

        def mutation():
            close_old_connections()
            try:
                response = self.client.post(url, dict(data, revoked_reason="commitまでロック"))
                self.assertEqual(response.status_code, 302)
            finally:
                connections.close_all()

        with (
            patch.object(PremiumSubscriptionAdmin, "log_change", new=log_change),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            first = pool.submit(writer)
            second = pool.submit(mutation)
            first.result(timeout=15)
            second.result(timeout=15)
        self.record.refresh_from_db()
        self.assertEqual(self.record.revoked_reason, "commitまでロック")
        self.assertEqual(self.record.last_webhook_event_id, "evt_after_admin_commit")
        self.assertEqual(LogEntry.objects.count(), 1)

    def test_direct_partial_save_waits_for_existing_billing_writer(self):
        locked = Event()
        waiting = Event()

        def writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    record = PremiumSubscription.objects.select_for_update().get(pk=self.record.pk)
                    locked.set()
                    self.assertTrue(waiting.wait(timeout=10))
                    record.subscription_status = "canceled"
                    record.current_period_end = timezone.now() + timedelta(days=2)
                    record.last_webhook_event_id = "evt_locked_writer"
                    record.save(update_fields=["subscription_status", "current_period_end", "last_webhook_event_id"])
            finally:
                connections.close_all()

        def mutation():
            close_old_connections()
            try:
                self.assertTrue(locked.wait(timeout=10))

                def observe(execute, sql, params, many, context):
                    if "accounts_premiumsubscription" in sql and "FOR UPDATE" in sql:
                        waiting.set()
                    return execute(sql, params, many, context)

                with connections["default"].execute_wrapper(observe):
                    self.record.revoked_reason = "並行編集"
                    self.saveAdmin(self.record, ["revoked_reason"])
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(writer)
            second = pool.submit(mutation)
            first.result(timeout=15)
            second.result(timeout=15)
        self.record.refresh_from_db()
        self.assertEqual(self.record.subscription_status, "canceled")
        self.assertEqual(self.record.last_webhook_event_id, "evt_locked_writer")
        self.assertIsNotNone(self.record.current_period_end)
        self.assertEqual(self.record.revoked_reason, "並行編集")
