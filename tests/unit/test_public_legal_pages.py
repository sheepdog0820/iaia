from pathlib import Path

from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse


class PublicLegalPagesTestCase(TestCase):
    def test_public_legal_pages_are_available(self):
        expected = {
            'terms': '利用規約',
            'privacy': 'プライバシーポリシー',
            'contact': '問い合わせ',
        }

        for name, heading in expected.items():
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, heading)

    def test_public_legal_pages_show_contact_email(self):
        expected_email = 'support@tableno.jp'

        for name in ['terms', 'privacy', 'contact']:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, expected_email)
                self.assertContains(response, f'href="mailto:{expected_email}"')

    @override_settings(CONTACT_EMAIL='help@example.com', SUPPORT_EMAIL='help@example.com')
    def test_contact_email_can_be_configured(self):
        response = self.client.get(reverse('contact'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'help@example.com')
        self.assertContains(response, 'href="mailto:help@example.com"')

    def test_404_page_uses_support_email(self):
        content = render_to_string('404.html', {'support_email': 'support@tableno.jp'})

        self.assertIn('href="mailto:support@tableno.jp"', content)
        self.assertNotIn('support@yourdomain.com', content)

    def test_403_page_uses_support_email(self):
        content = render_to_string('403.html', {'support_email': 'support@tableno.jp'})

        self.assertIn('403', content)
        self.assertIn('アクセス権限がありません', content)
        self.assertIn('href="mailto:support@tableno.jp"', content)
        self.assertNotIn('support@yourdomain.com', content)

    def test_base_footer_links_to_legal_pages(self):
        response = self.client.get(reverse('terms'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/terms/"')
        self.assertContains(response, 'href="/privacy/"')
        self.assertContains(response, 'href="/contact/"')

    def test_signup_pages_link_to_terms_and_privacy(self):
        for path in [
            Path('templates/account/signup.html'),
            Path('templates/socialaccount/signup.html'),
        ]:
            with self.subTest(path=str(path)):
                content = path.read_text(encoding='utf-8')
                self.assertIn("{% url 'terms' %}", content)
                self.assertIn("{% url 'privacy' %}", content)
