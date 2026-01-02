#!/usr/bin/env python3
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from django.test import Client
from accounts.models import CustomUser
from accounts.models import Group as CustomGroup, GroupMembership
from schedules.models import TRPGSession, SessionParticipant
from scenarios.models import Scenario, PlayHistory
from django.utils import timezone

# Create test client
client = Client()

# Create user
user = CustomUser.objects.create_user(username='testuser_export_manual', password='test123')

# Create group
group = CustomGroup.objects.create(name='Test Group 2', created_by=user)
GroupMembership.objects.create(user=user, group=group, role='admin')

# Login
client.force_login(user)

# Test JSON export
response = client.get('/api/accounts/export/statistics/', {'format': 'json'})
print(f'JSON response status: {response.status_code}')

# Test CSV export
response = client.get('/api/accounts/export/statistics/', {'format': 'csv'})
print(f'CSV response status: {response.status_code}')
if response.status_code != 200:
    print(f'CSV response content: {response.content[:200]}')
    print(f'CSV response headers: {response}')
    
# Clean up
user.delete()
group.delete()