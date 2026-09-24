from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import PremiumSubscription, StripeBillingRequest

User = get_user_model()


class UserDeletionPathTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="delete-path-admin")
        self.free = User.objects.create_user(username="delete-path-free")
        self.target = User.objects.create_user(username="delete-path-target")
        self.record = PremiumSubscription.objects.create(
            user=self.target,
            stripe_customer_id="cus_delete_paths",
            stripe_subscription_id="sub_delete_paths",
            subscription_status="past_due",
        )
        self.api = APIClient()

    def test_self_api_cannot_bypass_billing_check(self):
        self.api.force_authenticate(self.target)
        response = self.api.delete(f"/api/accounts/users/{self.target.pk}/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Stripeの契約が終了していません。", str(response.data))
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())

    def test_admin_api_cannot_bypass_billing_check(self):
        self.api.force_authenticate(self.admin)
        response = self.api.delete(f"/api/accounts/admin/users/{self.target.pk}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())

    def test_unknown_checkout_result_is_preserved_through_api(self):
        self.record.stripe_subscription_id = ""
        self.record.subscription_status = ""
        self.record.save()
        attempt = StripeBillingRequest.objects.create(subscription=self.record, operation="checkout")
        self.api.force_authenticate(self.target)
        response = self.api.delete(f"/api/accounts/users/{self.target.pk}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(StripeBillingRequest.objects.filter(pk=attempt.pk).exists())

    def test_admin_single_delete_shows_error_and_keeps_user(self):
        self.client.force_login(self.admin)
        url = reverse("admin:accounts_customuser_delete", args=[self.target.pk])
        response = self.client.post(url, {"post": "yes"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())
        self.assertContains(response, "Stripeの契約が終了していません。")
        self.assertFalse(LogEntry.objects.filter(action_flag=DELETION).exists())

    def test_admin_bulk_delete_rolls_back_entire_selection_if_one_is_blocked(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:accounts_customuser_changelist"),
            {"action": "delete_selected", "_selected_action": [self.free.pk, self.target.pk], "post": "yes"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=self.free.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())
        self.assertContains(response, "Stripeの契約が終了していません。")
        self.assertFalse(LogEntry.objects.filter(action_flag=DELETION).exists())

    def test_api_permissions_are_preserved(self):
        self.api.force_authenticate(self.free)
        self.assertEqual(self.api.delete(f"/api/accounts/users/{self.target.pk}/").status_code, 404)
        self.assertEqual(self.api.delete(f"/api/accounts/admin/users/{self.target.pk}/").status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())

    def test_free_self_api_deletion_still_works(self):
        self.api.force_authenticate(self.free)
        pk = self.free.pk
        self.assertEqual(self.api.delete(f"/api/accounts/users/{pk}/").status_code, 204)
        self.assertFalse(User.objects.filter(pk=pk).exists())

    def test_free_admin_api_deletion_still_works(self):
        self.api.force_authenticate(self.admin)
        pk = self.free.pk
        self.assertEqual(self.api.delete(f"/api/accounts/admin/users/{pk}/").status_code, 204)
        self.assertFalse(User.objects.filter(pk=pk).exists())

    def test_free_admin_single_and_bulk_deletion_still_work(self):
        self.client.force_login(self.admin)
        pk = self.free.pk
        self.client.post(reverse("admin:accounts_customuser_delete", args=[pk]), {"post": "yes"})
        self.assertFalse(User.objects.filter(pk=pk).exists())
        another = User.objects.create_user(username="delete-path-another-free")
        self.client.post(
            reverse("admin:accounts_customuser_changelist"),
            {"action": "delete_selected", "_selected_action": [another.pk], "post": "yes"},
        )
        self.assertFalse(User.objects.filter(pk=another.pk).exists())
