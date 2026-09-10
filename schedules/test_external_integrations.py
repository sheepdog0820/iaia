from datetime import timedelta
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from google.auth.exceptions import GoogleAuthError, RefreshError, TransportError
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.character_models import CharacterSheet7th
from accounts.models import CharacterSheet, Group
from schedules import session_permissions
from schedules.google_sheets import SHEET_COLUMNS, SHEETS_DEFAULT_DISPLAY_RANGE
from schedules.google_tokens import get_google_access_token
from schedules.models import AsyncJob, CalendarSubscription, GoogleCalendarSync, GoogleIntegration, TRPGSession
from schedules.tasks import sync_google_calendar


class CalendarSubscriptionTestCase(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="calendar-owner",
            email="calendar-owner@example.com",
            # Isolated test fixture or mocked credential; never a production secret.
            password="pass123",  # nosec B106
        )
        self.other = user_model.objects.create_user(
            username="calendar-other",
            email="calendar-other@example.com",
            # Isolated test fixture or mocked credential; never a production secret.
            password="pass123",  # nosec B106
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
            # Isolated test fixture or mocked credential; never a production secret.
            password="pass123",  # nosec B106
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
            # Isolated test fixture or mocked credential; never a production secret.
            token="access-token",  # nosec B106
            token_secret="",
        )
        GoogleIntegration.objects.create(user=self.user, scopes=scopes)
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
        self.assertContains(response, "Google Sheets キャラクターシート出力")
        self.assertNotContains(response, "取込プレビュー")
        self.assertNotContains(response, 'id="import-google-sheets"')
        self.assertContains(response, "直前の招待を失効")
        self.assertContains(response, "const websocketEnabled = false")

    def test_sheets_default_range_matches_export_columns(self):
        self.client.force_login(self.user)

        response = self.client.get("/integrations/")

        self.assertEqual(len(SHEET_COLUMNS), 17)
        self.assertEqual(SHEET_COLUMNS[-1], "LUCK")
        self.assertEqual(SHEETS_DEFAULT_DISPLAY_RANGE, "Characters!A:Q")
        self.assertContains(response, 'id="sheets-range" value="Characters!A:Q"')

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
        # Isolated test fixture or mocked credential; never a production secret.
        GOOGLE_OAUTH_CLIENT_SECRET="client-secret",  # nosec B106
    )
    @patch("schedules.google_tokens.Credentials")
    def test_expired_google_token_is_refreshed_before_api_use(self, credentials_class):
        self.connect_google()
        social_token = SocialToken.objects.get(account__user=self.user)
        social_token.expires_at = timezone.now() - timedelta(minutes=1)
        # Isolated test fixture or mocked credential; never a production secret.
        social_token.token_secret = "refresh-token"  # nosec B105
        social_token.save(update_fields=["expires_at", "token_secret"])

        credentials = credentials_class.return_value
        # Isolated test fixture or mocked credential; never a production secret.
        credentials.token = "new-access-token"  # nosec B105
        # Isolated test fixture or mocked credential; never a production secret.
        credentials.refresh_token = "new-refresh-token"  # nosec B105
        credentials.expiry = timezone.now() + timedelta(hours=1)

        access_token = get_google_access_token(self.user)

        self.assertEqual(access_token, "new-access-token")
        credentials.refresh.assert_called_once()
        social_token.refresh_from_db()
        self.assertEqual(social_token.token, "new-access-token")
        self.assertEqual(social_token.token_secret, "new-refresh-token")

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="fixture-client", GOOGLE_OAUTH_CLIENT_SECRET="fixture-secret"
    )  # nosec B106
    @patch("schedules.tasks.requests.put")
    @patch("schedules.tasks.requests.post")
    @patch("schedules.google_tokens.Credentials")
    def test_google_refresh_failures_finish_jobs_without_exporting(self, credentials_class, post, put):
        from schedules.tasks import export_google_sheet

        self.connect_google()
        token = SocialToken.objects.get(account__user=self.user)
        token.expires_at = timezone.now() - timedelta(minutes=1)
        token.token_secret = "isolated-refresh-fixture"  # nosec B105
        token.save(update_fields=["expires_at", "token_secret"])
        original = (token.token, token.token_secret, token.expires_at)
        sync = GoogleCalendarSync.objects.create(user=self.user, session=self.session)
        message = "Google認可の更新に失敗しました。時間をおいて再試行し、解消しない場合はGoogleを再連携してください。"
        for error_type in (RefreshError, TransportError):
            for kind in ("google_calendar_sync", "google_sheets_export"):
                with self.subTest(error=error_type.__name__, kind=kind):
                    credentials_class.return_value.refresh.side_effect = error_type("private-provider-error-fixture")
                    job = AsyncJob.objects.create(
                        owner=self.user, job_type=kind, expires_at=timezone.now() + timedelta(days=1)
                    )
                    result = None
                    try:
                        if kind == "google_calendar_sync":
                            result = sync_google_calendar.run(sync.pk, str(job.pk))
                        else:
                            result = export_google_sheet.run(str(job.pk), self.user.pk, "isolated-sheet", "A1", [])
                    except GoogleAuthError:
                        pass
                    job.refresh_from_db()
                    self.assertEqual(job.status, AsyncJob.Status.FAILED)
                    self.assertIsNotNone(job.finished_at)
                    self.assertEqual(job.error, message)
                    self.assertEqual(result, "missing-token")
                    if kind == "google_calendar_sync":
                        sync.refresh_from_db()
                        self.assertEqual(sync.status, GoogleCalendarSync.Status.FAILED)
                        self.assertEqual(sync.last_error, message)
                    token.refresh_from_db()
                    self.assertEqual((token.token, token.token_secret, token.expires_at), original)
                    post.assert_not_called()
                    put.assert_not_called()

    def test_sheets_import_endpoint_is_not_available(self):
        self.connect_google()
        response = self.client.post(
            "/api/character-sheets/google-sheets/import/",
            {"rows": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("schedules.integration_views.queue_google_sheet_export", return_value=True)
    def test_sheets_export_rejects_empty_or_invalid_selection_before_queueing(self, queue_export):
        self.connect_google()
        character = CharacterSheet.objects.create(user=self.user, edition="7th")
        CharacterSheet7th.objects.create(character_sheet=character, name="Private selection fixture")
        for selection in ([], None, "1", {}, [0], [-1], ["invalid"]):
            with self.subTest(selection=selection):
                response = self.client.post(
                    "/api/character-sheets/google-sheets/export/",
                    {"character_ids": selection, "spreadsheet_id": "isolated-sheet"},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("character_ids", response.data)
                if selection == []:
                    self.assertEqual(
                        response.data["character_ids"],
                        ["出力するキャラクターを1件以上指定してください。"],
                    )
                queue_export.assert_not_called()
                self.assertFalse(AsyncJob.objects.filter(job_type="google_sheets_export").exists())

    @patch("schedules.integration_views.queue_google_sheet_export", return_value=True)
    def test_sheets_export_selection_does_not_include_other_owned_or_foreign_characters(self, queue_export):
        self.connect_google()
        other = get_user_model().objects.create_user(username="sheet-other-owner")
        characters = []
        for owner, name in ((self.user, "Selected"), (self.user, "Not selected"), (other, "Other owner")):
            character = CharacterSheet.objects.create(user=owner, edition="7th")
            CharacterSheet7th.objects.create(character_sheet=character, name=name)
            characters.append(character)
        response = self.client.post(
            "/api/character-sheets/google-sheets/export/",
            {"character_ids": [characters[0].pk, characters[2].pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row[0] for row in response.data["rows"]], [characters[0].pk])
        response = self.client.post("/api/character-sheets/google-sheets/export/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row[0] for row in response.data["rows"]], [c.pk for c in characters[:2]])
        response = self.client.post(
            "/api/character-sheets/google-sheets/export/",
            {"character_ids": [str(characters[0].pk)], "spreadsheet_id": "isolated-sheet"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual([row[0] for row in queue_export.call_args.args[-1][1:]], [characters[0].pk])
        self.assertEqual(AsyncJob.objects.get(pk=response.data["job_id"]).payload["character_ids"], [characters[0].pk])

    def test_sheets_export_includes_7th_luck_and_current_statuses(self):
        self.connect_google()
        character = CharacterSheet.objects.create(user=self.user, edition="7th")
        CharacterSheet7th.objects.create(
            character_sheet=character,
            name="Exported Seventh Investigator",
            age=30,
            occupation="Detective",
            str_value=60,
            con_value=55,
            pow_value=65,
            dex_value=70,
            app_value=50,
            siz_value=60,
            int_value=75,
            edu_value=80,
            hit_points_current=9,
            hit_points_max=11,
            magic_points_current=8,
            magic_points_max=13,
            sanity_starting=65,
            sanity_current=51,
            sanity_max=99,
            luck_starting=47,
            luck_current=47,
            luck_max=47,
        )

        exported = self.client.post(
            "/api/character-sheets/google-sheets/export/",
            {"character_ids": [character.pk]},
            format="json",
        )

        self.assertEqual(exported.status_code, status.HTTP_200_OK)
        self.assertEqual(exported.data["columns"][-4:], ["HP", "MP", "SAN", "LUCK"])
        self.assertEqual(exported.data["rows"][0][-4:], [9, 8, 51, 47])
