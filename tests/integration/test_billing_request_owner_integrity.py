from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from functools import partial
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.db import OperationalError, close_old_connections, connections, transaction
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.billing import create_checkout_session, create_portal_session, get_or_create_stripe_customer
from accounts.models import PremiumAuditLog, PremiumSubscription, StripeBillingRequest

OWNER_ERROR = "課金情報の対応を確認できません。お問い合わせ窓口へご連絡ください。"


class BillingRequestOwnerSetup:
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="billing-request-owner")
        self.other = get_user_model().objects.create_user(username="billing-request-other")
        self.record = PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_owner_fixture")
        self.request = RequestFactory().post("/api/billing/checkout/")
        self.request.user = self.user
        self.stripe = Mock()
        self.stripe.v1.customers.create.return_value = SimpleNamespace(id="cus_created_fixture")
        self.stripe.v1.subscriptions.list.return_value.auto_paging_iter.side_effect = lambda: iter([])
        self.stripe.v1.checkout.sessions.list.return_value.auto_paging_iter.side_effect = lambda: iter([])
        self.session = SimpleNamespace(id="cs_owner_fixture", status="open", url="https://checkout.stripe.test/fixture")
        self.stripe.v1.checkout.sessions.create.return_value = self.session
        self.stripe.v1.checkout.sessions.retrieve.return_value = self.session
        self.stripe.v1.billing_portal.sessions.create.return_value = SimpleNamespace(
            url="https://billing.stripe.test/fixture"
        )
        stripe_patch = patch("accounts.billing.get_stripe", return_value=self.stripe)
        stripe_patch.start()
        self.addCleanup(stripe_patch.stop)

    def assertNoRemoteMutation(self):
        self.stripe.v1.customers.create.assert_not_called()
        self.stripe.v1.checkout.sessions.create.assert_not_called()
        self.stripe.v1.checkout.sessions.retrieve.assert_not_called()
        self.stripe.v1.checkout.sessions.expire.assert_not_called()
        self.stripe.v1.billing_portal.sessions.create.assert_not_called()
        self.assertFalse(PremiumAuditLog.objects.exists())
        self.user.refresh_from_db()
        self.other.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertFalse(self.other.is_premium)

    def saveUncertainCheckout(self):
        self.stripe.v1.checkout.sessions.create.side_effect = TimeoutError("isolated response lost")
        with self.assertRaises(TimeoutError):
            create_checkout_session(self.request)
        self.stripe.v1.checkout.sessions.create.side_effect = None
        self.stripe.reset_mock()
        return StripeBillingRequest.objects.get(subscription=self.record, operation="checkout")


@override_settings(STRIPE_PREMIUM_PRICE_ID="price_owner_fixture", STRIPE_CHECKOUT_ENABLED=True)
class BillingRequestOwnerIntegrityTests(BillingRequestOwnerSetup, TestCase):
    def test_customer_rejects_owner_changed_after_lookup(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(user=self.other, stripe_customer_id="")
        with patch("accounts.billing.get_or_create_subscription_record", return_value=self.record):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                get_or_create_stripe_customer(self.user)
        self.assertFalse(StripeBillingRequest.objects.exists())
        self.assertNoRemoteMutation()

    def test_customer_rejects_owner_changed_between_intent_and_execution(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(stripe_customer_id="")
        original = StripeBillingRequest.objects.get_or_create

        def transfer_after_intent(**kwargs):
            result = original(**kwargs)
            PremiumSubscription.objects.filter(pk=self.record.pk).update(user=self.other)
            return result

        with patch.object(StripeBillingRequest.objects, "get_or_create", side_effect=transfer_after_intent):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                get_or_create_stripe_customer(self.user)
        attempt = StripeBillingRequest.objects.get(subscription=self.record, operation="customer")
        self.assertEqual(attempt.parameters["metadata"]["user_id"], str(self.user.pk))
        self.assertEqual(attempt.resource_id, "")
        self.record.refresh_from_db()
        self.assertEqual(self.record.user_id, self.other.pk)
        self.assertEqual(self.record.stripe_customer_id, "")
        self.assertNoRemoteMutation()

    def test_customer_rejects_mismatched_saved_intent_without_replacing_key(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(stripe_customer_id="")
        self.stripe.v1.customers.create.side_effect = TimeoutError("isolated response lost")
        with self.assertRaises(TimeoutError):
            get_or_create_stripe_customer(self.user)
        attempt = StripeBillingRequest.objects.get(subscription=self.record, operation="customer")
        self.stripe.reset_mock()
        self.stripe.v1.customers.create.side_effect = None
        for parameters in [[], {}, {"metadata": None}, {"metadata": []}, {"metadata": {"user_id": str(self.other.pk)}}]:
            with self.subTest(parameters=parameters), transaction.atomic():
                self.stripe.reset_mock()
                StripeBillingRequest.objects.filter(pk=attempt.pk).update(parameters=parameters)
                before = StripeBillingRequest.objects.values().get(pk=attempt.pk)
                with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                    get_or_create_stripe_customer(self.user)
                self.assertEqual(StripeBillingRequest.objects.values().get(pk=attempt.pk), before)
                self.assertNoRemoteMutation()

    def test_customer_rechecks_saved_intent_before_execution(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(stripe_customer_id="")
        original = StripeBillingRequest.objects.get_or_create

        def change_after_intent(**kwargs):
            attempt, created = original(**kwargs)
            parameters = dict(attempt.parameters, metadata={"user_id": str(self.other.pk)})
            StripeBillingRequest.objects.filter(pk=attempt.pk).update(parameters=parameters)
            return attempt, created

        with patch.object(StripeBillingRequest.objects, "get_or_create", side_effect=change_after_intent):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                get_or_create_stripe_customer(self.user)
        attempt = StripeBillingRequest.objects.get(subscription=self.record, operation="customer")
        self.assertEqual(attempt.parameters["metadata"]["user_id"], str(self.other.pk))
        self.assertEqual(attempt.resource_id, "")
        self.assertNoRemoteMutation()

    def test_checkout_rejects_owner_changed_after_customer_lookup(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(user=self.other)
        with patch("accounts.billing.get_or_create_stripe_customer", return_value=self.record):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                create_checkout_session(self.request)
        self.stripe.v1.subscriptions.list.assert_not_called()
        self.assertFalse(StripeBillingRequest.objects.exists())
        self.assertNoRemoteMutation()

    def test_checkout_rejects_customer_changed_after_customer_lookup(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(stripe_customer_id="cus_changed_fixture")
        with patch("accounts.billing.get_or_create_stripe_customer", return_value=self.record):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                create_checkout_session(self.request)
        self.stripe.v1.subscriptions.list.assert_not_called()
        self.assertNoRemoteMutation()

    def test_checkout_rejects_missing_customer_without_remote_query(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(stripe_customer_id="")
        self.record.stripe_customer_id = ""
        with patch("accounts.billing.get_or_create_stripe_customer", return_value=self.record):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                create_checkout_session(self.request)
        self.stripe.v1.subscriptions.list.assert_not_called()
        self.assertFalse(StripeBillingRequest.objects.exists())
        self.assertNoRemoteMutation()

    def test_checkout_rejects_owner_changed_between_intent_and_execution(self):
        original = StripeBillingRequest.objects.create

        def transfer_after_intent(**kwargs):
            result = original(**kwargs)
            PremiumSubscription.objects.filter(pk=self.record.pk).update(user=self.other)
            return result

        with patch.object(StripeBillingRequest.objects, "create", side_effect=transfer_after_intent):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                create_checkout_session(self.request)
        attempt = StripeBillingRequest.objects.get(subscription=self.record, operation="checkout")
        self.assertEqual(attempt.parameters["client_reference_id"], str(self.user.pk))
        self.assertEqual(attempt.resource_id, "")
        self.assertEqual(self.stripe.v1.subscriptions.list.call_count, 1)
        self.assertNoRemoteMutation()

    def test_checkout_rejects_customer_changed_between_intent_and_execution(self):
        original = StripeBillingRequest.objects.create

        def change_after_intent(**kwargs):
            result = original(**kwargs)
            PremiumSubscription.objects.filter(pk=self.record.pk).update(stripe_customer_id="cus_changed_fixture")
            return result

        with patch.object(StripeBillingRequest.objects, "create", side_effect=change_after_intent):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                create_checkout_session(self.request)
        attempt = StripeBillingRequest.objects.get(subscription=self.record, operation="checkout")
        self.assertEqual(attempt.parameters["customer"], "cus_owner_fixture")
        self.assertEqual(attempt.resource_id, "")
        self.assertEqual(self.stripe.v1.subscriptions.list.call_count, 1)
        self.assertNoRemoteMutation()

    def test_unknown_checkout_status_keeps_retry_intent(self):
        attempt = self.saveUncertainCheckout()
        before = StripeBillingRequest.objects.values().get(pk=attempt.pk)
        self.stripe.v1.checkout.sessions.create.return_value = SimpleNamespace(
            id="cs_unknown_fixture", status="unknown"
        )
        with self.assertRaisesMessage(ValueError, "購入処理を確認できません。時間をおいて再度お試しください。"):
            create_checkout_session(self.request)
        self.assertEqual(StripeBillingRequest.objects.values().get(pk=attempt.pk), before)
        self.stripe.v1.checkout.sessions.create.assert_called_once()
        self.assertEqual(
            self.stripe.v1.checkout.sessions.create.call_args.kwargs["options"]["idempotency_key"],
            str(attempt.idempotency_key),
        )
        self.stripe.v1.checkout.sessions.expire.assert_not_called()

    def test_checkout_iteration_limit_keeps_last_committed_intent(self):
        self.stripe.v1.checkout.sessions.create.return_value = SimpleNamespace(
            id="cs_expired_fixture", status="expired"
        )
        with self.assertRaisesMessage(ValueError, "別の購入操作が進行中です。時間をおいて再度お試しください。"):
            create_checkout_session(self.request)
        calls = self.stripe.v1.checkout.sessions.create.call_args_list
        self.assertEqual(len(calls), 3)
        self.assertEqual(len({call.kwargs["options"]["idempotency_key"] for call in calls}), 3)
        attempt = StripeBillingRequest.objects.get(subscription=self.record, operation="checkout")
        self.assertEqual(attempt.parameters["client_reference_id"], str(self.user.pk))
        self.assertEqual(attempt.resource_id, "")
        self.stripe.v1.checkout.sessions.expire.assert_not_called()

    def test_checkout_rejects_mismatched_saved_intent_before_read_or_write(self):
        attempt = self.saveUncertainCheckout()
        original_parameters = deepcopy(attempt.parameters)
        changes = [
            {},
            {"metadata": None},
            {"metadata": []},
            {"metadata": {"user_id": str(self.other.pk)}},
            {"customer": "cus_other_fixture"},
            {"client_reference_id": str(self.other.pk)},
            {"subscription_data": None},
            {"subscription_data": {"metadata": None}},
            {"subscription_data": {"metadata": {"user_id": str(self.other.pk)}}},
        ]
        for resource_id in ["", "cs_saved_fixture"]:
            for change in changes:
                with self.subTest(resource_id=resource_id, change=change), transaction.atomic():
                    self.stripe.reset_mock()
                    parameters = dict(original_parameters, **change) if change else {}
                    StripeBillingRequest.objects.filter(pk=attempt.pk).update(
                        parameters=parameters, resource_id=resource_id
                    )
                    before = StripeBillingRequest.objects.values().get(pk=attempt.pk)
                    with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                        create_checkout_session(self.request)
                    self.assertEqual(StripeBillingRequest.objects.values().get(pk=attempt.pk), before)
                    self.stripe.v1.subscriptions.list.assert_not_called()
                    self.assertNoRemoteMutation()

    def test_transferred_checkout_intent_is_not_executed_for_new_owner(self):
        attempt = self.saveUncertainCheckout()
        PremiumSubscription.objects.filter(pk=self.record.pk).update(user=self.other)
        self.request.user = self.other
        before = StripeBillingRequest.objects.values().get(pk=attempt.pk)
        with self.assertRaisesMessage(ValueError, OWNER_ERROR):
            create_checkout_session(self.request)
        self.assertEqual(StripeBillingRequest.objects.values().get(pk=attempt.pk), before)
        self.assertNoRemoteMutation()

    def test_portal_rejects_owner_changed_after_lookup(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(user=self.other)
        with patch("accounts.billing.get_or_create_subscription_record", return_value=self.record):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                create_portal_session(self.request)
        self.assertNoRemoteMutation()

    def test_portal_rejects_customer_changed_after_lookup(self):
        PremiumSubscription.objects.filter(pk=self.record.pk).update(stripe_customer_id="cus_changed_fixture")
        with patch("accounts.billing.get_or_create_subscription_record", return_value=self.record):
            with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                create_portal_session(self.request)
        self.assertNoRemoteMutation()

    def test_api_reports_owner_mismatch_in_japanese_without_resource_url(self):
        client = APIClient()
        client.force_authenticate(self.user)
        PremiumSubscription.objects.filter(pk=self.record.pk).update(user=self.other)
        for endpoint in ["billing-checkout-session", "billing-portal-session"]:
            with self.subTest(endpoint=endpoint):
                with patch("accounts.billing.get_or_create_subscription_record", return_value=self.record):
                    response = client.post(reverse(endpoint))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data, {"error": OWNER_ERROR})
        self.assertNoRemoteMutation()


@skipUnlessDBFeature("has_select_for_update")
@override_settings(STRIPE_PREMIUM_PRICE_ID="price_owner_fixture")
class BillingRequestOwnerLockTests(BillingRequestOwnerSetup, TransactionTestCase):
    def assertRemoteCallHoldsLock(self, operation):
        called = Event()
        waiting = Event()
        acquired = Event()
        if operation == "customer":
            PremiumSubscription.objects.filter(pk=self.record.pk).update(stripe_customer_id="")
            remote = self.stripe.v1.customers.create
            function = partial(get_or_create_stripe_customer, self.user)
            result = SimpleNamespace(id="cus_created_fixture")
        elif operation == "checkout":
            remote = self.stripe.v1.checkout.sessions.create
            function = partial(create_checkout_session, self.request)
            result = self.session
        else:
            remote = self.stripe.v1.billing_portal.sessions.create
            function = partial(create_portal_session, self.request)
            result = SimpleNamespace(url="https://billing.stripe.test/fixture")

        def create(**kwargs):
            called.set()
            self.assertTrue(waiting.wait(timeout=10))
            self.assertFalse(acquired.is_set())
            return result

        remote.side_effect = create

        def writer():
            close_old_connections()
            try:
                self.assertTrue(called.wait(timeout=10))

                # NOWAIT proves a real conflicting row lock, not thread scheduling.
                try:
                    with self.assertRaises(OperationalError) as error, transaction.atomic():
                        PremiumSubscription.objects.select_for_update(nowait=True).get(pk=self.record.pk)
                    self.assertEqual(
                        getattr(error.exception.__cause__, "sqlstate", None)
                        or getattr(error.exception.__cause__, "pgcode", None),
                        "55P03",
                    )
                finally:
                    waiting.set()

                def observe(execute, sql, params, many, context):
                    if "accounts_premiumsubscription" in sql and "FOR UPDATE" in sql:
                        waiting.set()
                    return execute(sql, params, many, context)

                with transaction.atomic(), connections["default"].execute_wrapper(observe):
                    record = PremiumSubscription.objects.select_for_update().get(pk=self.record.pk)
                    acquired.set()
                    if operation == "customer":
                        self.assertEqual(record.stripe_customer_id, "cus_created_fixture")
                        self.assertEqual(
                            StripeBillingRequest.objects.get(subscription=record, operation="customer").resource_id,
                            "cus_created_fixture",
                        )
                    elif operation == "checkout":
                        self.assertEqual(
                            StripeBillingRequest.objects.get(subscription=record, operation="checkout").resource_id,
                            self.session.id,
                        )
                    record.user = self.other
                    record.save(update_fields=["user"])
            finally:
                connections.close_all()

        def mutation():
            close_old_connections()
            try:
                return function()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(writer)
            second = pool.submit(mutation)
            second.result(timeout=15)
            first.result(timeout=15)
        self.assertTrue(acquired.is_set())
        self.assertFalse(PremiumAuditLog.objects.exists())

    def test_customer_api_and_result_save_share_billing_lock(self):
        self.assertRemoteCallHoldsLock("customer")

    def test_checkout_api_and_result_save_share_billing_lock(self):
        self.assertRemoteCallHoldsLock("checkout")

    def test_portal_api_call_holds_billing_lock(self):
        self.assertRemoteCallHoldsLock("portal")

    def assertWaitsForOwnerChange(self, operation):
        locked = Event()
        waiting = Event()
        if operation == "customer":
            PremiumSubscription.objects.filter(pk=self.record.pk).update(stripe_customer_id="")
            function = partial(get_or_create_stripe_customer, self.user)
        elif operation == "checkout":
            function = partial(create_checkout_session, self.request)
        else:
            function = partial(create_portal_session, self.request)

        def writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    record = PremiumSubscription.objects.select_for_update().get(pk=self.record.pk)
                    locked.set()
                    self.assertTrue(waiting.wait(timeout=10))
                    record.user = self.other
                    record.save(update_fields=["user"])
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
                    with self.assertRaisesMessage(ValueError, OWNER_ERROR):
                        function()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(writer)
            second = pool.submit(mutation)
            first.result(timeout=15)
            second.result(timeout=15)
        self.record.refresh_from_db()
        self.assertEqual(self.record.user_id, self.other.pk)
        self.assertFalse(StripeBillingRequest.objects.exists())
        self.assertNoRemoteMutation()

    def test_customer_waits_and_rechecks_owner_after_billing_writer(self):
        self.assertWaitsForOwnerChange("customer")

    def test_checkout_waits_and_rechecks_owner_after_billing_writer(self):
        self.assertWaitsForOwnerChange("checkout")

    def test_portal_waits_and_rechecks_owner_after_billing_writer(self):
        self.assertWaitsForOwnerChange("portal")
