import io
import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from PIL import Image

from accounts.models import Group, GroupMembership
from scenarios.models import Scenario
from .models import HandoutInfo, SessionTemplate, SessionTemplateHandout, SessionTemplateImage

User = get_user_model()


class SessionTemplateApiTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123',
            nickname='User 1',
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123',
            nickname='User 2',
        )

        self.group1 = Group.objects.create(
            name='Group 1',
            created_by=self.user1,
        )
        GroupMembership.objects.create(user=self.user1, group=self.group1, role='admin')

        self.group2 = Group.objects.create(
            name='Group 2',
            created_by=self.user2,
        )
        GroupMembership.objects.create(user=self.user2, group=self.group2, role='admin')

        self.scenario_user1 = Scenario.objects.create(
            title='Scenario 1',
            created_by=self.user1,
            game_system='coc',
        )
        self.scenario_user2 = Scenario.objects.create(
            title='Scenario 2',
            created_by=self.user2,
            game_system='coc',
        )

    def create_test_image(self, name='template.png'):
        file = io.BytesIO()
        image = Image.new('RGB', (64, 64), color='blue')
        image.save(file, 'PNG')
        file.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=file.getvalue(),
            content_type='image/png',
        )

    def test_list_requires_authentication(self):
        response = self.client.get('/api/schedules/session-templates/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_list_returns_only_own_templates(self):
        SessionTemplate.objects.create(owner=self.user1, name='Mine')
        SessionTemplate.objects.create(owner=self.user2, name='Theirs')

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/schedules/session-templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Mine')

    def test_create_validates_group_membership(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            '/api/schedules/session-templates/',
            {
                'name': 'Template',
                'group': self.group2.id,  # not a member
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('group', response.json())

    def test_create_validates_scenario_owner(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            '/api/schedules/session-templates/',
            {
                'name': 'Template',
                'scenario': self.scenario_user2.id,  # not owned
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('scenario', response.json())

    def test_create_update_delete(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            '/api/schedules/session-templates/',
            {
                'name': 'Template',
                'group': self.group1.id,
                'duration_minutes': 240,
                'location': 'Online',
                'visibility': 'group',
                'coc_edition': '6th',
                'description': 'Hello',
                'youtube_url': '',
                'scenario': self.scenario_user1.id,
                'copy_handouts_to_session': True,
                'handout_templates': [
                    {
                        'title': 'HO1',
                        'content': 'secret',
                        'recommended_skills': '目星',
                        'is_secret': True,
                        'handout_number': 1,
                        'assigned_player_slot': 1,
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        template_id = response.json()['id']
        self.assertEqual(response.json()['duration_hhmm'], '0400')
        self.assertTrue(response.json()['copy_handouts_to_session'])
        self.assertEqual(len(response.json()['handout_templates']), 1)

        response = self.client.patch(
            f'/api/schedules/session-templates/{template_id}/',
            {'name': 'Template Updated'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['name'], 'Template Updated')

        response = self.client.delete(f'/api/schedules/session-templates/{template_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_name_must_be_unique_per_owner(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.post(
            '/api/schedules/session-templates/',
            {'name': 'Template'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            '/api/schedules/session-templates/',
            {'name': 'template'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.json())

    def test_upload_images_to_template(self):
        self.client.force_authenticate(user=self.user1)
        template = SessionTemplate.objects.create(owner=self.user1, name='Template')

        response = self.client.post(
            f'/api/schedules/session-templates/{template.id}/images/',
            {'images': [self.create_test_image('one.png'), self.create_test_image('two.png')]},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(SessionTemplateImage.objects.filter(session_template=template).count(), 2)

    def test_upload_images_rejects_non_image_file(self):
        self.client.force_authenticate(user=self.user1)
        template = SessionTemplate.objects.create(owner=self.user1, name='Template')
        invalid_file = SimpleUploadedFile(
            name='not-image.txt',
            content=b'not an image',
            content_type='text/plain',
        )

        response = self.client.post(
            f'/api/schedules/session-templates/{template.id}/images/',
            {'images': [invalid_file]},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SessionTemplateImage.objects.filter(session_template=template).count(), 0)

    def test_deleting_template_removes_uploaded_image_file(self):
        self.client.force_authenticate(user=self.user1)
        template = SessionTemplate.objects.create(owner=self.user1, name='Template')
        image = SessionTemplateImage.objects.create(
            session_template=template,
            image=self.create_test_image(),
            title='Visual',
        )
        image_path = image.image.path
        self.assertTrue(os.path.exists(image_path))

        response = self.client.delete(f'/api/schedules/session-templates/{template.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(os.path.exists(image_path))

    def test_create_session_from_template_copies_images_and_handouts(self):
        self.client.force_authenticate(user=self.user1)
        template = SessionTemplate.objects.create(
            owner=self.user1,
            name='Campaign Template',
            group=self.group1,
            duration_minutes=240,
            location='Online',
            visibility='group',
            copy_handouts_to_session=True,
        )
        SessionTemplateHandout.objects.create(
            session_template=template,
            title='HO1',
            content='secret mission',
            recommended_skills='図書館',
            is_secret=True,
            handout_number=1,
            assigned_player_slot=1,
        )
        SessionTemplateImage.objects.create(
            session_template=template,
            image=self.create_test_image(),
            title='Visual',
        )

        response = self.client.post(
            '/api/schedules/sessions/',
            {
                'title': 'Generated Session',
                'group': self.group1.id,
                'session_template': template.id,
                'duration_minutes': 240,
                'visibility': 'group',
                'coc_edition': '6th',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        session_id = response.json()['id']
        handout = HandoutInfo.objects.get(session_id=session_id, handout_number=1)
        self.assertTrue(handout.is_secret)
        self.assertEqual(handout.assigned_player_slot, 1)
        self.assertIsNone(handout.participant.user)
        self.assertTrue(handout.participant.guest_name.startswith('[template]'))
        self.assertEqual(response.json()['images_detail'][0]['title'], 'Visual')

    def test_joining_slot_rebinds_template_handout_to_player(self):
        GroupMembership.objects.get_or_create(user=self.user2, group=self.group1, defaults={'role': 'member'})

        self.client.force_authenticate(user=self.user1)
        template = SessionTemplate.objects.create(
            owner=self.user1,
            name='HO Template',
            group=self.group1,
            visibility='group',
            copy_handouts_to_session=True,
        )
        SessionTemplateHandout.objects.create(
            session_template=template,
            title='HO2',
            content='for player 2',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2,
        )

        response = self.client.post(
            '/api/schedules/sessions/',
            {
                'title': 'Slot Session',
                'group': self.group1.id,
                'session_template': template.id,
                'visibility': 'group',
                'coc_edition': '6th',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.json()['id']

        self.client.force_authenticate(user=self.user2)
        join_response = self.client.post(
            f'/api/schedules/sessions/{session_id}/join/',
            {'player_slot': 2},
            format='json',
        )
        self.assertEqual(join_response.status_code, status.HTTP_201_CREATED)

        handout = HandoutInfo.objects.get(session_id=session_id, handout_number=2)
        self.assertEqual(handout.participant.user, self.user2)

    def test_updating_player_slot_rebinds_template_handout(self):
        user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='pass123',
            nickname='User 3',
        )
        GroupMembership.objects.get_or_create(user=self.user2, group=self.group1, defaults={'role': 'member'})
        GroupMembership.objects.get_or_create(user=user3, group=self.group1, defaults={'role': 'member'})

        self.client.force_authenticate(user=self.user1)
        template = SessionTemplate.objects.create(
            owner=self.user1,
            name='Rebind Template',
            group=self.group1,
            visibility='group',
            copy_handouts_to_session=True,
        )
        SessionTemplateHandout.objects.create(
            session_template=template,
            title='HO1',
            content='for slot 1',
            is_secret=True,
            handout_number=1,
            assigned_player_slot=1,
        )

        response = self.client.post(
            '/api/schedules/sessions/',
            {
                'title': 'Rebind Session',
                'group': self.group1.id,
                'session_template': template.id,
                'visibility': 'group',
                'coc_edition': '6th',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.json()['id']

        self.client.force_authenticate(user=self.user2)
        join_response = self.client.post(
            f'/api/schedules/sessions/{session_id}/join/',
            {'player_slot': 1},
            format='json',
        )
        self.assertEqual(join_response.status_code, status.HTTP_201_CREATED)
        participant_id = join_response.json()['id']

        handout = HandoutInfo.objects.get(session_id=session_id, handout_number=1)
        self.assertEqual(handout.participant.user, self.user2)

        update_response = self.client.patch(
            f'/api/schedules/participants/{participant_id}/',
            {'player_slot': 2},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        handout.refresh_from_db()
        self.assertIsNone(handout.participant.user)
        self.assertTrue(handout.participant.guest_name.startswith('[template]'))

        self.client.force_authenticate(user=user3)
        join_response = self.client.post(
            f'/api/schedules/sessions/{session_id}/join/',
            {'player_slot': 1},
            format='json',
        )
        self.assertEqual(join_response.status_code, status.HTTP_201_CREATED)

        handout.refresh_from_db()
        self.assertEqual(handout.participant.user, user3)
