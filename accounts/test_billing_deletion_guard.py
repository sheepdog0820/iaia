from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import PremiumSubscription, StripeBillingRequest


class BillingDeletionGuardTests(TestCase):
    def setUp(self):
        self.stripe = Mock()
        self.stripe.Subscription.list.return_value.auto_paging_iter.return_value = []
        self.stripe.checkout.Session.list.return_value.auto_paging_iter.return_value = []
        self.stripe.Subscription.retrieve.return_value = {
            "id": "sub_guard",
            "customer": "cus_guard",
            "status": "canceled",
        }
        patcher = patch("accounts.billing_deletion.get_stripe", return_value=self.stripe)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_user(self, label, **subscription_fields):
        user = get_user_model().objects.create_user(username=label)
        user.set_unusable_password()
        user.save(update_fields=["password"])
        if subscription_fields:
            PremiumSubscription.objects.create(user=user, **subscription_fields)
        self.client.force_login(user)
        return user

    def delete_account(self):
        return self.client.post(reverse("account_delete"), {"confirm": "DELETE"})

    def test_nonterminal_contract_blocks_deletion_without_premium_access(self):
        for status in ("past_due", "unpaid", "paused", "incomplete", "revoked", "", "unknown_status"):
            with self.subTest(status=status):
                user = self.make_user(
                    "guard-" + (status or "blank"),
                    stripe_customer_id="cus_guard",
                    stripe_subscription_id="sub_guard",
                    subscription_status=status,
                    access_source="stripe",
                )
                self.assertFalse(user.is_premium)
                response = self.delete_account()
                self.assertRedirects(response, reverse("billing"), fetch_redirect_response=False)
                self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    def test_revoked_access_does_not_mean_contract_has_ended(self):
        self.make_user(
            "revoked-active",
            stripe_subscription_id="sub_guard",
            subscription_status="active",
            revoked_at=timezone.now(),
        )
        page = self.client.get(reverse("account_delete"))
        self.assertContains(page, "課金管理へ")
        self.assertContains(page, "Stripeの契約が終了していません。")
        self.assertContains(page, "契約期間の終了後にアカウントを削除できます。")
        self.assertRedirects(self.delete_account(), reverse("billing"), fetch_redirect_response=False)

    def test_customer_only_active_record_still_blocks_when_access_revoked(self):
        self.make_user(
            "legacy-active",
            stripe_customer_id="cus_guard",
            subscription_status="active",
            revoked_at=timezone.now(),
        )
        response = self.delete_account()
        self.assertRedirects(response, reverse("billing"), fetch_redirect_response=False)
        self.assertIn("Stripeの契約が終了していません。", str(list(get_messages(response.wsgi_request))[0]))

    def test_scheduled_cancellation_still_blocks_until_contract_ends(self):
        self.make_user(
            "scheduled-cancel",
            stripe_subscription_id="sub_guard",
            subscription_status="active",
            cancel_at_period_end=True,
        )
        self.assertRedirects(self.delete_account(), reverse("billing"), fetch_redirect_response=False)

    def test_terminal_contract_allows_deletion_even_with_revoked_access(self):
        for status in ("canceled", "incomplete_expired"):
            with self.subTest(status=status):
                user = self.make_user(
                    "terminal-" + status,
                    stripe_customer_id="cus_guard",
                    stripe_subscription_id="sub_guard",
                    subscription_status=status,
                    revoked_at=timezone.now(),
                )
                self.assertRedirects(self.delete_account(), reverse("home"), fetch_redirect_response=False)
                self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())

    def test_open_checkout_is_expired_before_deletion(self):
        user = self.make_user("open-checkout", stripe_customer_id="cus_guard")
        session = {"id": "cs_guard", "customer": "cus_guard", "status": "open"}
        self.stripe.checkout.Session.list.return_value.auto_paging_iter.return_value = [session]
        self.stripe.checkout.Session.expire.return_value = {**session, "status": "expired"}
        self.assertRedirects(self.delete_account(), reverse("home"), fetch_redirect_response=False)
        self.stripe.checkout.Session.expire.assert_called_once_with("cs_guard")
        self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())

    def test_completed_checkout_with_delayed_webhook_preserves_account(self):
        user = self.make_user("late-webhook", stripe_customer_id="cus_guard")
        self.stripe.Subscription.list.return_value.auto_paging_iter.return_value = [
            {"id": "sub_new", "customer": "cus_guard", "status": "active"}
        ]
        self.assertRedirects(self.delete_account(), reverse("billing"), fetch_redirect_response=False)
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    def test_unknown_checkout_creation_result_preserves_retry_record(self):
        user = self.make_user("lost-response", stripe_customer_id="cus_guard")
        attempt = StripeBillingRequest.objects.create(subscription=user.premium_subscription, operation="checkout")
        self.delete_account()
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertTrue(StripeBillingRequest.objects.filter(pk=attempt.pk).exists())

    def test_expiration_failure_preserves_account(self):
        user = self.make_user("expire-race", stripe_customer_id="cus_guard")
        self.stripe.checkout.Session.list.return_value.auto_paging_iter.return_value = [
            {"id": "cs_guard", "customer": "cus_guard", "status": "open"}
        ]
        self.stripe.checkout.Session.expire.side_effect = RuntimeError("simulated completion race")
        self.delete_account()
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    def test_remote_lookup_failure_preserves_account(self):
        user = self.make_user("lookup-failed", stripe_customer_id="cus_guard")
        self.stripe.Subscription.list.side_effect = RuntimeError("simulated lookup failure")
        self.delete_account()
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    def test_tracked_checkout_validation_and_terminal_states(self):
        cases = [
            ({"id": "cs_other", "customer": "cus_guard", "status": "expired"}, False),
            ({"id": "cs_guard", "customer": "cus_other", "status": "expired"}, False),
            ({"id": "cs_guard", "customer": "cus_guard", "status": "unexpected"}, False),
            ({"id": "cs_guard", "customer": "cus_guard", "status": "complete"}, False),
            ({"id": "cs_guard", "customer": "cus_guard", "status": "expired"}, True),
            ({"id": "cs_guard", "customer": "cus_guard", "status": "complete", "subscription": "sub_guard"}, True),
        ]
        for index, (session, allowed) in enumerate(cases):
            with self.subTest(session=session):
                user = self.make_user(f"tracked-{index}", stripe_customer_id="cus_guard")
                StripeBillingRequest.objects.create(
                    subscription=user.premium_subscription, operation="checkout", resource_id="cs_guard"
                )
                self.stripe.checkout.Session.retrieve.return_value = session
                self.delete_account()
                self.assertEqual(get_user_model().objects.filter(pk=user.pk).exists(), not allowed)

    def test_invalid_expiration_response_and_missing_id_preserve_account(self):
        for index, session in enumerate(
            (
                {"customer": "cus_guard", "status": "open"},
                {"id": "cs_guard", "customer": "cus_guard", "status": "open"},
            )
        ):
            user = self.make_user(f"bad-expiry-{index}", stripe_customer_id="cus_guard")
            self.stripe.checkout.Session.list.return_value.auto_paging_iter.return_value = [session]
            self.stripe.checkout.Session.expire.return_value = session
            self.delete_account()
            self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    def test_stale_canceled_record_requires_matching_remote_terminal_subscription(self):
        for index, remote in enumerate(
            (
                {"id": "sub_other", "customer": "cus_guard", "status": "canceled"},
                {"id": "sub_guard", "customer": "cus_other", "status": "canceled"},
                {"id": "sub_guard", "customer": "cus_guard", "status": "active"},
            )
        ):
            user = self.make_user(
                f"stale-{index}",
                stripe_customer_id="cus_guard",
                stripe_subscription_id="sub_guard",
                subscription_status="canceled",
            )
            self.stripe.Subscription.retrieve.return_value = remote
            self.delete_account()
            self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    def test_missing_customer_link_preserves_account(self):
        user = self.make_user("missing-customer", stripe_subscription_id="sub_guard", subscription_status="canceled")
        self.delete_account()
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    def test_free_manual_and_customer_only_accounts_can_be_deleted(self):
        cases = ({}, {"subscription_status": "promo"}, {"stripe_customer_id": "cus_no_contract"})
        for index, fields in enumerate(cases):
            with self.subTest(fields=fields):
                user = self.make_user(f"free-{index}", **fields)
                self.assertRedirects(self.delete_account(), reverse("home"), fetch_redirect_response=False)
                self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())
