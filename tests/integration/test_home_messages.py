"""Home feedback stays visible after the account and its login are removed."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse


class HomeMessageRenderingTests(SimpleTestCase):
    def render_messages(self, notices, user=None):
        request = RequestFactory().get(reverse("home"))
        request.user = user or AnonymousUser()
        return render_to_string("home.html", {"messages": notices}, request=request)

    def test_no_message_keeps_the_existing_home_without_an_empty_alert(self):
        html = self.render_messages([])
        self.assertNotIn('id="home-messages"', html)

    def test_standard_levels_use_bootstrap_alerts_and_japanese_dismissal(self):
        for level, style in (
            (messages.SUCCESS, "success"),
            (messages.INFO, "info"),
            (messages.WARNING, "warning"),
            (messages.ERROR, "danger"),
        ):
            with self.subTest(level=level):
                html = self.render_messages([Message(level, "操作結果を確認してください。")])
                self.assertIn(f'class="alert alert-{style} alert-dismissible fade show text-reset pe-5"', html)
                self.assertIn('role="alert"', html)
                self.assertIn('aria-label="閉じる"', html)
                self.assertIn('data-bs-dismiss="alert"', html)
                self.assertIn("操作結果を確認してください。", html)
                self.assertIn('<span class="home-message-text">操作結果を確認してください。</span>', html)

    def test_unknown_level_falls_back_to_info(self):
        html = self.render_messages([Message(15, "確認用の通知です。")])
        self.assertIn('class="alert alert-info alert-dismissible fade show text-reset pe-5"', html)

    def test_alert_text_inherits_theme_and_reserves_dismissal_space(self):
        html = self.render_messages([Message(messages.SUCCESS, "完了しました。")])
        self.assertIn("alert-dismissible fade show text-reset pe-5", html)

    def test_all_messages_are_rendered(self):
        html = self.render_messages(
            [Message(messages.SUCCESS, "完了しました。"), Message(messages.INFO, "確認事項です。")]
        )
        self.assertIn("完了しました。", html)
        self.assertIn("確認事項です。", html)
        self.assertEqual(html.count('role="alert"'), 2)

    def test_message_content_is_escaped_instead_of_rendered_as_html(self):
        html = self.render_messages([Message(messages.INFO, '<img src=x onerror="alert(1)">')])
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", html)
        self.assertNotIn('<img src=x onerror="alert(1)">', html)

    def test_authenticated_home_also_renders_feedback(self):
        user = get_user_model()(username="message-fixture", nickname="通知確認用")
        html = self.render_messages([Message(messages.SUCCESS, "更新しました。")], user=user)
        self.assertIn('id="home-messages"', html)
        self.assertIn("更新しました。", html)
        self.assertIn("タブレノへようこそ、通知確認用", html)


@override_settings(ACCOUNT_EMAIL_VERIFICATION="none", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountDeletionHomeFeedbackTests(TestCase):
    def test_deletion_redirects_to_public_home_with_feedback_and_ends_authentication(self):
        password = "isolated-home-feedback-fixture-password"  # nosec B105
        user = get_user_model().objects.create_user(
            username="home-feedback-fixture", email="home-feedback@example.test", password=password
        )
        self.client.force_login(user)

        response = self.client.post(reverse("account_delete"), {"confirm": "DELETE", "password": password}, follow=True)

        self.assertEqual(response.redirect_chain, [(reverse("home"), 302)])
        self.assertContains(response, "アカウントを削除しました。ご利用ありがとうございました。")
        self.assertContains(response, 'class="alert alert-success alert-dismissible fade show text-reset pe-5"')
        self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(
            self.client.get(reverse("dashboard")),
            reverse("account_login") + "?next=" + reverse("dashboard"),
            fetch_redirect_response=False,
        )
        self.assertNotContains(
            self.client.get(reverse("home")), "アカウントを削除しました。ご利用ありがとうございました。"
        )
