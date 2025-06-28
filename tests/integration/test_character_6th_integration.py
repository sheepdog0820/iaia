"""
Integration tests for Call of Cthulhu 6th Edition Character Sheet

Tests the complete integration between:
- Models
- Views/API
- Serializers
- Permissions
- Database transactions
"""

from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import json
from concurrent.futures import ThreadPoolExecutor
import time

from accounts.character_models import (
    CharacterSheet, CharacterSheet6th, CharacterSkill, 
    CharacterEquipment, CharacterBackground, GrowthRecord,
    CharacterDiceRollSetting, CharacterImage
)
from schedules.models import TRPGSession, SessionParticipant

User = get_user_model()


class Character6thFullWorkflowIntegrationTest(TransactionTestCase):
    """Test complete character lifecycle from creation to retirement"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='player1',
            password='testpass123',
            email='player1@example.com'
        )
        self.gm = User.objects.create_user(
            username='gamemaster',
            password='gmpass123',
            email='gm@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
    def test_complete_character_lifecycle(self):
        """Test character from creation through multiple sessions to retirement"""
        
        # === Phase 1: Character Creation ===
        print("\n=== Phase 1: Character Creation ===")
        
        character_data = {
            'name': '山田太郎',
            'age': 32,
            'gender': 'male',
            'occupation': '私立探偵',
            'birthplace': '東京都',
            'residence': '横浜市',
            'str_value': 14,
            'con_value': 13,
            'pow_value': 15,
            'dex_value': 12,
            'app_value': 11,
            'siz_value': 16,
            'int_value': 17,
            'edu_value': 16
        }
        
        response = self.client.post('/api/characters/create_6th_edition/', character_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character_id = response.data['id']
        print(f"Created character: {response.data['name']} (ID: {character_id})")
        
        # Verify calculations
        character = CharacterSheet.objects.get(id=character_id)
        char_6th = CharacterSheet6th.objects.get(character_sheet=character)
        
        self.assertEqual(character.hp_max, 15)  # (CON:13 + SIZ:16) / 2 = 14.5 -> 15
        self.assertEqual(character.mp_max, 15)  # POW:15
        self.assertEqual(character.san_max, 75)  # POW:15 × 5
        self.assertEqual(char_6th.idea_roll, 85)  # INT:17 × 5
        self.assertEqual(char_6th.luck_roll, 75)  # POW:15 × 5
        self.assertEqual(char_6th.know_roll, 80)  # EDU:16 × 5
        self.assertEqual(char_6th.damage_bonus, "+1D4")  # STR:14 + SIZ:16 = 30
        
        # === Phase 2: Skill Allocation ===
        print("\n=== Phase 2: Skill Allocation ===")
        
        # Check available points
        response = self.client.get(f'/api/characters/{character_id}/skill_points_summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        occupation_points = response.data['occupation_points']['total']
        hobby_points = response.data['hobby_points']['total']
        print(f"Available points - Occupation: {occupation_points}, Hobby: {hobby_points}")
        
        # Allocate skills
        skills_data = {
            'skills': [
                # Investigation skills for private detective
                {'skill_name': '目星', 'base_value': 25, 'occupation_points': 50, 'interest_points': 0},
                {'skill_name': '聞き耳', 'base_value': 25, 'occupation_points': 45, 'interest_points': 0},
                {'skill_name': '図書館', 'base_value': 25, 'occupation_points': 40, 'interest_points': 0},
                {'skill_name': '心理学', 'base_value': 5, 'occupation_points': 35, 'interest_points': 10},
                {'skill_name': '追跡', 'base_value': 10, 'occupation_points': 30, 'interest_points': 0},
                {'skill_name': '法律', 'base_value': 5, 'occupation_points': 25, 'interest_points': 0},
                {'skill_name': '写真術', 'base_value': 10, 'occupation_points': 20, 'interest_points': 0},
                # Combat skills
                {'skill_name': '拳銃', 'base_value': 20, 'occupation_points': 30, 'interest_points': 10},
                {'skill_name': '回避', 'base_value': 24, 'occupation_points': 0, 'interest_points': 26},  # DEX×2
                # Social skills
                {'skill_name': '説得', 'base_value': 15, 'occupation_points': 25, 'interest_points': 10},
                {'skill_name': '信用', 'base_value': 15, 'occupation_points': 20, 'interest_points': 0},
                # Other useful skills
                {'skill_name': '応急手当', 'base_value': 30, 'occupation_points': 0, 'interest_points': 20},
                {'skill_name': '運転(自動車)', 'base_value': 20, 'occupation_points': 0, 'interest_points': 30},
                {'skill_name': 'コンピューター', 'base_value': 1, 'occupation_points': 0, 'interest_points': 24},
            ]
        }
        
        response = self.client.post(
            f'/api/characters/{character_id}/batch_allocate_skill_points/',
            skills_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(f"Allocated {len(skills_data['skills'])} skills")
        
        # Verify point usage
        response = self.client.get(f'/api/characters/{character_id}/skill_points_summary/')
        self.assertEqual(response.data['occupation_points']['used'], 320)
        self.assertEqual(response.data['hobby_points']['used'], 120)
        
        # === Phase 3: Equipment and Background ===
        print("\n=== Phase 3: Equipment and Background ===")
        
        # Add equipment
        equipment_list = [
            {
                'equipment_type': 'weapon',
                'name': '.38リボルバー',
                'damage': '1D10',
                'attacks_per_round': 2,
                'weight': '0.5',
                'quantity': 1
            },
            {
                'equipment_type': 'weapon',
                'name': 'ナイフ',
                'damage': '1D4+db',
                'attacks_per_round': 1,
                'weight': '0.2',
                'quantity': 1
            },
            {
                'equipment_type': 'armor',
                'name': '革のジャケット',
                'armor_value': 1,
                'weight': '2.0',
                'quantity': 1
            },
            {
                'equipment_type': 'item',
                'name': '懐中電灯',
                'weight': '0.3',
                'quantity': 1
            },
            {
                'equipment_type': 'item',
                'name': 'カメラ',
                'weight': '0.5',
                'quantity': 1
            },
            {
                'equipment_type': 'item',
                'name': '調査ノート',
                'weight': '0.2',
                'quantity': 3
            },
            {
                'equipment_type': 'item',
                'name': '応急手当キット',
                'weight': '1.0',
                'quantity': 1
            }
        ]
        
        for item in equipment_list:
            response = self.client.post(
                f'/api/characters/{character_id}/equipment/',
                item
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        print(f"Added {len(equipment_list)} items to inventory")
        
        # Check combat summary
        response = self.client.get(f'/api/characters/{character_id}/combat_summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['damage_bonus'], '+1D4')
        self.assertEqual(len(response.data['weapons']), 2)
        self.assertEqual(response.data['armor']['total_armor'], 1)
        
        # Add background
        background_data = {
            'description': '元警察官の私立探偵。汚職事件を内部告発したことで警察を辞職し、現在は横浜で探偵事務所を営んでいる。',
            'personal_data': '''
            生年月日: 1892年4月15日
            家族: 妻（美香、28歳）、息子（健太、5歳）
            学歴: 東京帝国大学法学部卒
            職歴: 警視庁勤務（1914-1922）、山田探偵事務所開業（1923-現在）
            ''',
            'ideology_beliefs': '正義は必ず勝つ。真実を明らかにすることが使命。',
            'important_people': '妻の美香 - 自分を信じて支えてくれる唯一の理解者',
            'meaningful_locations': '横浜の探偵事務所 - 新しい人生を始めた場所',
            'treasured_possessions': '父の形見の懐中時計 - 時間を大切にすることを教えてくれた',
            'traits': '正義感が強い、観察力が鋭い、やや頑固'
        }
        
        response = self.client.post(
            f'/api/characters/{character_id}/background/',
            background_data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        print("Added character background")
        
        # Add financial information
        char_6th.annual_income = 50000
        char_6th.cash = 5000
        char_6th.assets = 45000
        char_6th.real_estate = "横浜市内の探偵事務所兼自宅"
        char_6th.save()
        
        # === Phase 4: First Session ===
        print("\n=== Phase 4: First Session ===")
        
        # GM creates a session
        self.client.force_authenticate(user=self.gm)
        session_data = {
            'title': '狂気山脈にて',
            'description': '南極探検隊の謎を追う',
            'session_date': '2024-03-01',
            'start_time': '19:00:00',
            'estimated_hours': 4,
            'min_players': 3,
            'max_players': 5,
            'location': 'オンライン'
        }
        response = self.client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.data['id']
        
        # Player joins session
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/schedules/sessions/{session_id}/register/',
            {'character_sheet_id': character_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Simulate session results
        # HP damage
        character.hp_current = character.hp_max - 3
        character.save()
        
        # SAN loss
        character.san_current = character.san_max - 5
        character.save()
        
        # Skill improvement
        listen_skill = CharacterSkill.objects.get(
            character_sheet=character,
            skill_name='聞き耳'
        )
        listen_skill.other_points += 3  # Gained through experience
        listen_skill.save()
        
        # Add Cthulhu Mythos
        cthulhu_skill = CharacterSkill.objects.create(
            character_sheet=character,
            skill_name='クトゥルフ神話',
            base_value=0,
            bonus_points=5  # Gained forbidden knowledge
        )
        
        # Create growth record
        growth_record = GrowthRecord.objects.create(
            character_sheet=character,
            session_date='2024-03-01',
            session_title='狂気山脈にて',
            session_id=session_id,
            changes={
                'hp': {'before': 15, 'after': 12},
                'san': {'before': 75, 'after': 70},
                'skills': {
                    '聞き耳': {'before': 70, 'after': 73},
                    'クトゥルフ神話': {'before': 0, 'after': 5}
                }
            }
        )
        
        # Update session count
        character.session_count = 1
        character.save()
        
        print("Session completed with HP damage, SAN loss, and skill improvements")
        
        # === Phase 5: Character Version ===
        print("\n=== Phase 5: Character Version ===")
        
        # Create new version after significant changes
        response = self.client.post(f'/api/characters/{character_id}/create_version/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        version_id = response.data['id']
        print(f"Created character version 2 (ID: {version_id})")
        
        # Verify version
        version = CharacterSheet.objects.get(id=version_id)
        self.assertEqual(version.version_number, 2)
        self.assertEqual(version.parent_sheet_id, character_id)
        
        # Check version history
        response = self.client.get(f'/api/characters/{character_id}/versions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Original + 1 version
        
        # === Phase 6: Multiple Sessions ===
        print("\n=== Phase 6: Multiple Sessions ===")
        
        # Participate in more sessions
        for i in range(2, 5):
            # Create session
            self.client.force_authenticate(user=self.gm)
            session_data = {
                'title': f'セッション {i}',
                'session_date': f'2024-03-{i*7:02d}',
                'start_time': '19:00:00',
                'estimated_hours': 4
            }
            response = self.client.post('/api/schedules/sessions/', session_data)
            session_id = response.data['id']
            
            # Join with latest version
            self.client.force_authenticate(user=self.user)
            response = self.client.post(
                f'/api/schedules/sessions/{session_id}/register/',
                {'character_sheet_id': version_id}
            )
            
            # Record growth
            growth = GrowthRecord.objects.create(
                character_sheet_id=version_id,
                session_date=f'2024-03-{i*7:02d}',
                session_title=f'セッション {i}',
                session_id=session_id,
                changes={'session': i}
            )
            
        # Update session count
        version = CharacterSheet.objects.get(id=version_id)
        version.session_count = 4
        version.save()
        
        # === Phase 7: Character Export ===
        print("\n=== Phase 7: Character Export ===")
        
        # Export to CCFOLIA
        response = self.client.get(f'/api/characters/{version_id}/ccfolia_json/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ccfolia_data = response.json()
        self.assertEqual(ccfolia_data['name'], '山田太郎')
        self.assertEqual(ccfolia_data['params'][0]['value'], 14)  # STR
        self.assertTrue(any(s['name'] == '聞き耳' for s in ccfolia_data['skills']))
        print("Successfully exported to CCFOLIA format")
        
        # === Phase 8: Character Retirement ===
        print("\n=== Phase 8: Character Retirement ===")
        
        # Deactivate character
        response = self.client.post(f'/api/characters/{version_id}/toggle_active/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_active'])
        
        # Verify character lifecycle
        response = self.client.get(f'/api/characters/{version_id}/growth_summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        summary = response.data
        self.assertEqual(summary['total_sessions'], 4)
        self.assertEqual(summary['version_count'], 2)
        self.assertEqual(len(summary['growth_records']), 3)  # Version 2's records
        
        print("\n=== Character Lifecycle Complete ===")
        print(f"Character '{character_data['name']}' completed {summary['total_sessions']} sessions")
        print(f"Created {summary['version_count']} versions")
        print("Character successfully retired")


class Character6thConcurrencyIntegrationTest(TransactionTestCase):
    """Test concurrent operations and race conditions"""
    
    def setUp(self):
        self.users = []
        self.clients = []
        
        # Create multiple users
        for i in range(3):
            user = User.objects.create_user(
                username=f'player{i}',
                password='testpass123'
            )
            self.users.append(user)
            
            client = APIClient()
            client.force_authenticate(user=user)
            self.clients.append(client)
            
    def test_concurrent_skill_allocation(self):
        """Test multiple users allocating skills simultaneously"""
        # Create characters for each user
        character_ids = []
        for i, client in enumerate(self.clients):
            response = client.post('/api/characters/create_6th_edition/', {
                'name': f'Character {i}',
                'age': 25,
                'str_value': 10, 'con_value': 10, 'pow_value': 10, 'dex_value': 10,
                'app_value': 10, 'siz_value': 10, 'int_value': 10, 'edu_value': 15,
                'occupation': '医師'
            })
            character_ids.append(response.data['id'])
            
        # Simulate concurrent skill allocation
        def allocate_skills(client, character_id, skill_name):
            return client.post(
                f'/api/characters/{character_id}/allocate_skill_points/',
                {
                    'skill_name': skill_name,
                    'base_value': 5,
                    'occupation_points': 50,
                    'interest_points': 10
                }
            )
            
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i, (client, char_id) in enumerate(zip(self.clients, character_ids)):
                future = executor.submit(allocate_skills, client, char_id, f'医学{i}')
                futures.append(future)
                
            # Collect results
            results = [f.result() for f in futures]
            
        # All should succeed since they're different characters
        for result in results:
            self.assertEqual(result.status_code, status.HTTP_200_OK)
            
    def test_concurrent_character_modification(self):
        """Test concurrent modifications to the same character"""
        # Create a shared character
        character = CharacterSheet.objects.create(
            user=self.users[0],
            name="Shared Character",
            age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        # Try concurrent updates
        def update_character(client, character_id, update_data):
            return client.patch(
                f'/api/characters/{character_id}/',
                update_data
            )
            
        # Only owner should be able to update
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            # Owner update
            futures.append(executor.submit(
                update_character,
                self.clients[0],
                character.id,
                {'age': 26}
            ))
            
            # Non-owner updates (should fail)
            futures.append(executor.submit(
                update_character,
                self.clients[1],
                character.id,
                {'age': 27}
            ))
            futures.append(executor.submit(
                update_character,
                self.clients[2],
                character.id,
                {'age': 28}
            ))
            
            results = [f.result() for f in futures]
            
        # Check results
        self.assertEqual(results[0].status_code, status.HTTP_200_OK)  # Owner
        self.assertEqual(results[1].status_code, status.HTTP_404_NOT_FOUND)  # Non-owner
        self.assertEqual(results[2].status_code, status.HTTP_404_NOT_FOUND)  # Non-owner
        
        # Verify final state
        character.refresh_from_db()
        self.assertEqual(character.age, 26)  # Only owner's update applied


class Character6thPermissionIntegrationTest(TransactionTestCase):
    """Test permission and access control integration"""
    
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='ownerpass'
        )
        self.friend = User.objects.create_user(
            username='friend',
            password='friendpass'
        )
        self.stranger = User.objects.create_user(
            username='stranger',
            password='strangerpass'
        )
        
        # Create characters
        self.private_char = CharacterSheet.objects.create(
            user=self.owner,
            name="Private Character",
            age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10,
            is_public=False
        )
        
        self.public_char = CharacterSheet.objects.create(
            user=self.owner,
            name="Public Character",
            age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10,
            is_public=True
        )
        
    def test_character_visibility_permissions(self):
        """Test character visibility based on public/private settings"""
        # Test as owner
        client = APIClient()
        client.force_authenticate(user=self.owner)
        
        # Owner can see both
        response = client.get(f'/api/characters/{self.private_char.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = client.get(f'/api/characters/{self.public_char.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test as stranger
        client.force_authenticate(user=self.stranger)
        
        # Stranger cannot see private
        response = client.get(f'/api/characters/{self.private_char.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Stranger can see public
        response = client.get(f'/api/characters/{self.public_char.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_character_modification_permissions(self):
        """Test only owner can modify character"""
        client = APIClient()
        
        # Owner can modify
        client.force_authenticate(user=self.owner)
        response = client.patch(
            f'/api/characters/{self.public_char.id}/',
            {'age': 26}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Non-owner cannot modify even public character
        client.force_authenticate(user=self.stranger)
        response = client.patch(
            f'/api/characters/{self.public_char.id}/',
            {'age': 27}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_skill_allocation_permissions(self):
        """Test only owner can allocate skill points"""
        client = APIClient()
        
        # Owner can allocate
        client.force_authenticate(user=self.owner)
        response = client.post(
            f'/api/characters/{self.public_char.id}/allocate_skill_points/',
            {
                'skill_name': '医学',
                'base_value': 5,
                'occupation_points': 50
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Non-owner cannot allocate even to public character
        client.force_authenticate(user=self.stranger)
        response = client.post(
            f'/api/characters/{self.public_char.id}/allocate_skill_points/',
            {
                'skill_name': '心理学',
                'base_value': 5,
                'occupation_points': 30
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class Character6thSessionIntegrationTest(TransactionTestCase):
    """Test character integration with sessions"""
    
    def setUp(self):
        self.gm = User.objects.create_user(
            username='gm',
            password='gmpass'
        )
        self.player = User.objects.create_user(
            username='player',
            password='playerpass'
        )
        
        # Create character
        self.character = CharacterSheet.objects.create(
            user=self.player,
            name="Session Test Character",
            age=25,
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17
        )
        
        # Create session
        self.session = TRPGSession.objects.create(
            gm=self.gm,
            title="Test Session",
            session_date="2024-03-01",
            start_time="19:00:00",
            estimated_hours=4
        )
        
    def test_session_participation_with_character(self):
        """Test character participation in sessions"""
        client = APIClient()
        client.force_authenticate(user=self.player)
        
        # Register for session with character
        response = client.post(
            f'/api/schedules/sessions/{self.session.id}/register/',
            {'character_sheet_id': self.character.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify participation
        participant = SessionParticipant.objects.get(
            session=self.session,
            user=self.player
        )
        self.assertEqual(participant.character_sheet_id, self.character.id)
        
        # Get session details should include character info
        response = client.get(f'/api/schedules/sessions/{self.session.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        participant_data = response.data['participants'][0]
        self.assertEqual(participant_data['character_sheet']['name'], self.character.name)
        
    def test_character_handout_integration(self):
        """Test character receiving handouts in session"""
        # Player joins session
        SessionParticipant.objects.create(
            session=self.session,
            user=self.player,
            character_sheet=self.character
        )
        
        # GM creates handout
        client = APIClient()
        client.force_authenticate(user=self.gm)
        
        handout_data = {
            'session': self.session.id,
            'title': 'Secret Note',
            'content': 'You find a mysterious letter...',
            'is_secret': True,
            'recipient': self.player.id
        }
        
        response = client.post('/api/schedules/handouts/', handout_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Player can see their handout
        client.force_authenticate(user=self.player)
        response = client.get('/api/schedules/handouts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Secret Note')


class Character6thDataIntegrityTest(TransactionTestCase):
    """Test data integrity and cascading operations"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        
    def test_character_deletion_cascades(self):
        """Test all related data is properly deleted with character"""
        # Create character with all related data
        character = CharacterSheet.objects.create(
            user=self.user,
            name="Delete Test",
            age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        # Add related data
        skill = CharacterSkill.objects.create(
            character_sheet=character,
            skill_name="医学",
            base_value=5
        )
        
        equipment = CharacterEquipment.objects.create(
            character_sheet=character,
            equipment_type='item',
            name="Test Item"
        )
        
        background = CharacterBackground.objects.create(
            character_sheet=character,
            description="Test background"
        )
        
        growth = GrowthRecord.objects.create(
            character_sheet=character,
            session_date="2024-01-01",
            session_title="Test Session"
        )
        
        dice_setting = CharacterDiceRollSetting.objects.create(
            character_sheet=character,
            name="Test Roll",
            dice_count=2,
            dice_sides=6
        )
        
        # Get related object IDs
        char_6th_id = character.sheet_6th.id
        
        # Delete character
        character_id = character.id
        character.delete()
        
        # Verify all related data is deleted
        self.assertFalse(CharacterSheet.objects.filter(id=character_id).exists())
        self.assertFalse(CharacterSheet6th.objects.filter(id=char_6th_id).exists())
        self.assertFalse(CharacterSkill.objects.filter(id=skill.id).exists())
        self.assertFalse(CharacterEquipment.objects.filter(id=equipment.id).exists())
        self.assertFalse(CharacterBackground.objects.filter(id=background.id).exists())
        self.assertFalse(GrowthRecord.objects.filter(id=growth.id).exists())
        self.assertFalse(CharacterDiceRollSetting.objects.filter(id=dice_setting.id).exists())
        
    def test_version_integrity(self):
        """Test version relationships maintain integrity"""
        # Create character and versions
        original = CharacterSheet.objects.create(
            user=self.user,
            name="Version Test",
            age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        v2 = original.create_version()
        v3 = v2.create_version()
        
        # Try to delete middle version (should handle gracefully)
        v2_id = v2.id
        v2.delete()
        
        # v3 should still exist but parent reference is gone
        v3.refresh_from_db()
        self.assertFalse(CharacterSheet.objects.filter(id=v2_id).exists())
        self.assertTrue(CharacterSheet.objects.filter(id=v3.id).exists())
        
        # Original should still have correct version list
        versions = original.get_all_versions()
        self.assertEqual(len(versions), 2)  # Original + v3


class Character6thPerformanceIntegrationTest(TransactionTestCase):
    """Test performance with realistic data volumes"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='perfuser',
            password='perfpass'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
    def test_large_character_list_performance(self):
        """Test API performance with many characters"""
        # Create 50 characters
        characters = []
        for i in range(50):
            char = CharacterSheet(
                user=self.user,
                name=f"Character {i:03d}",
                age=20 + (i % 60),
                str_value=10 + (i % 8),
                con_value=10 + ((i+1) % 8),
                pow_value=10 + ((i+2) % 8),
                dex_value=10 + ((i+3) % 8),
                app_value=10 + ((i+4) % 8),
                siz_value=10 + ((i+5) % 8),
                int_value=10 + ((i+6) % 8),
                edu_value=10 + ((i+7) % 8),
                is_public=(i % 3 == 0)  # Every 3rd is public
            )
            characters.append(char)
            
        CharacterSheet.objects.bulk_create(characters)
        
        # Measure list performance
        start_time = time.time()
        response = self.client.get('/api/characters/', {'page_size': 20})
        elapsed = time.time() - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 50)
        self.assertEqual(len(response.data['results']), 20)  # Pagination
        self.assertLess(elapsed, 1.0)  # Should complete within 1 second
        
        # Test filtering performance
        start_time = time.time()
        response = self.client.get('/api/characters/', {
            'is_active': True,
            'is_public': True,
            'search': 'Character 01'
        })
        elapsed = time.time() - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed, 0.5)  # Filtering should be fast
        
    def test_complex_character_detail_performance(self):
        """Test performance loading character with many related objects"""
        # Create character with lots of data
        character = CharacterSheet.objects.create(
            user=self.user,
            name="Complex Character",
            age=25,
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17
        )
        
        # Add 30 skills
        skills = []
        for i in range(30):
            skill = CharacterSkill(
                character_sheet=character,
                skill_name=f"Skill {i:02d}",
                base_value=5 + (i % 20),
                occupation_points=(i % 5) * 10,
                interest_points=(i % 3) * 5
            )
            skills.append(skill)
        CharacterSkill.objects.bulk_create(skills)
        
        # Add 20 equipment items
        equipment = []
        for i in range(20):
            item = CharacterEquipment(
                character_sheet=character,
                equipment_type='item',
                name=f"Item {i:02d}",
                weight=Decimal(f"{0.1 + i * 0.1:.1f}"),
                quantity=1 + (i % 5)
            )
            equipment.append(item)
        CharacterEquipment.objects.bulk_create(equipment)
        
        # Add 10 growth records
        growth_records = []
        for i in range(10):
            record = GrowthRecord(
                character_sheet=character,
                session_date=f"2024-01-{i+1:02d}",
                session_title=f"Session {i+1}",
                changes={'session': i+1}
            )
            growth_records.append(record)
        GrowthRecord.objects.bulk_create(growth_records)
        
        # Measure detail retrieval performance
        start_time = time.time()
        response = self.client.get(f'/api/characters/{character.id}/')
        elapsed = time.time() - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['skills']), 30)
        self.assertEqual(len(response.data['equipment']), 20)
        self.assertLess(elapsed, 1.0)  # Should load within 1 second
        
    def test_batch_operation_performance(self):
        """Test performance of batch operations"""
        character = CharacterSheet.objects.create(
            user=self.user,
            name="Batch Test",
            age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=16,
            occupation="医師"
        )
        
        # Prepare batch skill data
        skills_data = {
            'skills': [
                {
                    'skill_name': f'Skill {i:02d}',
                    'base_value': 5 + (i % 20),
                    'occupation_points': min((i % 10) * 5, 50),
                    'interest_points': min((i % 5) * 3, 15)
                }
                for i in range(25)
            ]
        }
        
        # Measure batch allocation performance
        start_time = time.time()
        response = self.client.post(
            f'/api/characters/{character.id}/batch_allocate_skill_points/',
            skills_data,
            format='json'
        )
        elapsed = time.time() - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            CharacterSkill.objects.filter(character_sheet=character).count(),
            25
        )
        self.assertLess(elapsed, 2.0)  # Batch creation should be reasonably fast


# Additional test utilities
def create_test_character(user, **kwargs):
    """Helper function to create test characters"""
    defaults = {
        'name': 'Test Character',
        'age': 25,
        'str_value': 10,
        'con_value': 10,
        'pow_value': 10,
        'dex_value': 10,
        'app_value': 10,
        'siz_value': 10,
        'int_value': 10,
        'edu_value': 10
    }
    defaults.update(kwargs)
    return CharacterSheet.objects.create(user=user, **defaults)