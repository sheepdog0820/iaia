from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, Group, GroupMembership
from .character_models import CharacterSheet
from schedules.models import TRPGSession, SessionParticipant

User = get_user_model()


class BasicAccountsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='basicuser',
            email='basic@example.com',
            password='basicpass123',
            nickname='Basic User'
        )

    def test_custom_user_model(self):
        """カスタムユーザーモデルのテスト"""
        self.assertIsInstance(self.user, CustomUser)
        self.assertEqual(self.user.email, 'basic@example.com')
        self.assertEqual(self.user.nickname, 'Basic User')

    def test_user_str_representation(self):
        """ユーザー文字列表現のテスト"""
        self.assertEqual(str(self.user), 'Basic User')

    def test_login_view(self):
        """ログインビューのテスト"""
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)

    def test_signup_view(self):
        """サインアップビューのテスト"""
        response = self.client.get('/accounts/signup/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_view_unauthenticated(self):
        """未認証ダッシュボードビューのテスト"""
        response = self.client.get('/accounts/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_dashboard_view_authenticated(self):
        """認証済みダッシュボードビューのテスト"""
        self.client.force_login(self.user)
        response = self.client.get('/accounts/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_profile_edit_saves_trpg_introduction_sheet(self):
        """プロフィール編集でTRPG自己紹介シートが保存されること"""
        self.client.force_login(self.user)

        response = self.client.post('/accounts/profile/edit/', data={
            'nickname': 'Updated User',
            'email': 'basic@example.com',
            'first_name': '太郎',
            'last_name': '田中',
            'trpg_history': 'CoC中心に遊んでいます',

            'trpg_env': ['online'],
            'trpg_tools': 'Discord / CCFOLIA',

            'trpg_systems_played': ['coc6'],
            'trpg_systems_favorite': ['coc6'],

            'trpg_scenario_structure': 'semi_free',
            'trpg_loss_preference': 'conditional',
            'trpg_loss_preference_note': 'KPと相談したい',

            'trpg_ng_expression': ['gore'],
            'trpg_ng_share_method': 'kp_only',

            'trpg_free_comment': 'よろしくお願いします',
            'trpg_profile_visibility': 'participants',
        })
        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        sheet = self.user.trpg_introduction_sheet

        self.assertEqual(sheet.get('basic', {}).get('environment'), ['online'])
        self.assertEqual(sheet.get('basic', {}).get('tools'), 'Discord / CCFOLIA')
        self.assertEqual(sheet.get('systems', {}).get('played'), ['coc6'])
        self.assertEqual(sheet.get('scenario', {}).get('loss'), 'conditional')
        self.assertEqual(sheet.get('ng', {}).get('expression'), ['gore'])
        self.assertEqual(sheet.get('visibility'), 'participants')

    def test_user_profile_view_requires_shared_group(self):
        """グループメンバーのプロフィール参照は共通グループが必要"""
        owner = User.objects.create_user(
            username='owneruser',
            email='owner@example.com',
            password='pass1234',
            nickname='Owner User',
        )
        other = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='pass1234',
            nickname='Other User',
        )
        outsider = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='pass1234',
            nickname='Outsider',
        )

        group = Group.objects.create(name='Shared Group', created_by=owner)
        GroupMembership.objects.create(user=owner, group=group, role='admin')
        GroupMembership.objects.create(user=other, group=group, role='member')

        url = f'/accounts/users/{other.id}/profile/'

        self.client.force_login(outsider)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.force_login(owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, other.email)

    def test_character_detail_api_allows_session_gm(self):
        """ログイン済みユーザーは他人のキャラも参照できる"""
        gm = User.objects.create_user(
            username='gmuser',
            email='gm@example.com',
            password='pass1234',
            nickname='GM User',
        )
        player = User.objects.create_user(
            username='playeruser',
            email='player@example.com',
            password='pass1234',
            nickname='Player User',
        )
        outsider = User.objects.create_user(
            username='outsideruser',
            email='outsider@example.com',
            password='pass1234',
            nickname='Outsider User',
        )

        group = Group.objects.create(name='Session Group', created_by=gm)
        GroupMembership.objects.create(user=gm, group=group, role='admin')
        GroupMembership.objects.create(user=player, group=group, role='member')

        character = CharacterSheet.objects.create(
            user=player,
            edition='6th',
            name='Test PC',
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
            is_public=False,
        )

        session = TRPGSession.objects.create(
            title='Test Session',
            description='',
            date=timezone.now() + timedelta(days=1),
            location='オンライン',
            gm=gm,
            group=group,
            status='planned',
            visibility='private',
            duration_minutes=60,
        )
        SessionParticipant.objects.create(
            session=session,
            user=player,
            role='player',
            player_slot=1,
            character_sheet=character,
        )

        self.client.force_login(gm)
        response = self.client.get(f'/api/accounts/character-sheets/{character.id}/')
        self.assertEqual(response.status_code, 200)

        self.client.force_login(player)
        response = self.client.get(f'/api/accounts/character-sheets/{character.id}/')
        self.assertEqual(response.status_code, 200)

        self.client.force_login(outsider)
        response = self.client.get(f'/api/accounts/character-sheets/{character.id}/')
        self.assertEqual(response.status_code, 200)


class GroupBasicTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='groupowner',
            email='owner@example.com',
            password='pass123',
            nickname='Group Owner'
        )

    def test_group_creation(self):
        """グループ作成のテスト"""
        group = Group.objects.create(
            name='Test Group',
            description='Test Description',
            created_by=self.user
        )
        self.assertEqual(group.name, 'Test Group')
        self.assertEqual(group.created_by, self.user)

    def test_group_str_representation(self):
        """グループ文字列表現のテスト"""
        group = Group.objects.create(
            name='Test Group',
            created_by=self.user
        )
        self.assertEqual(str(group), 'Test Group')

    def test_group_membership_creation(self):
        """グループメンバーシップ作成のテスト"""
        group = Group.objects.create(
            name='Test Group',
            created_by=self.user
        )
        membership = GroupMembership.objects.create(
            user=self.user,
            group=group,
            role='admin'
        )
        self.assertEqual(membership.role, 'admin')
        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.group, group)
