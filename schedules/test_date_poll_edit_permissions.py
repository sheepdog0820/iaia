from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership
from schedules.models import DatePoll, DatePollOption, TRPGSession


class DatePollEditPermissionTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="poll-editor")
        self.other = get_user_model().objects.create_user(username="other-owner")
        self.group = Group.objects.create(name="所属グループ", created_by=self.user)
        self.other_group = Group.objects.create(name="別グループ", created_by=self.other)
        self.poll = DatePoll.objects.create(title="日程調整", group=self.group, created_by=self.user)
        self.option = DatePollOption.objects.create(poll=self.poll, datetime=timezone.now() + timedelta(days=1))
        self.client.force_authenticate(self.user)
        self.url = f"/api/schedules/date-polls/{self.poll.pk}/"

    def test_owner_cannot_move_poll_to_unrelated_group(self):
        response = self.client.patch(self.url, {"group": self.other_group.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("group", response.data)
        self.poll.refresh_from_db()
        self.assertEqual(self.poll.group_id, self.group.pk)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_owner_can_move_unlinked_poll_to_member_group(self):
        self.other_group.members.add(self.user)
        response = self.client.patch(self.url, {"group": self.other_group.pk}, format="json")
        self.assertEqual(response.status_code, 200)
        self.poll.refresh_from_db()
        self.assertEqual(self.poll.group_id, self.other_group.pk)

    def test_linked_poll_cannot_move_away_from_session_group(self):
        self.other_group.members.add(self.user)
        session = TRPGSession.objects.create(title="関連セッション", group=self.group, gm=self.user, date=None)
        self.poll.session = session
        self.poll.save(update_fields=["session"])
        response = self.client.patch(self.url, {"group": self.other_group.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("group", response.data)
        self.poll.refresh_from_db()
        self.assertEqual(self.poll.group_id, self.group.pk)

    def test_former_admin_cannot_confirm_linked_session(self):
        membership = GroupMembership.objects.create(group=self.other_group, user=self.user, role="admin")
        session = TRPGSession.objects.create(title="権限変更検証", group=self.other_group, gm=self.other, date=None)
        created = self.client.post(
            "/api/schedules/date-polls/",
            {
                "title": "管理者が作成した投票",
                "group": self.other_group.pk,
                "session": session.pk,
                "options": [{"datetime": self.option.datetime.isoformat()}],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        poll = DatePoll.objects.get(pk=created.data["id"])
        membership.role = "member"
        membership.save(update_fields=["role"])
        response = self.client.post(
            f"/api/schedules/date-polls/{poll.pk}/confirm/",
            {"option_id": poll.options.get().pk},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("セッションを編集する権限がありません", str(response.data))
        poll.refresh_from_db()
        session.refresh_from_db()
        self.assertFalse(poll.is_closed)
        self.assertIsNone(session.date)

    def test_legacy_mismatched_group_cannot_confirm_session(self):
        self.other_group.members.add(self.user)
        session = TRPGSession.objects.create(title="不整合検証", group=self.group, gm=self.user, date=None)
        self.poll.session = session
        self.poll.group = self.other_group
        self.poll.save(update_fields=["session", "group"])
        response = self.client.post(self.url + "confirm/", {"option_id": self.option.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        session.refresh_from_db()
        self.poll.refresh_from_db()
        self.assertIsNone(session.date)
        self.assertFalse(self.poll.is_closed)
