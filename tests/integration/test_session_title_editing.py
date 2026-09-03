from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules.models import TRPGSession


class SessionTitleEditingIntegrationTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="title-owner", password="testpass123")
        self.outsider = user_model.objects.create_user(username="title-outsider", password="testpass123")
        self.group = Group.objects.create(name="タイトル編集テスト", created_by=self.owner)
        self.session = TRPGSession.objects.create(
            title="変更前タイトル",
            gm=self.owner,
            created_by=self.owner,
            group=self.group,
            visibility="group",
        )
        self.client.force_login(self.owner)

    def patch_title(self, title):
        return self.client.patch(
            reverse("session-detail", kwargs={"pk": self.session.pk}),
            {"title": title},
            format="json",
        )

    def test_title_can_be_saved_from_detail_screen_and_is_rendered_after_reload(self):
        detail_url = reverse("session_detail", kwargs={"pk": self.session.pk})
        before = self.client.get(detail_url)
        self.assertEqual(before.status_code, status.HTTP_200_OK)
        self.assertContains(before, 'id="editSessionTitle"')

        response = self.patch_title("詳細画面から変更")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, "詳細画面から変更")
        after = self.client.get(detail_url)
        self.assertContains(after, "詳細画面から変更")

    def test_title_can_be_saved_from_list_screen_and_is_returned_by_list_api(self):
        list_screen = self.client.get(reverse("sessions_view"), follow=True)
        self.assertEqual(list_screen.status_code, status.HTTP_200_OK)
        self.assertContains(list_screen, 'id="editSessionTitle"')

        response = self.patch_title("一覧画面から変更")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, "一覧画面から変更")
        sessions_response = self.client.get(reverse("session-list"), {"period": "all"})
        self.assertEqual(sessions_response.status_code, status.HTTP_200_OK)
        payload = (
            sessions_response.data.get("results", sessions_response.data)
            if isinstance(sessions_response.data, dict)
            else sessions_response.data
        )
        matching = next(item for item in payload if item["id"] == self.session.pk)
        self.assertEqual(matching["title"], "一覧画面から変更")

    def test_user_without_edit_permission_cannot_change_title(self):
        self.client.force_login(self.outsider)

        response = self.patch_title("不正な変更")

        self.assertIn(response.status_code, {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND})
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, "変更前タイトル")
