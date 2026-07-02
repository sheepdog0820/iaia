from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse


class BillingLegalPagesTestCase(TestCase):
    MOJIBAKE_MARKERS = [
        chr(0x90E2) + chr(0xFF67),
        chr(0x90B5) + chr(0xFF7A),
        chr(0x96B4) + chr(0xFFFD),
        chr(0x9AEB) + chr(0xFF71),
        chr(0x9B2E) + chr(0xFF6F),
        chr(0x9677) + chr(0xFFFD),
        chr(0x9A4D) + chr(0xFFFD),
        chr(0x7E5D),
        chr(0x8B5B),
        chr(0x8711),
    ]

    def setUp(self):
        self.factory = RequestFactory()

    def test_commercial_disclosure_page_is_public(self):
        response = self.client.get(reverse("commercial_disclosure"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "特定商取引法に基づく表記")
        self.assertContains(response, "販売価格")
        self.assertContains(response, "解約方法")
        self.assertContains(response, "返品・キャンセル・返金")

    def test_commercial_disclosure_page_contains_required_legal_items(self):
        response = self.client.get(reverse("commercial_disclosure"))

        required_labels = [
            "販売事業者",
            "所在地",
            "電話番号",
            "問い合わせ先",
            "販売価格",
            "商品代金以外の必要料金",
            "支払方法",
            "支払時期",
            "提供時期",
            "解約方法",
            "解約の効力",
            "返品・キャンセル・返金",
            "動作環境",
        ]
        for label in required_labels:
            self.assertContains(response, label)

    def test_billing_legal_pages_do_not_render_mojibake_markers(self):
        for url_name in ("commercial_disclosure", "premium_features"):
            response = self.client.get(reverse(url_name))
            html = response.content.decode(response.charset)
            for marker in self.MOJIBAKE_MARKERS:
                self.assertNotIn(marker, html, f"{url_name} contains mojibake marker {marker!r}")

    def test_premium_features_page_is_available_to_logged_in_users(self):
        User = get_user_model()
        user = User.objects.create_user(username="premium-page-user", password="pass123")
        self.client.force_login(user)

        response = self.client.get(reverse("premium_features"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "プレミアム機能")
        self.assertContains(response, "シナリオアーカイブ")
        self.assertContains(response, "特定商取引法に基づく表記を見る")
        self.assertContains(response, reverse("billing"))
        self.assertContains(response, "プレミアム管理へ")

    def test_premium_features_page_links_to_commercial_disclosure_for_required_terms(self):
        response = self.client.get(reverse("premium_features"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "\u8ca9\u58f2\u4fa1\u683c")
        self.assertContains(response, "月額料金")
        self.assertContains(response, "年額4,800円")
        self.assertContains(response, "支払方法")
        self.assertContains(response, "提供時期")
        self.assertContains(response, "解約方法")
        self.assertContains(response, "返金条件")
        self.assertContains(response, "事業者情報")
        self.assertContains(response, reverse("commercial_disclosure"))
        self.assertContains(response, "特定商取引法に基づく表記")

    @override_settings(
        CONTACT_EMAIL="billing-help@example.com",
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_PAYMENT_METHOD="クレジットカード",
        LEGAL_PAYMENT_TIMING="毎月の更新日に課金します。",
        LEGAL_SERVICE_DELIVERY_TIMING="決済完了後ただちに提供します。",
        LEGAL_CANCELLATION_METHOD="管理画面からいつでも解約できます。",
        LEGAL_CANCELLATION_EFFECT="支払い済み期間の終了まで利用できます。",
        LEGAL_REFUND_POLICY="返金は原則受け付けません。",
        LEGAL_SELLER_NAME="テスト販売者",
    )
    def test_commercial_disclosure_uses_configured_values(self):
        response = self.client.get(reverse("commercial_disclosure"))

        self.assertContains(response, "billing-help@example.com")
        self.assertContains(response, "月額500円")
        self.assertContains(response, "クレジットカード")
        self.assertContains(response, "毎月の更新日に課金します。")
        self.assertContains(response, "決済完了後ただちに提供します。")
        self.assertContains(response, "管理画面からいつでも解約できます。")
        self.assertContains(response, "支払い済み期間の終了まで利用できます。")
        self.assertContains(response, "返金は原則受け付けません。")
        self.assertContains(response, "テスト販売者")

    @override_settings(
        PREMIUM_PRICE_LABEL="月額500円",
        LEGAL_CANCELLATION_EFFECT="解約後も支払い済み期間の終了まで利用できます。",
    )
    def test_premium_features_page_shows_price_and_cancellation_effect(self):
        response = self.client.get(reverse("premium_features"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "月額500円")
        self.assertContains(response, "解約後も支払い済み期間の終了まで利用できます。")

    def test_default_billing_terms_cover_monthly_and_yearly_subscription_timing(self):
        for url_name in ("commercial_disclosure", "premium_features"):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "\u6708\u984d480\u5186 / \u5e74\u984d4,800\u5186")
                self.assertContains(
                    response,
                    "\u9078\u629e\u3057\u305f\u6708\u984d\u307e\u305f\u306f\u5e74\u984d\u30b5\u30d6\u30b9\u30af\u30ea\u30d7\u30b7\u30e7\u30f3",
                )

    def test_premium_features_page_shows_free_and_paid_feature_differences(self):
        response = self.client.get(reverse("premium_features"))

        self.assertEqual(response.status_code, 200)
        for feature_key in (
            "character_management",
            "session_management",
            "scenario_archive",
            "billing_management",
            "premium_code",
        ):
            self.assertContains(response, f'data-feature="{feature_key}"')
        self.assertContains(response, "シナリオアーカイブ")
        self.assertContains(response, "利用不可")
        self.assertContains(response, "Stripe Customer Portal")
        self.assertContains(response, "運営発行コード")
        self.assertContains(response, "課金なし")

    @override_settings(
        PREMIUM_PRICE_LABEL="Monthly 500 JPY",
        LEGAL_PAYMENT_TIMING="Charged at signup and on each monthly renewal.",
        LEGAL_SERVICE_DELIVERY_TIMING="Premium access is available after payment confirmation.",
        LEGAL_CANCELLATION_METHOD="Cancel from the billing management page.",
        LEGAL_REFUND_POLICY="Refunds are reviewed individually for duplicate or incorrect charges.",
    )
    def test_premium_features_page_shows_billing_terms(self):
        response = self.client.get(reverse("premium_features"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monthly 500 JPY")
        self.assertContains(response, "Charged at signup and on each monthly renewal.")
        self.assertContains(response, "Premium access is available after payment confirmation.")
        self.assertContains(response, "Cancel from the billing management page.")
        self.assertContains(response, "Refunds are reviewed individually for duplicate or incorrect charges.")

    def test_premium_required_template_links_to_billing_and_legal_pages(self):
        User = get_user_model()
        request = self.factory.get("/premium-required/")
        request.user = User.objects.create_user(username="premium-required-user")

        html = render_to_string("accounts/premium_required.html", request=request)

        self.assertIn(reverse("billing"), html)
        self.assertIn(reverse("premium_features"), html)
        self.assertIn(reverse("commercial_disclosure"), html)
        self.assertIn("運営発行コードの入力", html)
        self.assertIn("料金・解約条件", html)
