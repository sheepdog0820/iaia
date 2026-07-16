from datetime import timedelta
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CharacterSheet, Group
from schedules.google_tokens import get_google_access_token
from schedules import session_permissions
from schedules.models import AsyncJob, CalendarSubscription, GoogleCalendarSync, GoogleIntegration, TRPGSession
from schedules.tasks import sync_google_calendar


class CalendarSubscriptionTestCase(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="calendar-owner",
            email="calendar-owner@example.com",
            password="pass123",
        )
        self.other = user_model.objects.create_user(
            username="calendar-other",
            email="calendar-other@example.com",
            password="pass123",
        )
        self.group = Group.objects.create(name="Calendar Group", created_by=self.user)
        self.other_group = Group.objects.create(name="Other Group", created_by=self.other)
        future_session = TRPGSession.objects.create(
            title="Owned Future Session",
            gm=self.user,
            group=self.group,
            date=timezone.now() + timedelta(days=10),
        )
        undated_session = TRPGSession.objects.create(
            title="Owned Undated Session",
            gm=self.user,
            group=self.group,
            date=None,
        )
        session_permissions.create_participant(session=future_session, user=self.user, role="gm")
        session_permissions.create_participant(session=undated_session, user=self.user, role="gm")
        TRPGSession.objects.create(
            title="Private Other Session",
            gm=self.other,
            group=self.other_group,
            date=timezone.now() + timedelta(days=10),
            visibility="private",
        )
        self.client.force_authenticate(self.user)

    def test_rotate_returns_raw_token_but_stores_only_digest(self):
        response = self.client.post("/api/calendar/subscription-token/rotate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data["token"]
        subscription = CalendarSubscription.objects.get(user=self.user)
        self.assertNotEqual(subscription.token_digest, token)
        self.assertEqual(subscription.token_digest, CalendarSubscription.digest(token))

        feed = self.client.get(f"/calendar/subscribe/{token}.ics")
        content = feed.content.decode("utf-8")
        self.assertEqual(feed.status_code, status.HTTP_200_OK)
        self.assertIn("Owned Future Session", content)
        self.assertIn("Owned Undated Session", content)
        self.assertNotIn("Private Other Session", content)

    def test_rotating_invalidates_previous_token(self):
        first = self.client.post("/api/calendar/subscription-token/rotate/").data["token"]
        second = self.client.post("/api/calendar/subscription-token/rotate/").data["token"]
        self.assertNotEqual(first, second)
        self.assertEqual(
            self.client.get(f"/calendar/subscribe/{first}.ics").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get(f"/calendar/subscribe/{second}.ics").status_code,
            status.HTTP_200_OK,
        )

    def test_subscription_marks_gm_participant_role_without_legacy_gm(self):
        role_session = TRPGSession.objects.create(
            title="Role GM Subscription Session",
            gm=None,
            created_by=self.user,
            group=self.group,
            date=timezone.now() + timedelta(days=12),
        )
        session_permissions.create_participant(session=role_session, user=self.user, role="gm")

        token = self.client.post("/api/calendar/subscription-token/rotate/").data["token"]
        feed = self.client.get(f"/calendar/subscribe/{token}.ics")
        content = feed.content.decode("utf-8")

        self.assertEqual(feed.status_code, status.HTTP_200_OK)
        self.assertIn("SUMMARY:[GM] Role GM Subscription Session", content)


class GoogleIntegrationTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="google-owner",
            email="google-owner@example.com",
            password="pass123",
        )
        self.group = Group.objects.create(name="Google Group", created_by=self.user)
        self.session = TRPGSession.objects.create(
            title="Google Session",
            gm=self.user,
            group=self.group,
            date=timezone.now() + timedelta(days=3),
            duration_minutes=120,
        )
        self.client.force_authenticate(self.user)

    def connect_google(self):
        scopes = [
            GoogleIntegration.REQUIRED_CALENDAR_SCOPE,
            GoogleIntegration.REQUIRED_SHEETS_SCOPE,
        ]
        account = SocialAccount.objects.create(
            user=self.user,
            provider="google",
            uid="google-owner",
            extra_data={"scope": " ".join(scopes)},
        )
        SocialToken.objects.create(
            account=account,
            token="access-token",
            token_secret="",
        )
        response = self.client.put(
            "/api/google/integration/",
            {
                "calendar_enabled": True,
                "sheets_enabled": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_permissions_must_be_granted_by_google(self):
        response = self.client.put(
            "/api/google/integration/",
            {
                "calendar_enabled": True,
                "sheets_enabled": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(GoogleIntegration.objects.filter(user=self.user).exists())

    def test_google_login_default_scope_is_sign_in_only(self):
        google_scopes = settings.SOCIALACCOUNT_PROVIDERS["google"]["SCOPE"]
        self.assertEqual(set(google_scopes), {"openid", "email", "profile"})
        self.assertNotIn(GoogleIntegration.REQUIRED_CALENDAR_SCOPE, google_scopes)
        self.assertNotIn(GoogleIntegration.REQUIRED_SHEETS_SCOPE, google_scopes)

    def test_google_integration_reconnect_url_requests_feature_scopes(self):
        response = self.client.get("/api/google/integration/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reconnect_url = response.data["reconnect_url"]
        query = parse_qs(urlparse(reconnect_url).query)
        self.assertEqual(query["process"], ["connect"])
        scopes = query["scope"][0].split(",")
        self.assertIn(GoogleIntegration.REQUIRED_CALENDAR_SCOPE, scopes)
        self.assertIn(GoogleIntegration.REQUIRED_SHEETS_SCOPE, scopes)

    def test_integration_settings_page_is_available(self):
        self.client.force_login(self.user)
        response = self.client.get("/integrations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "連携設定")
        self.assertContains(response, "ICS購読URLを再発行")
        self.assertContains(response, "通知対象イベント")
        self.assertContains(response, "連携ジョブ状況")
        self.assertContains(response, "Google Sheets キャラクターシート入出力")
        self.assertContains(response, "直前の招待を失効")
        self.assertContains(response, "const websocketEnabled = false")

    def test_calendar_sync_endpoint_creates_job(self):
        self.connect_google()
        response = self.client.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(AsyncJob.objects.filter(pk=response.data["job_id"]).exists())
        self.assertTrue(GoogleCalendarSync.objects.filter(user=self.user, session=self.session).exists())

    @patch("schedules.tasks.requests.post")
    def test_calendar_task_creates_external_event_idempotently(self, post):
        self.connect_google()
        sync = GoogleCalendarSync.objects.create(user=self.user, session=self.session)
        job = AsyncJob.objects.create(
            owner=self.user,
            job_type="google_calendar_sync",
            expires_at=timezone.now() + timedelta(days=1),
        )
        post.return_value = Mock(status_code=200)
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"id": "google-event-1"}

        result = sync_google_calendar.run(sync.pk, str(job.pk))

        self.assertEqual(result, GoogleCalendarSync.Status.SYNCED)
        sync.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(sync.external_event_id, "google-event-1")
        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
    )
    @patch("schedules.google_tokens.Credentials")
    def test_expired_google_token_is_refreshed_before_api_use(self, credentials_class):
        self.connect_google()
        social_token = SocialToken.objects.get(account__user=self.user)
        social_token.expires_at = timezone.now() - timedelta(minutes=1)
        social_token.token_secret = "refresh-token"
        social_token.save(update_fields=["expires_at", "token_secret"])

        credentials = credentials_class.return_value
        credentials.token = "new-access-token"
        credentials.refresh_token = "new-refresh-token"
        credentials.expiry = timezone.now() + timedelta(hours=1)

        access_token = get_google_access_token(self.user)

        self.assertEqual(access_token, "new-access-token")
        credentials.refresh.assert_called_once()
        social_token.refresh_from_db()
        self.assertEqual(social_token.token, "new-access-token")
        self.assertEqual(social_token.token_secret, "new-refresh-token")

    def test_sheets_preview_and_import_use_fixed_columns(self):
        self.connect_google()
        row = {
            "name": "Imported Investigator",
            "edition": "6th",
            "age": 30,
            "occupation": "Detective",
            "STR": 12,
            "CON": 11,
            "POW": 13,
            "DEX": 14,
            "APP": 10,
            "SIZ": 12,
            "INT": 15,
            "EDU": 16,
            "SAN": 65,
        }
        preview = self.client.post(
            "/api/character-sheets/google-sheets/import/",
            {"rows": [row], "preview": True},
            format="json",
        )
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        self.assertEqual(preview.data["rows"][0]["errors"], {})
        self.assertIn("STR", preview.data["columns"])

        imported = self.client.post(
            "/api/character-sheets/google-sheets/import/",
            {"rows": [row], "preview": False, "conflict_action": "create"},
            format="json",
        )
        self.assertEqual(imported.status_code, status.HTTP_201_CREATED)
        character = CharacterSheet.objects.get(pk=imported.data["imported_ids"][0])
        self.assertEqual(character.user, self.user)
        self.assertEqual(character.system_data.name, "Imported Investigator")
