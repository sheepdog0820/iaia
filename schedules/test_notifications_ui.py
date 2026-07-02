from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser


class NotificationsUIViewTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="notify_user", email="notify_user@example.com", nickname="通知ユーザー"
        )

    def test_notifications_view_redirects_for_anonymous_user(self):
        response = self.client.get(reverse("notifications_view"))
        self.assertRedirects(
            response,
            "/accounts/login/?next=/api/schedules/notifications/view/",
            fetch_redirect_response=False,
        )

    def test_notifications_view_renders_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("notifications_view"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "notifications-list-container")
