import json
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import CommandError, call_command
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.admin import (
    CustomUserAdmin,
    PaymentIssueListFilter,
    PremiumAccessCodeAdmin,
    PremiumAccessCodeRedemptionInline,
    PremiumAccessCodeStatusFilter,
    PremiumAuditActorFilter,
    PremiumAuditLogAdmin,
    PremiumSubscriptionAdmin,
    RefundOrDisputeListFilter,
    StripeWebhookEventAdmin,
    SubscriptionOperationalIssueFilter,
    UserPremiumSourceFilter,
    WebhookOperationalIssueFilter,
)
from accounts.billing import handle_checkout_completed, sync_subscription_object
from accounts.models import (
    PremiumAccessCode,
    PremiumAccessCodeRedemption,
    PremiumAuditLog,
    PremiumSubscription,
    StripeWebhookEvent,
)

User = get_user_model()


def active_portal_configuration(livemode=False, *, features=None):
    default_features = {
        "payment_method_update": {"enabled": True},
        "subscription_cancel": {"enabled": True},
        "invoice_history": {"enabled": True},
    }
    if features:
        default_features.update(features)
    return {
        "id": "bpc_remote",
        "active": True,
        "livemode": livemode,
        "features": default_features,
    }


class PremiumSubscriptionModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="billing-user",
            email="billing@example.com",
            password="pass123",
        )

    def test_active_subscription_grants_premium(self):
        record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_active",
            subscription_status="active",
        )
        record.sync_user_premium_access()

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertTrue(self.user.has_premium_access)

    def test_trialing_subscription_grants_premium(self):
        record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_trial",
            subscription_status="trialing",
        )
        record.sync_user_premium_access()

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

    def test_inactive_subscription_revokes_premium(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_canceled",
            subscription_status="canceled",
        )

        record.sync_user_premium_access()

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)

    def test_manual_grant_survives_inactive_subscription_sync(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumAuditLog.objects.create(
            user=self.user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_manual_override_canceled",
            subscription_status="canceled",
            access_source="stripe",
        )

        record.sync_user_premium_access()

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

    def test_manual_revoke_allows_inactive_subscription_to_remove_access(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumAuditLog.objects.create(
            user=self.user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        PremiumAuditLog.objects.create(
            user=self.user,
            action="revoked",
            source="manual",
            reason="Support comp ended",
        )
        record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_manual_override_revoked",
            subscription_status="canceled",
            access_source="stripe",
        )

        record.sync_user_premium_access()

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)

    def test_revoked_active_subscription_does_not_grant_premium(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_revoked_active",
            subscription_status="active",
            access_source="stripe",
            revoked_at=timezone.now(),
            revoked_reason="Stripe charge refunded",
        )

        record.sync_user_premium_access()

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)

    def test_staff_keeps_premium_access_property(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

        self.assertTrue(self.user.has_premium_access)

    def test_premium_access_code_status_label(self):
        active_code, _ = PremiumAccessCode.issue(max_uses=2)
        self.assertEqual(active_code.status_label, "active")

        exhausted_code, _ = PremiumAccessCode.issue(max_uses=1)
        exhausted_code.use_count = 1
        exhausted_code.save(update_fields=["use_count"])
        self.assertEqual(exhausted_code.status_label, "exhausted")

        expired_code, _ = PremiumAccessCode.issue(
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertEqual(expired_code.status_label, "expired")

        revoked_code, _ = PremiumAccessCode.issue()
        revoked_code.revoked_at = timezone.now()
        revoked_code.save(update_fields=["revoked_at"])
        self.assertEqual(revoked_code.status_label, "revoked")


@override_settings(
    STRIPE_CHECKOUT_ENABLED=True,
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_PREMIUM_PRICE_ID="price_dummy",
)
class BillingApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="api-billing-user",
            email="api-billing@example.com",
            password="pass123",
        )

    def test_billing_view_failures_use_operational_logger(self):
        from accounts.views import billing_views

        self.assertEqual(billing_views.logger.name, "tableno.billing")

    def test_checkout_enabled_helper_defaults_to_disabled_when_setting_is_missing(self):
        from accounts.views.billing_views import is_checkout_enabled

        with patch("accounts.views.billing_views.settings", SimpleNamespace()):
            self.assertFalse(is_checkout_enabled())

    def test_checkout_requires_authentication(self):
        response = self.client.post(reverse("billing-checkout-session"))
        self.assertEqual(response.status_code, 401)

    @override_settings(STRIPE_CHECKOUT_ENABLED=False)
    @patch("accounts.views.billing_views.create_checkout_session")
    def test_checkout_disabled_returns_service_unavailable_without_calling_stripe(self, create_checkout_session):
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-checkout-session"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.data["error"],
            "Stripe Checkout is disabled until billing verification is complete",
        )
        create_checkout_session.assert_not_called()

    @patch("accounts.views.billing_views.create_checkout_session")
    def test_checkout_returns_stripe_redirect_url(self, create_checkout_session):
        create_checkout_session.return_value = SimpleNamespace(url="https://checkout.stripe.test/session")
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-checkout-session"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["url"], "https://checkout.stripe.test/session")
        create_checkout_session.assert_called_once()

    @patch("accounts.billing.get_stripe")
    def test_checkout_creates_customer_for_new_user(self, get_stripe):
        stripe = Mock()
        stripe.Customer.create.return_value = SimpleNamespace(id="cus_new")
        stripe.checkout.Session.create.return_value = SimpleNamespace(url="https://checkout.stripe.test/new")
        get_stripe.return_value = stripe
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-checkout-session"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["url"], "https://checkout.stripe.test/new")
        record = PremiumSubscription.objects.get(user=self.user)
        self.assertEqual(record.stripe_customer_id, "cus_new")
        stripe.Customer.create.assert_called_once()

    @patch("accounts.billing.get_stripe")
    def test_checkout_reuses_existing_customer(self, get_stripe):
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_existing")
        stripe = Mock()
        stripe.checkout.Session.create.return_value = SimpleNamespace(url="https://checkout.stripe.test/existing")
        get_stripe.return_value = stripe
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-checkout-session"))

        self.assertEqual(response.status_code, 200)
        stripe.Customer.create.assert_not_called()
        stripe.checkout.Session.create.assert_called_once()
        self.assertEqual(
            stripe.checkout.Session.create.call_args.kwargs["customer"],
            "cus_existing",
        )

    @patch("accounts.billing.get_stripe")
    def test_checkout_uses_yearly_price_when_requested(self, get_stripe):
        stripe = Mock()
        stripe.Customer.create.return_value = SimpleNamespace(id="cus_yearly")
        stripe.checkout.Session.create.return_value = SimpleNamespace(url="https://checkout.stripe.test/yearly")
        get_stripe.return_value = stripe
        self.client.force_authenticate(self.user)

        with override_settings(STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_dummy"):
            response = self.client.post(
                reverse("billing-checkout-session"),
                {"plan": "yearly"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            stripe.checkout.Session.create.call_args.kwargs["line_items"],
            [{"price": "price_yearly_dummy", "quantity": 1}],
        )
        self.assertEqual(
            stripe.checkout.Session.create.call_args.kwargs["metadata"]["billing_plan"],
            "yearly",
        )
        self.assertEqual(
            stripe.checkout.Session.create.call_args.kwargs["subscription_data"]["metadata"],
            {"user_id": str(self.user.id), "billing_plan": "yearly"},
        )

    @patch("accounts.billing.get_stripe")
    def test_checkout_sets_subscription_metadata_for_subscription_webhooks(self, get_stripe):
        stripe = Mock()
        stripe.Customer.create.return_value = SimpleNamespace(id="cus_metadata")
        stripe.checkout.Session.create.return_value = SimpleNamespace(url="https://checkout.stripe.test/metadata")
        get_stripe.return_value = stripe
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-checkout-session"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            stripe.checkout.Session.create.call_args.kwargs["subscription_data"]["metadata"],
            {"user_id": str(self.user.id), "billing_plan": "monthly"},
        )

    def test_checkout_rejects_invalid_plan(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("billing-checkout-session"),
            {"plan": "weekly"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Invalid billing plan")

    @patch("accounts.views.billing_views.create_checkout_session")
    def test_checkout_stripe_temporary_failure_returns_service_unavailable(self, create_checkout_session):
        create_checkout_session.side_effect = RuntimeError("stripe connection timeout")
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-checkout-session"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error"], "Stripe service is temporarily unavailable")
        self.assertNotIn("stripe connection timeout", str(response.data))

    def test_portal_requires_customer(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("billing-portal-session"))
        self.assertEqual(response.status_code, 400)

    @patch("accounts.billing.get_stripe")
    def test_portal_returns_redirect_url(self, get_stripe):
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_portal")
        stripe = Mock()
        stripe.billing_portal.Session.create.return_value = SimpleNamespace(url="https://billing.stripe.test/portal")
        get_stripe.return_value = stripe
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-portal-session"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["url"], "https://billing.stripe.test/portal")

    @override_settings(STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_test_config")
    @patch("accounts.billing.get_stripe")
    def test_portal_uses_configured_portal_configuration(self, get_stripe):
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_portal")
        stripe = Mock()
        stripe.billing_portal.Session.create.return_value = SimpleNamespace(url="https://billing.stripe.test/portal")
        get_stripe.return_value = stripe
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-portal-session"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            stripe.billing_portal.Session.create.call_args.kwargs["configuration"],
            "bpc_test_config",
        )

    @patch("accounts.views.billing_views.create_portal_session")
    def test_portal_stripe_temporary_failure_returns_service_unavailable(self, create_portal_session):
        create_portal_session.side_effect = RuntimeError("stripe portal timeout")
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-portal-session"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error"], "Stripe service is temporarily unavailable")
        self.assertNotIn("stripe portal timeout", str(response.data))

    def test_redeem_code_requires_authentication(self):
        response = self.client.post(reverse("billing-redeem-code"), {"code": "PREMIUM-TEST"})
        self.assertEqual(response.status_code, 401)

    def test_redeem_code_grants_premium(self):
        _, raw_code = PremiumAccessCode.issue(
            label="Local campaign",
            campaign_name="local-campaign-2026",
        )
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-redeem-code"), {"code": raw_code})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["redeemed"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        record = PremiumSubscription.objects.get(user=self.user)
        self.assertEqual(record.subscription_status, "promo")
        self.assertEqual(record.access_source, "promo_code")
        code = PremiumAccessCode.objects.get(label="Local campaign")
        self.assertEqual(code.use_count, 1)
        self.assertTrue(PremiumAccessCodeRedemption.objects.filter(user=self.user).exists())
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="granted",
            source="promo_code",
        )
        self.assertEqual(audit_log.metadata["access_code_id"], code.pk)
        self.assertEqual(audit_log.metadata["access_code_label"], "Local campaign")
        self.assertEqual(audit_log.metadata["access_code_campaign_name"], "local-campaign-2026")

    def test_redeem_code_rejects_invalid_code(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("billing-redeem-code"), {"code": "missing"})
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)

    def test_redeem_code_respects_max_uses(self):
        _, raw_code = PremiumAccessCode.issue(max_uses=1)
        other = User.objects.create_user(username="other-code-user", password="pass123")

        self.client.force_authenticate(other)
        first = self.client.post(reverse("billing-redeem-code"), {"code": raw_code})
        self.assertEqual(first.status_code, 200)

        self.client.force_authenticate(self.user)
        second = self.client.post(reverse("billing-redeem-code"), {"code": raw_code})
        self.assertEqual(second.status_code, 400)

    def test_redeem_code_does_not_consume_for_already_premium_user(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        code, raw_code = PremiumAccessCode.issue(max_uses=1)
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("billing-redeem-code"), {"code": raw_code})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["redeemed"])
        code.refresh_from_db()
        self.assertEqual(code.use_count, 0)


class BillingPageTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="billing-page-user",
            email="billing-page@example.com",
            password="pass123",
        )

    def test_billing_page_shows_payment_failed_card_update_notice(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_failed_page",
            subscription_status="active",
            access_source="stripe",
            last_payment_failed_at=timezone.now(),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "カード更新が必要です")
        self.assertContains(response, "支払いに失敗した請求があります")
        self.assertContains(response, "支払い・解約を管理")

    def test_billing_page_hides_payment_failed_notice_after_recovery(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_recovered_page",
            subscription_status="active",
            access_source="stripe",
            last_payment_failed_at=None,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "カード更新が必要です")
        self.assertNotContains(response, "支払いに失敗した請求があります")

    @override_settings(
        STRIPE_CHECKOUT_ENABLED=True,
        STRIPE_SECRET_KEY="sk_test_page",
        STRIPE_PREMIUM_PRICE_ID="price_monthly_page",
        STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_page",
        PREMIUM_MONTHLY_PRICE_DESCRIPTION="480\u5186/\u6708",
        PREMIUM_YEARLY_PRICE_DESCRIPTION="4,800\u5186/\u5e74",
    )
    def test_billing_page_shows_monthly_and_yearly_checkout_options(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-plan="monthly"')
        self.assertContains(response, 'data-plan="yearly"')
        self.assertContains(response, "480\u5186/\u6708")
        self.assertContains(response, "4,800\u5186/\u5e74")

    @override_settings(
        STRIPE_CHECKOUT_ENABLED=False,
        STRIPE_SECRET_KEY="sk_test_page",
        STRIPE_PREMIUM_PRICE_ID="price_monthly_page",
    )
    def test_billing_page_hides_checkout_options_when_checkout_disabled(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stripe Checkout")
        self.assertContains(
            response,
            "\u8ab2\u91d1\u691c\u8a3c\u304c\u5b8c\u4e86\u3059\u308b\u307e\u3067\u8ab2\u91d1\u7533\u3057\u8fbc\u307f\u306f\u5229\u7528\u3067\u304d\u307e\u305b\u3093",
        )
        self.assertNotContains(response, 'data-plan="monthly"')
        self.assertContains(response, 'id="checkout-btn"')

    @override_settings(STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=True)
    def test_billing_page_shows_refund_or_dispute_auto_revoke_notice(self):
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_refund_page",
            subscription_status="revoked",
            access_source="stripe",
            last_refund_or_dispute_at=timezone.now(),
            revoked_at=timezone.now(),
            revoked_reason="Stripe charge refunded",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "返金またはチャージバックが検知されました")
        self.assertContains(response, "プレミアム権限は自動停止されています")
        self.assertContains(response, 'id="billing-portal-btn"')
        self.assertContains(response, 'id="checkout-btn"')

    @override_settings(STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=False)
    def test_billing_page_shows_refund_or_dispute_manual_review_notice(self):
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_refund_manual_page",
            subscription_status="active",
            access_source="stripe",
            last_refund_or_dispute_at=timezone.now(),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "返金またはチャージバックが検知されました")
        self.assertContains(response, "管理者が確認するまでプレミアム権限が停止される場合があります")

    def test_billing_page_shows_cancel_at_period_end_state(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_canceling_page",
            subscription_status="active",
            access_source="stripe",
            current_period_end=timezone.now() + timedelta(days=10),
            cancel_at_period_end=True,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "解約予定")
        self.assertContains(response, "あり")
        self.assertContains(response, "次回更新日")

    def test_billing_page_shows_monthly_stripe_plan(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_monthly_page",
            subscription_status="active",
            access_source="stripe",
            stripe_price_id="price_monthly_page",
            billing_interval="month",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "加入プラン")
        self.assertContains(response, "月額プラン")
        self.assertContains(response, "Price ID: price_monthly_page")

    def test_billing_page_shows_yearly_stripe_plan(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_yearly_page",
            subscription_status="active",
            access_source="stripe",
            stripe_price_id="price_yearly_page",
            billing_interval="year",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "加入プラン")
        self.assertContains(response, "年額プラン")
        self.assertContains(response, "Price ID: price_yearly_page")

    def test_billing_page_explains_promo_code_expiration(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() + timedelta(days=30),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "プレミアム期限")
        self.assertContains(response, "この運営コード由来のプレミアム権限は期限到達後に自動失効します")
        self.assertContains(response, "期限付きコードは表示されたプレミアム期限まで有効です")

    def test_billing_page_explains_indefinite_promo_code_access(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            subscription_status="promo",
            access_source="promo_code",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "プレミアム期限")
        self.assertContains(response, "無期限")
        self.assertContains(response, "この運営コード由来のプレミアム権限は、管理者が失効するまで有効です")
        self.assertContains(response, "期限なしコードは管理者が失効するまで有効です")


@override_settings(
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_WEBHOOK_SECRET="whsec_dummy",
)
class StripeWebhookTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_webhook_rejects_missing_signature(self):
        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_rejects_invalid_signature(self, get_stripe):
        stripe = Mock()
        stripe.Webhook.construct_event.side_effect = ValueError("bad signature")
        get_stripe.return_value = stripe

        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid",
        )

        self.assertEqual(response.status_code, 400)

    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_rejects_event_without_id_or_type(self, get_stripe):
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = {
            "data": {"object": {}},
        }
        get_stripe.return_value = stripe

        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(StripeWebhookEvent.objects.exists())

    @patch("accounts.views.billing_views.handle_checkout_completed")
    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_processes_checkout_completed_once(self, get_stripe, handle_checkout_completed_mock):
        event = {
            "id": "evt_checkout",
            "type": "checkout.session.completed",
            "data": {"object": {"customer": "cus_test", "subscription": "sub_test"}},
        }
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = event
        get_stripe.return_value = stripe

        for _ in range(2):
            response = self.client.post(
                reverse("billing-webhook"),
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid",
            )
            self.assertEqual(response.status_code, 200)

        handle_checkout_completed_mock.assert_called_once_with(
            event["data"]["object"],
            event_id="evt_checkout",
        )
        webhook_event = StripeWebhookEvent.objects.get(event_id="evt_checkout")
        self.assertEqual(webhook_event.processing_status, StripeWebhookEvent.STATUS_SUCCEEDED)

    @patch("accounts.views.billing_views.handle_checkout_completed")
    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_duplicate_insert_skips_processing(
        self,
        get_stripe,
        handle_checkout_completed_mock,
    ):
        event = {
            "id": "evt_checkout_race",
            "type": "checkout.session.completed",
            "data": {"object": {"customer": "cus_test", "subscription": "sub_test"}},
        }
        StripeWebhookEvent.objects.create(
            event_id="evt_checkout_race",
            event_type="checkout.session.completed",
            processing_status=StripeWebhookEvent.STATUS_SUCCEEDED,
        )
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = event
        get_stripe.return_value = stripe

        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"received": True, "duplicate": True})
        handle_checkout_completed_mock.assert_not_called()

    @patch("accounts.views.billing_views.handle_checkout_completed")
    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_records_failure_and_allows_retry(self, get_stripe, handle_checkout_completed_mock):
        event = {
            "id": "evt_checkout_retry",
            "type": "checkout.session.completed",
            "data": {"object": {"customer": "cus_test", "subscription": "sub_test"}},
        }
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = event
        get_stripe.return_value = stripe
        handle_checkout_completed_mock.side_effect = [RuntimeError("temporary failure"), None]

        first_response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(first_response.status_code, 500)
        webhook_event = StripeWebhookEvent.objects.get(event_id="evt_checkout_retry")
        self.assertEqual(webhook_event.processing_status, StripeWebhookEvent.STATUS_FAILED)
        self.assertIn("temporary failure", webhook_event.error_message)

        second_response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(second_response.status_code, 200)
        webhook_event.refresh_from_db()
        self.assertEqual(webhook_event.processing_status, StripeWebhookEvent.STATUS_SUCCEEDED)
        self.assertEqual(webhook_event.error_message, "")
        self.assertEqual(handle_checkout_completed_mock.call_count, 2)

    @patch("accounts.views.billing_views.sync_subscription_object")
    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_routes_subscription_created(self, get_stripe, sync_subscription_object_mock):
        event = {
            "id": "evt_sub_created",
            "type": "customer.subscription.created",
            "data": {"object": {"id": "sub_test", "customer": "cus_test", "status": "active"}},
        }
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = event
        get_stripe.return_value = stripe

        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(response.status_code, 200)
        sync_subscription_object_mock.assert_called_once_with(
            event["data"]["object"],
            event_id="evt_sub_created",
        )

    @patch("accounts.views.billing_views.sync_subscription_object")
    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_routes_subscription_update(self, get_stripe, sync_subscription_object_mock):
        event = {
            "id": "evt_sub",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_test", "customer": "cus_test", "status": "active"}},
        }
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = event
        get_stripe.return_value = stripe

        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(response.status_code, 200)
        sync_subscription_object_mock.assert_called_once_with(
            event["data"]["object"],
            event_id="evt_sub",
        )

    @patch("accounts.views.billing_views.sync_subscription_object")
    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_routes_subscription_deleted(self, get_stripe, sync_subscription_object_mock):
        event = {
            "id": "evt_sub_deleted",
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_test", "customer": "cus_test", "status": "canceled"}},
        }
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = event
        get_stripe.return_value = stripe

        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(response.status_code, 200)
        sync_subscription_object_mock.assert_called_once_with(
            event["data"]["object"],
            event_id="evt_sub_deleted",
        )

    @patch("accounts.views.billing_views.mark_invoice_payment_failed")
    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_routes_invoice_payment_failed(self, get_stripe, mark_payment_failed_mock):
        event = {
            "id": "evt_invoice_failed",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": "in_failed",
                    "customer": "cus_test",
                    "subscription": "sub_test",
                }
            },
        }
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = event
        get_stripe.return_value = stripe

        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(response.status_code, 200)
        mark_payment_failed_mock.assert_called_once_with(
            event["data"]["object"],
            event_id="evt_invoice_failed",
        )

    @patch("accounts.views.billing_views.mark_invoice_payment_succeeded")
    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_routes_invoice_payment_succeeded(self, get_stripe, mark_payment_succeeded_mock):
        event = {
            "id": "evt_invoice_succeeded",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_succeeded",
                    "customer": "cus_test",
                    "subscription": "sub_test",
                }
            },
        }
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = event
        get_stripe.return_value = stripe

        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(response.status_code, 200)
        mark_payment_succeeded_mock.assert_called_once_with(
            event["data"]["object"],
            event_id="evt_invoice_succeeded",
        )

    @patch("accounts.views.billing_views.mark_refund_or_dispute")
    @patch("accounts.views.billing_views.get_stripe")
    def test_webhook_routes_charge_dispute_created(self, get_stripe, mark_refund_or_dispute_mock):
        event = {
            "id": "evt_dispute",
            "type": "charge.dispute.created",
            "data": {"object": {"id": "dp_test", "charge": "ch_test"}},
        }
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = event
        get_stripe.return_value = stripe

        response = self.client.post(
            reverse("billing-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )

        self.assertEqual(response.status_code, 200)
        mark_refund_or_dispute_mock.assert_called_once_with(
            event["data"]["object"],
            event_type="charge.dispute.created",
            event_id="evt_dispute",
        )


@override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
class BillingServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="service-billing-user",
            email="service-billing@example.com",
            password="pass123",
        )

    def test_sync_subscription_object_updates_user_access(self):
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_sync")
        subscription = {
            "id": "sub_sync",
            "customer": "cus_sync",
            "status": "active",
            "current_period_end": int(timezone.now().timestamp()) + 3600,
            "cancel_at_period_end": True,
            "items": {
                "data": [
                    {
                        "price": {
                            "id": "price_sync_monthly",
                            "recurring": {"interval": "month"},
                        }
                    }
                ]
            },
        }

        record = sync_subscription_object(subscription, event_id="evt_sync")

        self.assertEqual(record.stripe_subscription_id, "sub_sync")
        self.assertEqual(record.stripe_price_id, "price_sync_monthly")
        self.assertEqual(record.billing_interval, "month")
        self.assertTrue(record.cancel_at_period_end)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="granted",
            source="stripe",
        )
        self.assertEqual(audit_log.metadata["stripe_subscription_id"], "sub_sync")
        self.assertEqual(audit_log.metadata["stripe_price_id"], "price_sync_monthly")
        self.assertEqual(audit_log.metadata["billing_interval"], "month")
        self.assertTrue(audit_log.metadata["cancel_at_period_end"])

    def test_sync_subscription_object_accepts_attribute_style_subscription(self):
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_attr")
        subscription = SimpleNamespace(
            id="sub_attr",
            customer="cus_attr",
            status="active",
            current_period_end=int(timezone.now().timestamp()) + 3600,
            cancel_at_period_end=False,
            items={
                "data": [
                    {
                        "price": {
                            "id": "price_attr",
                            "recurring": {"interval": "month"},
                        }
                    }
                ]
            },
        )

        record = sync_subscription_object(subscription, event_id="evt_attr")

        self.assertEqual(record.stripe_subscription_id, "sub_attr")
        self.assertEqual(record.stripe_price_id, "price_attr")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

    def test_subscription_unpaid_revokes_user_access(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_unpaid",
            subscription_status="active",
            access_source="stripe",
        )

        record = sync_subscription_object(
            {
                "id": "sub_unpaid",
                "customer": "cus_unpaid",
                "status": "unpaid",
                "current_period_end": int(timezone.now().timestamp()) + 3600,
                "cancel_at_period_end": False,
                "items": {
                    "data": [
                        {
                            "price": {
                                "id": "price_sync_yearly",
                                "recurring": {"interval": "year"},
                            }
                        }
                    ]
                },
            },
            event_id="evt_unpaid",
        )

        self.assertEqual(record.subscription_status, "unpaid")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertTrue(
            PremiumAuditLog.objects.filter(
                user=self.user,
                action="revoked",
                source="stripe",
                stripe_event_id="evt_unpaid",
            ).exists()
        )

    def test_subscription_update_does_not_restore_refund_revoked_access(self):
        self.user.is_premium = False
        self.user.save(update_fields=["is_premium"])
        revoked_at = timezone.now()
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_refund_revoked_sync",
            subscription_status="revoked",
            access_source="stripe",
            revoked_at=revoked_at,
            revoked_reason="Stripe charge refunded",
        )

        record = sync_subscription_object(
            {
                "id": "sub_refund_revoked_sync",
                "customer": "cus_refund_revoked_sync",
                "status": "active",
                "current_period_end": int(timezone.now().timestamp()) + 3600,
                "cancel_at_period_end": False,
            },
            event_id="evt_active_after_refund",
        )

        record.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(record.subscription_status, "active")
        self.assertEqual(record.revoked_reason, "Stripe charge refunded")
        self.assertEqual(record.revoked_at, revoked_at)
        self.assertFalse(self.user.is_premium)

    def test_subscription_update_restores_expired_promo_record_for_new_stripe_access(self):
        self.user.is_premium = False
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_promo_to_stripe",
            subscription_status="revoked",
            access_source="promo_code",
            revoked_at=timezone.now(),
            revoked_reason="Premium access code expired",
        )

        record = sync_subscription_object(
            {
                "id": "sub_promo_to_stripe",
                "customer": "cus_promo_to_stripe",
                "status": "active",
                "current_period_end": int(timezone.now().timestamp()) + 3600,
                "cancel_at_period_end": False,
            },
            event_id="evt_promo_to_stripe",
        )

        record.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(record.access_source, "stripe")
        self.assertIsNone(record.revoked_at)
        self.assertEqual(record.revoked_reason, "")
        self.assertTrue(self.user.is_premium)

    def test_inactive_stripe_update_does_not_remove_active_promo_access(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        promo_expires_at = timezone.now() + timedelta(days=14)
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_active_promo_with_old_stripe",
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=promo_expires_at,
        )

        record = sync_subscription_object(
            {
                "id": "sub_old_canceled",
                "customer": "cus_active_promo_with_old_stripe",
                "status": "canceled",
                "current_period_end": int((timezone.now() - timedelta(days=1)).timestamp()),
                "cancel_at_period_end": False,
            },
            event_id="evt_old_canceled_after_promo",
        )

        record.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(record.subscription_status, "promo")
        self.assertEqual(record.access_source, "promo_code")
        self.assertEqual(record.premium_expires_at, promo_expires_at)
        self.assertTrue(self.user.is_premium)
        self.assertFalse(
            PremiumAuditLog.objects.filter(
                user=self.user,
                action="revoked",
                stripe_event_id="evt_old_canceled_after_promo",
            ).exists()
        )

    def test_subscription_deleted_canceled_revokes_user_access(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_deleted",
            subscription_status="active",
            access_source="stripe",
        )

        record = sync_subscription_object(
            {
                "id": "sub_deleted",
                "customer": "cus_deleted",
                "status": "canceled",
                "current_period_end": int(timezone.now().timestamp()),
                "cancel_at_period_end": False,
            },
            event_id="evt_deleted",
        )

        self.assertEqual(record.subscription_status, "canceled")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)

    @patch("accounts.billing.get_stripe")
    def test_checkout_completed_links_user_and_subscription(self, get_stripe):
        stripe = Mock()
        stripe.Subscription.retrieve.return_value = {
            "id": "sub_checkout",
            "customer": "cus_checkout",
            "status": "active",
            "current_period_end": None,
            "cancel_at_period_end": False,
        }
        get_stripe.return_value = stripe
        session = {
            "client_reference_id": str(self.user.id),
            "customer": "cus_checkout",
            "subscription": "sub_checkout",
            "metadata": {},
        }

        record = handle_checkout_completed(session, event_id="evt_checkout_link")

        self.assertEqual(record.stripe_customer_id, "cus_checkout")
        self.assertEqual(record.stripe_subscription_id, "sub_checkout")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

    def test_checkout_completed_can_use_expanded_subscription_without_remote_retrieve(self):
        session = {
            "client_reference_id": str(self.user.id),
            "customer": "cus_checkout_expanded",
            "subscription": {
                "id": "sub_checkout_expanded",
                "customer": "cus_checkout_expanded",
                "status": "active",
                "current_period_end": None,
                "cancel_at_period_end": False,
            },
            "metadata": {},
        }

        record = handle_checkout_completed(session, event_id="evt_checkout_expanded")

        self.assertEqual(record.stripe_customer_id, "cus_checkout_expanded")
        self.assertEqual(record.stripe_subscription_id, "sub_checkout_expanded")
        self.assertEqual(record.subscription_status, "active")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        PUBLIC_SITE_URL="https://example.test",
    )
    def test_payment_failed_sends_email_and_logs_audit(self):
        from accounts.billing import mark_invoice_payment_failed

        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_payment_failed",
            subscription_status="active",
            access_source="stripe",
        )

        record = mark_invoice_payment_failed(
            {"id": "in_failed", "customer": "cus_payment_failed"},
            event_id="evt_payment_failed",
        )

        self.assertIsNotNone(record)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://example.test/accounts/billing/", mail.outbox[0].body)
        self.assertIn("カード更新が必要です。", mail.outbox[0].body)
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="payment_failed",
            stripe_event_id="evt_payment_failed",
        )
        self.assertEqual(audit_log.metadata["invoice_id"], "in_failed")
        self.assertTrue(audit_log.metadata["email_sent"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_payment_failed_records_when_email_is_not_sent(self):
        from accounts.billing import mark_invoice_payment_failed

        self.user.email = ""
        self.user.save(update_fields=["email"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_payment_failed_no_email",
            subscription_status="active",
            access_source="stripe",
        )

        record = mark_invoice_payment_failed(
            {"id": "in_failed_no_email", "customer": "cus_payment_failed_no_email"},
            event_id="evt_payment_failed_no_email",
        )

        self.assertIsNotNone(record)
        self.assertEqual(len(mail.outbox), 0)
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="payment_failed",
            stripe_event_id="evt_payment_failed_no_email",
        )
        self.assertEqual(audit_log.metadata["invoice_id"], "in_failed_no_email")
        self.assertFalse(audit_log.metadata["email_sent"])

    def test_payment_succeeded_clears_failed_notice_and_logs_recovery(self):
        from accounts.billing import mark_invoice_payment_succeeded

        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_payment_recovered",
            subscription_status="active",
            access_source="stripe",
            last_payment_failed_at=timezone.now(),
        )

        record = mark_invoice_payment_succeeded(
            {"id": "in_recovered", "customer": "cus_payment_recovered"},
            event_id="evt_payment_recovered",
        )

        self.assertIsNotNone(record)
        self.assertIsNone(record.last_payment_failed_at)
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="payment_recovered",
            stripe_event_id="evt_payment_recovered",
        )
        self.assertEqual(audit_log.metadata["invoice_id"], "in_recovered")

    def test_payment_succeeded_without_previous_failure_only_updates_record(self):
        from accounts.billing import mark_invoice_payment_succeeded

        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_payment_succeeded",
            subscription_status="active",
            access_source="stripe",
        )

        record = mark_invoice_payment_succeeded(
            {"id": "in_succeeded", "customer": "cus_payment_succeeded"},
            event_id="evt_payment_succeeded",
        )

        self.assertIsNotNone(record)
        self.assertIsNone(record.last_payment_failed_at)
        self.assertFalse(PremiumAuditLog.objects.filter(user=self.user).exists())

    def test_expire_promo_subscriptions_revokes_expired_access(self):
        from accounts.billing import expire_promo_subscriptions

        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() - timedelta(minutes=1),
        )

        count = expire_promo_subscriptions()

        self.assertEqual(count, 1)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertTrue(
            PremiumAuditLog.objects.filter(
                user=self.user,
                action="revoked",
                source="promo_code",
            ).exists()
        )

    @override_settings(STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=True)
    def test_refund_revokes_access_and_logs_audit(self):
        from accounts.billing import mark_refund_or_dispute

        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_refund",
            subscription_status="active",
            access_source="stripe",
        )

        record = mark_refund_or_dispute(
            {
                "id": "ch_refund",
                "customer": "cus_refund",
                "invoice": "in_refund",
                "payment_intent": "pi_refund",
                "amount": 1200,
                "currency": "jpy",
            },
            event_type="charge.refunded",
            event_id="evt_refund",
        )

        self.assertIsNotNone(record)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="refunded",
            stripe_event_id="evt_refund",
        )
        self.assertEqual(audit_log.metadata["event_type"], "charge.refunded")
        self.assertEqual(audit_log.metadata["charge_id"], "ch_refund")
        self.assertEqual(audit_log.metadata["invoice_id"], "in_refund")
        self.assertEqual(audit_log.metadata["payment_intent_id"], "pi_refund")
        self.assertEqual(audit_log.metadata["amount"], 1200)
        self.assertEqual(audit_log.metadata["currency"], "jpy")
        self.assertTrue(audit_log.metadata["access_was_active"])
        self.assertTrue(audit_log.metadata["auto_revoked"])

    @override_settings(STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=True)
    def test_refund_auto_revoke_preserves_manual_grant(self):
        from accounts.billing import mark_refund_or_dispute

        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumAuditLog.objects.create(
            user=self.user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_refund_manual_override",
            subscription_status="active",
            access_source="stripe",
        )

        updated = mark_refund_or_dispute(
            {"id": "ch_refund_manual_override", "customer": "cus_refund_manual_override"},
            event_type="charge.refunded",
            event_id="evt_refund_manual_override",
        )

        self.assertEqual(updated.pk, record.pk)
        self.user.refresh_from_db()
        record.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(record.subscription_status, "revoked")
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="refunded",
            stripe_event_id="evt_refund_manual_override",
        )
        self.assertTrue(audit_log.metadata["auto_revoked"])
        self.assertFalse(audit_log.metadata["access_revoked"])

    @override_settings(STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=False)
    def test_refund_can_be_recorded_without_auto_revoking_access(self):
        from accounts.billing import mark_refund_or_dispute

        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_refund_manual",
            subscription_status="active",
            access_source="stripe",
        )

        record = mark_refund_or_dispute(
            {"id": "re_refund_manual", "customer": "cus_refund_manual"},
            event_type="charge.refunded",
            event_id="evt_refund_manual",
        )

        self.assertIsNotNone(record)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertTrue(
            PremiumAuditLog.objects.filter(
                user=self.user,
                action="refunded",
                stripe_event_id="evt_refund_manual",
            ).exists()
        )

    @override_settings(STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=False)
    @patch("accounts.billing.get_stripe")
    def test_dispute_audit_log_includes_retrieved_charge_metadata(self, get_stripe):
        from accounts.billing import mark_refund_or_dispute

        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_dispute",
            subscription_status="active",
            access_source="stripe",
        )
        stripe = Mock()
        stripe.Charge.retrieve.return_value = {
            "id": "ch_dispute",
            "customer": "cus_dispute",
            "invoice": "in_dispute",
            "payment_intent": "pi_dispute",
        }
        get_stripe.return_value = stripe

        record = mark_refund_or_dispute(
            {
                "id": "dp_dispute",
                "charge": "ch_dispute",
                "amount": 3400,
                "currency": "jpy",
                "status": "needs_response",
                "reason": "fraudulent",
            },
            event_type="charge.dispute.created",
            event_id="evt_dispute_metadata",
        )

        self.assertIsNotNone(record)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        stripe.Charge.retrieve.assert_called_once_with("ch_dispute")
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="disputed",
            stripe_event_id="evt_dispute_metadata",
        )
        self.assertEqual(audit_log.metadata["object_id"], "dp_dispute")
        self.assertEqual(audit_log.metadata["charge_id"], "ch_dispute")
        self.assertEqual(audit_log.metadata["invoice_id"], "in_dispute")
        self.assertEqual(audit_log.metadata["payment_intent_id"], "pi_dispute")
        self.assertEqual(audit_log.metadata["dispute_status"], "needs_response")
        self.assertEqual(audit_log.metadata["dispute_reason"], "fraudulent")
        self.assertFalse(audit_log.metadata["auto_revoked"])
        self.assertFalse(audit_log.metadata["access_revoked"])

    def test_dispute_closed_won_logs_without_revoking_access(self):
        from accounts.billing import mark_refund_or_dispute

        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_dispute_won",
            subscription_status="active",
            access_source="stripe",
        )

        record = mark_refund_or_dispute(
            {
                "id": "dp_dispute_won",
                "charge": "ch_dispute_won",
                "customer": "cus_dispute_won",
                "status": "won",
                "reason": "fraudulent",
            },
            event_type="charge.dispute.closed",
            event_id="evt_dispute_won",
        )

        self.assertIsNotNone(record)
        self.user.refresh_from_db()
        record.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertIsNone(record.revoked_at)
        self.assertIsNone(record.last_refund_or_dispute_at)
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="disputed",
            stripe_event_id="evt_dispute_won",
        )
        self.assertEqual(audit_log.metadata["dispute_status"], "won")
        self.assertTrue(audit_log.metadata["auto_revoked"])
        self.assertFalse(audit_log.metadata["access_revoked"])
        self.assertFalse(audit_log.metadata["access_restored"])

    def test_dispute_closed_won_restores_dispute_revoked_access(self):
        from accounts.billing import mark_refund_or_dispute

        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_dispute_created_then_won",
            stripe_subscription_id="sub_dispute_created_then_won",
            subscription_status="active",
            access_source="stripe",
        )
        mark_refund_or_dispute(
            {
                "id": "dp_dispute_created",
                "charge": "ch_dispute_created",
                "customer": "cus_dispute_created_then_won",
                "status": "needs_response",
                "reason": "fraudulent",
            },
            event_type="charge.dispute.created",
            event_id="evt_dispute_created_before_won",
        )
        self.user.refresh_from_db()
        record.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertEqual(record.subscription_status, "revoked")

        record = mark_refund_or_dispute(
            {
                "id": "dp_dispute_created",
                "charge": "ch_dispute_created",
                "customer": "cus_dispute_created_then_won",
                "status": "won",
                "reason": "fraudulent",
            },
            event_type="charge.dispute.closed",
            event_id="evt_dispute_won_after_created",
        )

        self.user.refresh_from_db()
        record.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(record.subscription_status, "active")
        self.assertIsNone(record.revoked_at)
        self.assertEqual(record.revoked_reason, "")
        self.assertIsNone(record.last_refund_or_dispute_at)
        dispute_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="disputed",
            stripe_event_id="evt_dispute_won_after_created",
        )
        self.assertTrue(dispute_log.metadata["access_restored"])
        restored_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="restored",
            stripe_event_id="evt_dispute_won_after_created",
        )
        self.assertEqual(restored_log.reason, "Stripe dispute won")

    def test_dispute_closed_lost_revokes_access(self):
        from accounts.billing import mark_refund_or_dispute

        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_dispute_lost",
            subscription_status="active",
            access_source="stripe",
        )

        record = mark_refund_or_dispute(
            {
                "id": "dp_dispute_lost",
                "charge": "ch_dispute_lost",
                "customer": "cus_dispute_lost",
                "status": "lost",
                "reason": "fraudulent",
            },
            event_type="charge.dispute.closed",
            event_id="evt_dispute_lost",
        )

        self.user.refresh_from_db()
        record.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertEqual(record.subscription_status, "revoked")
        self.assertIsNotNone(record.last_refund_or_dispute_at)
        audit_log = PremiumAuditLog.objects.get(
            user=self.user,
            action="disputed",
            stripe_event_id="evt_dispute_lost",
        )
        self.assertEqual(audit_log.metadata["dispute_status"], "lost")
        self.assertTrue(audit_log.metadata["access_revoked"])
        self.assertFalse(audit_log.metadata["access_restored"])


class PremiumAccessCodeCommandTestCase(TestCase):
    def test_set_premium_user_command_logs_manual_grant_and_revoke(self):
        user = User.objects.create_user(username="manual-premium-user")

        call_command(
            "set_premium_user",
            "manual-premium-user",
            "--on",
            "--reason",
            "Support comp",
            stdout=StringIO(),
        )

        user.refresh_from_db()
        self.assertTrue(user.is_premium)
        grant_log = PremiumAuditLog.objects.get(user=user, action="granted")
        self.assertEqual(grant_log.source, "manual")
        self.assertEqual(grant_log.reason, "Support comp")
        self.assertEqual(grant_log.metadata["command"], "set_premium_user")

        call_command(
            "set_premium_user",
            "manual-premium-user",
            "--off",
            "--reason",
            "Support comp ended",
            stdout=StringIO(),
        )

        user.refresh_from_db()
        self.assertFalse(user.is_premium)
        revoke_log = PremiumAuditLog.objects.get(user=user, action="revoked")
        self.assertEqual(revoke_log.source, "manual")
        self.assertEqual(revoke_log.reason, "Support comp ended")

    def test_set_premium_user_command_does_not_log_when_unchanged(self):
        user = User.objects.create_user(username="manual-premium-unchanged", is_premium=True)

        call_command("set_premium_user", "manual-premium-unchanged", "--on", stdout=StringIO())

        self.assertFalse(PremiumAuditLog.objects.filter(user=user).exists())

    def test_issue_premium_code_bulk_csv_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "codes.csv"
            stdout = StringIO()

            call_command(
                "issue_premium_code",
                "--label",
                "campaign",
                "--campaign",
                "spring-2026",
                "--count",
                "3",
                "--max-uses",
                "2",
                "--output-csv",
                str(output_path),
                stdout=stdout,
            )

            self.assertEqual(PremiumAccessCode.objects.count(), 3)
            self.assertEqual(
                set(PremiumAccessCode.objects.values_list("campaign_name", flat=True)),
                {"spring-2026"},
            )
            self.assertTrue(output_path.exists())
            content = output_path.read_text(encoding="utf-8")
            self.assertIn(
                "id,code,label,campaign_name,status,max_uses,use_count,remaining_uses,expires_at",
                content,
            )
            self.assertIn("campaign-1", content)
            self.assertIn("spring-2026", content)
            self.assertIn("active,2,0,2", content)
            self.assertIn("Premium code issued: 3", stdout.getvalue())
            self.assertIn("campaign_name=spring-2026", stdout.getvalue())

    def test_issue_premium_code_rejects_custom_code_with_bulk_count(self):
        with self.assertRaises(Exception):
            call_command(
                "issue_premium_code",
                "--code",
                "PREMIUM-CUSTOM",
                "--count",
                "2",
                stdout=StringIO(),
            )

    def test_expire_premium_access_task_calls_expiration(self):
        from schedules.tasks import expire_premium_access

        user = User.objects.create_user(username="task-expire-user")
        user.is_premium = True
        user.save(update_fields=["is_premium"])
        access_code, _ = PremiumAccessCode.issue(
            label="task-expire-code",
            campaign_name="task-expire-campaign",
        )
        PremiumAccessCodeRedemption.objects.create(access_code=access_code, user=user)
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() - timedelta(minutes=1),
        )

        result = expire_premium_access()

        self.assertEqual(result, 1)
        user.refresh_from_db()
        self.assertFalse(user.is_premium)
        audit_log = PremiumAuditLog.objects.get(user=user, action="revoked")
        self.assertEqual(audit_log.metadata["access_code_id"], access_code.pk)
        self.assertEqual(audit_log.metadata["access_code_label"], "task-expire-code")
        self.assertEqual(audit_log.metadata["access_code_campaign_name"], "task-expire-campaign")

    def test_expired_promo_does_not_remove_manual_grant(self):
        from schedules.tasks import expire_premium_access

        user = User.objects.create_user(username="task-expire-manual-user")
        user.is_premium = True
        user.save(update_fields=["is_premium"])
        PremiumAuditLog.objects.create(
            user=user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() - timedelta(minutes=1),
        )

        result = expire_premium_access()

        self.assertEqual(result, 1)
        user.refresh_from_db()
        self.assertTrue(user.is_premium)

    def test_expire_premium_access_dry_run_reports_without_changing(self):
        user = User.objects.create_user(username="command-expire-dry-run-user")
        user.is_premium = True
        user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() - timedelta(minutes=1),
        )
        stdout = StringIO()

        call_command("expire_premium_access", "--dry-run", stdout=stdout)

        user.refresh_from_db()
        self.assertTrue(user.is_premium)
        self.assertIn("expired_premium_access_dry_run=1", stdout.getvalue())
        self.assertFalse(
            PremiumAuditLog.objects.filter(
                user=user,
                action="revoked",
                reason="Premium access code expired",
            ).exists()
        )

    def test_reconcile_premium_access_dry_run_reports_without_changing(self):
        user = User.objects.create_user(username="reconcile-dry-user")
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
        )
        stdout = StringIO()

        call_command("reconcile_premium_access", "--dry-run", stdout=stdout)

        user.refresh_from_db()
        self.assertFalse(user.is_premium)
        self.assertIn("reconcile-dry-user: is_premium False -> True", stdout.getvalue())
        self.assertIn("changed=1", stdout.getvalue())
        self.assertFalse(PremiumAuditLog.objects.filter(user=user).exists())

    def test_reconcile_premium_access_updates_stale_user_flag_and_logs(self):
        user = User.objects.create_user(username="reconcile-active-user")
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
        )
        stdout = StringIO()

        call_command("reconcile_premium_access", stdout=stdout)

        user.refresh_from_db()
        self.assertTrue(user.is_premium)
        self.assertIn("changed=1", stdout.getvalue())
        self.assertTrue(
            PremiumAuditLog.objects.filter(
                user=user,
                action="granted",
                reason="Premium access reconciled from billing record",
            ).exists()
        )

    def test_reconcile_premium_access_preserves_manual_grant(self):
        user = User.objects.create_user(username="reconcile-manual-user", is_premium=True)
        PremiumAuditLog.objects.create(
            user=user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="canceled",
            access_source="stripe",
        )
        stdout = StringIO()

        call_command("reconcile_premium_access", stdout=stdout)

        user.refresh_from_db()
        self.assertTrue(user.is_premium)
        self.assertIn("changed=0", stdout.getvalue())

    def test_reconcile_premium_access_expires_promo_records_first(self):
        user = User.objects.create_user(username="reconcile-expired-user")
        user.is_premium = True
        user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() - timedelta(minutes=1),
        )
        stdout = StringIO()

        call_command("reconcile_premium_access", stdout=stdout)

        user.refresh_from_db()
        self.assertFalse(user.is_premium)
        self.assertIn("expired=1", stdout.getvalue())

    @override_settings(
        STRIPE_CHECKOUT_ENABLED=True,
        STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy",
        STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480",
        STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT="4800",
    )
    def test_billing_status_report_outputs_operational_counts(self):
        active_user = User.objects.create_user(username="report-active-user")
        active_user.is_premium = True
        active_user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=active_user,
            subscription_status="active",
            access_source="stripe",
            cancel_at_period_end=True,
        )
        stale_user = User.objects.create_user(username="report-stale-user")
        PremiumSubscription.objects.create(
            user=stale_user,
            subscription_status="active",
            access_source="stripe",
            last_payment_failed_at=timezone.now(),
        )
        expired_user = User.objects.create_user(username="report-expired-user")
        expired_user.is_premium = True
        expired_user.save(update_fields=["is_premium"])
        expired_code, _ = PremiumAccessCode.issue(
            label="report-expired-code",
            campaign_name="expired-campaign",
        )
        PremiumAccessCodeRedemption.objects.create(access_code=expired_code, user=expired_user)
        PremiumSubscription.objects.create(
            user=expired_user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() - timedelta(minutes=1),
            last_refund_or_dispute_at=timezone.now(),
        )
        indefinite_promo_user = User.objects.create_user(username="report-indefinite-promo-user")
        indefinite_promo_user.is_premium = True
        indefinite_promo_user.save(update_fields=["is_premium"])
        indefinite_code, _ = PremiumAccessCode.issue(
            label="report-indefinite-code",
            campaign_name="indefinite-campaign",
        )
        PremiumAccessCodeRedemption.objects.create(
            access_code=indefinite_code,
            user=indefinite_promo_user,
        )
        PremiumSubscription.objects.create(
            user=indefinite_promo_user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=None,
        )
        expiring_promo_user = User.objects.create_user(username="report-expiring-promo-user")
        expiring_promo_user.is_premium = True
        expiring_promo_user.save(update_fields=["is_premium"])
        expiring_code, _ = PremiumAccessCode.issue(
            label="report-expiring-code",
            campaign_name="expiring-campaign",
        )
        PremiumAccessCodeRedemption.objects.create(
            access_code=expiring_code,
            user=expiring_promo_user,
        )
        PremiumSubscription.objects.create(
            user=expiring_promo_user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() + timedelta(days=7),
        )
        active_refund_user = User.objects.create_user(username="report-active-refund-user")
        active_refund_user.is_premium = True
        active_refund_user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=active_refund_user,
            subscription_status="active",
            access_source="stripe",
            stripe_price_id="price_report_monthly",
            billing_interval="month",
            last_refund_or_dispute_at=timezone.now(),
        )
        manual_without_subscription_user = User.objects.create_user(
            username="report-manual-without-subscription-user",
            is_premium=True,
        )
        PremiumAuditLog.objects.create(
            user=manual_without_subscription_user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        stale_manual_without_subscription_user = User.objects.create_user(
            username="report-stale-manual-without-subscription-user",
            is_premium=False,
        )
        PremiumAuditLog.objects.create(
            user=stale_manual_without_subscription_user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        manual_with_subscription_user = User.objects.create_user(
            username="report-manual-with-subscription-user",
            is_premium=True,
        )
        PremiumAuditLog.objects.create(
            user=manual_with_subscription_user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        PremiumSubscription.objects.create(
            user=manual_with_subscription_user,
            subscription_status="canceled",
            access_source="stripe",
            stripe_price_id="price_report_yearly",
            billing_interval="year",
        )
        StripeWebhookEvent.objects.create(
            event_id="evt_report_latest",
            event_type="customer.subscription.updated",
        )
        StripeWebhookEvent.objects.create(
            event_id="evt_report_failed",
            event_type="invoice.payment_failed",
            processing_status=StripeWebhookEvent.STATUS_FAILED,
            error_message="temporary failure",
            processed_at=timezone.now() - timedelta(minutes=5),
        )
        StripeWebhookEvent.objects.create(
            event_id="evt_report_processing",
            event_type="customer.subscription.updated",
            processing_status=StripeWebhookEvent.STATUS_PROCESSING,
            processed_at=timezone.now() - timedelta(minutes=10),
        )
        stdout = StringIO()

        call_command("billing_status_report", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("billing_status_report=ok", output)
        self.assertIn("total_subscriptions=7", output)
        self.assertIn("active_access=8", output)
        self.assertIn("stripe_checkout_enabled=true", output)
        self.assertIn("expected_stripe_price_currency=jpy", output)
        self.assertIn("expected_monthly_unit_amount=480", output)
        self.assertIn("expected_yearly_unit_amount=4800", output)
        self.assertIn("manual_override_users=3", output)
        self.assertIn("manual_override_without_subscription=2", output)
        self.assertIn("stale_user_flags=3", output)
        self.assertIn("expired_promo_records=1", output)
        self.assertIn("promo_indefinite_records=1", output)
        self.assertIn("promo_expiring_active_records=1", output)
        self.assertIn("promo_expiring_soon_records=1", output)
        self.assertIn("cancel_at_period_end_records=1", output)
        self.assertIn("billing_intervals:", output)
        self.assertIn("- (blank)=5", output)
        self.assertIn("- month=1", output)
        self.assertIn("- year=1", output)
        self.assertIn("payment_failed_records=1", output)
        self.assertIn("refund_or_dispute_records=2", output)
        self.assertIn("refund_or_dispute_active_records=1", output)
        self.assertIn("last_webhook_event_id=evt_report_latest", output)
        self.assertIn("last_webhook_event_type=customer.subscription.updated", output)
        self.assertIn("last_webhook_processed_at=", output)
        self.assertIn("failed_webhook_events=1", output)
        self.assertIn("processing_webhook_events=1", output)
        self.assertIn("stale_processing_webhook_events=0", output)
        self.assertIn("last_failed_webhook_event_id=evt_report_failed", output)
        self.assertIn("last_failed_webhook_event_type=invoice.payment_failed", output)
        self.assertIn("last_stale_processing_webhook_event_id=(none)", output)
        self.assertIn("- active=3", output)
        self.assertIn("- canceled=1", output)
        self.assertIn("- promo=3", output)
        self.assertIn("promo_campaigns:", output)
        self.assertIn(
            "- expired-campaign: total=1 active=0 expired=1 expiring_soon=0 indefinite=0",
            output,
        )
        self.assertIn(
            "- expiring-campaign: total=1 active=1 expired=0 expiring_soon=1 indefinite=0",
            output,
        )
        self.assertIn(
            "- indefinite-campaign: total=1 active=1 expired=0 expiring_soon=0 indefinite=1",
            output,
        )

    @override_settings(
        STRIPE_CHECKOUT_ENABLED=False,
        STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy",
        STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480",
        STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT="4800",
    )
    def test_billing_status_report_json_output(self):
        user = User.objects.create_user(username="report-json-user")
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="canceled",
            access_source="stripe",
        )
        StripeWebhookEvent.objects.create(
            event_id="evt_report_json",
            event_type="checkout.session.completed",
        )
        StripeWebhookEvent.objects.create(
            event_id="evt_report_json_failed",
            event_type="invoice.payment_failed",
            processing_status=StripeWebhookEvent.STATUS_FAILED,
            processed_at=timezone.now() - timedelta(minutes=5),
        )
        stdout = StringIO()

        call_command("billing_status_report", "--json", stdout=stdout)

        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["total_subscriptions"], 1)
        self.assertFalse(payload["stripe_checkout_enabled"])
        self.assertEqual(payload["expected_stripe_price_currency"], "jpy")
        self.assertEqual(payload["expected_monthly_unit_amount"], "480")
        self.assertEqual(payload["expected_yearly_unit_amount"], "4800")
        self.assertEqual(payload["statuses"], {"canceled": 1})
        self.assertEqual(payload["manual_override_users"], 0)
        self.assertEqual(payload["manual_override_without_subscription"], 0)
        self.assertEqual(payload["promo_indefinite_records"], 0)
        self.assertEqual(payload["promo_expiring_active_records"], 0)
        self.assertEqual(payload["promo_expiring_soon_records"], 0)
        self.assertEqual(payload["promo_campaigns"], [])
        self.assertEqual(payload["cancel_at_period_end_records"], 0)
        self.assertEqual(payload["refund_or_dispute_active_records"], 0)
        self.assertEqual(payload["last_webhook_event_id"], "evt_report_json")
        self.assertEqual(payload["last_webhook_event_type"], "checkout.session.completed")
        self.assertTrue(payload["last_webhook_processed_at"])
        self.assertEqual(payload["failed_webhook_events"], 1)
        self.assertEqual(payload["processing_webhook_events"], 0)
        self.assertEqual(payload["stale_processing_webhook_events"], 0)
        self.assertEqual(payload["last_failed_webhook_event_id"], "evt_report_json_failed")
        self.assertEqual(payload["last_failed_webhook_event_type"], "invoice.payment_failed")
        self.assertEqual(payload["last_stale_processing_webhook_event_id"], "")

    def test_billing_status_report_fail_on_issues_raises_for_stale_access(self):
        user = User.objects.create_user(username="report-fail-stale-user")
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
        )

        with self.assertRaises(CommandError) as context:
            call_command("billing_status_report", "--fail-on-issues", stdout=StringIO())

        self.assertIn("stale_user_flags=1", str(context.exception))

    def test_billing_status_report_can_fail_on_payment_issues(self):
        user = User.objects.create_user(username="report-fail-payment-user")
        user.is_premium = True
        user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
            last_payment_failed_at=timezone.now(),
        )

        call_command("billing_status_report", "--fail-on-issues", stdout=StringIO())
        with self.assertRaises(CommandError) as context:
            call_command(
                "billing_status_report",
                "--fail-on-issues",
                "--include-payment-issues",
                stdout=StringIO(),
            )

        self.assertIn("payment_failed_records=1", str(context.exception))

    def test_billing_status_report_can_fail_on_failed_webhook_events(self):
        StripeWebhookEvent.objects.create(
            event_id="evt_report_failed_issue",
            event_type="invoice.payment_failed",
            processing_status=StripeWebhookEvent.STATUS_FAILED,
            error_message="temporary failure",
        )

        call_command("billing_status_report", "--fail-on-issues", stdout=StringIO())
        with self.assertRaises(CommandError) as context:
            call_command(
                "billing_status_report",
                "--fail-on-issues",
                "--include-payment-issues",
                stdout=StringIO(),
            )

        self.assertIn("failed_webhook_events=1", str(context.exception))

    def test_billing_status_report_can_fail_on_stale_processing_webhook_events(self):
        StripeWebhookEvent.objects.create(
            event_id="evt_report_stale_processing_issue",
            event_type="checkout.session.completed",
            processing_status=StripeWebhookEvent.STATUS_PROCESSING,
            processed_at=timezone.now() - timedelta(minutes=20),
        )

        call_command("billing_status_report", "--fail-on-issues", stdout=StringIO())
        with self.assertRaises(CommandError) as context:
            call_command(
                "billing_status_report",
                "--fail-on-issues",
                "--include-payment-issues",
                stdout=StringIO(),
            )

        self.assertIn("stale_processing_webhook_events=1", str(context.exception))

    def test_billing_status_report_can_fail_on_active_refund_or_dispute(self):
        user = User.objects.create_user(username="report-fail-active-refund-user")
        user.is_premium = True
        user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
            last_refund_or_dispute_at=timezone.now(),
        )

        with self.assertRaises(CommandError) as context:
            call_command(
                "billing_status_report",
                "--fail-on-issues",
                "--include-payment-issues",
                stdout=StringIO(),
            )

        self.assertIn("refund_or_dispute_active_records=1", str(context.exception))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
    )
    def test_billing_webhook_smoke_command_exercises_subscription_states(self):
        stdout = StringIO()

        call_command("billing_webhook_smoke", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("OK checkout.session.completed is_premium=True", output)
        self.assertIn("OK subscription.active is_premium=True", output)
        self.assertIn(
            "OK subscription.active stripe_price_id=price_smoke_monthly billing_interval=month",
            output,
        )
        self.assertIn("OK subscription.cancel_at_period_end is_premium=True", output)
        self.assertIn(
            "OK subscription.cancel_at_period_end stripe_price_id=price_smoke_monthly billing_interval=month",
            output,
        )
        self.assertIn("OK subscription.yearly_active is_premium=True", output)
        self.assertIn(
            "OK subscription.yearly_active stripe_price_id=price_smoke_yearly billing_interval=year",
            output,
        )
        self.assertIn("OK invoice.payment_failed", output)
        self.assertIn("OK invoice.payment_succeeded", output)
        self.assertIn("OK subscription.unpaid is_premium=False", output)
        self.assertIn("OK subscription.deleted is_premium=False", output)
        self.assertIn("OK subscription.active.before_refund is_premium=True", output)
        self.assertIn("OK charge.refunded is_premium=False", output)
        self.assertIn("OK charge.refunded", output)
        self.assertIn("OK subscription.active_after_refund is_premium=False", output)
        self.assertIn("OK subscription.active.before_dispute is_premium=True", output)
        self.assertIn("OK charge.dispute.created is_premium=False", output)
        self.assertIn("OK charge.dispute.created", output)
        self.assertIn("OK subscription.active_after_dispute is_premium=False", output)
        self.assertIn("OK charge.dispute.closed.won is_premium=True", output)
        self.assertIn("OK charge.dispute.closed.won", output)
        self.assertIn("billing_webhook_smoke=ok", output)

    @override_settings(
        STRIPE_CHECKOUT_ENABLED=True,
        STRIPE_PREMIUM_PRICE_ID="price_record",
        STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy",
        STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480",
        STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT="4800",
        STRIPE_PUBLISHABLE_KEY="pk_test_record",
        STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_record",
        PUBLIC_SITE_URL="https://example.test",
    )
    def test_billing_verification_record_command_outputs_markdown(self):
        stdout = StringIO()

        call_command(
            "billing_verification_record",
            "--environment",
            "local",
            "--stripe-mode",
            "test",
            "--confirmed-by",
            "tester",
            "--commit",
            "abc123",
            "--skip-command-checks",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("# Stripe課金確認記録", output)
        self.assertIn("| 確認者 | tester |", output)
        self.assertIn("| 環境 | local |", output)
        self.assertIn("| Monthly Price ID | price_record |", output)
        self.assertIn("| Yearly Price ID | 未設定 |", output)
        self.assertIn("| Expected Stripe Price currency | jpy |", output)
        self.assertIn("| Expected monthly unit amount | 480 |", output)
        self.assertIn("| Expected yearly unit amount | 4800 |", output)
        self.assertIn("| Stripe Checkout enabled | yes |", output)
        self.assertIn("| Stripe publishable key configured | yes |", output)
        self.assertIn("| Customer Portal configuration ID | bpc_record |", output)
        self.assertNotIn("pk_test_record", output)
        self.assertIn("| Webhook endpoint URL | https://example.test/api/billing/webhook/ |", output)
        self.assertIn("checkout.session.completed", output)
        self.assertIn("invoice.payment_failed", output)
        self.assertIn("charge.dispute.closed", output)
        self.assertIn("status=wonはチャージバック由来の自動停止を復旧", output)
        self.assertIn("issue_premium_code --campaign", output)
        self.assertIn("billing_status_reportのpromo_campaignsを確認", output)
        self.assertIn("Premium audit logs", output)
        self.assertIn("skip-command-checks指定", output)
        self.assertIn("Stripe remote check", output)
        self.assertIn("Billing status report", output)
        self.assertIn("python manage.py billing_status_report", output)
        self.assertIn("Check billing_intervals for month/year/blank counts.", output)
        self.assertIn("stripe_price_id / billing_interval", output)
        self.assertIn("Stripe subscription metadata includes stripe_price_id / billing_interval", output)

    def test_billing_release_gate_defaults_to_disabled_when_setting_is_missing(self):
        stdout = StringIO()

        with patch("accounts.management.commands.billing_release_gate.settings", SimpleNamespace()):
            call_command("billing_release_gate", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("stripe_checkout_enabled=false", output)
        self.assertIn("billing_release_gate=ok checkout-disabled", output)

    @override_settings(STRIPE_CHECKOUT_ENABLED=False)
    def test_billing_release_gate_passes_when_checkout_disabled(self):
        stdout = StringIO()

        call_command("billing_release_gate", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("stripe_checkout_enabled=false", output)
        self.assertIn("billing_release_gate=ok checkout-disabled", output)

    @override_settings(STRIPE_CHECKOUT_ENABLED=True)
    def test_billing_release_gate_requires_verification_record_when_checkout_enabled(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_release_gate", stdout=StringIO())

        self.assertIn("--verification-record", str(context.exception))

    @override_settings(STRIPE_CHECKOUT_ENABLED=True)
    def test_billing_release_gate_rejects_incomplete_local_verification_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            record_path = Path(tmpdir) / "local-record.md"
            record_path.write_text(
                """# Stripe billing record
| Stripe mode | test |
| Stripe Checkout enabled | yes |
remote check not run or produced no output
""",
                encoding="utf-8",
            )

            with self.assertRaises(CommandError) as context:
                call_command(
                    "billing_release_gate",
                    "--verification-record",
                    str(record_path),
                    stdout=StringIO(),
                )

        message = str(context.exception)
        self.assertIn("not release-ready", message)
        self.assertIn("remote check not run or produced no output", message)

    @override_settings(STRIPE_CHECKOUT_ENABLED=True)
    def test_billing_release_gate_accepts_complete_test_mode_verification_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            record_path = Path(tmpdir) / "aws-pre-record.md"
            record_path.write_text(self._complete_billing_release_record(), encoding="utf-8")
            stdout = StringIO()

            call_command(
                "billing_release_gate",
                "--verification-record",
                str(record_path),
                stdout=stdout,
            )

        output = stdout.getvalue()
        self.assertIn("stripe_checkout_enabled=true", output)
        self.assertIn("billing_release_gate=ok checkout-verified", output)

    def _complete_billing_release_record(self):
        return """# Stripe billing verification record

| Stripe mode | test |
| Stripe Checkout enabled | yes |
| Expected Stripe Price currency | jpy |
| Expected monthly unit amount | 480 |
| Expected yearly unit amount | 4800 |

billing_stripe_remote_check=ok
recent_event_ids:
- checkout.session.completed: evt_checkout_recent
- customer.subscription.created: evt_created_recent
- customer.subscription.updated: evt_update_recent
- customer.subscription.deleted: evt_deleted_recent
- invoice.payment_failed: evt_failed_recent
- invoice.payment_succeeded: evt_succeeded_recent
- charge.refunded: evt_refunded_recent
- charge.dispute.created: evt_dispute_recent
- charge.dispute.closed: evt_dispute_closed_recent
recent_cancel_at_period_end_event_ids: evt_cancel_at_period_end_recent
cancel_at_period_end=true
StripeWebhookEvent
PremiumSubscription
Premium audit logs
"""

    @override_settings(
        STRIPE_PREMIUM_PRICE_ID="price_record",
        PUBLIC_SITE_URL="https://example.test",
    )
    def test_billing_verification_record_command_can_write_output_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "billing-record.md"

            call_command(
                "billing_verification_record",
                "--output",
                str(output_path),
                "--skip-command-checks",
                stdout=StringIO(),
            )

            content = output_path.read_text(encoding="utf-8")
            self.assertIn("# Stripe課金確認記録", content)
            self.assertIn("Secrets、実カード情報、顧客の個人情報", content)

    @override_settings(
        STRIPE_PREMIUM_PRICE_ID="price_record",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_verification_record.call_command")
    def test_billing_verification_record_command_can_run_remote_check(self, command_mock):
        def command_side_effect(command_name, *args, **kwargs):
            stdout = kwargs["stdout"]
            if command_name == "check":
                stdout.write("System check identified no issues (0 silenced).\n")
            elif command_name == "billing_preflight":
                stdout.write("billing_preflight=ok\n")
            elif command_name == "billing_status_report":
                stdout.write("billing_status_report=ok\n")
                stdout.write("last_webhook_event_id=evt_latest\n")
                stdout.write("last_webhook_event_type=customer.subscription.updated\n")
                stdout.write("last_webhook_processed_at=2026-06-20T00:00:00+00:00\n")
                stdout.write("failed_webhook_events=0\n")
                stdout.write("stale_processing_webhook_events=0\n")
                stdout.write("last_failed_webhook_event_id=(none)\n")
                stdout.write("last_stale_processing_webhook_event_id=(none)\n")
            elif command_name == "billing_stripe_remote_check":
                stdout.write("recent_event_ids:\n")
                stdout.write("- checkout.session.completed: evt_checkout_recent\n")
                stdout.write("- customer.subscription.created: evt_created_recent\n")
                stdout.write("- customer.subscription.updated: evt_update_recent\n")
                stdout.write("- customer.subscription.deleted: evt_deleted_recent\n")
                stdout.write("- invoice.payment_failed: evt_failed_recent\n")
                stdout.write("- invoice.payment_succeeded: evt_succeeded_recent\n")
                stdout.write("- charge.refunded: evt_refunded_recent\n")
                stdout.write("- charge.dispute.created: evt_dispute_recent\n")
                stdout.write("- charge.dispute.closed: evt_dispute_closed_recent\n")
                stdout.write("recent_cancel_at_period_end_event_ids: evt_update_recent\n")
                stdout.write("OK stripe recent operational events last 48h\n")
                stdout.write("billing_stripe_remote_check=ok\n")
            else:
                raise AssertionError(command_name)

        command_mock.side_effect = command_side_effect
        stdout = StringIO()

        call_command(
            "billing_verification_record",
            "--run-remote-check",
            "--remote-skip-portal",
            "--remote-require-recent-events",
            "--remote-recent-hours",
            "48",
            "--base-url",
            "https://billing.example",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("Stripe remote check", output)
        self.assertIn("billing_stripe_remote_check=ok", output)
        self.assertIn("last_webhook_event_id=evt_latest", output)
        self.assertIn("last_webhook_event_type=customer.subscription.updated", output)
        self.assertIn("last_webhook_processed_at=2026-06-20T00:00:00+00:00", output)
        self.assertIn("failed_webhook_events=0", output)
        self.assertIn("stale_processing_webhook_events=0", output)
        self.assertIn("last_failed_webhook_event_id=(none)", output)
        self.assertIn("last_stale_processing_webhook_event_id=(none)", output)
        self.assertIn("## Stripe recent event IDs", output)
        self.assertIn("- checkout.session.completed: evt_checkout_recent", output)
        self.assertIn("- customer.subscription.created: evt_created_recent", output)
        self.assertIn("- customer.subscription.updated: evt_update_recent", output)
        self.assertIn("- charge.dispute.closed: evt_dispute_closed_recent", output)
        self.assertIn("recent_cancel_at_period_end_event_ids: evt_update_recent", output)
        self.assertIn(
            "python manage.py billing_stripe_remote_check --skip-portal "
            "--require-recent-events --recent-hours 48 --webhook-url "
            "https://billing.example/api/billing/webhook/",
            output,
        )
        command_mock.assert_any_call(
            "billing_stripe_remote_check",
            "--skip-portal",
            "--require-recent-events",
            "--recent-hours",
            "48",
            "--webhook-url",
            "https://billing.example/api/billing/webhook/",
            stdout=ANY,
        )

    def test_setup_billing_local_creates_demo_users_and_code(self):
        stdout = StringIO()

        call_command(
            "setup_billing_local",
            "--password",
            "localpass123",
            "--code-expires-in-days",
            "7",
            stdout=stdout,
        )

        free_user = User.objects.get(username="billing-free")
        premium_user = User.objects.get(username="billing-premium")
        code_user = User.objects.get(username="billing-code")
        self.assertTrue(free_user.check_password("localpass123"))
        self.assertFalse(free_user.is_premium)
        self.assertTrue(premium_user.is_premium)
        self.assertFalse(code_user.is_premium)
        self.assertTrue(
            PremiumSubscription.objects.filter(
                user=premium_user,
                access_source="manual",
                subscription_status="promo",
            ).exists()
        )
        access_code = PremiumAccessCode.objects.get(label="local-demo")
        self.assertEqual(access_code.max_uses, 10)
        self.assertIsNotNone(access_code.expires_at)
        output = stdout.getvalue()
        self.assertIn("Local billing users are ready.", output)
        self.assertIn("billing-free / localpass123", output)
        self.assertIn("premium code:", output)
        self.assertIn("premium code expires at:", output)
        self.assertIn("Stripe checkout configuration:", output)
        self.assertIn("development env file: .env.development", output)
        self.assertIn("create test Prices: python manage.py create_stripe_development_prices", output)
        self.assertIn("verify settings: python manage.py billing_preflight", output)
        self.assertIn("monthly checkout button appears when STRIPE_PREMIUM_PRICE_ID is set", output)
        self.assertIn("yearly checkout button appears when STRIPE_PREMIUM_YEARLY_PRICE_ID is set", output)
        self.assertIn("http://127.0.0.1:8000/accounts/billing/", output)
        self.assertIn("http://127.0.0.1:8000/premium/", output)
        self.assertIn("http://127.0.0.1:8000/commercial-disclosure/", output)

    def test_setup_billing_local_can_create_admin_user(self):
        call_command(
            "setup_billing_local",
            "--include-admin",
            stdout=StringIO(),
        )

        admin_user = User.objects.get(username="billing-admin")
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    @override_settings(
        STRIPE_PREMIUM_PRICE_ID="price_monthly_local",
        STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_local",
        STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy",
        STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480",
        STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT="4800",
    )
    def test_setup_billing_local_outputs_configured_monthly_and_yearly_prices(self):
        stdout = StringIO()

        call_command("setup_billing_local", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("- monthly price id: price_monthly_local", output)
        self.assertIn("- yearly price id: price_yearly_local", output)
        self.assertIn("- expected currency: jpy", output)
        self.assertIn("- expected monthly unit amount: 480", output)
        self.assertIn("- expected yearly unit amount: 4800", output)


@override_settings(
    STRIPE_PREMIUM_EXPECTED_CURRENCY="",
    STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="",
    STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT="",
)
class BillingPreflightCommandTestCase(TestCase):
    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_SELLER_NAME="テスト販売者",
        LEGAL_SELLER_ADDRESS="東京都テスト区1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_passes_with_required_settings(self):
        stdout = StringIO()

        call_command("billing_preflight", "--strict", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("OK STRIPE_SECRET_KEY", output)
        self.assertIn("OK STRIPE_REVOKE_ON_REFUND_OR_DISPUTE: auto revoke", output)
        self.assertIn("OK url:billing-webhook", output)
        self.assertIn("OK page:commercial_disclosure", output)
        self.assertIn("OK page:premium_features", output)
        self.assertIn("billing_preflight=ok", output)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        STRIPE_PUBLISHABLE_KEY="pk_test_preflight",
        STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_preflight",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_accepts_optional_stripe_public_settings(self):
        stdout = StringIO()

        call_command("billing_preflight", "--strict", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("OK STRIPE_PUBLISHABLE_KEY", output)
        self.assertIn("OK STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID", output)
        self.assertIn("billing_preflight=ok", output)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        STRIPE_PUBLISHABLE_KEY="invalid_publishable_key",
        STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="invalid_portal_config",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_invalid_optional_stripe_public_settings(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("STRIPE_PUBLISHABLE_KEY", message)
        self.assertIn("set a value starting with pk_", message)
        self.assertIn("STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID", message)
        self.assertIn("set a value starting with bpc_", message)

    @override_settings(
        ENVIRONMENT="development",
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        STRIPE_PUBLISHABLE_KEY="pk_live_preflight",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_live_publishable_key_outside_production(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("STRIPE_PUBLISHABLE_KEY", message)
        self.assertIn("live Stripe publishable key cannot be used outside production", message)

    @override_settings(
        ENVIRONMENT="production",
        STRIPE_SECRET_KEY="sk_live_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        STRIPE_PUBLISHABLE_KEY="pk_test_preflight",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_test_publishable_key_in_production(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("STRIPE_PUBLISHABLE_KEY", message)
        self.assertIn("test Stripe publishable key cannot be used in production", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy",
        STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480",
        STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT="4800",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_accepts_expected_price_configuration(self):
        stdout = StringIO()

        call_command("billing_preflight", "--strict", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("OK expected-price-configuration", output)
        self.assertIn("billing_preflight=ok", output)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        STRIPE_PREMIUM_EXPECTED_CURRENCY="JPY",
        STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="not-an-integer",
        STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT="0",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_invalid_expected_price_configuration(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("expected-price-configuration", message)
        self.assertIn("STRIPE_PREMIUM_EXPECTED_CURRENCY", message)
        self.assertIn("STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT", message)
        self.assertIn("STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_preflight",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186 / \u5e74\u984d5,000\u5186",
        LEGAL_PAYMENT_TIMING="\u521d\u56de\u7533\u3057\u8fbc\u307f\u6642\u304a\u3088\u3073\u9078\u629e\u3057\u305f\u6708\u984d\u307e\u305f\u306f\u5e74\u984d\u306e\u66f4\u65b0\u65e5\u306b\u8ab2\u91d1\u3057\u307e\u3059\u3002",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_accepts_yearly_legal_text(self):
        stdout = StringIO()

        call_command("billing_preflight", "--strict", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("OK STRIPE_PREMIUM_YEARLY_PRICE_ID", output)
        self.assertIn("OK yearly-plan-legal-text", output)
        self.assertIn("billing_preflight=ok", output)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_preflight",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186",
        LEGAL_PAYMENT_TIMING="\u521d\u56de\u7533\u3057\u8fbc\u307f\u6642\u306b\u8ab2\u91d1\u3055\u308c\u3001\u4ee5\u5f8c\u306f\u6708\u984d\u30b5\u30d6\u30b9\u30af\u30ea\u30d7\u30b7\u30e7\u30f3\u3068\u3057\u3066\u81ea\u52d5\u66f4\u65b0\u3055\u308c\u307e\u3059\u3002",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_yearly_plan_without_yearly_legal_text(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("yearly-plan-legal-text", message)
        self.assertIn("PREMIUM_PRICE_LABEL", message)
        self.assertIn("LEGAL_PAYMENT_TIMING", message)

    @override_settings(
        ENVIRONMENT="development",
        STRIPE_SECRET_KEY="sk_live_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_SELLER_NAME="テスト販売者",
        LEGAL_SELLER_ADDRESS="東京都テスト区1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_live_secret_key_outside_production(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("STRIPE_SECRET_KEY", message)
        self.assertIn("live Stripe secret key cannot be used outside production", message)

    @override_settings(
        STRIPE_SECRET_KEY="",
        STRIPE_WEBHOOK_SECRET="",
        STRIPE_PREMIUM_PRICE_ID="",
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_SELLER_NAME="テスト販売者",
        LEGAL_SELLER_ADDRESS="東京都テスト区1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_fails_when_required_settings_missing(self):
        with self.assertRaises(CommandError):
            call_command("billing_preflight", "--strict", stdout=StringIO())

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="月額料金はStripe Checkout画面に表示される金額",
        LEGAL_SELLER_NAME="テスト販売者",
        LEGAL_SELLER_ADDRESS="東京都テスト区1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_placeholder_price_label(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("PREMIUM_PRICE_LABEL", message)
        self.assertIn("月額料金", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_SELLER_NAME="タブレノ運営",
        LEGAL_SELLER_ADDRESS="東京都テスト区1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_placeholder_seller_name(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("LEGAL_SELLER_NAME", message)
        self.assertIn("販売事業者名", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_SELLER_NAME="テスト販売者",
        LEGAL_SELLER_ADDRESS="東京都テスト区1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="not-an-email",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_invalid_contact_email(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("CONTACT_EMAIL", message)
        self.assertIn("問い合わせ先メール", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_SELLER_NAME="テスト販売者",
        LEGAL_SELLER_ADDRESS="東京都テスト区1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    @patch("accounts.management.commands.billing_preflight.Client")
    def test_billing_preflight_strict_rejects_missing_legal_page_values(self, client_class):
        response = Mock()
        response.status_code = 200
        response.charset = "utf-8"
        response.content = "月額500円だけ表示".encode("utf-8")
        client_class.return_value.get.return_value = response

        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("page:commercial_disclosure", message)
        self.assertIn("LEGAL_SELLER_NAME", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_SELLER_NAME="テスト販売者",
        LEGAL_SELLER_ADDRESS="東京都テスト区1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    @patch("accounts.management.commands.billing_preflight.Client")
    def test_billing_preflight_strict_rejects_mojibake_legal_page(self, client_class):
        response = Mock()
        response.status_code = 200
        response.charset = "utf-8"
        response.content = (
            "\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005 \u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1 03-0000-0000 "
            "billing-help@example.test \u6708\u984d500\u5186 "
            "Stripe Checkout\u3067\u5229\u7528\u53ef\u80fd\u306a\u30af\u30ec\u30b8\u30c3\u30c8\u30ab\u30fc\u30c9\u7b49\u306e\u6c7a\u6e08\u624b\u6bb5\u3002 "
            "\u521d\u56de\u7533\u3057\u8fbc\u307f\u6642\u306b\u8ab2\u91d1\u3055\u308c\u3001\u4ee5\u5f8c\u306f\u6708\u984d\u30b5\u30d6\u30b9\u30af\u30ea\u30d7\u30b7\u30e7\u30f3\u3068\u3057\u3066\u81ea\u52d5\u66f4\u65b0\u3055\u308c\u307e\u3059\u3002 "
            "\u6c7a\u6e08\u5b8c\u4e86\u5f8c\u3001Stripe Webhook\u306e\u51e6\u7406\u5b8c\u4e86\u3092\u3082\u3063\u3066\u30d7\u30ec\u30df\u30a2\u30e0\u6a5f\u80fd\u3092\u5229\u7528\u3067\u304d\u307e\u3059\u3002 "
            "\u30ed\u30b0\u30a4\u30f3\u5f8c\u306e\u30d7\u30ec\u30df\u30a2\u30e0\u7ba1\u7406\u753b\u9762\u304b\u3089Stripe Customer Portal\u3078\u79fb\u52d5\u3057\u3001\u3044\u3064\u3067\u3082\u89e3\u7d04\u3067\u304d\u307e\u3059\u3002 "
            "\u89e3\u7d04\u5f8c\u3082\u652f\u6255\u3044\u6e08\u307f\u671f\u9593\u306e\u7d42\u4e86\u307e\u3067\u306f\u30d7\u30ec\u30df\u30a2\u30e0\u6a5f\u80fd\u3092\u5229\u7528\u3067\u304d\u307e\u3059\u3002 "
            "\u30c7\u30b8\u30bf\u30eb\u30b5\u30fc\u30d3\u30b9\u306e\u6027\u8cea\u4e0a\u3001\u6c7a\u6e08\u5b8c\u4e86\u5f8c\u306e\u304a\u5ba2\u69d8\u90fd\u5408\u306b\u3088\u308b\u8fd4\u91d1\u306f\u539f\u5247\u3068\u3057\u3066\u53d7\u3051\u4ed8\u3051\u307e\u305b\u3093\u3002"
            "\u91cd\u8907\u8acb\u6c42\u3084\u8aa4\u8acb\u6c42\u304c\u78ba\u8a8d\u3055\u308c\u305f\u5834\u5408\u306f\u500b\u5225\u306b\u5bfe\u5fdc\u3057\u307e\u3059\u3002 "
            "\u7279\u5b9a\u5546\u53d6\u5f15\u6cd5\u306b\u57fa\u3065\u304f\u8868\u8a18 \u8ca9\u58f2\u4e8b\u696d\u8005 \u8ca9\u58f2\u4fa1\u683c \u652f\u6255\u65b9\u6cd5 "
            "\u652f\u6255\u6642\u671f \u63d0\u4f9b\u6642\u671f \u89e3\u7d04\u65b9\u6cd5 \u8fd4\u54c1\u30fb\u30ad\u30e3\u30f3\u30bb\u30eb\u30fb\u8fd4\u91d1 "
            "\u30d7\u30ec\u30df\u30a2\u30e0\u6a5f\u80fd \u6599\u91d1 \u30b7\u30ca\u30ea\u30aa\u30a2\u30fc\u30ab\u30a4\u30d6 \u6708\u984d\u6599\u91d1 \u8fd4\u91d1\u6761\u4ef6 \u4e8b\u696d\u8005\u60c5\u5831 "
            "\u7e5d"
        ).encode("utf-8")
        client_class.return_value.get.return_value = response

        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("page-quality:commercial_disclosure", message)
        self.assertIn("mojibake marker found", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="\u6708\u984d500\u5186",
        LEGAL_SELLER_NAME="\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005",
        LEGAL_SELLER_ADDRESS="\u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 3600.0,
            },
        },
    )
    @patch("accounts.management.commands.billing_preflight.Client")
    def test_billing_preflight_strict_rejects_missing_legal_page_labels(self, client_class):
        response = Mock()
        response.status_code = 200
        response.charset = "utf-8"
        response.content = (
            "\u30c6\u30b9\u30c8\u8ca9\u58f2\u8005 \u6771\u4eac\u90fd\u30c6\u30b9\u30c8\u533a1-1-1 03-0000-0000 "
            "billing-help@example.test \u6708\u984d500\u5186 "
            "Stripe Checkout\u3067\u5229\u7528\u53ef\u80fd\u306a\u30af\u30ec\u30b8\u30c3\u30c8\u30ab\u30fc\u30c9\u7b49\u306e\u6c7a\u6e08\u624b\u6bb5\u3002 "
            "\u521d\u56de\u7533\u3057\u8fbc\u307f\u6642\u306b\u8ab2\u91d1\u3055\u308c\u3001\u4ee5\u5f8c\u306f\u6708\u984d\u30b5\u30d6\u30b9\u30af\u30ea\u30d7\u30b7\u30e7\u30f3\u3068\u3057\u3066\u81ea\u52d5\u66f4\u65b0\u3055\u308c\u307e\u3059\u3002 "
            "\u6c7a\u6e08\u5b8c\u4e86\u5f8c\u3001Stripe Webhook\u306e\u51e6\u7406\u5b8c\u4e86\u3092\u3082\u3063\u3066\u30d7\u30ec\u30df\u30a2\u30e0\u6a5f\u80fd\u3092\u5229\u7528\u3067\u304d\u307e\u3059\u3002 "
            "\u30ed\u30b0\u30a4\u30f3\u5f8c\u306e\u30d7\u30ec\u30df\u30a2\u30e0\u7ba1\u7406\u753b\u9762\u304b\u3089Stripe Customer Portal\u3078\u79fb\u52d5\u3057\u3001\u3044\u3064\u3067\u3082\u89e3\u7d04\u3067\u304d\u307e\u3059\u3002 "
            "\u89e3\u7d04\u5f8c\u3082\u652f\u6255\u3044\u6e08\u307f\u671f\u9593\u306e\u7d42\u4e86\u307e\u3067\u306f\u30d7\u30ec\u30df\u30a2\u30e0\u6a5f\u80fd\u3092\u5229\u7528\u3067\u304d\u307e\u3059\u3002 "
            "\u30c7\u30b8\u30bf\u30eb\u30b5\u30fc\u30d3\u30b9\u306e\u6027\u8cea\u4e0a\u3001\u6c7a\u6e08\u5b8c\u4e86\u5f8c\u306e\u304a\u5ba2\u69d8\u90fd\u5408\u306b\u3088\u308b\u8fd4\u91d1\u306f\u539f\u5247\u3068\u3057\u3066\u53d7\u3051\u4ed8\u3051\u307e\u305b\u3093\u3002"
            "\u91cd\u8907\u8acb\u6c42\u3084\u8aa4\u8acb\u6c42\u304c\u78ba\u8a8d\u3055\u308c\u305f\u5834\u5408\u306f\u500b\u5225\u306b\u5bfe\u5fdc\u3057\u307e\u3059\u3002 "
        ).encode("utf-8")
        client_class.return_value.get.return_value = response

        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("page-quality:commercial_disclosure", message)
        self.assertIn("required legal text missing", message)

    def test_billing_preflight_strict_rejects_non_delivery_email_backend(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("EMAIL_BACKEND", message)
        self.assertIn("支払い失敗通知", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_preflight",
        STRIPE_WEBHOOK_SECRET="whsec_preflight",
        STRIPE_PREMIUM_PRICE_ID="price_preflight",
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_SELLER_NAME="テスト販売者",
        LEGAL_SELLER_ADDRESS="東京都テスト区1-1-1",
        LEGAL_SELLER_PHONE="03-0000-0000",
        CONTACT_EMAIL="billing-help@example.test",
        PUBLIC_SITE_URL="https://example.test",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        CELERY_BEAT_SCHEDULE={
            "expire-premium-access": {
                "task": "schedules.tasks.expire_premium_access",
                "schedule": 7200.0,
            },
        },
    )
    def test_billing_preflight_strict_rejects_slow_premium_expiration_schedule(self):
        with self.assertRaises(CommandError) as context:
            call_command("billing_preflight", "--strict", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("celery:expire-premium-access", message)
        self.assertIn("1時間以内", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
        STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_remote",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_passes_for_monthly_price_and_webhook(self, get_stripe):
        from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS

        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.WebhookEndpoint.list.return_value = {
            "data": [
                {
                    "url": "https://example.test/api/billing/webhook/",
                    "livemode": False,
                    "enabled_events": list(REQUIRED_WEBHOOK_EVENTS),
                }
            ]
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": [active_portal_configuration()]}
        get_stripe.return_value = stripe
        stdout = StringIO()

        call_command("billing_stripe_remote_check", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("OK stripe price monthly", output)
        self.assertIn("OK stripe customer portal", output)
        self.assertIn("OK stripe webhook endpoint https://example.test/api/billing/webhook/", output)
        self.assertIn("billing_stripe_remote_check=ok", output)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_monthly_remote",
        STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_validates_optional_yearly_price(self, get_stripe):
        from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS

        stripe = Mock()
        stripe.Price.retrieve.side_effect = [
            {
                "id": "price_monthly_remote",
                "active": True,
                "type": "recurring",
                "livemode": False,
                "recurring": {"interval": "month"},
            },
            {
                "id": "price_yearly_remote",
                "active": True,
                "type": "recurring",
                "livemode": False,
                "recurring": {"interval": "year"},
            },
        ]
        stripe.WebhookEndpoint.list.return_value = {
            "data": [
                {
                    "url": "https://example.test/api/billing/webhook/",
                    "livemode": False,
                    "enabled_events": list(REQUIRED_WEBHOOK_EVENTS),
                }
            ]
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": [active_portal_configuration()]}
        get_stripe.return_value = stripe
        stdout = StringIO()

        call_command("billing_stripe_remote_check", stdout=stdout)

        output = stdout.getvalue()
        self.assertEqual(stripe.Price.retrieve.call_args_list[0].args[0], "price_monthly_remote")
        self.assertEqual(stripe.Price.retrieve.call_args_list[1].args[0], "price_yearly_remote")
        self.assertIn("OK stripe price monthly", output)
        self.assertIn("OK stripe price yearly", output)
        self.assertIn("billing_stripe_remote_check=ok", output)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_monthly_remote",
        STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_non_yearly_yearly_price(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.side_effect = [
            {
                "id": "price_monthly_remote",
                "active": True,
                "type": "recurring",
                "livemode": False,
                "recurring": {"interval": "month"},
            },
            {
                "id": "price_yearly_remote",
                "active": True,
                "type": "recurring",
                "livemode": False,
                "recurring": {"interval": "month"},
            },
        ]
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", stdout=StringIO())

        self.assertIn("Stripe yearly price check failed", str(context.exception))
        self.assertIn("price interval is not year", str(context.exception))

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_can_require_recent_events(self, get_stripe):
        from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS

        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.WebhookEndpoint.list.return_value = {
            "data": [
                {
                    "url": "https://example.test/api/billing/webhook/",
                    "livemode": False,
                    "enabled_events": list(REQUIRED_WEBHOOK_EVENTS),
                }
            ]
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": [active_portal_configuration()]}
        stripe.Event.list.return_value = {
            "data": [
                {"id": "evt_checkout_recent", "type": "checkout.session.completed", "livemode": False},
                {"id": "evt_created_recent", "type": "customer.subscription.created", "livemode": False},
                {
                    "id": "evt_update_recent",
                    "type": "customer.subscription.updated",
                    "livemode": False,
                    "data": {"object": {"cancel_at_period_end": True}},
                },
                {"id": "evt_deleted_recent", "type": "customer.subscription.deleted", "livemode": False},
                {"id": "evt_failed_recent", "type": "invoice.payment_failed", "livemode": False},
                {"id": "evt_succeeded_recent", "type": "invoice.payment_succeeded", "livemode": False},
                {"id": "evt_refunded_recent", "type": "charge.refunded", "livemode": False},
                {"id": "evt_dispute_recent", "type": "charge.dispute.created", "livemode": False},
                {"id": "evt_dispute_closed_recent", "type": "charge.dispute.closed", "livemode": False},
            ]
        }
        get_stripe.return_value = stripe
        stdout = StringIO()

        call_command(
            "billing_stripe_remote_check",
            "--require-recent-events",
            "--recent-hours",
            "48",
            stdout=stdout,
        )

        output = stdout.getvalue()
        stripe.Event.list.assert_called_once()
        requested_event_types = set(stripe.Event.list.call_args.kwargs["types"])
        self.assertIn("customer.subscription.created", requested_event_types)
        self.assertIn("invoice.payment_succeeded", requested_event_types)
        self.assertIn("charge.refunded", requested_event_types)
        self.assertIn("charge.dispute.created", requested_event_types)
        self.assertIn("charge.dispute.closed", requested_event_types)
        self.assertIn("recent_event_ids:", output)
        self.assertIn("- checkout.session.completed: evt_checkout_recent", output)
        self.assertIn("- customer.subscription.created: evt_created_recent", output)
        self.assertIn("- customer.subscription.updated: evt_update_recent", output)
        self.assertIn("- charge.dispute.closed: evt_dispute_closed_recent", output)
        self.assertIn("recent_cancel_at_period_end_event_ids: evt_update_recent", output)
        self.assertIn("OK stripe recent operational events last 48h", output)
        self.assertIn("billing_stripe_remote_check=ok", output)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_missing_recent_canceling_event(self, get_stripe):
        from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS

        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.WebhookEndpoint.list.return_value = {
            "data": [
                {
                    "url": "https://example.test/api/billing/webhook/",
                    "livemode": False,
                    "enabled_events": list(REQUIRED_WEBHOOK_EVENTS),
                }
            ]
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": [active_portal_configuration()]}
        stripe.Event.list.return_value = {
            "data": [
                {"id": "evt_checkout_recent", "type": "checkout.session.completed", "livemode": False},
                {"id": "evt_created_recent", "type": "customer.subscription.created", "livemode": False},
                {
                    "id": "evt_update_recent",
                    "type": "customer.subscription.updated",
                    "livemode": False,
                    "data": {"object": {"cancel_at_period_end": False}},
                },
                {"id": "evt_deleted_recent", "type": "customer.subscription.deleted", "livemode": False},
                {"id": "evt_failed_recent", "type": "invoice.payment_failed", "livemode": False},
                {"id": "evt_succeeded_recent", "type": "invoice.payment_succeeded", "livemode": False},
                {"id": "evt_refunded_recent", "type": "charge.refunded", "livemode": False},
                {"id": "evt_dispute_recent", "type": "charge.dispute.created", "livemode": False},
                {"id": "evt_dispute_closed_recent", "type": "charge.dispute.closed", "livemode": False},
            ]
        }
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", "--require-recent-events", stdout=StringIO())

        self.assertIn(
            "missing recent customer.subscription.updated with cancel_at_period_end=true",
            str(context.exception),
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_missing_recent_refund_and_dispute_events(self, get_stripe):
        from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS

        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.WebhookEndpoint.list.return_value = {
            "data": [
                {
                    "url": "https://example.test/api/billing/webhook/",
                    "livemode": False,
                    "enabled_events": list(REQUIRED_WEBHOOK_EVENTS),
                }
            ]
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": [active_portal_configuration()]}
        stripe.Event.list.return_value = {
            "data": [
                {"id": "evt_checkout_recent", "type": "checkout.session.completed", "livemode": False},
                {"id": "evt_created_recent", "type": "customer.subscription.created", "livemode": False},
                {
                    "id": "evt_update_recent",
                    "type": "customer.subscription.updated",
                    "livemode": False,
                    "data": {"object": {"cancel_at_period_end": True}},
                },
                {"id": "evt_deleted_recent", "type": "customer.subscription.deleted", "livemode": False},
                {"id": "evt_failed_recent", "type": "invoice.payment_failed", "livemode": False},
                {"id": "evt_succeeded_recent", "type": "invoice.payment_succeeded", "livemode": False},
            ]
        }
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", "--require-recent-events", stdout=StringIO())

        message = str(context.exception)
        self.assertIn("missing recent events:", message)
        self.assertIn("charge.refunded", message)
        self.assertIn("charge.dispute.created", message)
        self.assertIn("charge.dispute.closed", message)

    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_live_secret_key_outside_production(self, get_stripe):
        live_key = chr(115) + chr(107) + "_" + "live" + "_remote"
        with override_settings(
            ENVIRONMENT="development",
            STRIPE_SECRET_KEY=live_key,
            STRIPE_PREMIUM_PRICE_ID="price_remote",
            PUBLIC_SITE_URL="https://example.test",
        ):
            with self.assertRaises(CommandError) as context:
                call_command(
                    "billing_stripe_remote_check",
                    "--skip-webhook",
                    "--skip-portal",
                    stdout=StringIO(),
                )

        self.assertIn(
            "STRIPE_SECRET_KEY live key cannot be used outside production",
            str(context.exception),
        )
        get_stripe.assert_not_called()

    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_test_secret_key_in_production(self, get_stripe):
        test_key = chr(115) + chr(107) + "_" + "test" + "_remote"
        with override_settings(
            ENVIRONMENT="production",
            STRIPE_SECRET_KEY=test_key,
            STRIPE_PREMIUM_PRICE_ID="price_remote",
            PUBLIC_SITE_URL="https://example.test",
        ):
            with self.assertRaises(CommandError) as context:
                call_command(
                    "billing_stripe_remote_check",
                    "--skip-webhook",
                    "--skip-portal",
                    stdout=StringIO(),
                )

        self.assertIn(
            "STRIPE_SECRET_KEY test key cannot be used in production",
            str(context.exception),
        )
        get_stripe.assert_not_called()

    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_unknown_secret_key_prefix(self, get_stripe):
        with override_settings(
            ENVIRONMENT="development",
            STRIPE_SECRET_KEY="invalid_remote_key",
            STRIPE_PREMIUM_PRICE_ID="price_remote",
            PUBLIC_SITE_URL="https://example.test",
        ):
            with self.assertRaises(CommandError) as context:
                call_command(
                    "billing_stripe_remote_check",
                    "--skip-webhook",
                    "--skip-portal",
                    stdout=StringIO(),
                )

        self.assertIn("STRIPE_SECRET_KEY must start with", str(context.exception))
        get_stripe.assert_not_called()

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_non_monthly_price(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "year"},
        }
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command(
                "billing_stripe_remote_check",
                "--skip-webhook",
                "--skip-portal",
                stdout=StringIO(),
            )

        self.assertIn("price interval is not month", str(context.exception))

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_price_livemode_mismatch(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": True,
            "recurring": {"interval": "month"},
        }
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command(
                "billing_stripe_remote_check",
                "--skip-webhook",
                "--skip-portal",
                stdout=StringIO(),
            )

        self.assertIn("price livemode mismatch: expected test, got live", str(context.exception))

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy",
        STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_validates_expected_monthly_price_amount(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "currency": "jpy",
            "unit_amount": 480,
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        get_stripe.return_value = stripe
        stdout = StringIO()

        call_command(
            "billing_stripe_remote_check",
            "--skip-webhook",
            "--skip-portal",
            stdout=stdout,
        )

        self.assertIn("OK stripe price monthly", stdout.getvalue())
        self.assertIn("billing_stripe_remote_check=ok", stdout.getvalue())

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy",
        STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_unexpected_price_amount_or_currency(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "currency": "usd",
            "unit_amount": 500,
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command(
                "billing_stripe_remote_check",
                "--skip-webhook",
                "--skip-portal",
                stdout=StringIO(),
            )

        message = str(context.exception)
        self.assertIn("price currency mismatch: expected jpy, got usd", message)
        self.assertIn("price unit_amount mismatch: expected 480, got 500", message)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="not-an-integer",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_invalid_expected_price_amount_setting(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command(
                "billing_stripe_remote_check",
                "--skip-webhook",
                "--skip-portal",
                stdout=StringIO(),
            )

        self.assertIn(
            "STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT must be an integer minor-unit amount",
            str(context.exception),
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_missing_webhook_event(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.WebhookEndpoint.list.return_value = {
            "data": [
                {
                    "url": "https://example.test/api/billing/webhook/",
                    "livemode": False,
                    "enabled_events": ["checkout.session.completed"],
                }
            ]
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": [active_portal_configuration()]}
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", stdout=StringIO())

        self.assertIn("missing webhook events", str(context.exception))

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_disabled_webhook_endpoint(self, get_stripe):
        from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS

        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.WebhookEndpoint.list.return_value = {
            "data": [
                {
                    "url": "https://example.test/api/billing/webhook/",
                    "status": "disabled",
                    "livemode": False,
                    "enabled_events": list(REQUIRED_WEBHOOK_EVENTS),
                }
            ]
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": [active_portal_configuration()]}
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", stdout=StringIO())

        self.assertIn("webhook endpoint is not enabled: disabled", str(context.exception))

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_webhook_livemode_mismatch(self, get_stripe):
        from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS

        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.WebhookEndpoint.list.return_value = {
            "data": [
                {
                    "url": "https://example.test/api/billing/webhook/",
                    "livemode": True,
                    "enabled_events": list(REQUIRED_WEBHOOK_EVENTS),
                }
            ]
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": [active_portal_configuration()]}
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", stdout=StringIO())

        self.assertIn(
            "webhook endpoint livemode mismatch: expected test, got live",
            str(context.exception),
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_portal_livemode_mismatch(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": [active_portal_configuration(livemode=True)]}
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", "--skip-webhook", stdout=StringIO())

        self.assertIn(
            "customer portal livemode mismatch: expected test, got live",
            str(context.exception),
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
        STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_missing",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_missing_customer_portal(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.billing_portal.Configuration.list.return_value = {"data": []}
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", "--skip-webhook", stdout=StringIO())

        self.assertIn("customer portal configuration not found: bpc_missing", str(context.exception))

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
        STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_inactive",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_inactive_configured_customer_portal(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        inactive_configuration = active_portal_configuration()
        inactive_configuration["id"] = "bpc_inactive"
        inactive_configuration["active"] = False
        stripe.billing_portal.Configuration.list.return_value = {"data": [inactive_configuration]}
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", "--skip-webhook", stdout=StringIO())

        self.assertIn(
            "customer portal configuration is not active: bpc_inactive",
            str(context.exception),
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_remote",
        STRIPE_PREMIUM_PRICE_ID="price_remote",
        PUBLIC_SITE_URL="https://example.test",
    )
    @patch("accounts.management.commands.billing_stripe_remote_check.get_stripe")
    def test_billing_stripe_remote_check_rejects_portal_without_cancellation(self, get_stripe):
        stripe = Mock()
        stripe.Price.retrieve.return_value = {
            "id": "price_remote",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "recurring": {"interval": "month"},
        }
        stripe.billing_portal.Configuration.list.return_value = {
            "data": [
                active_portal_configuration(
                    features={"subscription_cancel": {"enabled": False}},
                )
            ]
        }
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("billing_stripe_remote_check", "--skip-webhook", stdout=StringIO())

        self.assertIn(
            "customer portal subscription cancellation is not enabled",
            str(context.exception),
        )


class BillingAdminTestCase(TestCase):
    def _admin_request(self, user=None):
        if user is None:
            return SimpleNamespace()
        return SimpleNamespace(user=user)

    def test_user_admin_queryset_selects_premium_subscription(self):
        admin_instance = CustomUserAdmin(User, AdminSite())

        queryset = admin_instance.get_queryset(self._admin_request())

        self.assertIn("premium_subscription", queryset.query.select_related)

    def test_user_admin_shows_current_premium_status_reason(self):
        user = User.objects.create_user(username="admin-premium-user")
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="revoked",
            access_source="promo_code",
            revoked_at=timezone.now(),
            revoked_reason="Premium access code expired",
        )
        admin_instance = CustomUserAdmin(User, AdminSite())

        self.assertEqual(
            admin_instance.premium_status(user),
            "revoked: Premium access code expired",
        )

    def test_user_admin_shows_stripe_canceling_status_reason(self):
        user = User.objects.create_user(username="admin-canceling-user")
        PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
            cancel_at_period_end=True,
        )
        admin_instance = CustomUserAdmin(User, AdminSite())

        self.assertEqual(
            admin_instance.premium_status(user),
            "stripe: active until period end",
        )

    def test_user_admin_lists_premium_source_filter(self):
        admin_instance = CustomUserAdmin(User, AdminSite())

        self.assertIn(UserPremiumSourceFilter, admin_instance.list_filter)

    def test_user_admin_premium_source_filter(self):
        stripe_user = User.objects.create_user(username="admin-filter-stripe", is_premium=True)
        code_user = User.objects.create_user(username="admin-filter-code", is_premium=True)
        manual_user = User.objects.create_user(username="admin-filter-manual", is_premium=True)
        manual_without_subscription_user = User.objects.create_user(
            username="admin-filter-manual-no-subscription",
            is_premium=True,
        )
        none_user = User.objects.create_user(username="admin-filter-none", is_premium=False)
        ended_manual_user = User.objects.create_user(
            username="admin-filter-ended-manual",
            is_premium=False,
        )
        PremiumSubscription.objects.create(
            user=stripe_user,
            access_source="stripe",
            subscription_status="active",
        )
        PremiumSubscription.objects.create(
            user=code_user,
            access_source="promo_code",
            subscription_status=PremiumSubscription.PROMO_STATUS,
        )
        PremiumSubscription.objects.create(
            user=manual_user,
            access_source="stripe",
            subscription_status="canceled",
        )
        PremiumAuditLog.objects.create(
            user=manual_user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        PremiumAuditLog.objects.create(
            user=manual_without_subscription_user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        PremiumAuditLog.objects.create(
            user=ended_manual_user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        PremiumAuditLog.objects.create(
            user=ended_manual_user,
            action="revoked",
            source="manual",
            reason="Support comp ended",
        )
        admin_instance = CustomUserAdmin(User, AdminSite())

        def filtered_usernames(value):
            request = self._admin_request()
            request.GET = QueryDict(f"premium_source={value}")
            filter_instance = UserPremiumSourceFilter(
                request,
                request.GET.copy(),
                User,
                admin_instance,
            )
            return set(filter_instance.queryset(request, User.objects.all()).values_list("username", flat=True))

        self.assertIn(stripe_user.username, filtered_usernames("stripe"))
        self.assertIn(code_user.username, filtered_usernames("promo_code"))
        self.assertIn(manual_user.username, filtered_usernames("manual_override"))
        self.assertIn(
            manual_without_subscription_user.username,
            filtered_usernames("manual_without_subscription"),
        )
        self.assertNotIn(
            ended_manual_user.username,
            filtered_usernames("manual_override"),
        )
        self.assertIn(none_user.username, filtered_usernames("none"))

    def test_user_admin_manual_premium_change_logs_audit(self):
        user = User.objects.create_user(username="admin-manual-premium-user")
        actor = User.objects.create_user(username="admin-manual-premium-actor", is_staff=True)
        admin_instance = CustomUserAdmin(User, AdminSite())

        user.is_premium = True
        admin_instance.save_model(self._admin_request(actor), user, form=None, change=True)

        user.refresh_from_db()
        self.assertTrue(user.is_premium)
        grant_log = PremiumAuditLog.objects.get(user=user, action="granted")
        self.assertEqual(grant_log.source, "manual")
        self.assertEqual(grant_log.actor, actor)
        self.assertEqual(grant_log.reason, "Manual premium access updated in Django admin")
        self.assertEqual(grant_log.metadata["admin_model"], "CustomUser")
        self.assertEqual(grant_log.metadata["field"], "is_premium")

        user.is_premium = False
        admin_instance.save_model(self._admin_request(actor), user, form=None, change=True)

        user.refresh_from_db()
        self.assertFalse(user.is_premium)
        revoke_log = PremiumAuditLog.objects.get(user=user, action="revoked")
        self.assertEqual(revoke_log.source, "manual")
        self.assertEqual(revoke_log.actor, actor)

    def test_user_admin_manual_premium_unchanged_does_not_log_audit(self):
        user = User.objects.create_user(username="admin-manual-premium-unchanged")
        actor = User.objects.create_user(username="admin-manual-premium-unchanged-actor", is_staff=True)
        admin_instance = CustomUserAdmin(User, AdminSite())

        admin_instance.save_model(self._admin_request(actor), user, form=None, change=True)

        self.assertFalse(PremiumAuditLog.objects.filter(user=user).exists())

    def test_subscription_admin_queryset_selects_user(self):
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())

        queryset = admin_instance.get_queryset(self._admin_request())

        self.assertIn("user", queryset.query.select_related)

    def test_subscription_admin_shows_access_state_and_reason(self):
        stripe_user = User.objects.create_user(username="admin-access-stripe-user")
        stripe_record = PremiumSubscription.objects.create(
            user=stripe_user,
            subscription_status="active",
            access_source="stripe",
            cancel_at_period_end=True,
        )
        indefinite_user = User.objects.create_user(username="admin-access-indefinite-user")
        indefinite_record = PremiumSubscription.objects.create(
            user=indefinite_user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=None,
        )
        expired_user = User.objects.create_user(username="admin-access-expired-user")
        expired_record = PremiumSubscription.objects.create(
            user=expired_user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() - timedelta(minutes=1),
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())

        self.assertEqual(admin_instance.access_state(stripe_record), "active")
        self.assertEqual(admin_instance.access_reason(stripe_record), "stripe: active until period end")
        self.assertEqual(admin_instance.access_state(indefinite_record), "active")
        self.assertEqual(admin_instance.access_reason(indefinite_record), "promo code: indefinite")
        self.assertEqual(admin_instance.access_state(expired_record), "inactive")
        self.assertEqual(admin_instance.access_reason(expired_record), "promo code: expired")

    def test_subscription_admin_shows_manual_override_reason(self):
        user = User.objects.create_user(username="admin-access-manual-override-user")
        PremiumAuditLog.objects.create(
            user=user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        record = PremiumSubscription.objects.create(
            user=user,
            subscription_status="canceled",
            access_source="stripe",
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())

        self.assertEqual(admin_instance.access_state(record), "active")
        self.assertEqual(admin_instance.access_reason(record), "manual: active override")

    @override_settings(STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=False)
    def test_subscription_admin_shows_manual_review_for_refund_or_dispute(self):
        user = User.objects.create_user(username="admin-refund-review-user")
        record = PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
            last_refund_or_dispute_at=timezone.now(),
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())

        self.assertEqual(admin_instance.access_state(record), "active")
        self.assertEqual(
            admin_instance.access_reason(record),
            "refund/dispute detected: manual review",
        )

    def test_subscription_admin_lists_access_state_and_reason(self):
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())

        self.assertIn("user_link", admin_instance.list_display)
        self.assertIn("access_state", admin_instance.list_display)
        self.assertIn("access_reason", admin_instance.list_display)
        self.assertIn("stripe_price_id", admin_instance.list_display)
        self.assertIn("billing_interval", admin_instance.list_display)
        self.assertIn("billing_interval", admin_instance.list_filter)
        self.assertIn("stripe_price_id", admin_instance.search_fields)
        self.assertIn(SubscriptionOperationalIssueFilter, admin_instance.list_filter)
        self.assertIn(PaymentIssueListFilter, admin_instance.list_filter)
        self.assertIn(RefundOrDisputeListFilter, admin_instance.list_filter)
        self.assertIn("last_refund_or_dispute_at", admin_instance.list_filter)
        self.assertIn("restore_selected_access", admin_instance.actions)
        self.assertIn("mark_refund_or_dispute_reviewed", admin_instance.actions)

    def test_subscription_admin_user_link_opens_user_billing_detail(self):
        user = User.objects.create_user(username="admin-subscription-link-user")
        record = PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())

        link = str(admin_instance.user_link(record))

        self.assertIn("/admin/accounts/customuser/", link)
        self.assertIn(str(user.pk), link)
        self.assertIn("admin-subscription-link-user", link)

    def test_subscription_admin_operational_issue_filter_finds_expired_promo(self):
        expired_user = User.objects.create_user(username="admin-expired-promo-user")
        future_user = User.objects.create_user(username="admin-future-promo-user")
        expired_record = PremiumSubscription.objects.create(
            user=expired_user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() - timedelta(minutes=1),
        )
        future_record = PremiumSubscription.objects.create(
            user=future_user,
            subscription_status="promo",
            access_source="promo_code",
            premium_expires_at=timezone.now() + timedelta(days=14),
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        request = self._admin_request()
        filter_instance = SubscriptionOperationalIssueFilter(
            request,
            {"operational_issue": ["expired_promo"]},
            PremiumSubscription,
            admin_instance,
        )

        queryset = filter_instance.queryset(request, PremiumSubscription.objects.all())

        self.assertIn(expired_record, queryset)
        self.assertNotIn(future_record, queryset)

    def test_subscription_admin_operational_issue_filter_finds_stale_user_flag(self):
        stale_user = User.objects.create_user(username="admin-stale-flag-user")
        synced_user = User.objects.create_user(username="admin-synced-flag-user")
        manual_user = User.objects.create_user(
            username="admin-manual-override-not-stale-user",
            is_premium=True,
        )
        stale_record = PremiumSubscription.objects.create(
            user=stale_user,
            subscription_status="active",
            access_source="stripe",
        )
        synced_user.is_premium = True
        synced_user.save(update_fields=["is_premium"])
        synced_record = PremiumSubscription.objects.create(
            user=synced_user,
            subscription_status="active",
            access_source="stripe",
        )
        PremiumAuditLog.objects.create(
            user=manual_user,
            action="granted",
            source="manual",
            reason="Support comp",
        )
        manual_record = PremiumSubscription.objects.create(
            user=manual_user,
            subscription_status="canceled",
            access_source="stripe",
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        request = self._admin_request()
        filter_instance = SubscriptionOperationalIssueFilter(
            request,
            {"operational_issue": ["stale_user_flag"]},
            PremiumSubscription,
            admin_instance,
        )

        queryset = filter_instance.queryset(request, PremiumSubscription.objects.all())

        self.assertIn(stale_record, queryset)
        self.assertNotIn(synced_record, queryset)
        self.assertNotIn(manual_record, queryset)

    def test_subscription_admin_payment_issue_filter(self):
        failed_user = User.objects.create_user(username="admin-payment-failed-user")
        clean_user = User.objects.create_user(username="admin-payment-clean-user")
        failed_record = PremiumSubscription.objects.create(
            user=failed_user,
            subscription_status="active",
            access_source="stripe",
            last_payment_failed_at=timezone.now(),
        )
        clean_record = PremiumSubscription.objects.create(
            user=clean_user,
            subscription_status="active",
            access_source="stripe",
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        request = self._admin_request()
        filter_instance = PaymentIssueListFilter(
            request,
            {"payment_issue": ["yes"]},
            PremiumSubscription,
            admin_instance,
        )

        queryset = filter_instance.queryset(request, PremiumSubscription.objects.all())

        self.assertIn(failed_record, queryset)
        self.assertNotIn(clean_record, queryset)

    def test_webhook_admin_lists_operational_issue_filter(self):
        admin_instance = StripeWebhookEventAdmin(StripeWebhookEvent, AdminSite())

        self.assertIn(WebhookOperationalIssueFilter, admin_instance.list_filter)

    def test_webhook_admin_operational_issue_filter_finds_stale_processing(self):
        stale_event = StripeWebhookEvent.objects.create(
            event_id="evt_admin_stale_processing",
            event_type="customer.subscription.updated",
            processing_status=StripeWebhookEvent.STATUS_PROCESSING,
            processed_at=timezone.now() - timedelta(minutes=20),
        )
        fresh_event = StripeWebhookEvent.objects.create(
            event_id="evt_admin_fresh_processing",
            event_type="customer.subscription.updated",
            processing_status=StripeWebhookEvent.STATUS_PROCESSING,
            processed_at=timezone.now(),
        )
        admin_instance = StripeWebhookEventAdmin(StripeWebhookEvent, AdminSite())
        request = self._admin_request()
        filter_instance = WebhookOperationalIssueFilter(
            request,
            {"webhook_issue": ["stale_processing"]},
            StripeWebhookEvent,
            admin_instance,
        )

        queryset = filter_instance.queryset(request, StripeWebhookEvent.objects.all())

        self.assertIn(stale_event, queryset)
        self.assertNotIn(fresh_event, queryset)

    def test_subscription_admin_refund_or_dispute_active_filter(self):
        active_user = User.objects.create_user(username="admin-refund-active-user")
        active_user.is_premium = True
        active_user.save(update_fields=["is_premium"])
        revoked_user = User.objects.create_user(username="admin-refund-revoked-user")
        active_record = PremiumSubscription.objects.create(
            user=active_user,
            subscription_status="active",
            access_source="stripe",
            last_refund_or_dispute_at=timezone.now(),
        )
        revoked_record = PremiumSubscription.objects.create(
            user=revoked_user,
            subscription_status="revoked",
            access_source="stripe",
            last_refund_or_dispute_at=timezone.now(),
            revoked_at=timezone.now(),
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        request = self._admin_request()
        filter_instance = RefundOrDisputeListFilter(
            request,
            {"refund_or_dispute": ["active"]},
            PremiumSubscription,
            admin_instance,
        )

        queryset = filter_instance.queryset(request, PremiumSubscription.objects.all())

        self.assertIn(active_record, queryset)
        self.assertNotIn(revoked_record, queryset)

    def test_subscription_admin_can_mark_refund_or_dispute_reviewed(self):
        user = User.objects.create_user(username="admin-refund-reviewed-user")
        actor = User.objects.create_user(username="admin-refund-reviewed-actor", is_staff=True)
        user.is_premium = True
        user.save(update_fields=["is_premium"])
        detected_at = timezone.now()
        record = PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
            last_refund_or_dispute_at=detected_at,
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        admin_instance.message_user = Mock()

        admin_instance.mark_refund_or_dispute_reviewed(
            self._admin_request(actor),
            PremiumSubscription.objects.filter(pk=record.pk),
        )

        user.refresh_from_db()
        record.refresh_from_db()
        self.assertTrue(user.is_premium)
        self.assertIsNone(record.last_refund_or_dispute_at)
        audit_log = PremiumAuditLog.objects.get(
            user=user,
            action="reviewed",
            reason="Refund/dispute manually reviewed by admin action",
        )
        self.assertEqual(audit_log.actor, actor)
        self.assertEqual(audit_log.source, "stripe")
        self.assertEqual(audit_log.metadata["subscription_id"], record.pk)
        stdout = StringIO()
        call_command("billing_status_report", "--json", stdout=stdout)
        self.assertEqual(json.loads(stdout.getvalue())["refund_or_dispute_active_records"], 0)
        admin_instance.message_user.assert_called_once()

    def test_subscription_admin_revoke_action_stops_access_and_logs(self):
        user = User.objects.create_user(username="admin-revoke-sub-user")
        actor = User.objects.create_user(username="admin-revoke-actor", is_staff=True)
        user.is_premium = True
        user.save(update_fields=["is_premium"])
        record = PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
            stripe_customer_id="cus_admin_revoke",
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        admin_instance.message_user = Mock()

        admin_instance.revoke_selected_access(
            self._admin_request(actor),
            PremiumSubscription.objects.filter(pk=record.pk),
        )

        user.refresh_from_db()
        record.refresh_from_db()
        self.assertFalse(user.is_premium)
        self.assertEqual(record.subscription_status, "revoked")
        self.assertEqual(record.revoked_reason, "Revoked manually by admin action")
        audit_log = PremiumAuditLog.objects.get(
            user=user,
            action="revoked",
            reason="Revoked manually by admin action",
        )
        self.assertEqual(audit_log.actor, actor)
        admin_instance.message_user.assert_called_once()

    def test_subscription_admin_restore_action_restores_revoked_active_access_and_logs(self):
        user = User.objects.create_user(username="admin-restore-sub-user")
        actor = User.objects.create_user(username="admin-restore-actor", is_staff=True)
        record = PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
            stripe_customer_id="cus_admin_restore",
            revoked_at=timezone.now(),
            revoked_reason="Stripe charge refunded",
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        admin_instance.message_user = Mock()

        admin_instance.restore_selected_access(
            self._admin_request(actor),
            PremiumSubscription.objects.filter(pk=record.pk),
        )

        user.refresh_from_db()
        record.refresh_from_db()
        self.assertTrue(user.is_premium)
        self.assertIsNone(record.revoked_at)
        self.assertEqual(record.revoked_reason, "")
        audit_log = PremiumAuditLog.objects.get(
            user=user,
            action="restored",
            reason="Premium access restored manually by admin action",
        )
        self.assertEqual(audit_log.actor, actor)
        admin_instance.message_user.assert_called_once()

    def test_subscription_admin_sync_action_reconciles_user_flag_and_logs(self):
        user = User.objects.create_user(username="admin-sync-sub-user")
        actor = User.objects.create_user(username="admin-sync-actor", is_staff=True)
        record = PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
            stripe_customer_id="cus_admin_sync",
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())
        admin_instance.message_user = Mock()

        admin_instance.sync_selected_user_access(
            self._admin_request(actor),
            PremiumSubscription.objects.filter(pk=record.pk),
        )

        user.refresh_from_db()
        self.assertTrue(user.is_premium)
        audit_log = PremiumAuditLog.objects.get(
            user=user,
            action="granted",
            reason="Premium access synced manually by admin action",
        )
        self.assertEqual(audit_log.actor, actor)
        admin_instance.message_user.assert_called_once()

    def test_subscription_admin_shows_stripe_dashboard_links(self):
        user = User.objects.create_user(username="admin-stripe-link-user")
        record = PremiumSubscription.objects.create(
            user=user,
            subscription_status="active",
            access_source="stripe",
            stripe_customer_id="cus_admin_link",
            stripe_subscription_id="sub_admin_link",
        )
        admin_instance = PremiumSubscriptionAdmin(PremiumSubscription, AdminSite())

        customer_link = str(admin_instance.stripe_customer_link(record))
        subscription_link = str(admin_instance.stripe_subscription_link(record))

        self.assertIn("https://dashboard.stripe.com/customers/cus_admin_link", customer_link)
        self.assertIn("cus_admin_link", customer_link)
        self.assertIn(
            "https://dashboard.stripe.com/subscriptions/sub_admin_link",
            subscription_link,
        )
        self.assertIn("sub_admin_link", subscription_link)

    def test_access_code_admin_links_recent_redemptions(self):
        user = User.objects.create_user(username="redeemed-user")
        access_code, _ = PremiumAccessCode.issue(label="campaign")
        PremiumAccessCodeRedemption.objects.create(access_code=access_code, user=user)
        admin_instance = PremiumAccessCodeAdmin(PremiumAccessCode, AdminSite())

        html = str(admin_instance.redemption_list(access_code))

        self.assertIn("redeemed-user", html)
        self.assertIn("/admin/accounts/customuser/", html)

    def test_redemption_inline_shows_code_status_and_links(self):
        user = User.objects.create_user(username="inline-redeemed-user")
        expires_at = timezone.now() + timedelta(days=7)
        access_code, _ = PremiumAccessCode.issue(
            label="inline-campaign",
            expires_at=expires_at,
        )
        redemption = PremiumAccessCodeRedemption.objects.create(
            access_code=access_code,
            user=user,
        )
        inline = PremiumAccessCodeRedemptionInline(User, AdminSite())

        access_code_link = str(inline.access_code_link(redemption))
        user_link = str(inline.user_link(redemption))

        self.assertIn("access_code_link", inline.fields)
        self.assertIn("code_label", inline.fields)
        self.assertIn("code_campaign_name", inline.fields)
        self.assertIn("code_status", inline.fields)
        self.assertIn("code_expires_at", inline.fields)
        self.assertIn("user_link", inline.fields)
        self.assertIn("/admin/accounts/premiumaccesscode/", access_code_link)
        self.assertIn("inline-campaign", access_code_link)
        self.assertIn("/admin/accounts/customuser/", user_link)
        self.assertIn("inline-redeemed-user", user_link)
        self.assertEqual(inline.code_label(redemption), "inline-campaign")
        self.assertEqual(inline.code_campaign_name(redemption), "-")
        self.assertEqual(inline.code_status(redemption), "active")
        self.assertEqual(inline.code_expires_at(redemption), expires_at)

    def test_access_code_admin_revoke_action_sets_revoked_at(self):
        access_code, _ = PremiumAccessCode.issue(label="revoke-campaign")
        admin_instance = PremiumAccessCodeAdmin(PremiumAccessCode, AdminSite())
        admin_instance.message_user = Mock()

        admin_instance.revoke_codes(
            self._admin_request(),
            PremiumAccessCode.objects.filter(pk=access_code.pk),
        )

        access_code.refresh_from_db()
        self.assertIsNotNone(access_code.revoked_at)
        admin_instance.message_user.assert_called_once()

    def test_access_code_admin_can_revoke_granted_promo_access(self):
        actor = User.objects.create_user(username="admin-code-revoke-actor", is_staff=True)
        promo_user = User.objects.create_user(username="admin-code-revoke-promo-user")
        promo_user.is_premium = True
        promo_user.save(update_fields=["is_premium"])
        stripe_user = User.objects.create_user(username="admin-code-revoke-stripe-user")
        stripe_user.is_premium = True
        stripe_user.save(update_fields=["is_premium"])
        access_code, _ = PremiumAccessCode.issue(
            label="bad-campaign",
            campaign_name="bad-campaign-group",
        )
        PremiumAccessCodeRedemption.objects.create(access_code=access_code, user=promo_user)
        PremiumAccessCodeRedemption.objects.create(access_code=access_code, user=stripe_user)
        promo_record = PremiumSubscription.objects.create(
            user=promo_user,
            subscription_status="promo",
            access_source="promo_code",
        )
        stripe_record = PremiumSubscription.objects.create(
            user=stripe_user,
            subscription_status="active",
            access_source="stripe",
        )
        admin_instance = PremiumAccessCodeAdmin(PremiumAccessCode, AdminSite())
        admin_instance.message_user = Mock()

        admin_instance.revoke_code_granted_access(
            self._admin_request(actor),
            PremiumAccessCode.objects.filter(pk=access_code.pk),
        )

        promo_user.refresh_from_db()
        stripe_user.refresh_from_db()
        promo_record.refresh_from_db()
        stripe_record.refresh_from_db()
        self.assertFalse(promo_user.is_premium)
        self.assertEqual(promo_record.subscription_status, "revoked")
        self.assertEqual(promo_record.revoked_reason, "Premium access code revoked by admin action")
        self.assertTrue(stripe_user.is_premium)
        self.assertEqual(stripe_record.subscription_status, "active")
        audit_log = PremiumAuditLog.objects.get(
            user=promo_user,
            action="revoked",
            reason="Premium access code revoked by admin action",
        )
        self.assertEqual(audit_log.actor, actor)
        self.assertEqual(audit_log.source, "promo_code")
        self.assertEqual(audit_log.metadata["access_code_id"], access_code.pk)
        self.assertEqual(audit_log.metadata["access_code_label"], "bad-campaign")
        self.assertEqual(audit_log.metadata["access_code_campaign_name"], "bad-campaign-group")
        admin_instance.message_user.assert_called_once()

    def test_access_code_admin_shows_code_status(self):
        access_code, _ = PremiumAccessCode.issue(label="status-campaign", max_uses=1)
        access_code.use_count = 1
        access_code.save(update_fields=["use_count"])
        admin_instance = PremiumAccessCodeAdmin(PremiumAccessCode, AdminSite())

        self.assertEqual(admin_instance.code_status(access_code), "exhausted")

    def test_access_code_admin_lists_status_filter(self):
        admin_instance = PremiumAccessCodeAdmin(PremiumAccessCode, AdminSite())

        self.assertIn("campaign_name", admin_instance.list_display)
        self.assertIn("campaign_name", admin_instance.list_filter)
        self.assertIn("campaign_name", admin_instance.search_fields)
        self.assertIn(PremiumAccessCodeStatusFilter, admin_instance.list_filter)
        self.assertIn("revoke_code_granted_access", admin_instance.actions)

    def test_access_code_admin_status_filter(self):
        active_code, _ = PremiumAccessCode.issue(label="active-code", max_uses=2)
        expired_code, _ = PremiumAccessCode.issue(
            label="expired-code",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        exhausted_code, _ = PremiumAccessCode.issue(label="exhausted-code", max_uses=1)
        exhausted_code.use_count = 1
        exhausted_code.save(update_fields=["use_count"])
        revoked_code, _ = PremiumAccessCode.issue(label="revoked-code")
        revoked_code.revoked_at = timezone.now()
        revoked_code.save(update_fields=["revoked_at"])
        admin_instance = PremiumAccessCodeAdmin(PremiumAccessCode, AdminSite())
        request = self._admin_request()

        active_filter = PremiumAccessCodeStatusFilter(
            request,
            {"code_status": ["active"]},
            PremiumAccessCode,
            admin_instance,
        )
        expired_filter = PremiumAccessCodeStatusFilter(
            request,
            {"code_status": ["expired"]},
            PremiumAccessCode,
            admin_instance,
        )
        exhausted_filter = PremiumAccessCodeStatusFilter(
            request,
            {"code_status": ["exhausted"]},
            PremiumAccessCode,
            admin_instance,
        )
        revoked_filter = PremiumAccessCodeStatusFilter(
            request,
            {"code_status": ["revoked"]},
            PremiumAccessCode,
            admin_instance,
        )

        all_codes = PremiumAccessCode.objects.all()

        self.assertEqual(set(active_filter.queryset(request, all_codes)), {active_code})
        self.assertEqual(set(expired_filter.queryset(request, all_codes)), {expired_code})
        self.assertEqual(set(exhausted_filter.queryset(request, all_codes)), {exhausted_code})
        self.assertEqual(set(revoked_filter.queryset(request, all_codes)), {revoked_code})

    def test_audit_log_admin_shows_links_and_metadata_summary(self):
        user = User.objects.create_user(username="audit-user")
        actor = User.objects.create_user(username="audit-actor")
        audit_log = PremiumAuditLog.objects.create(
            user=user,
            actor=actor,
            action="payment_failed",
            source="stripe",
            reason="Invoice payment failed",
            stripe_event_id="evt_audit_admin",
            metadata={"invoice_id": "in_audit_admin", "email_sent": True},
        )
        admin_instance = PremiumAuditLogAdmin(PremiumAuditLog, AdminSite())

        user_link = str(admin_instance.user_link(audit_log))
        actor_link = str(admin_instance.actor_link(audit_log))
        metadata_summary = admin_instance.metadata_summary(audit_log)

        self.assertIn("user_link", admin_instance.list_display)
        self.assertIn("actor_link", admin_instance.list_display)
        self.assertIn("metadata_summary", admin_instance.list_display)
        self.assertIn("/admin/accounts/customuser/", user_link)
        self.assertIn("audit-user", user_link)
        self.assertIn("/admin/accounts/customuser/", actor_link)
        self.assertIn("audit-actor", actor_link)
        self.assertIn("invoice_id=in_audit_admin", metadata_summary)
        self.assertIn("email_sent=True", metadata_summary)

    def test_audit_log_admin_queryset_selects_user_and_actor(self):
        admin_instance = PremiumAuditLogAdmin(PremiumAuditLog, AdminSite())

        queryset = admin_instance.get_queryset(self._admin_request())

        self.assertIn("user", queryset.query.select_related)
        self.assertIn("actor", queryset.query.select_related)

    def test_audit_log_admin_actor_filter_separates_system_and_admin_actions(self):
        user = User.objects.create_user(username="audit-filter-user")
        actor = User.objects.create_user(username="audit-filter-actor")
        system_log = PremiumAuditLog.objects.create(
            user=user,
            action="payment_failed",
            source="stripe",
            reason="System webhook action",
        )
        admin_log = PremiumAuditLog.objects.create(
            user=user,
            actor=actor,
            action="revoked",
            source="manual",
            reason="Admin action",
        )
        admin_instance = PremiumAuditLogAdmin(PremiumAuditLog, AdminSite())
        request = self._admin_request()

        system_filter = PremiumAuditActorFilter(
            request,
            {"audit_actor": ["system"]},
            PremiumAuditLog,
            admin_instance,
        )
        admin_filter = PremiumAuditActorFilter(
            request,
            {"audit_actor": ["admin"]},
            PremiumAuditLog,
            admin_instance,
        )

        all_logs = PremiumAuditLog.objects.all()

        self.assertEqual(set(system_filter.queryset(request, all_logs)), {system_log})
        self.assertEqual(set(admin_filter.queryset(request, all_logs)), {admin_log})
        self.assertIn(PremiumAuditActorFilter, admin_instance.list_filter)

    def test_billing_admin_and_code_command_labels_are_readable_japanese(self):
        paths = [
            Path("accounts/admin.py"),
            Path("accounts/management/commands/issue_premium_code.py"),
        ]
        markers = ["???", chr(0xFFFD), chr(0x7E1D), chr(0x7E3A), chr(0x9A55), chr(0x8389) + chr(0xFF76)]

        for file_path in paths:
            content = file_path.read_text(encoding="utf-8")
            for marker in markers:
                self.assertNotIn(marker, content, f"{file_path} contains mojibake marker {marker!r}")
        command_content = paths[1].read_text(encoding="utf-8")
        self.assertIn(
            "運営発行のプレミアムコードを作成します",
            command_content,
        )
        self.assertIn(
            "発行したコードをCSVへ出力するパス",
            command_content,
        )
        admin_content = paths[0].read_text(encoding="utf-8")
        self.assertIn(
            "選択した課金レコードのプレミアム権限を停止する",
            admin_content,
        )
        self.assertIn(
            "選択したプレミアムコードをCSV出力する",
            admin_content,
        )

    def test_access_code_admin_csv_export_includes_usage_without_raw_code(self):
        user = User.objects.create_user(username="csv-user", email="csv-user@example.test")
        access_code, raw_code = PremiumAccessCode.issue(
            label="csv-campaign",
            campaign_name="retention-2026",
            max_uses=3,
        )
        PremiumAccessCodeRedemption.objects.create(access_code=access_code, user=user)
        access_code.use_count = 1
        access_code.save(update_fields=["use_count"])
        admin_instance = PremiumAccessCodeAdmin(PremiumAccessCode, AdminSite())

        response = admin_instance.export_codes_csv(
            self._admin_request(),
            PremiumAccessCode.objects.filter(pk=access_code.pk),
        )
        content = response.content.decode("utf-8-sig")

        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("csv-campaign", content)
        self.assertIn("campaign_name", content)
        self.assertIn("retention-2026", content)
        self.assertIn("csv-user", content)
        self.assertIn("csv-user@example.test", content)
        self.assertIn("redemption_user_emails", content)
        self.assertIn("redemption_details", content)
        self.assertIn(" at ", content)
        self.assertIn("status", content)
        self.assertIn("active", content)
        self.assertIn("remaining_uses", content)
        self.assertNotIn(raw_code, content)


class BillingDevelopmentCheckCommandTestCase(TestCase):
    def test_billing_development_check_allows_blank_stripe_values_before_test_prices_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            env_path = self._write_env(base_dir)
            stdout = StringIO()

            with override_settings(BASE_DIR=base_dir):
                call_command("billing_development_check", "--env-file", str(env_path), stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("OK development-env-file", output)
        self.assertIn("WARN STRIPE_SECRET_KEY is blank", output)
        self.assertIn("WARN STRIPE_PREMIUM_PRICE_ID is blank", output)
        self.assertIn("billing_development_check=warnings", output)

    def test_billing_development_check_requires_exact_gitignore_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            env_path = self._write_env(base_dir)
            (base_dir / ".gitignore").write_text(
                "# .env.development\n.env.development.example\n",
                encoding="utf-8",
            )

            with override_settings(BASE_DIR=base_dir):
                with self.assertRaises(CommandError) as context:
                    call_command("billing_development_check", "--env-file", str(env_path), stdout=StringIO())

        self.assertIn(".env.development is not listed in .gitignore", str(context.exception))

    def test_billing_development_check_rejects_live_secret_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            env_path = self._write_env(base_dir, STRIPE_SECRET_KEY="sk_live_accidental")

            with override_settings(BASE_DIR=base_dir):
                with self.assertRaises(CommandError) as context:
                    call_command("billing_development_check", "--env-file", str(env_path), stdout=StringIO())

        self.assertIn("live Stripe key", str(context.exception))

    def test_billing_development_check_accepts_complete_test_mode_configuration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            env_path = self._write_env(
                base_dir,
                STRIPE_SECRET_KEY="sk_test_development",
                STRIPE_PUBLISHABLE_KEY="pk_test_development",
                STRIPE_WEBHOOK_SECRET="whsec_development",
                STRIPE_PREMIUM_PRICE_ID="price_monthly_development",
                STRIPE_PREMIUM_YEARLY_PRICE_ID="price_yearly_development",
            )
            stdout = StringIO()

            with override_settings(BASE_DIR=base_dir):
                call_command(
                    "billing_development_check",
                    "--env-file",
                    str(env_path),
                    "--require-stripe",
                    stdout=stdout,
                )

        output = stdout.getvalue()
        self.assertIn("OK STRIPE_SECRET_KEY: configured with test/development prefix", output)
        self.assertIn("OK STRIPE_PREMIUM_YEARLY_PRICE_ID: configured with test/development prefix", output)
        self.assertIn("billing_development_check=ok", output)

    def _write_env(self, base_dir, **overrides):
        (base_dir / ".gitignore").write_text(".env.development\n", encoding="utf-8")
        values = {
            "APP_ENV": "local",
            "ENVIRONMENT": "development",
            "SECRET_KEY": "development-secret",
            "DEBUG": "True",
            "PUBLIC_SITE_URL": "http://127.0.0.1:8000",
            "STRIPE_CHECKOUT_ENABLED": "True",
            "STRIPE_SECRET_KEY": "",
            "STRIPE_WEBHOOK_SECRET": "",
            "STRIPE_PREMIUM_PRICE_ID": "",
            "STRIPE_PREMIUM_YEARLY_PRICE_ID": "",
            "STRIPE_PREMIUM_EXPECTED_CURRENCY": "jpy",
            "STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT": "480",
            "STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT": "4800",
            "STRIPE_PUBLISHABLE_KEY": "",
        }
        values.update(overrides)
        env_path = base_dir / ".env.development"
        env_path.write_text(
            "".join(f"{key}={value}\n" for key, value in values.items()),
            encoding="utf-8",
        )
        return env_path


class CreateStripeDevelopmentPricesCommandTestCase(TestCase):
    @override_settings(
        STRIPE_SECRET_KEY="sk_test_development_prices",
        ENVIRONMENT="development",
    )
    @patch("accounts.management.commands.create_stripe_development_prices.get_stripe")
    def test_create_stripe_development_prices_creates_monthly_and_yearly_prices(self, get_stripe):
        stripe = Mock()
        stripe.Product.create.return_value = {
            "id": "prod_development",
            "livemode": False,
        }
        stripe.Price.create.side_effect = [
            {"id": "price_monthly_development", "livemode": False},
            {"id": "price_yearly_development", "livemode": False},
        ]
        get_stripe.return_value = stripe
        stdout = StringIO()

        call_command("create_stripe_development_prices", stdout=stdout)

        output = stdout.getvalue()
        stripe.Product.create.assert_called_once()
        self.assertEqual(stripe.Price.create.call_count, 2)
        monthly_call = stripe.Price.create.call_args_list[0].kwargs
        yearly_call = stripe.Price.create.call_args_list[1].kwargs
        self.assertEqual(monthly_call["unit_amount"], 480)
        self.assertEqual(monthly_call["currency"], "jpy")
        self.assertEqual(monthly_call["recurring"], {"interval": "month"})
        self.assertEqual(yearly_call["unit_amount"], 4800)
        self.assertEqual(yearly_call["recurring"], {"interval": "year"})
        self.assertIn("stripe_development_prices=ok", output)
        self.assertIn("STRIPE_PREMIUM_PRICE_ID=price_monthly_development", output)
        self.assertIn("STRIPE_PREMIUM_YEARLY_PRICE_ID=price_yearly_development", output)

    @override_settings(
        STRIPE_SECRET_KEY="sk_live_development_prices",
        ENVIRONMENT="development",
    )
    def test_create_stripe_development_prices_rejects_live_secret_key(self):
        with self.assertRaises(CommandError) as context:
            call_command("create_stripe_development_prices", stdout=StringIO())

        self.assertIn("sk_test_", str(context.exception))

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_development_prices",
        ENVIRONMENT="development",
    )
    @patch("accounts.management.commands.create_stripe_development_prices.get_stripe")
    def test_create_stripe_development_prices_disables_live_product_response(self, get_stripe):
        stripe = Mock()
        stripe.Product.create.return_value = {
            "id": "prod_live_accidental",
            "livemode": True,
        }
        get_stripe.return_value = stripe

        with self.assertRaises(CommandError) as context:
            call_command("create_stripe_development_prices", stdout=StringIO())

        self.assertIn("not test mode", str(context.exception))
        stripe.Product.modify.assert_called_once()
        self.assertEqual(stripe.Product.modify.call_args.args[0], "prod_live_accidental")
        self.assertIs(stripe.Product.modify.call_args.kwargs["active"], False)
        stripe.Price.create.assert_not_called()
