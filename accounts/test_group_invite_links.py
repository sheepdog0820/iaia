from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership


User = get_user_model()


class GroupInviteLinkAPITestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='group_link_admin',
            email='group_link_admin@example.com',
            password='pass123',
            nickname='Group Link Admin'
        )
        self.member = User.objects.create_user(
            username='group_link_member',
            email='group_link_member@example.com',
            password='pass123',
            nickname='Group Link Member'
        )
        self.invitee = User.objects.create_user(
            username='group_link_invitee',
            email='group_link_invitee@example.com',
            password='pass123',
            nickname='Group Link Invitee'
        )
        self.group = Group.objects.create(
            name='Invite Link Private Group',
            visibility='private',
            created_by=self.admin
        )
        GroupMembership.objects.create(user=self.admin, group=self.group, role='admin')
        GroupMembership.objects.create(user=self.member, group=self.group, role='member')

    def issue_link(self, user=None, **payload):
        self.client.force_authenticate(user=user or self.admin)
        body = {'expires_in_hours': 24, 'max_uses': 2}
        body.update(payload)
        return self.client.post(
            f'/api/accounts/groups/{self.group.id}/invite-links/',
            body,
            format='json'
        )

    def test_admin_can_issue_invite_link_for_private_group(self):
        response = self.issue_link()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('/group-invitations/', response.data['invitation_url'])
        self.assertEqual(response.data['group'], self.group.id)
        self.assertEqual(response.data['max_uses'], 2)
        self.assertEqual(response.data['use_count'], 0)
        self.assertNotIn('token_digest', response.data)

    def test_non_admin_cannot_issue_invite_link(self):
        response = self.issue_link(user=self.member)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_can_view_invite_landing_page(self):
        issued = self.issue_link()
        token = issued.data['token']
        self.client.force_authenticate(user=None)

        response = self.client.get(f'/group-invitations/{token}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.group.name)

    def test_login_required_to_join_with_invite_link(self):
        issued = self.issue_link()
        token = issued.data['token']
        self.client.force_authenticate(user=None)

        response = self.client.post(f'/api/group-invitations/{token}/join/')

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        )
        self.assertFalse(
            GroupMembership.objects.filter(user=self.invitee, group=self.group).exists()
        )

    def test_authenticated_user_can_join_private_group_with_invite_link(self):
        issued = self.issue_link()
        token = issued.data['token']
        self.client.force_authenticate(user=self.invitee)

        response = self.client.post(f'/api/group-invitations/{token}/join/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            GroupMembership.objects.filter(user=self.invitee, group=self.group).exists()
        )
        self.assertEqual(response.data['group'], self.group.id)
        self.assertEqual(response.data['use_count'], 1)

    def test_invite_link_respects_max_uses(self):
        issued = self.issue_link(max_uses=1)
        token = issued.data['token']
        self.client.force_authenticate(user=self.invitee)
        first = self.client.post(f'/api/group-invitations/{token}/join/')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        other = User.objects.create_user(username='group_link_other', password='pass123')
        self.client.force_authenticate(user=other)
        second = self.client.post(f'/api/group-invitations/{token}/join/')

        self.assertEqual(second.status_code, status.HTTP_410_GONE)
        self.assertFalse(
            GroupMembership.objects.filter(user=other, group=self.group).exists()
        )

    def test_revoked_invite_link_cannot_be_used(self):
        issued = self.issue_link()
        link_id = issued.data['id']
        token = issued.data['token']
        self.client.force_authenticate(user=self.admin)
        revoke = self.client.delete(
            f'/api/accounts/groups/{self.group.id}/invite-links/{link_id}/'
        )
        self.assertEqual(revoke.status_code, status.HTTP_204_NO_CONTENT)

        self.client.force_authenticate(user=self.invitee)
        response = self.client.post(f'/api/group-invitations/{token}/join/')

        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    def test_expired_invite_link_cannot_be_used(self):
        issued = self.issue_link()
        token = issued.data['token']
        from accounts.models import GroupInviteLink
        link = GroupInviteLink.objects.get(pk=issued.data['id'])
        link.expires_at = timezone.now() - timedelta(hours=1)
        link.save(update_fields=['expires_at'])

        self.client.force_authenticate(user=self.invitee)
        response = self.client.post(f'/api/group-invitations/{token}/join/')

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
