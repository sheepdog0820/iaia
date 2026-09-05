from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from schedules.models import TRPGSession


class SessionPermissionPageTests(TestCase):
    def setUp(self):
        owner = CustomUser.objects.create_user(username="permission-page-owner")
        outsider = CustomUser.objects.create_user(username="permission-page-outsider")
        self.session = TRPGSession.objects.create(
            title="非公開セッションの題名", description="非公開セッションの説明", gm=owner, visibility="private"
        )
        self.client.force_login(outsider)

    def test_html_denial_uses_application_page_without_private_details(self):
        for name in ("session_detail", "session_date_poll"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name, kwargs={"pk": self.session.pk}), HTTP_ACCEPT="text/html")
                self.assertEqual(response.status_code, 403)
                self.assertTemplateUsed(response, "403.html")
                self.assertContains(response, "アクセス権限がありません", status_code=403)
                self.assertContains(response, "ホームへ", status_code=403)
                self.assertNotContains(response, "Django REST framework", status_code=403)
                self.assertNotContains(response, self.session.title, status_code=403)
                self.assertNotContains(response, self.session.description, status_code=403)

    def test_json_denial_preserves_api_contract(self):
        for name in ("session_detail", "session_date_poll"):
            with self.subTest(name=name):
                response = self.client.get(
                    reverse(name, kwargs={"pk": self.session.pk}), HTTP_ACCEPT="application/json"
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {"error": "Permission denied"})
