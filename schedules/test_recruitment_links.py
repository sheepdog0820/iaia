from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import IntegrityError, transaction
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.adapters import CustomAccountAdapter
from accounts.auth_redirects import AUTH_NEXT_SESSION_KEY
from accounts.models import Group, GroupMembership
from schedules import session_permissions
from schedules.models import (
    SessionParticipant,
    SessionParticipantRole,
    SessionRecruitmentLink,
    SessionRecruitmentLinkUse,
    TRPGSession,
)


class SessionRecruitmentLinkTestCase(APITestCase):
    password = "pass12345"

    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username="recruitment-manager",
            email="recruitment-manager@example.com",
            password=self.password,
            nickname="募集GM",
        )
        self.player = user_model.objects.create_user(
            username="recruitment-player",
            email="recruitment-player@example.com",
            password=self.password,
        )
        self.second_player = user_model.objects.create_user(
            username="recruitment-player-2",
            email="recruitment-player-2@example.com",
            password=self.password,
        )
        self.outsider = user_model.objects.create_user(
            username="recruitment-outsider",
            email="recruitment-outsider@example.com",
            password=self.password,
        )
        self.group = Group.objects.create(name="Recruitment Group", created_by=self.manager)
        GroupMembership.objects.get_or_create(group=self.group, user=self.manager, defaults={"role": "admin"})
        self.session = TRPGSession.objects.create(
            title="秘密の募集セッション",
            gm=self.manager,
            created_by=self.manager,
            group=self.group,
            visibility="private",
            date=timezone.now() + timedelta(days=2),
        )

    def issue_link(self, *, max_uses=2, expires_in_hours=24):
        self.client.force_authenticate(self.manager)
        response = self.client.post(
            f"/api/sessions/{self.session.pk}/recruitment-links/",
            {
                "expires_in_hours": expires_in_hours,
                "max_uses": max_uses,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        token = response.data["recruitment_url"].rstrip("/").rsplit("/", 1)[-1]
        return response, SessionRecruitmentLink.objects.get(pk=response.data["id"]), token

    def test_manager_can_issue_list_and_revoke_without_persisting_raw_token(self):
        issued, recruitment_link, token = self.issue_link(max_uses=4)

        self.assertNotEqual(recruitment_link.token_digest, token)
        self.assertEqual(len(recruitment_link.token_digest), 64)
        self.assertNotIn("token", issued.data)
        self.assertTrue(issued.data["recruitment_url"].endswith(f"/session-recruitment/{token}/"))
        self.assertEqual(issued.data["max_uses"], 4)
        self.assertEqual(issued.data["use_count"], 0)
        self.assertTrue(issued.data["is_active"])

        listed = self.client.get(f"/api/sessions/{self.session.pk}/recruitment-links/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listed.data), 1)
        self.assertNotIn("token", listed.data[0])
        self.assertNotIn("recruitment_url", listed.data[0])

        revoked = self.client.delete(f"/api/sessions/{self.session.pk}/recruitment-links/{recruitment_link.pk}/")
        self.assertEqual(revoked.status_code, status.HTTP_204_NO_CONTENT)
        recruitment_link.refresh_from_db()
        self.assertIsNotNone(recruitment_link.revoked_at)
        self.assertFalse(recruitment_link.is_active)

    def test_non_manager_cannot_manage_recruitment_links(self):
        _, recruitment_link, _ = self.issue_link()
        self.client.force_authenticate(self.outsider)

        issued = self.client.post(
            f"/api/sessions/{self.session.pk}/recruitment-links/",
            {"expires_in_hours": 24, "max_uses": 2},
            format="json",
        )
        listed = self.client.get(f"/api/sessions/{self.session.pk}/recruitment-links/")
        revoked = self.client.delete(f"/api/sessions/{self.session.pk}/recruitment-links/{recruitment_link.pk}/")

        self.assertEqual(issued.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(listed.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(revoked.status_code, status.HTTP_403_FORBIDDEN)

    def test_issue_rejects_values_outside_documented_ranges(self):
        self.client.force_authenticate(self.manager)

        for payload in (
            {"expires_in_hours": 0, "max_uses": 1},
            {"expires_in_hours": 721, "max_uses": 1},
            {"expires_in_hours": 1, "max_uses": 0},
            {"expires_in_hours": 1, "max_uses": 1001},
            {"expires_in_hours": "tomorrow", "max_uses": 1},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(
                    f"/api/sessions/{self.session.pk}/recruitment-links/",
                    payload,
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_landing_shows_only_safe_information_and_auth_return_links(self):
        _, recruitment_link, token = self.issue_link()
        self.client.force_authenticate(user=None)

        response = self.client.get(f"/session-recruitment/{token}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.session.title)
        self.assertContains(response, "募集GM")
        self.assertContains(response, recruitment_link.expires_at.strftime("%Y"))
        self.assertContains(response, "/login/?next=%2Fsession-recruitment%2F")
        self.assertContains(response, "/signup/?next=%2Fsession-recruitment%2F")
        self.assertNotContains(response, self.manager.email)
        self.assertFalse(SessionParticipant.objects.filter(session=self.session, user=self.player).exists())

    def test_landing_shows_unscheduled_label(self):
        self.session.date = None
        self.session.save(update_fields=["date"])
        _, _, token = self.issue_link()
        self.client.force_authenticate(user=None)

        response = self.client.get(f"/session-recruitment/{token}/")

        self.assertContains(response, "日程未定")

    def test_authenticated_landing_uses_csrf_post_and_get_does_not_join(self):
        _, _, token = self.issue_link()
        self.client.force_authenticate(user=None)
        self.client.force_login(self.player)

        response = self.client.get(f"/session-recruitment/{token}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'id="recruitment-join-form"')
        self.assertContains(response, "requestSubmit()")
        self.assertFalse(SessionParticipant.objects.filter(session=self.session, user=self.player).exists())

        joined = self.client.post(f"/session-recruitment/{token}/join/")
        self.assertEqual(joined.status_code, status.HTTP_200_OK)
        self.assertContains(joined, "参加登録が完了しました")

    def test_api_join_is_authenticated_idempotent_and_player_only(self):
        _, recruitment_link, token = self.issue_link(max_uses=1)
        self.client.force_authenticate(user=None)

        anonymous = self.client.post(f"/api/session-recruitment/{token}/join/")
        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.player)
        joined = self.client.post(f"/api/session-recruitment/{token}/join/")
        repeated = self.client.post(f"/api/session-recruitment/{token}/join/")

        self.assertEqual(joined.status_code, status.HTTP_201_CREATED)
        self.assertFalse(joined.data["already_joined"])
        self.assertEqual(repeated.status_code, status.HTTP_200_OK)
        self.assertTrue(repeated.data["already_joined"])
        self.assertEqual(
            SessionParticipant.objects.filter(session=self.session, user=self.player).count(),
            1,
        )
        participant = SessionParticipant.objects.get(session=self.session, user=self.player)
        self.assertEqual(
            list(participant.participant_roles.values_list("role", flat=True)),
            [SessionParticipantRole.Role.PLAYER],
        )
        recruitment_link.refresh_from_db()
        self.assertEqual(recruitment_link.use_count, 1)
        self.assertEqual(
            SessionRecruitmentLinkUse.objects.filter(
                recruitment_link=recruitment_link,
                joined_by=self.player,
                participant=participant,
            ).count(),
            1,
        )
        self.assertFalse(GroupMembership.objects.filter(group=self.group, user=self.player).exists())

        self.client.force_authenticate(user=None)
        self.client.force_login(self.player)
        landing = self.client.get(f"/session-recruitment/{token}/")
        self.assertEqual(landing.status_code, status.HTTP_200_OK)
        self.assertContains(landing, "すでに参加しています")

        self.client.logout()
        self.client.force_login(self.second_player)
        full_landing = self.client.get(f"/session-recruitment/{token}/")
        self.assertEqual(full_landing.status_code, status.HTTP_410_GONE)
        self.assertNotContains(
            full_landing,
            self.session.title,
            status_code=status.HTTP_410_GONE,
        )

    def test_api_join_requires_csrf_for_session_authenticated_users(self):
        _, _, token = self.issue_link(max_uses=1)
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_client.force_login(self.player)

        rejected = csrf_client.post(f"/api/session-recruitment/{token}/join/")
        self.assertEqual(rejected.status_code, status.HTTP_403_FORBIDDEN)

        landing = csrf_client.get(f"/session-recruitment/{token}/")
        csrf_token = landing.cookies["csrftoken"].value
        accepted = csrf_client.post(
            f"/api/session-recruitment/{token}/join/",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED)

    def test_existing_participant_does_not_consume_a_use(self):
        _, recruitment_link, token = self.issue_link(max_uses=1)
        participant = session_permissions.create_participant(
            session=self.session,
            user=self.player,
            role=SessionParticipantRole.Role.PLAYER,
            granted_by=self.manager,
        )
        self.client.force_authenticate(self.player)

        response = self.client.post(f"/api/session-recruitment/{token}/join/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["already_joined"])
        self.assertEqual(response.data["participant_id"], participant.pk)
        recruitment_link.refresh_from_db()
        self.assertEqual(recruitment_link.use_count, 0)
        self.assertFalse(SessionRecruitmentLinkUse.objects.filter(recruitment_link=recruitment_link).exists())

    def test_max_uses_expiry_revocation_and_invalid_tokens_do_not_create_participants(self):
        _, recruitment_link, token = self.issue_link(max_uses=1)
        self.client.force_authenticate(self.player)
        first = self.client.post(f"/api/session-recruitment/{token}/join/")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.second_player)
        full = self.client.post(f"/api/session-recruitment/{token}/join/")
        self.assertEqual(full.status_code, status.HTTP_410_GONE)

        recruitment_link.expires_at = timezone.now() - timedelta(minutes=1)
        recruitment_link.max_uses = 2
        recruitment_link.save(update_fields=["expires_at", "max_uses"])
        expired = self.client.post(f"/api/session-recruitment/{token}/join/")
        self.assertEqual(expired.status_code, status.HTTP_410_GONE)

        recruitment_link.expires_at = timezone.now() + timedelta(hours=1)
        recruitment_link.revoked_at = timezone.now()
        recruitment_link.save(update_fields=["expires_at", "revoked_at"])
        revoked = self.client.post(f"/api/session-recruitment/{token}/join/")
        invalid = self.client.post("/api/session-recruitment/not-a-real-token/join/")

        self.assertEqual(revoked.status_code, status.HTTP_410_GONE)
        self.assertEqual(invalid.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(SessionParticipant.objects.filter(session=self.session, user=self.second_player).exists())

    def test_database_constraint_prevents_use_count_from_exceeding_max_uses(self):
        _, recruitment_link, _ = self.issue_link(max_uses=1)

        with self.assertRaises(IntegrityError), transaction.atomic():
            SessionRecruitmentLink.objects.filter(pk=recruitment_link.pk).update(use_count=2)

    def test_inactive_and_invalid_landings_do_not_disclose_session_information(self):
        _, recruitment_link, token = self.issue_link()
        recruitment_link.revoked_at = timezone.now()
        recruitment_link.save(update_fields=["revoked_at"])
        self.client.force_authenticate(user=None)

        revoked = self.client.get(f"/session-recruitment/{token}/")
        invalid = self.client.get("/session-recruitment/not-a-real-token/")

        self.assertEqual(revoked.status_code, status.HTTP_410_GONE)
        self.assertEqual(invalid.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotContains(revoked, self.session.title, status_code=status.HTTP_410_GONE)
        self.assertNotContains(invalid, self.session.title, status_code=status.HTTP_404_NOT_FOUND)

    def test_login_and_signup_honor_safe_next_destination(self):
        _, _, token = self.issue_link()
        self.client.force_authenticate(user=None)
        next_path = f"/session-recruitment/{token}/"

        logged_in = self.client.post(
            f"/login/?next={next_path}",
            {
                "username": self.player.username,
                "password": self.password,
                "next": next_path,
            },
        )
        self.assertRedirects(logged_in, next_path, fetch_redirect_response=False)

        self.client.logout()
        signed_up = self.client.post(
            f"/signup/?next={next_path}",
            {
                "username": "new-recruitment-player",
                "email": "new-recruitment-player@example.com",
                "password1": "AnotherPass123!",
                "password2": "AnotherPass123!",
                "next": next_path,
            },
        )
        self.assertRedirects(signed_up, next_path, fetch_redirect_response=False)

    def test_external_next_destination_is_rejected(self):
        response = self.client.post(
            "/login/?next=https://evil.example/steal",
            {
                "username": self.player.username,
                "password": self.password,
                "next": "https://evil.example/steal",
            },
        )

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_recruitment_management_ui_is_visible_only_to_participant_managers(self):
        self.client.force_authenticate(self.manager)
        manager_response = self.client.get(reverse("session_detail", kwargs={"pk": self.session.pk}))

        self.assertEqual(manager_response.status_code, status.HTTP_200_OK)
        self.assertContains(manager_response, 'id="recruitmentLinksModal"')

        session_permissions.create_participant(
            session=self.session,
            user=self.player,
            role=SessionParticipantRole.Role.PLAYER,
            granted_by=self.manager,
        )
        self.client.force_authenticate(self.player)
        player_response = self.client.get(reverse("session_detail", kwargs={"pk": self.session.pk}))

        self.assertEqual(player_response.status_code, status.HTTP_200_OK)
        self.assertNotContains(player_response, 'id="recruitmentLinksModal"')


class RecruitmentAndCharacterActionTemplateTestCase(SimpleTestCase):
    def test_auth_templates_and_allauth_adapter_preserve_safe_next(self):
        login_template = Path("templates/account/login.html").read_text(encoding="utf-8")
        signup_template = Path("templates/account/signup.html").read_text(encoding="utf-8")

        self.assertIn("provider_login_url 'google' next=auth_next", login_template)
        self.assertIn("provider_login_url provider.id next=auth_next", signup_template)
        self.assertIn('name="next" value="{{ auth_next }}"', login_template)
        self.assertIn('name="next" value="{{ auth_next }}"', signup_template)

        request = RequestFactory().get("/")
        SessionMiddleware(lambda current_request: None).process_request(request)
        request.session[AUTH_NEXT_SESSION_KEY] = "/session-recruitment/safe-token/"

        self.assertEqual(
            CustomAccountAdapter().get_login_redirect_url(request),
            "/session-recruitment/safe-token/",
        )
        self.assertNotIn(AUTH_NEXT_SESSION_KEY, request.session)

    def test_session_detail_contains_recruitment_management_ui(self):
        template = Path("templates/schedules/session_detail.html").read_text(encoding="utf-8")

        self.assertIn('id="recruitmentLinksModal"', template)
        self.assertIn('id="issueRecruitmentLinkForm"', template)
        self.assertIn("recruitment-links/", template)
        self.assertIn("{% if can_invite and not is_public_view %}", template)

    def test_character_actions_use_semantic_groups_and_mobile_grid_positions(self):
        template = Path("templates/accounts/character_detail.html").read_text(encoding="utf-8")

        self.assertIn('<nav class="character-actions"', template)
        self.assertIn('aria-label="キャラクター操作"', template)
        self.assertIn("action-group--left", template)
        self.assertIn("action-group--right", template)
        self.assertIn("action-button--move", template)
        self.assertIn("action-button--output", template)
        self.assertIn("action-button--recreate", template)
        self.assertIn("action-button--edit", template)
        self.assertIn("#characterContent .action-button--move,", template)
        self.assertIn("#characterContent .action-button--recreate {", template)
        self.assertIn("#characterContent .action-button--output,", template)
        self.assertIn("#characterContent .action-button--edit {", template)
