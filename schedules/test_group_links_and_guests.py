from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group, GroupLink, GroupLinkShare, GroupMembership
from schedules.models import (
    GuestClaimAudit,
    GuestInvitation,
    HandoutInfo,
    SessionParticipant,
    TRPGSession,
)


class GroupLinkTestCase(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.source_admin = user_model.objects.create_user(
            username='source-admin',
            email='source-admin@example.com',
            password='pass123',
        )
        self.target_admin = user_model.objects.create_user(
            username='target-admin',
            email='target-admin@example.com',
            password='pass123',
        )
        self.target_member = user_model.objects.create_user(
            username='target-member',
            email='target-member@example.com',
            password='pass123',
        )
        self.source = Group.objects.create(
            name='Source Group', created_by=self.source_admin
        )
        self.target = Group.objects.create(
            name='Target Group', created_by=self.target_admin
        )
        GroupMembership.objects.create(
            group=self.target, user=self.target_member, role='member'
        )
        self.shared_session = TRPGSession.objects.create(
            title='Explicitly Shared Session',
            gm=self.source_admin,
            group=self.source,
            visibility='private',
            date=timezone.now() + timedelta(days=1),
        )
        self.private_session = TRPGSession.objects.create(
            title='Unshared Session',
            gm=self.source_admin,
            group=self.source,
            visibility='private',
            date=timezone.now() + timedelta(days=2),
        )

    def test_mutual_approval_and_explicit_share_boundary(self):
        self.client.force_authenticate(self.source_admin)
        requested = self.client.post(
            f'/api/groups/{self.source.pk}/links/',
            {'target_group_id': self.target.pk},
            format='json',
        )
        self.assertEqual(requested.status_code, status.HTTP_201_CREATED)
        link_id = requested.data['id']
        self.assertEqual(requested.data['status'], GroupLink.Status.PENDING)

        self.client.force_authenticate(self.target_admin)
        accepted = self.client.post(
            f'/api/groups/{self.target.pk}/links/{link_id}/accept/'
        )
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.source_admin)
        shared = self.client.post(
            f'/api/groups/{self.source.pk}/links/{link_id}/shares/',
            {
                'resource_type': GroupLinkShare.ResourceType.SESSION,
                'object_id': self.shared_session.pk,
            },
            format='json',
        )
        self.assertEqual(shared.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.target_member)
        sessions = self.client.get('/api/schedules/sessions/')
        results = sessions.data.get('results', sessions.data) if isinstance(
            sessions.data, dict
        ) else sessions.data
        session_ids = {item['id'] for item in results}
        self.assertIn(self.shared_session.pk, session_ids)
        self.assertNotIn(self.private_session.pk, session_ids)

        update = self.client.patch(
            f'/api/schedules/sessions/{self.shared_session.pk}/',
            {'title': 'Unauthorized change'},
            format='json',
        )
        self.assertEqual(update.status_code, status.HTTP_403_FORBIDDEN)
        self.shared_session.refresh_from_db()
        self.assertEqual(self.shared_session.title, 'Explicitly Shared Session')

    def test_only_target_admin_can_accept(self):
        link = GroupLink.objects.create(
            source_group=self.source,
            target_group=self.target,
            requested_by=self.source_admin,
        )
        self.client.force_authenticate(self.target_member)
        response = self.client.post(
            f'/api/groups/{self.target.pk}/links/{link.pk}/accept/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        link.refresh_from_db()
        self.assertEqual(link.status, GroupLink.Status.PENDING)


class GuestInvitationClaimTestCase(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.gm = user_model.objects.create_user(
            username='guest-gm',
            email='guest-gm@example.com',
            password='pass123',
        )
        self.claimant = user_model.objects.create_user(
            username='guest-claimant',
            email='guest-claimant@example.com',
            password='pass123',
        )
        self.other = user_model.objects.create_user(
            username='guest-other',
            email='guest-other@example.com',
            password='pass123',
        )
        self.group_admin = user_model.objects.create_user(
            username='guest-group-admin',
            email='guest-group-admin@example.com',
            password='pass123',
        )
        self.group = Group.objects.create(name='Guest Group', created_by=self.gm)
        GroupMembership.objects.create(
            group=self.group, user=self.group_admin, role='admin'
        )
        self.session = TRPGSession.objects.create(
            title='Guest Session',
            gm=self.gm,
            group=self.group,
            date=timezone.now() + timedelta(days=1),
        )

    def issue_and_respond(self):
        self.client.force_authenticate(self.gm)
        issued = self.client.post(
            f'/api/sessions/{self.session.pk}/guest-invitations/',
            {'expires_in_hours': 24},
            format='json',
        )
        self.assertEqual(issued.status_code, status.HTTP_201_CREATED)
        token = issued.data['token']
        invitation = GuestInvitation.objects.get(pk=issued.data['id'])
        self.assertNotEqual(invitation.token_digest, token)
        landing = self.client.get(issued.data['invitation_url'])
        self.assertEqual(landing.status_code, status.HTTP_200_OK)
        self.assertContains(landing, self.session.title)

        self.client.force_authenticate(user=None)
        responded = self.client.post(
            f'/api/guest-invitations/{token}/respond/',
            {
                'guest_name': 'Guest Alice',
                'player_slot': 1,
                'character_name': 'Alice Investigator',
                'character_sheet_url': 'https://example.com/alice',
            },
            format='json',
        )
        self.assertEqual(responded.status_code, status.HTTP_201_CREATED)
        self.assertEqual(responded.data['claim_token'], token)
        return invitation, SessionParticipant.objects.get(
            pk=responded.data['participant_id']
        ), token

    def test_claim_preserves_slot_character_and_handout_assignment(self):
        invitation, participant, token = self.issue_and_respond()
        handout = HandoutInfo.objects.create(
            session=self.session,
            participant=participant,
            title='Guest HO',
            content='secret',
            handout_number=1,
            assigned_player_slot=1,
        )

        self.client.force_authenticate(self.claimant)
        claimed = self.client.post(
            f'/api/participants/{participant.pk}/claim/',
            {'claim_token': token},
            format='json',
        )
        self.assertEqual(claimed.status_code, status.HTTP_200_OK)

        participant.refresh_from_db()
        handout.refresh_from_db()
        self.assertEqual(participant.user, self.claimant)
        self.assertEqual(participant.guest_name, '')
        self.assertEqual(participant.player_slot, 1)
        self.assertEqual(participant.character_name, 'Alice Investigator')
        self.assertEqual(handout.participant, participant)
        audit = GuestClaimAudit.objects.get(invitation=invitation)
        self.assertEqual(audit.guest_name, 'Guest Alice')
        self.assertEqual(audit.claimed_by, self.claimant)

        self.client.force_authenticate(self.gm)
        delete_response = self.client.delete(
            f'/api/schedules/sessions/{self.session.pk}/'
        )
        self.assertEqual(delete_response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(TRPGSession.objects.filter(pk=self.session.pk).exists())

    def test_guest_claim_requires_invitation_token(self):
        invitation, participant, token = self.issue_and_respond()

        self.client.force_authenticate(self.claimant)
        missing_token = self.client.post(f'/api/participants/{participant.pk}/claim/')
        self.assertEqual(missing_token.status_code, status.HTTP_403_FORBIDDEN)

        invalid_token = self.client.post(
            f'/api/participants/{participant.pk}/claim/',
            {'claim_token': 'wrong-token'},
            format='json',
        )
        self.assertEqual(invalid_token.status_code, status.HTTP_403_FORBIDDEN)

        participant.refresh_from_db()
        self.assertIsNone(participant.user_id)
        self.assertFalse(GuestClaimAudit.objects.filter(invitation=invitation).exists())

        valid_token = self.client.post(
            f'/api/participants/{participant.pk}/claim/',
            {'claim_token': token},
            format='json',
        )
        self.assertEqual(valid_token.status_code, status.HTTP_200_OK)

    def test_existing_participation_rejects_claim_without_partial_update(self):
        invitation, participant, token = self.issue_and_respond()
        SessionParticipant.objects.create(
            session=self.session,
            user=self.claimant,
            role='player',
            player_slot=2,
        )

        self.client.force_authenticate(self.claimant)
        response = self.client.post(
            f'/api/participants/{participant.pk}/claim/',
            {'claim_token': token},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        participant.refresh_from_db()
        self.assertIsNone(participant.user_id)
        self.assertFalse(
            GuestClaimAudit.objects.filter(invitation=invitation).exists()
        )

    def test_revoked_invitation_cannot_be_used(self):
        self.client.force_authenticate(self.gm)
        issued = self.client.post(
            f'/api/sessions/{self.session.pk}/guest-invitations/',
            format='json',
        )
        token = issued.data['token']
        revoked = self.client.delete(
            f'/api/sessions/{self.session.pk}/guest-invitations/{issued.data["id"]}/'
        )
        self.assertEqual(revoked.status_code, status.HTTP_204_NO_CONTENT)

        self.client.force_authenticate(user=None)
        response = self.client.post(
            f'/api/guest-invitations/{token}/respond/',
            {'guest_name': 'Late Guest'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    def test_expired_invitation_landing_does_not_expose_session_details(self):
        invitation, token = GuestInvitation.issue(
            session=self.session,
            created_by=self.gm,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.get(f'/guest-invitations/{token}/')

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertContains(response, 'この招待は期限切れ、失効済み、または使用済みです。', status_code=status.HTTP_410_GONE)
        self.assertNotContains(response, self.session.title, status_code=status.HTTP_410_GONE)
        self.assertFalse(invitation.is_active)

    def test_revoked_invitation_landing_does_not_expose_session_details(self):
        invitation, token = GuestInvitation.issue(
            session=self.session,
            created_by=self.gm,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=['revoked_at'])

        response = self.client.get(f'/guest-invitations/{token}/')

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertContains(response, 'この招待は期限切れ、失効済み、または使用済みです。', status_code=status.HTTP_410_GONE)
        self.assertNotContains(response, self.session.title, status_code=status.HTTP_410_GONE)

    def test_group_admin_can_issue_and_revoke_guest_invitation(self):
        self.client.force_authenticate(self.group_admin)

        issued = self.client.post(
            f'/api/sessions/{self.session.pk}/guest-invitations/',
            {'expires_in_hours': 24},
            format='json',
        )
        self.assertEqual(issued.status_code, status.HTTP_201_CREATED)
        invitation = GuestInvitation.objects.get(pk=issued.data['id'])
        self.assertEqual(invitation.created_by, self.group_admin)

        revoked = self.client.delete(
            f'/api/sessions/{self.session.pk}/guest-invitations/{invitation.pk}/'
        )
        self.assertEqual(revoked.status_code, status.HTTP_204_NO_CONTENT)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.revoked_at)

    def test_outsider_cannot_issue_guest_invitation(self):
        self.client.force_authenticate(self.other)

        response = self.client.post(
            f'/api/sessions/{self.session.pk}/guest-invitations/',
            {'expires_in_hours': 24},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
