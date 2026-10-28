from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections, connections, transaction
from django.db.models.query import QuerySet
from django.forms import BooleanField, FileField, ModelMultipleChoiceField, MultiWidget
from django.http import Http404
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from accounts.admin import CustomUserAdmin, PremiumSubscriptionInline
from accounts.models import PremiumAuditLog, PremiumSubscription


class ManualPremiumSetup:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="manual-premium-integrity", nickname="original", email="manual-premium@example.test"
        )
        self.actor = get_user_model().objects.create_user(username="manual-premium-actor", is_staff=True)

    def saveAdmin(self, user, changed_fields=None, *, actor=True, change=True):
        form = SimpleNamespace(changed_data=changed_fields) if changed_fields is not None else None
        CustomUserAdmin(get_user_model(), AdminSite()).save_model(
            SimpleNamespace(user=self.actor if actor else None), user, form, change
        )

    def runCommand(self, enable=True, *, identifier=None):
        output = StringIO()
        call_command(
            "set_premium_user",
            identifier or self.user.username,
            "--on" if enable else "--off",
            "--reason",
            "isolated manual fixture",
            stdout=output,
        )
        return output.getvalue()


class ManualPremiumIntegrityTests(ManualPremiumSetup, TestCase):
    def test_profile_only_edit_preserves_new_purchase_and_other_unsubmitted_fields(self):
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=True, email="latest@example.test")
        self.user.nickname = "updated"
        self.saveAdmin(self.user, ["nickname", "groups"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(self.user.email, "latest@example.test")
        self.assertEqual(self.user.nickname, "updated")
        self.assertFalse(PremiumAuditLog.objects.exists())
        self.assertFalse(PremiumSubscription.objects.exists())

    def test_profile_only_edit_does_not_restore_access_canceled_after_form_read(self):
        self.user.is_premium = True
        self.user.nickname = "updated"
        self.saveAdmin(self.user, ["nickname"])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertEqual(self.user.nickname, "updated")
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_relation_only_edit_does_not_save_stale_premium_or_profile(self):
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=True, nickname="latest")
        self.saveAdmin(self.user, ["groups", "user_permissions"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(self.user.nickname, "latest")
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_admin_audit_failure_rolls_back_profile_access_and_new_lock_record(self):
        before = get_user_model().objects.filter(pk=self.user.pk).values().get()
        self.user.is_premium = True
        self.user.nickname = "updated"
        with (
            patch("accounts.admin.create_premium_audit_log", side_effect=RuntimeError("isolated audit failure")),
            self.assertRaisesMessage(RuntimeError, "isolated audit failure"),
        ):
            self.saveAdmin(self.user, ["nickname", "is_premium"])
        self.assertEqual(get_user_model().objects.filter(pk=self.user.pk).values().get(), before)
        self.assertFalse(PremiumSubscription.objects.exists())
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_new_admin_user_and_grant_roll_back_if_audit_fails(self):
        user = get_user_model()(username="new-manual-integrity", is_premium=True)
        with (
            patch("accounts.admin.create_premium_audit_log", side_effect=RuntimeError("isolated audit failure")),
            self.assertRaisesMessage(RuntimeError, "isolated audit failure"),
        ):
            self.saveAdmin(user, change=False)
        self.assertFalse(get_user_model().objects.filter(username="new-manual-integrity").exists())
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_command_audit_failure_rolls_back_access_and_new_lock_record(self):
        with (
            patch(
                "accounts.management.commands.set_premium_user.create_premium_audit_log",
                side_effect=RuntimeError("isolated audit failure"),
            ),
            self.assertRaisesMessage(RuntimeError, "isolated audit failure"),
        ):
            self.runCommand()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertFalse(PremiumSubscription.objects.exists())
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_deleted_admin_target_is_not_recreated(self):
        get_user_model().objects.filter(pk=self.user.pk).delete()
        self.user.is_premium = True
        with self.assertRaisesMessage(Http404, "ユーザーが見つかりません。"):
            self.saveAdmin(self.user, ["is_premium"])
        self.assertFalse(get_user_model().objects.filter(username=self.user.username).exists())
        self.assertFalse(PremiumSubscription.objects.exists())
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_command_target_deleted_after_lookup_fails_without_success_or_recreation(self):
        original_first = QuerySet.first
        captured = []

        def delete_after_lookup(queryset):
            result = original_first(queryset)
            if queryset.model is get_user_model() and result and result.pk == self.user.pk and not captured:
                captured.append(True)
                get_user_model().objects.filter(pk=self.user.pk).delete()
            return result

        output = StringIO()
        with (
            patch.object(QuerySet, "first", new=delete_after_lookup),
            self.assertRaisesMessage(CommandError, "対象ユーザーは削除されています。"),
        ):
            call_command("set_premium_user", self.user.email, "--on", stdout=output)
        self.assertEqual(captured, [True])
        self.assertEqual(output.getvalue(), "")
        self.assertFalse(get_user_model().objects.filter(username=self.user.username).exists())
        self.assertFalse(PremiumSubscription.objects.exists())
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_deleted_profile_target_is_not_recreated(self):
        get_user_model().objects.filter(pk=self.user.pk).delete()
        with self.assertRaisesMessage(Http404, "ユーザーが見つかりません。"):
            self.saveAdmin(self.user, ["nickname"])
        self.assertFalse(get_user_model().objects.filter(username=self.user.username).exists())

    def test_missing_command_target_reports_failure_without_writes(self):
        with self.assertRaisesMessage(CommandError, "User not found: isolated-missing-user"):
            call_command("set_premium_user", "isolated-missing-user", stdout=StringIO())
        self.assertFalse(PremiumAuditLog.objects.exists())
        self.assertFalse(PremiumSubscription.objects.exists())

    def test_command_rejects_user_without_premium_field_before_writing(self):
        unsupported_user = SimpleNamespace(username="unsupported-fixture")
        model = SimpleNamespace(
            objects=SimpleNamespace(filter=lambda **kwargs: SimpleNamespace(first=lambda: unsupported_user))
        )
        with (
            patch("accounts.management.commands.set_premium_user.get_user_model", return_value=model),
            self.assertRaisesMessage(CommandError, "This project does not have is_premium on the user model."),
        ):
            call_command("set_premium_user", "unsupported-fixture", stdout=StringIO())
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_manual_changes_preserve_billing_identity_and_actor_contract(self):
        record = PremiumSubscription.objects.create(
            user=self.user,
            subscription_status="active",
            access_source="stripe",
            stripe_customer_id="cus_manual_fixture",
            stripe_subscription_id="sub_manual_fixture",
        )
        before = PremiumSubscription.objects.filter(pk=record.pk).values().get()
        self.user.is_premium = True
        self.saveAdmin(self.user, ["is_premium"])
        audit = PremiumAuditLog.objects.get()
        self.assertEqual(audit.actor, self.actor)
        self.assertEqual(audit.action, "granted")
        self.assertEqual(audit.source, "manual")
        self.assertEqual(audit.metadata, {"admin_model": "CustomUser", "field": "is_premium"})
        self.assertEqual(audit.reason, "Manual premium access updated in Django admin")
        self.user.is_premium = False
        self.saveAdmin(self.user, ["is_premium"], actor=False)
        self.assertIsNone(PremiumAuditLog.objects.latest("pk").actor)
        self.assertEqual(PremiumAuditLog.objects.latest("pk").action, "revoked")
        self.assertEqual(PremiumSubscription.objects.filter(pk=record.pk).values().get(), before)

    def test_new_admin_users_preserve_grant_and_no_grant_behavior(self):
        for enable in (False, True):
            with self.subTest(enable=enable):
                user = get_user_model()(username=f"new-manual-{enable}", is_premium=enable)
                self.saveAdmin(user, change=False)
                self.assertEqual(PremiumAuditLog.objects.filter(user=user).exists(), enable)
                self.assertFalse(PremiumSubscription.objects.filter(user=user).exists())

    def test_command_email_lookup_and_repeat_do_not_duplicate_audit(self):
        self.assertIn("is_premium=ON", self.runCommand(identifier=self.user.email))
        self.runCommand()
        self.assertEqual(PremiumAuditLog.objects.count(), 1)
        self.assertEqual(PremiumAuditLog.objects.get().metadata, {"command": "set_premium_user"})
        self.assertEqual(PremiumAuditLog.objects.get().reason, "isolated manual fixture")
        self.assertIn("is_premium=OFF", self.runCommand(False))
        self.runCommand(False)
        self.assertEqual(PremiumAuditLog.objects.count(), 2)

    def assertUnchangedLegacyGrantDoesNotBecomeReconciliationCandidate(self, operation):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        if operation == "command":
            self.runCommand()
        else:
            self.saveAdmin(self.user)
        self.assertFalse(PremiumSubscription.objects.filter(user=self.user).exists())
        call_command("reconcile_premium_access", "--skip-expire", stdout=StringIO())
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertFalse(PremiumAuditLog.objects.filter(user=self.user).exists())

    def test_unchanged_legacy_command_grant_does_not_create_inactive_reconciliation_candidate(self):
        self.assertUnchangedLegacyGrantDoesNotBecomeReconciliationCandidate("command")

    def test_unchanged_legacy_admin_grant_does_not_create_inactive_reconciliation_candidate(self):
        self.assertUnchangedLegacyGrantDoesNotBecomeReconciliationCandidate("admin")

    def test_subscription_inline_already_disallows_model_edits_and_creation(self):
        inline = PremiumSubscriptionInline(get_user_model(), AdminSite())
        field_names = {name for group in inline.fields for name in (group if isinstance(group, tuple) else (group,))}
        self.assertLessEqual(field_names, set(inline.readonly_fields))
        self.assertFalse(inline.has_add_permission(SimpleNamespace(user=self.actor), self.user))
        self.assertFalse(inline.can_delete)

    def adminFormPayload(self):
        self.actor.is_superuser = True
        self.actor.save(update_fields=["is_superuser"])
        self.client.force_login(self.actor)
        url = reverse("admin:accounts_customuser_change", args=[self.user.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context["adminform"].form
        data = {"_save": "Save"}
        for name, field in form.fields.items():
            value = form[name].value()
            if isinstance(field, FileField):
                continue
            if isinstance(field.widget, MultiWidget):
                for index, part in enumerate(field.widget.decompress(value)):
                    data[f"{name}_{index}"] = str(part) if part is not None else ""
            elif isinstance(field, BooleanField):
                if value:
                    data[name] = "on"
            elif isinstance(field, ModelMultipleChoiceField):
                data[name] = value or []
            else:
                data[name] = value if value is not None else ""
        for inline in response.context["inline_admin_formsets"]:
            prefix = inline.formset.prefix
            data.update(
                {
                    f"{prefix}-TOTAL_FORMS": str(inline.formset.total_form_count()),
                    f"{prefix}-INITIAL_FORMS": str(inline.formset.initial_form_count()),
                    f"{prefix}-MIN_NUM_FORMS": "0",
                    f"{prefix}-MAX_NUM_FORMS": "1000",
                }
            )
        return url, data

    def test_actual_admin_profile_post_preserves_billing_change_and_saves_groups(self):
        url, data = self.adminFormPayload()
        group = Group.objects.create(name="isolated-admin-group")
        data.update(nickname="フォーム更新", groups=[str(group.pk)])
        original_save = CustomUserAdmin.save_model

        def billing_change_before_save(admin, request, obj, form, change):
            self.assertNotIn("is_premium", form.changed_data)
            get_user_model().objects.filter(pk=obj.pk).update(is_premium=True)
            return original_save(admin, request, obj, form, change)

        with patch.object(CustomUserAdmin, "save_model", new=billing_change_before_save):
            response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(self.user.nickname, "フォーム更新")
        self.assertEqual(list(self.user.groups.all()), [group])
        self.assertFalse(PremiumAuditLog.objects.filter(user=self.user).exists())
        self.assertFalse(PremiumSubscription.objects.filter(user=self.user).exists())

    def test_actual_admin_explicit_premium_post_creates_one_manual_audit(self):
        url, data = self.adminFormPayload()
        data.update(nickname="手動付与", is_premium="on")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(self.user.nickname, "手動付与")
        audit = PremiumAuditLog.objects.get(user=self.user)
        self.assertEqual(audit.action, "granted")
        self.assertEqual(audit.source, "manual")
        self.assertEqual(audit.actor, self.actor)

    def test_staff_without_user_change_permission_cannot_grant_access(self):
        self.client.force_login(self.actor)
        url = reverse("admin:accounts_customuser_change", args=[self.user.pk])
        response = self.client.post(url, {"username": self.user.username, "is_premium": "on", "_save": "Save"})
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertFalse(PremiumAuditLog.objects.exists())


@skipUnlessDBFeature("has_select_for_update")
class ManualPremiumConcurrencyTests(ManualPremiumSetup, TransactionTestCase):
    def assertLateDeletionFailsClosed(self, operation, *, remove_user):
        record = PremiumSubscription.objects.create(user=self.user, subscription_status="active")
        self.user.is_premium = True
        looked_up = Event()
        deleted = Event()
        original_get = QuerySet.get
        captured = []

        def observe_lookup(queryset, *args, **kwargs):
            result = original_get(queryset, *args, **kwargs)
            if queryset.model is PremiumSubscription and not queryset.query.select_for_update and not captured:
                captured.append(True)
                looked_up.set()
                self.assertTrue(deleted.wait(timeout=10))
            return result

        def deletion():
            close_old_connections()
            try:
                with transaction.atomic():
                    PremiumSubscription.objects.select_for_update().get(pk=record.pk)
                    self.assertTrue(looked_up.wait(timeout=10))
                    if remove_user:
                        get_user_model().objects.filter(pk=self.user.pk).delete()
                    else:
                        PremiumSubscription.objects.filter(pk=record.pk).delete()
                deleted.set()
            finally:
                connections.close_all()

        def mutation():
            close_old_connections()
            try:
                if operation == "admin":
                    with self.assertRaisesMessage(Http404, "課金情報が変更されています。再読み込みしてください。"):
                        self.saveAdmin(self.user, ["is_premium"])
                else:
                    output = StringIO()
                    with self.assertRaisesMessage(CommandError, "課金情報が変更されています。再試行してください。"):
                        call_command("set_premium_user", self.user.username, "--on", stdout=output)
                    self.assertEqual(output.getvalue(), "")
            finally:
                connections.close_all()

        with patch.object(QuerySet, "get", new=observe_lookup), ThreadPoolExecutor(max_workers=2) as pool:
            removal = pool.submit(deletion)
            manual = pool.submit(mutation)
            removal.result(timeout=15)
            manual.result(timeout=15)
        self.assertEqual(captured, [True])
        self.assertFalse(PremiumSubscription.objects.filter(pk=record.pk).exists())
        self.assertFalse(PremiumAuditLog.objects.exists())
        if remove_user:
            self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
        else:
            self.user.refresh_from_db()
            self.assertFalse(self.user.is_premium)

    def test_admin_rejects_user_deleted_between_billing_lookup_and_lock(self):
        self.assertLateDeletionFailsClosed("admin", remove_user=True)

    def test_admin_rejects_record_deleted_between_billing_lookup_and_lock(self):
        self.assertLateDeletionFailsClosed("admin", remove_user=False)

    def test_command_rejects_user_deleted_between_billing_lookup_and_lock(self):
        self.assertLateDeletionFailsClosed("command", remove_user=True)

    def test_command_rejects_record_deleted_between_billing_lookup_and_lock(self):
        self.assertLateDeletionFailsClosed("command", remove_user=False)

    def assertWaitsForBillingWriter(self, operation, *, initial_flag=True, new_record=False):
        get_user_model().objects.filter(pk=self.user.pk).update(is_premium=initial_flag)
        self.user.is_premium = initial_flag
        if not new_record:
            PremiumSubscription.objects.create(user=self.user, subscription_status="active", access_source="stripe")
        locked = Event()
        waiting = Event()

        def writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    if new_record:
                        record = PremiumSubscription.objects.create(
                            user_id=self.user.pk, subscription_status="canceled", access_source="stripe"
                        )
                    else:
                        record = PremiumSubscription.objects.select_for_update().get(user_id=self.user.pk)
                    locked.set()
                    self.assertTrue(waiting.wait(timeout=10), "manual mutation did not reach billing serialization")
                    record.subscription_status = "canceled"
                    record.save(update_fields=["subscription_status"])
                    get_user_model().objects.filter(pk=self.user.pk).update(is_premium=not initial_flag)
            finally:
                connections.close_all()

        def mutation():
            close_old_connections()
            try:
                self.assertTrue(locked.wait(timeout=10))

                def observe(execute, sql, params, many, context):
                    if "accounts_premiumsubscription" in sql and (
                        (new_record and sql.startswith("INSERT")) or (not new_record and "FOR UPDATE" in sql)
                    ):
                        waiting.set()
                    return execute(sql, params, many, context)

                with connections["default"].execute_wrapper(observe):
                    if operation == "admin":
                        self.saveAdmin(self.user, ["is_premium"])
                    else:
                        self.runCommand(initial_flag)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            billing = pool.submit(writer)
            manual = pool.submit(mutation)
            billing.result(timeout=15)
            manual.result(timeout=15)
        self.user.refresh_from_db()
        self.assertEqual(self.user.is_premium, initial_flag)
        record = PremiumSubscription.objects.get(user_id=self.user.pk)
        self.assertEqual(record.subscription_status, "canceled")
        self.assertEqual(record.access_source, "stripe")
        audit = PremiumAuditLog.objects.get()
        self.assertEqual(audit.action, "granted" if initial_flag else "revoked")
        self.assertEqual(audit.source, "manual")
        self.assertEqual(audit.actor, self.actor if operation == "admin" else None)

    def test_admin_grant_reads_flag_after_existing_billing_writer_commits(self):
        self.assertWaitsForBillingWriter("admin")

    def test_command_grant_reads_flag_after_existing_billing_writer_commits(self):
        self.assertWaitsForBillingWriter("command")

    def test_command_revoke_reads_flag_after_existing_billing_writer_commits(self):
        self.assertWaitsForBillingWriter("command", initial_flag=False)

    def test_admin_waits_for_concurrently_created_first_billing_record(self):
        self.assertWaitsForBillingWriter("admin", new_record=True)

    def test_command_waits_for_concurrently_created_first_billing_record(self):
        self.assertWaitsForBillingWriter("command", new_record=True)
