from pathlib import Path

from django.test import TestCase
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
                self.assertContains(response, '正式な')

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
