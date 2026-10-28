from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership
from schedules.integration_views import _build_ical
from schedules.models import CalendarSubscription, SessionParticipant, TRPGSession


class CalendarSubscriptionAuthorizationTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="subscription-reader")
        self.other = user_model.objects.create_user(username="subscription-other")
        self.admin = user_model.objects.create_user(username="subscription-admin", is_staff=True, is_superuser=True)
        self.group = Group.objects.create(name="購読認可の検証", created_by=self.other)
        self.owned_session = TRPGSession.objects.create(
            title="購読者が作成した予定",
            description="購読者の説明",
            created_by=self.user,
            gm=self.user,
            date=timezone.now() + timedelta(days=1),
        )
        self.shared_session = TRPGSession.objects.create(
            title="参加中の非公開予定",
            description="参加者にだけ公開する説明",
            created_by=self.other,
            gm=self.other,
            group=self.group,
            visibility="private",
            date=timezone.now() + timedelta(days=2),
        )
        self.participant = SessionParticipant.objects.create(session=self.shared_session, user=self.user)
        self.unrelated_session = TRPGSession.objects.create(
            title="参加していない非公開予定",
            created_by=self.other,
            gm=self.other,
            visibility="private",
            date=timezone.now() + timedelta(days=3),
        )
        self.subscription, self.token = CalendarSubscription.issue_for(self.user)
        self.url = reverse("calendar-subscription", kwargs={"token": self.token})

    def assert_feed(self, response, *, includes_shared=True):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Content-Type"], "text/calendar; charset=utf-8")
        self.assertContains(response, self.owned_session.title)
        self.assertNotContains(response, self.unrelated_session.title)
        if includes_shared:
            self.assertContains(response, self.shared_session.title)
        else:
            self.assertNotContains(response, self.shared_session.title)
            self.assertNotContains(response, self.shared_session.description)

    def test_active_owner_can_subscribe_without_browser_authentication(self):
        self.assert_feed(self.client.get(self.url))

    def test_inactive_owner_cannot_export_with_get_or_head_even_with_another_login(self):
        self.assert_feed(self.client.get(self.url))
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        for login in (None, self.other, self.admin):
            self.client.logout()
            if login:
                self.client.force_login(login)
            for method in ("get", "head"):
                with self.subTest(login=login.username if login else "anonymous", method=method):
                    with patch("schedules.integration_views._build_ical", wraps=_build_ical) as build:
                        response = getattr(self.client, method)(self.url)
                        self.assertEqual(response.status_code, 404)
                        self.assertNotIn(self.owned_session.title.encode(), response.content)
                        self.assertNotIn(self.shared_session.description.encode(), response.content)
                        build.assert_not_called()
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.token_digest, CalendarSubscription.digest(self.token))

    def test_reactivation_does_not_rotate_or_delete_a_subscription(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        self.assert_feed(self.client.get(self.url))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.token_digest, CalendarSubscription.digest(self.token))

    def test_membership_and_participation_are_checked_again_on_each_fetch(self):
        self.assert_feed(self.client.get(self.url))
        self.participant.delete()
        self.shared_session.description = "脱退後に追加された非公開情報"
        self.shared_session.save(update_fields=["description"])
        self.assert_feed(self.client.get(self.url), includes_shared=False)
        membership = GroupMembership.objects.create(user=self.user, group=self.group, role="admin")
        self.assert_feed(self.client.get(self.url))
        membership.role = "member"
        membership.save(update_fields=["role"])
        self.assert_feed(self.client.get(self.url), includes_shared=False)
        membership.delete()
        self.assert_feed(self.client.get(self.url), includes_shared=False)

    def test_rotated_and_deleted_subscriptions_do_not_build_a_feed(self):
        new_token = self.subscription.rotate()
        with patch("schedules.integration_views._build_ical", wraps=_build_ical) as build:
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 404)
            build.assert_not_called()
        new_url = reverse("calendar-subscription", kwargs={"token": new_token})
        self.assert_feed(self.client.get(new_url))
        self.subscription.delete()
        with patch("schedules.integration_views._build_ical", wraps=_build_ical) as build:
            self.assertEqual(self.client.get(new_url).status_code, 404)
            build.assert_not_called()

    def test_deleted_owner_cannot_leave_a_readable_subscription(self):
        self.participant.delete()
        self.owned_session.delete()
        self.user.delete()
        self.assertFalse(CalendarSubscription.objects.filter(pk=self.subscription.pk).exists())
        with patch("schedules.integration_views._build_ical", wraps=_build_ical) as build:
            self.assertEqual(self.client.get(self.url).status_code, 404)
            build.assert_not_called()
