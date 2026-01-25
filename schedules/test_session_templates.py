from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership
from scenarios.models import Scenario
from .models import SessionTemplate

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
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        template_id = response.json()['id']

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
