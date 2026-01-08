from datetime import timedelta
import math

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import Group, GroupMembership, GroupInvitation
from accounts.character_models import CharacterSheet
from schedules.models import HandoutNotification, UserNotificationPreferences


User = get_user_model()


class GroupSearchAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='search_user',
            email='search@example.com',
            password='pass123',
            nickname='Search User'
        )
        self.owner = User.objects.create_user(
            username='owner_user',
            email='owner@example.com',
            password='pass123',
            nickname='Owner User'
        )
        self.client.force_authenticate(user=self.user)

        self.public_group = Group.objects.create(
            name='Arkham Seekers',
            description='Public investigation group',
            visibility='public',
            created_by=self.owner
        )
        GroupMembership.objects.create(user=self.owner, group=self.public_group, role='admin')

        self.private_group = Group.objects.create(
            name='Arkham Secret',
            description='Private group',
            visibility='private',
            created_by=self.owner
        )
        GroupMembership.objects.create(user=self.owner, group=self.private_group, role='admin')

    def test_public_group_search(self):
        response = self.client.get('/api/accounts/groups/search/?q=Arkham')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.public_group.id)

    def test_public_groups_filter(self):
        response = self.client.get('/api/accounts/groups/public/?q=Secret')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class GroupInvitationFlowAPITestCase(APITestCase):
    def setUp(self):
        self.inviter = User.objects.create_user(
            username='inviter',
            email='inviter@example.com',
            password='pass123',
            nickname='Inviter'
        )
        self.invitee1 = User.objects.create_user(
            username='invitee1',
            email='invitee1@example.com',
            password='pass123',
            nickname='Invitee1'
        )
        self.invitee2 = User.objects.create_user(
            username='invitee2',
            email='invitee2@example.com',
            password='pass123',
            nickname='Invitee2'
        )
        self.group = Group.objects.create(
            name='Invite Group',
            visibility='private',
            created_by=self.inviter
        )
        GroupMembership.objects.create(user=self.inviter, group=self.group, role='admin')

    def test_bulk_invite(self):
        self.client.force_authenticate(user=self.inviter)
        response = self.client.post(
            f'/api/accounts/groups/{self.group.id}/invite/',
            {
                'invitee_ids': [self.invitee1.id, self.invitee2.id],
                'message': 'Join us'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(GroupInvitation.objects.filter(group=self.group).count(), 2)

    def test_bulk_invite_skips_members(self):
        GroupMembership.objects.create(user=self.invitee2, group=self.group, role='member')
        self.client.force_authenticate(user=self.inviter)
        response = self.client.post(
            f'/api/accounts/groups/{self.group.id}/invite/',
            {
                'invitee_ids': [self.invitee1.id, self.invitee2.id],
                'message': 'Join us'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['count'], 1)
        skipped = response.data['skipped']
        self.assertTrue(any(item['reason'] == 'already_member' for item in skipped))

    def test_invitation_expired_on_accept(self):
        invitation = GroupInvitation.objects.create(
            group=self.group,
            inviter=self.inviter,
            invitee=self.invitee1,
            message='Join us'
        )
        invitation.created_at = timezone.now() - timedelta(days=8)
        invitation.save(update_fields=['created_at'])

        self.client.force_authenticate(user=self.invitee1)
        response = self.client.post(f'/api/accounts/invitations/{invitation.id}/accept/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'expired')
        self.assertIsNotNone(invitation.responded_at)

    def test_invitation_list_marks_expired(self):
        invitation = GroupInvitation.objects.create(
            group=self.group,
            inviter=self.inviter,
            invitee=self.invitee1,
            message='Join us'
        )
        invitation.created_at = timezone.now() - timedelta(days=8)
        invitation.save(update_fields=['created_at'])

        self.client.force_authenticate(user=self.invitee1)
        response = self.client.get('/api/accounts/invitations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['status'], 'expired')


class GroupInvitationNotificationTestCase(APITestCase):
    """グループ招待時の通知生成テスト"""

    def setUp(self):
        self.inviter = User.objects.create_user(
            username='inviter_notify',
            email='inviter_notify@example.com',
            password='pass123',
            nickname='InviterNotify'
        )
        self.invitee = User.objects.create_user(
            username='invitee_notify',
            email='invitee_notify@example.com',
            password='pass123',
            nickname='InviteeNotify'
        )
        self.group = Group.objects.create(
            name='Notify Group',
            visibility='private',
            created_by=self.inviter
        )
        GroupMembership.objects.create(user=self.inviter, group=self.group, role='admin')
        self.client.force_authenticate(user=self.inviter)

    def test_notification_created_on_invite(self):
        response = self.client.post(
            f'/api/accounts/groups/{self.group.id}/invite/',
            {'user_id': self.invitee.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = HandoutNotification.objects.filter(
            recipient=self.invitee,
            notification_type='group_invitation'
        ).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.sender, self.inviter)
        self.assertEqual(notification.metadata.get('group_id'), self.group.id)
        self.assertEqual(notification.metadata.get('group_name'), self.group.name)

    def test_notification_respects_user_preferences(self):
        prefs = UserNotificationPreferences.get_or_create_for_user(self.invitee)
        prefs.group_notifications_enabled = False
        prefs.save()

        response = self.client.post(
            f'/api/accounts/groups/{self.group.id}/invite/',
            {'user_id': self.invitee.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(
            HandoutNotification.objects.filter(
                recipient=self.invitee,
                notification_type='group_invitation'
            ).exists()
        )


class GroupMemberRoleManagementTestCase(APITestCase):
    """グループのメンバー権限（管理者/メンバー）変更テスト"""

    def setUp(self):
        self.owner = User.objects.create_user(
            username='role_owner',
            email='role_owner@example.com',
            password='pass123',
            nickname='RoleOwner'
        )
        self.member = User.objects.create_user(
            username='role_member',
            email='role_member@example.com',
            password='pass123',
            nickname='RoleMember'
        )

        self.group = Group.objects.create(
            name='Role Group',
            visibility='private',
            created_by=self.owner
        )
        GroupMembership.objects.create(user=self.owner, group=self.group, role='admin')
        GroupMembership.objects.create(user=self.member, group=self.group, role='member')

    def test_admin_can_promote_and_demote_member(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f'/api/accounts/groups/{self.group.id}/set_member_role/',
            {'user_id': self.member.id, 'role': 'admin'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            GroupMembership.objects.filter(group=self.group, user=self.member, role='admin').exists()
        )

        response = self.client.post(
            f'/api/accounts/groups/{self.group.id}/set_member_role/',
            {'user_id': self.member.id, 'role': 'member'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            GroupMembership.objects.filter(group=self.group, user=self.member, role='member').exists()
        )

    def test_non_admin_cannot_change_roles(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            f'/api/accounts/groups/{self.group.id}/set_member_role/',
            {'user_id': self.member.id, 'role': 'admin'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_demote_creator(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/accounts/groups/{self.group.id}/set_member_role/',
            {'user_id': self.owner.id, 'role': 'member'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GroupLeaveSafetyTestCase(APITestCase):
    """退出時の安全対策（作成者/管理者）テスト"""

    def setUp(self):
        self.owner = User.objects.create_user(
            username='leave_owner',
            email='leave_owner@example.com',
            password='pass123',
            nickname='LeaveOwner'
        )
        self.member = User.objects.create_user(
            username='leave_member',
            email='leave_member@example.com',
            password='pass123',
            nickname='LeaveMember'
        )

        self.group = Group.objects.create(
            name='Leave Group',
            visibility='private',
            created_by=self.owner
        )
        GroupMembership.objects.create(user=self.owner, group=self.group, role='admin')
        GroupMembership.objects.create(user=self.member, group=self.group, role='member')

    def test_creator_cannot_leave(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f'/api/accounts/groups/{self.group.id}/leave/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(GroupMembership.objects.filter(group=self.group, user=self.owner).exists())

    def test_member_can_leave(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(f'/api/accounts/groups/{self.group.id}/leave/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(GroupMembership.objects.filter(group=self.group, user=self.member).exists())


class GroupMemberCharactersAPITestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='pass123',
            nickname='Admin User'
        )
        self.member = User.objects.create_user(
            username='member_user',
            email='member@example.com',
            password='pass123',
            nickname='Member User'
        )
        self.non_member = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='pass123',
            nickname='Outsider'
        )

        self.group = Group.objects.create(
            name='Character Group',
            visibility='private',
            created_by=self.admin
        )
        GroupMembership.objects.create(user=self.admin, group=self.group, role='admin')
        GroupMembership.objects.create(user=self.member, group=self.group, role='member')

        self.create_character(self.admin, 'Admin Public', is_public=True)
        self.create_character(self.admin, 'Admin Private', is_public=False)
        self.create_character(self.member, 'Member Public', is_public=True)
        self.create_character(self.member, 'Member Private', is_public=False)

    def create_character(self, user, name, is_public):
        stats = {
            'str_value': 10,
            'con_value': 12,
            'pow_value': 11,
            'dex_value': 10,
            'app_value': 9,
            'siz_value': 11,
            'int_value': 12,
            'edu_value': 13
        }
        hp_max = math.ceil((stats['con_value'] + stats['siz_value']) / 2)
        mp_max = stats['pow_value']
        san_start = stats['pow_value'] * 5

        return CharacterSheet.objects.create(
            user=user,
            edition='6th',
            name=name,
            age=25,
            **stats,
            hit_points_max=hp_max,
            hit_points_current=hp_max,
            magic_points_max=mp_max,
            magic_points_current=mp_max,
            sanity_starting=san_start,
            sanity_max=99,
            sanity_current=san_start,
            is_public=is_public,
            is_active=True
        )

    def test_member_characters_visibility(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'/api/accounts/groups/{self.group.id}/member_characters/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        admin_entry = next(item for item in data if item['user_id'] == self.admin.id)
        member_entry = next(item for item in data if item['user_id'] == self.member.id)

        self.assertEqual(len(admin_entry['characters']), 2)
        self.assertEqual(len(member_entry['characters']), 1)
        self.assertTrue(member_entry['characters'][0]['is_public'])

    def test_member_characters_non_member_forbidden(self):
        self.client.force_authenticate(user=self.non_member)
        response = self.client.get(f'/api/accounts/groups/{self.group.id}/member_characters/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GroupAdminActionsAPITestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_action_user',
            email='admin_action@example.com',
            password='pass123',
            nickname='Admin Action'
        )
        self.member = User.objects.create_user(
            username='member_action_user',
            email='member_action@example.com',
            password='pass123',
            nickname='Member Action'
        )
        self.group = Group.objects.create(
            name='Action Group',
            description='Initial description',
            visibility='private',
            created_by=self.admin
        )
        GroupMembership.objects.create(user=self.admin, group=self.group, role='admin')
        GroupMembership.objects.create(user=self.member, group=self.group, role='member')

    def test_admin_can_update_group(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/accounts/groups/{self.group.id}/',
            {
                'name': 'Updated Group',
                'description': 'Updated description',
                'visibility': 'public'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.name, 'Updated Group')
        self.assertEqual(self.group.description, 'Updated description')
        self.assertEqual(self.group.visibility, 'public')

    def test_member_cannot_update_group(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.patch(
            f'/api/accounts/groups/{self.group.id}/',
            {'name': 'Blocked Update'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_group(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/accounts/groups/{self.group.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group.objects.filter(id=self.group.id).exists())

    def test_member_cannot_delete_group(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.delete(f'/api/accounts/groups/{self.group.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_remove_member_by_user_id(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(
            f'/api/accounts/groups/{self.group.id}/remove_member/',
            data={'user_id': self.member.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            GroupMembership.objects.filter(user=self.member, group=self.group).exists()
        )

    def test_remove_member_requires_user_identifier(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(
            f'/api/accounts/groups/{self.group.id}/remove_member/',
            data={},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_cannot_remove_member(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.delete(
            f'/api/accounts/groups/{self.group.id}/remove_member/',
            data={'user_id': self.admin.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
