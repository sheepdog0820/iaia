from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import PremiumSubscription


class BillingDeletionGuardTests(TestCase):
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
                    stripe_subscription_id="sub_guard",
                    subscription_status=status,
                    revoked_at=timezone.now(),
                )
                self.assertRedirects(self.delete_account(), reverse("home"), fetch_redirect_response=False)
                self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())

    def test_free_manual_and_customer_only_accounts_can_be_deleted(self):
        cases = ({}, {"subscription_status": "promo"}, {"stripe_customer_id": "cus_no_contract"})
        for index, fields in enumerate(cases):
            with self.subTest(fields=fields):
                user = self.make_user(f"free-{index}", **fields)
                self.assertRedirects(self.delete_account(), reverse("home"), fetch_redirect_response=False)
                self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())
