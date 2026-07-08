from schedules import session_permissions
import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from schedules.models import SessionParticipant, TRPGSession

from .character_models import CharacterImage, CharacterSheet
from .models import CustomUser, Group, GroupMembership

User = get_user_model()


class BasicAccountsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="basicuser", email="basic@example.com", password="basicpass123", nickname="Basic User"
        )

    def test_custom_user_model(self):
        """カスタムユーザーモデルのテスト"""
        self.assertIsInstance(self.user, CustomUser)
        self.assertEqual(self.user.email, "basic@example.com")
        self.assertEqual(self.user.nickname, "Basic User")

    def test_user_str_representation(self):
        """ユーザー文字列表現のテスト"""
        self.assertEqual(str(self.user), "Basic User")

    def test_login_view(self):
        """ログインビューのテスト"""
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)

    def test_signup_view(self):
        """サインアップビューのテスト"""
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_view_unauthenticated(self):
        """未認証ダッシュボードビューのテスト"""
        response = self.client.get("/accounts/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_dashboard_view_authenticated(self):
        """認証済みダッシュボードビューのテスト"""
        self.client.force_login(self.user)
        response = self.client.get("/accounts/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_profile_edit_saves_trpg_introduction_sheet(self):
        """プロフィール編集でTRPG自己紹介シートが保存されること"""
        self.client.force_login(self.user)

        response = self.client.post(
            "/accounts/profile/edit/",
            data={
                "nickname": "Updated User",
                "email": "basic@example.com",
                "first_name": "太郎",
                "last_name": "田中",
                "trpg_history": "CoC中心に遊んでいます",
                "trpg_env": ["online"],
                "trpg_tools": "Discord / CCFOLIA",
                "trpg_systems_played": ["coc6"],
                "trpg_systems_favorite": ["coc6"],
                "trpg_scenario_structure": "semi_free",
                "trpg_loss_preference": "conditional",
                "trpg_loss_preference_note": "KPと相談したい",
                "trpg_ng_expression": ["gore"],
                "trpg_ng_share_method": "kp_only",
                "trpg_free_comment": "よろしくお願いします",
                "trpg_profile_visibility": "participants",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        sheet = self.user.trpg_introduction_sheet

        self.assertEqual(sheet.get("basic", {}).get("environment"), ["online"])
        self.assertEqual(sheet.get("basic", {}).get("tools"), "Discord / CCFOLIA")
        self.assertEqual(sheet.get("systems", {}).get("played"), ["coc6"])
        self.assertEqual(sheet.get("scenario", {}).get("loss"), "conditional")
        self.assertEqual(sheet.get("ng", {}).get("expression"), ["gore"])
        self.assertEqual(sheet.get("visibility"), "participants")

    def test_user_profile_view_requires_shared_group(self):
        """グループメンバーのプロフィール参照は共通グループが必要"""
        owner = User.objects.create_user(
            username="owneruser",
            email="owner@example.com",
            password="pass1234",
            nickname="Owner User",
        )
        other = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="pass1234",
            nickname="Other User",
        )
        outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="pass1234",
            nickname="Outsider",
        )

        group = Group.objects.create(name="Shared Group", created_by=owner)
        GroupMembership.objects.create(user=owner, group=group, role="admin")
        GroupMembership.objects.create(user=other, group=group, role="member")

        url = f"/accounts/users/{other.id}/profile/"

        self.client.force_login(outsider)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.force_login(owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, other.email)

    def test_user_detail_api_does_not_expose_other_users(self):
        other = User.objects.create_user(
            username="apiother",
            email="apiother@example.com",
            password="pass1234",
            nickname="API Other",
            trpg_history="private history",
        )

        self.client.force_login(self.user)

        own_response = self.client.get(f"/api/accounts/users/{self.user.id}/")
        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(own_response.json()["email"], self.user.email)

        other_response = self.client.get(f"/api/accounts/users/{other.id}/")
        self.assertEqual(other_response.status_code, 404)
        self.assertNotContains(
            other_response,
            other.email,
            status_code=404,
        )
        self.assertNotContains(
            other_response,
            other.trpg_history,
            status_code=404,
        )

    def test_character_detail_api_allows_session_gm(self):
        """ログイン済みユーザーは他人のキャラも参照できる"""
        gm = User.objects.create_user(
            username="gmuser",
            email="gm@example.com",
            password="pass1234",
            nickname="GM User",
        )
        player = User.objects.create_user(
            username="playeruser",
            email="player@example.com",
            password="pass1234",
            nickname="Player User",
        )
        outsider = User.objects.create_user(
            username="outsideruser",
            email="outsider@example.com",
            password="pass1234",
            nickname="Outsider User",
        )

        group = Group.objects.create(name="Session Group", created_by=gm)
        GroupMembership.objects.create(user=gm, group=group, role="admin")
        GroupMembership.objects.create(user=player, group=group, role="member")

        character = CharacterSheet.objects.create(
            user=player,
            edition="6th",
            name="Test PC",
            age=20,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_max=50,
            sanity_current=50,
            sanity_starting=50,
        )

        session = TRPGSession.objects.create(
            title="Test Session",
            description="",
            date=timezone.now() + timedelta(days=1),
            location="オンライン",
            gm=gm,
            group=group,
            status="planned",
            visibility="private",
            duration_minutes=60,
        )
        session_permissions.create_participant(
            session=session,
            user=player,
            role="player",
            player_slot=1,
            character_sheet=character,
        )

        self.client.force_login(gm)
        response = self.client.get(f"/api/accounts/character-sheets/{character.id}/")
        self.assertEqual(response.status_code, 200)

        self.client.force_login(player)
        response = self.client.get(f"/api/accounts/character-sheets/{character.id}/")
        self.assertEqual(response.status_code, 200)

        self.client.force_login(outsider)
        response = self.client.get(f"/api/accounts/character-sheets/{character.id}/")
        self.assertEqual(response.status_code, 404)

        self.client.force_login(gm)
        response = self.client.get(reverse("character_detail_6th", kwargs={"character_id": character.id}))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(outsider)
        response = self.client.get(reverse("character_detail_6th", kwargs={"character_id": character.id}))
        self.assertEqual(response.status_code, 404)

    def test_character_sheet_access_scope_group_private_public_and_allowed_users(self):
        owner = User.objects.create_user(
            username="scope_owner",
            email="scope_owner@example.com",
            password="pass1234",
            nickname="Scope Owner",
        )
        group_user = User.objects.create_user(
            username="scope_group_user",
            email="scope_group@example.com",
            password="pass1234",
            nickname="Scope Group",
        )
        allowed_user = User.objects.create_user(
            username="scope_allowed_user",
            email="scope_allowed@example.com",
            password="pass1234",
            nickname="Scope Allowed",
        )
        outsider = User.objects.create_user(
            username="scope_outsider",
            email="scope_outsider@example.com",
            password="pass1234",
            nickname="Scope Outsider",
        )
        group = Group.objects.create(name="Scope Group", created_by=owner)
        GroupMembership.objects.create(user=owner, group=group, role="admin")
        GroupMembership.objects.create(user=group_user, group=group, role="member")

        character = CharacterSheet.objects.create(
            user=owner,
            edition="6th",
            name="Scoped PC",
            age=20,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_max=50,
            sanity_current=50,
            sanity_starting=50,
        )
        url = f"/api/accounts/character-sheets/{character.id}/"

        self.client.force_login(group_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.force_login(outsider)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        character.access_scope = "private"
        character.save(update_fields=["access_scope"])
        character.allowed_users.add(allowed_user)

        self.client.force_login(group_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        self.client.force_login(allowed_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        character.access_scope = "public"
        character.save(update_fields=["access_scope"])

        self.client.force_login(outsider)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_access_scope_private_update_closes_fixed_share_view(self):
        owner = User.objects.create_user(
            username="scope_update_owner",
            email="scope_update_owner@example.com",
            password="pass1234",
            nickname="Scope Update Owner",
        )
        character = CharacterSheet.objects.create(
            user=owner,
            edition="6th",
            name="Scope Update PC",
            age=20,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_max=50,
            sanity_current=50,
            sanity_starting=50,
            access_scope="public",
        )
        self.client.force_login(owner)

        response = self.client.patch(
            f"/api/accounts/character-sheets/{character.id}/",
            data=json.dumps({"access_scope": "private"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        character.refresh_from_db()
        self.assertEqual(character.access_scope, "private")

        self.client.logout()
        old_public_api_response = self.client.get(f"/api/accounts/character-sheets/{character.id}/public/")
        self.assertEqual(old_public_api_response.status_code, 404)

        fixed_share_response = self.client.get(
            reverse("fixed-shared-character-view", kwargs={"share_token": character.share_token})
        )
        self.assertEqual(fixed_share_response.status_code, 404)

    def test_fixed_character_share_view_requires_shareable_scope(self):
        owner = User.objects.create_user(
            username="direct_link_owner",
            email="direct_link_owner@example.com",
            password="pass1234",
            nickname="Direct Link Owner",
        )
        character = CharacterSheet.objects.create(
            user=owner,
            edition="6th",
            name="Direct Link PC",
            player_name="Direct Link PL",
            occupation="Investigator",
            age=20,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_max=50,
            sanity_current=50,
            sanity_starting=50,
            access_scope="public",
        )
        image_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01"
            b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01"
            b"\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        CharacterImage.objects.create(
            character_sheet=character,
            image=SimpleUploadedFile(
                "sensitive-original-name.gif",
                image_bytes,
                content_type="image/gif",
            ),
            is_main=True,
        )

        self.client.force_login(owner)
        owner_page_response = self.client.get(reverse("character_detail_6th", kwargs={"character_id": character.id}))
        self.assertEqual(owner_page_response.status_code, 200)
        self.assertContains(
            owner_page_response, f'data-character-reference-url="/share/characters/{character.share_token}/view/"'
        )

        self.client.logout()

        normal_api_response = self.client.get(f"/api/accounts/character-sheets/{character.id}/")
        self.assertIn(normal_api_response.status_code, [302, 401, 403])

        old_public_api_response = self.client.get(f"/api/accounts/character-sheets/{character.id}/public/")
        self.assertEqual(old_public_api_response.status_code, 404)
        old_public_ccfolia_response = self.client.get(
            f"/api/accounts/character-sheets/{character.id}/public/ccfolia_json/"
        )
        self.assertEqual(old_public_ccfolia_response.status_code, 404)

        shared_api_response = self.client.get(f"/share/characters/{character.share_token}/")
        self.assertEqual(shared_api_response.status_code, 200)
        self.assertEqual(shared_api_response.json()["name"], "Direct Link PC")

        shared_ccfolia_response = self.client.get(f"/share/characters/{character.share_token}/ccfolia.json")
        self.assertEqual(shared_ccfolia_response.status_code, 200)
        self.assertEqual(shared_ccfolia_response.json()["kind"], "character")
        self.assertEqual(shared_ccfolia_response.json()["data"]["name"], "Direct Link PC")

        normal_page_response = self.client.get(reverse("character_detail_6th", kwargs={"character_id": character.id}))
        self.assertEqual(normal_page_response.status_code, 302)

        page_response = self.client.get(
            reverse("fixed-shared-character-view", kwargs={"share_token": character.share_token})
        )
        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "Direct Link PC")
        self.assertContains(page_response, "og:title")
        self.assertContains(page_response, "Direct Link PL")
        self.assertContains(
            page_response, f'data-character-ccfolia-json-url="/share/characters/{character.share_token}/ccfolia.json"'
        )
        self.assertContains(
            page_response, f'data-character-reference-url="/share/characters/{character.share_token}/view/"'
        )
        self.assertContains(page_response, 'id="characterImagesDownloadLink"')
        self.assertContains(page_response, 'id="ccfoliaExportLink"')
        self.assertNotContains(page_response, 'download="character-')
        self.assertNotContains(page_response, 'id="editButton"')
        self.assertNotContains(page_response, "characterImageFileNames")
        self.assertNotContains(page_response, "sensitive-original-name")
        self.assertNotContains(page_response, "character_images/")
        self.assertContains(
            page_response,
            f'<meta property="og:image" content="http://testserver/share/characters/{character.share_token}/preview-image/">',
        )

        preview_image_response = self.client.get(f"/share/characters/{character.share_token}/preview-image/")
        self.assertEqual(preview_image_response.status_code, 200)
        self.assertEqual(b"".join(preview_image_response.streaming_content), image_bytes)
        self.assertNotIn("sensitive-original-name", preview_image_response.get("Content-Disposition", ""))

        character.access_scope = "private"
        character.save(update_fields=["access_scope"])

        private_shared_api_response = self.client.get(f"/share/characters/{character.share_token}/")
        self.assertEqual(private_shared_api_response.status_code, 404)
        private_fixed_page_response = self.client.get(
            reverse("fixed-shared-character-view", kwargs={"share_token": character.share_token})
        )
        self.assertEqual(private_fixed_page_response.status_code, 404)


class GroupBasicTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="groupowner", email="owner@example.com", password="pass123", nickname="Group Owner"
        )

    def test_group_creation(self):
        """グループ作成のテスト"""
        group = Group.objects.create(name="Test Group", description="Test Description", created_by=self.user)
        self.assertEqual(group.name, "Test Group")
        self.assertEqual(group.created_by, self.user)

    def test_group_str_representation(self):
        """グループ文字列表現のテスト"""
        group = Group.objects.create(name="Test Group", created_by=self.user)
        self.assertEqual(str(group), "Test Group")

    def test_group_membership_creation(self):
        """グループメンバーシップ作成のテスト"""
        group = Group.objects.create(name="Test Group", created_by=self.user)
        membership = GroupMembership.objects.create(user=self.user, group=group, role="admin")
        self.assertEqual(membership.role, "admin")
        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.group, group)
