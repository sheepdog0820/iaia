"""
Comprehensive test suite for Call of Cthulhu 6th Edition Character Sheet

This test suite covers:
1. Model validation and constraints
2. Calculations and derived values
3. API endpoints and permissions
4. Character workflows
5. Edge cases and error handling
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
import json
from unittest.mock import patch, MagicMock

from accounts.character_models import (
    CharacterSheet, CharacterSheet6th, CharacterSkill, CharacterEquipment, 
    CharacterBackground, GrowthRecord, CharacterImage, CharacterDiceRollSetting
)
from accounts.views.character_views import CharacterSheetViewSet

User = get_user_model()


def create_test_character(user, **kwargs):
    """Helper function to create test character with defaults"""
    defaults = {
        'name': 'Test Character',
        'age': 25,
        'edition': '6th',
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
    if 'edition' not in defaults:
        defaults['edition'] = '6th'

    temp = CharacterSheet(user=user, **defaults)
    stats = temp.calculate_derived_stats()

    defaults.setdefault('hit_points_max', stats['hit_points_max'])
    defaults.setdefault('magic_points_max', stats['magic_points_max'])
    defaults.setdefault('sanity_starting', stats['sanity_starting'])
    defaults.setdefault('sanity_max', stats['sanity_max'])

    defaults.setdefault('hit_points_current', defaults['hit_points_max'])
    defaults.setdefault('magic_points_current', defaults['magic_points_max'])
    defaults.setdefault('sanity_current', defaults['sanity_starting'])

    character = CharacterSheet.objects.create(user=user, **defaults)
    if defaults.get('edition') == '6th':
        CharacterSheet6th.objects.get_or_create(character_sheet=character)
    return character


class Character6thModelValidationTestCase(TestCase):
    """Test model field validation and constraints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
    def test_ability_value_constraints(self):
        """Test ability values must be between 1 and 999"""
        # Test minimum values
        character = CharacterSheet.objects.create(
            user=self.user,
            name="Min Abilities",
            age=20,
            edition='6th',
            str_value=1,
            con_value=1,
            pow_value=1,
            dex_value=1,
            app_value=1,
            siz_value=1,
            int_value=1,
            edu_value=1,
            hit_points_max=1,
            hit_points_current=1,
            magic_points_max=1,
            magic_points_current=1,
            sanity_starting=5,
            sanity_max=5,
            sanity_current=5
        )
        character.full_clean()  # Should not raise
        
        # Test maximum values
        character.str_value = 999
        character.con_value = 999
        character.full_clean()  # Should not raise
        
        # Test invalid values
        character.str_value = 0
        with self.assertRaises(ValidationError):
            character.full_clean()
            
        character.str_value = 1000
        with self.assertRaises(ValidationError):
            character.full_clean()
            
    def test_age_constraints(self):
        """Test age must be between 15 and 90"""
        character = CharacterSheet(
            user=self.user,
            name="Age Test",
            age=15,  # Minimum
            edition='6th',
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10,
            hit_points_max=10, hit_points_current=10,
            magic_points_max=10, magic_points_current=10,
            sanity_starting=50, sanity_max=50, sanity_current=50
        )
        character.full_clean()  # Should not raise
        
        character.age = 90  # Maximum
        character.full_clean()  # Should not raise
        
        character.age = 14
        with self.assertRaises(ValidationError):
            character.full_clean()
            
        character.age = 91
        with self.assertRaises(ValidationError):
            character.full_clean()
            
    def test_san_value_constraints(self):
        """Test SAN values validation"""
        character = create_test_character(
            self.user,
            name="SAN Test",
            pow_value=50,
            sanity_max=50,
            sanity_current=50
        )
        
        # Test SAN current can equal SAN max
        character.sanity_max = 50
        character.sanity_current = 50
        character.full_clean()  # Should not raise
        
        # Note: The model doesn't seem to have validators for SAN current > max
        # This would need to be implemented in the model clean() method
            
    def test_hp_mp_constraints(self):
        """Test HP and MP value constraints"""
        character = create_test_character(
            self.user,
            name="HP/MP Test",
            con_value=12,
            pow_value=14,
            siz_value=11,
            hit_points_max=12,
            hit_points_current=12,
            magic_points_max=14,
            magic_points_current=14
        )
        
        # Test values can be equal
        character.hit_points_max = 12
        character.hit_points_current = 12
        character.full_clean()  # Should not raise
        
        # Note: The model doesn't seem to have validators for current > max
        # This would need to be implemented in the model clean() method


class Character6thCalculationTestCase(TestCase):
    """Test all calculated fields and formulas"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_hp_calculation(self):
        """Test HP = (CON + SIZ) / 2 rounded up"""
        test_cases = [
            # (CON, SIZ, expected_HP)
            (10, 10, 10),  # 20/2 = 10
            (11, 10, 11),  # 21/2 = 10.5 -> 11
            (15, 13, 14),  # 28/2 = 14
            (3, 3, 3),     # 6/2 = 3
            (18, 18, 18),  # 36/2 = 18
        ]
        
        for con, siz, expected_hp in test_cases:
            character = create_test_character(
                self.user,
                name=f"HP Test {con}/{siz}",
                con_value=con,
                siz_value=siz
            )
            self.assertEqual(character.hit_points_max, expected_hp)
            self.assertEqual(character.hit_points_current, expected_hp)
            
    def test_mp_calculation(self):
        """Test MP = POW"""
        test_cases = [3, 8, 12, 16, 18]
        
        for pow_val in test_cases:
            character = create_test_character(
                self.user,
                name=f"MP Test POW={pow_val}",
                pow_value=pow_val
            )
            self.assertEqual(character.magic_points_max, pow_val)
            self.assertEqual(character.magic_points_current, pow_val)
            
    def test_san_calculation(self):
        """Test SAN = POW × 5"""
        test_cases = [
            (3, 15),   # 3 × 5 = 15
            (10, 50),  # 10 × 5 = 50
            (15, 75),  # 15 × 5 = 75
            (18, 90),  # 18 × 5 = 90
        ]
        
        for pow_val, expected_san in test_cases:
            character = create_test_character(
                self.user,
                name=f"SAN Test POW={pow_val}",
                pow_value=pow_val
            )
            self.assertEqual(character.sanity_starting, expected_san)
            self.assertEqual(character.sanity_current, expected_san)
            self.assertEqual(character.sanity_max, 99)
            
    def test_idea_luck_know_calculation(self):
        """Test 6th edition specific calculations"""
        character = create_test_character(
            self.user,
            name="Derived Stats Test",
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17
        )
        
        char_6th = character.sixth_edition_data
        
        # Idea = INT × 5
        self.assertEqual(char_6th.idea_roll, 16 * 5)  # 80
        
        # Luck = POW × 5
        self.assertEqual(char_6th.luck_roll, 14 * 5)  # 70
        
        # Know = EDU × 5
        self.assertEqual(char_6th.know_roll, 17 * 5)  # 85
        
    def test_damage_bonus_calculation(self):
        """Test damage bonus calculation based on STR + SIZ"""
        test_cases = [
            # (STR, SIZ, expected_damage_bonus)
            (6, 6, "-1D6"),      # 12 total
            (8, 8, "-1D4"),      # 16 total
            (10, 10, "0"),       # 20 total
            (15, 15, "+1D4"),    # 30 total
            (18, 18, "+1D6"),    # 36 total
            (20, 25, "+2D6"),    # 45 total
            (30, 40, "+3D6"),    # 70 total
        ]
        
        for str_val, siz_val, expected_db in test_cases:
            character = create_test_character(
                self.user,
                name=f"DB Test STR={str_val} SIZ={siz_val}",
                str_value=str_val,
                siz_value=siz_val
            )
            self.assertEqual(character.sixth_edition_data.damage_bonus, expected_db)
            
    def test_occupation_points_calculation(self):
        """Test occupation point calculations for all types"""
        character = create_test_character(
            self.user,
            name="Occupation Points Test",
            edu_value=18
        )

        self.assertEqual(character.calculate_occupation_points(), 18 * 20)

        character.occupation_multiplier = 25
        self.assertEqual(character.calculate_occupation_points(), 18 * 25)


    def test_hobby_points_calculation(self):
        """Test hobby points = INT × 10"""
        test_cases = [3, 8, 12, 16, 18]
        
        for int_val in test_cases:
            character = create_test_character(
                self.user,
                name=f"Hobby Test INT={int_val}",
                int_value=int_val
            )
            self.assertEqual(character.calculate_hobby_points(), int_val * 10)


class Character6thSkillManagementTestCase(TestCase):
    """Test skill allocation and management"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.character = create_test_character(
            self.user,
            name="Skill Test Character",
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17,
            occupation="蛹ｻ蟶ｫ"
        )

    def test_skill_creation_and_validation(self):
        """Test skill creation with valid point allocations"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name="Test Skill",
            base_value=5,
            occupation_points=70,
            interest_points=20,
            bonus_points=0,
            other_points=0
        )

        # Total should be base + all points
        self.assertEqual(skill.current_value, 5 + 70 + 20 + 0 + 0)  # 95

        # Points cannot be negative
        skill.occupation_points = -10
        with self.assertRaises(ValidationError):
            skill.full_clean()

        # Total cannot exceed 999 for regular skills
        skill.occupation_points = 0
        skill.interest_points = 0
        skill.base_value = 5
        skill.bonus_points = 994
        skill.other_points = 0
        skill.full_clean()  # Total = 999, should be valid

        skill.bonus_points = 995
        with self.assertRaises(ValidationError):
            skill.full_clean()


    def test_skill_points_allocation_limits(self):
        """Test occupation and interest point limits"""
        # Create multiple skills
        skills_data = [
            ("医学", 5, 70, 0),
            ("応急手当", 30, 40, 0),
            ("心理学", 5, 30, 20),
            ("図書館", 25, 0, 40),
        ]
        
        for name, base, occ, int_pts in skills_data:
            CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name=name,
                base_value=base,
                occupation_points=occ,
                interest_points=int_pts
            )
            
        # Calculate total allocated points
        total_occupation = CharacterSkill.objects.filter(
            character_sheet=self.character
        ).aggregate(total=models.Sum('occupation_points'))['total']
        
        total_interest = CharacterSkill.objects.filter(
            character_sheet=self.character
        ).aggregate(total=models.Sum('interest_points'))['total']
        
        self.assertEqual(total_occupation, 140)  # 70 + 40 + 30 + 0
        self.assertEqual(total_interest, 60)     # 0 + 0 + 20 + 40
        
        # Check available points
        occupation_available = self.character.calculate_occupation_points() - total_occupation
        hobby_available = self.character.calculate_hobby_points() - total_interest
        
        self.assertEqual(occupation_available, 340 - 140)  # 200
        self.assertEqual(hobby_available, 160 - 60)        # 100
        
    def test_cthulhu_mythos_special_case(self):
        """Test Cthulhu Mythos skill can store bonus/other points"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name="クトゥルフ神話",
            base_value=0,
            occupation_points=0,
            interest_points=0,
            bonus_points=5,
            other_points=10
        )
        self.assertEqual(skill.current_value, 15)


    def test_san_max_reduction_with_cthulhu_mythos(self):
        """Test SAN max = 99 - Cthulhu Mythos"""
        self.assertEqual(self.character.sanity_max, 99)

        cthulhu_skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name="クトゥルフ神話",
            base_value=0,
            bonus_points=15
        )

        self.character.refresh_from_db()
        expected_san_max = 99 - cthulhu_skill.current_value
        self.assertEqual(self.character.sanity_max, expected_san_max)


class Character6thEquipmentTestCase(TestCase):
    """Test equipment and inventory management"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.character = create_test_character(
            self.user,
            name="Equipment Test",
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17
        )

    def test_equipment_creation(self):
        """Test equipment creation and validation"""
        weapon = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='weapon',
            name='Test Revolver',
            damage='1D10',
            attacks_per_round=2,
            weight=0.5,
            quantity=1
        )

        self.assertAlmostEqual(weapon.weight * weapon.quantity, 0.5)

        armor = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='armor',
            name='Leather Jacket',
            armor_points=1,
            weight=2.0,
            quantity=1
        )

        self.assertEqual(armor.armor_points, 1)

        item = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='item',
            name='Ration',
            weight=0.1,
            quantity=20
        )

        self.assertAlmostEqual(item.weight * item.quantity, 2.0)


    def test_movement_penalty_calculation(self):
        """Test movement penalty based on total weight"""
        items = [
            ('Item A', 10.0, 1),
            ('Item B', 5.0, 1),
            ('Item C', 2.0, 3),
            ('Item D', 1.0, 5),
        ]

        for name, weight, qty in items:
            CharacterEquipment.objects.create(
                character_sheet=self.character,
                item_type='item',
                name=name,
                weight=weight,
                quantity=qty
            )

        total_weight = sum(weight * qty for _, weight, qty in items)
        self.assertEqual(total_weight, 26.0)

        penalty = self.character.calculate_movement_penalty(total_weight)
        self.assertEqual(penalty, 0)


class Character6thVersioningTestCase(TestCase):
    """Test character versioning functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.original = create_test_character(
            self.user,
            name='Original Character',
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17
        )

    def test_create_version(self):
        """Test creating a new version of a character"""
        CharacterSkill.objects.create(
            character_sheet=self.original,
            skill_name='Test Skill',
            base_value=5,
            occupation_points=70
        )

        version = self.original.create_new_version(copy_skills=True)

        self.assertEqual(version.parent_sheet, self.original)
        self.assertEqual(version.version, self.original.version + 1)
        self.assertEqual(version.name, self.original.name)
        self.assertEqual(version.age, self.original.age)

        original_skills = CharacterSkill.objects.filter(character_sheet=self.original)
        version_skills = CharacterSkill.objects.filter(character_sheet=version)
        self.assertEqual(original_skills.count(), version_skills.count())

        self.assertEqual(
            version.sixth_edition_data.damage_bonus,
            self.original.sixth_edition_data.damage_bonus
        )

    def test_version_hierarchy(self):
        """Test multiple versions and hierarchy"""
        v2 = self.original.create_new_version()
        v3 = v2.create_new_version()

        self.assertEqual(self.original.version, 1)
        self.assertEqual(v2.version, 2)
        self.assertEqual(v3.version, 3)

        self.assertIsNone(self.original.parent_sheet)
        self.assertEqual(v2.parent_sheet, self.original)
        self.assertEqual(v3.parent_sheet, v2)

        versions = self.original.get_version_history()
        self.assertEqual(len(versions), 3)

    def test_circular_reference_prevention(self):
        """Test prevention of circular version references"""
        v2 = self.original.create_new_version()

        self.original.parent_sheet = v2
        with self.assertRaises(ValidationError):
            self.original.save()


class Character6thAPITestCase(APITestCase):
    """Test API endpoints for character sheet"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_6th_edition_character(self):
        """Test character creation via API"""
        data = {
            'name': 'API Test Character',
            'age': 28,
            'gender': 'male',
            'occupation': 'Detective',
            'birthplace': 'Tokyo',
            'residence': 'Yokohama',
            'str_value': 13,
            'con_value': 12,
            'pow_value': 14,
            'dex_value': 11,
            'app_value': 10,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 17
        }

        response = self.client.post('/api/accounts/character-sheets/create_6th_edition/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        character = CharacterSheet.objects.get(id=response.data['id'])
        self.assertEqual(character.name, 'API Test Character')
        self.assertEqual(character.user, self.user)
        self.assertEqual(character.edition, '6th')

        self.assertTrue(CharacterSheet6th.objects.filter(character_sheet=character).exists())
        self.assertEqual(character.sixth_edition_data.idea_roll, 16 * 5)

    def test_character_list_permissions(self):
        """Test character list shows only user's characters"""
        create_test_character(self.user, name='My Character')
        create_test_character(self.other_user, name='Other Character')

        response = self.client.get('/api/accounts/character-sheets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        if isinstance(data, list):
            names = [item['name'] for item in data]
        else:
            names = [item['name'] for item in data.get('results', [])]

        self.assertIn('My Character', names)
        self.assertNotIn('Other Character', names)

    def test_public_character_access(self):
        """Test public character visibility"""
        private_char = create_test_character(self.other_user, name='Private Character', is_public=False)
        public_char = create_test_character(self.other_user, name='Public Character', is_public=True)

        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.get(f'/api/accounts/character-sheets/{private_char.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.get(f'/api/accounts/character-sheets/{public_char.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_skill_points_allocation_api(self):
        """Test skill point allocation endpoints"""
        character = create_test_character(self.user, name='Skill API Test', edu_value=16, int_value=10)
        skill = CharacterSkill.objects.create(
            character_sheet=character,
            skill_name='Test Skill',
            base_value=5
        )

        response = self.client.get(f'/api/accounts/character-sheets/{character.id}/skill-points-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['occupation_points']['total'], 16 * 20)
        self.assertEqual(response.data['hobby_points']['total'], 10 * 10)

        response = self.client.post(
            f'/api/accounts/character-sheets/{character.id}/allocate_skill_points/',
            {
                'skill_id': skill.id,
                'occupation_points': 70,
                'interest_points': 20
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        skill.refresh_from_db()
        self.assertEqual(skill.occupation_points, 70)
        self.assertEqual(skill.interest_points, 20)
        self.assertEqual(skill.current_value, 95)

    def test_batch_skill_allocation(self):
        """Test batch skill point allocation"""
        character = create_test_character(self.user, name='Batch Skill Test', edu_value=16, int_value=10)
        skills = [
            CharacterSkill.objects.create(character_sheet=character, skill_name='Skill A', base_value=5),
            CharacterSkill.objects.create(character_sheet=character, skill_name='Skill B', base_value=30),
            CharacterSkill.objects.create(character_sheet=character, skill_name='Skill C', base_value=5),
        ]

        allocations = [
            {'skill_id': skills[0].id, 'occupation_points': 70, 'interest_points': 0},
            {'skill_id': skills[1].id, 'occupation_points': 40, 'interest_points': 0},
            {'skill_id': skills[2].id, 'occupation_points': 30, 'interest_points': 20},
        ]

        response = self.client.post(
            f'/api/accounts/character-sheets/{character.id}/batch_allocate_skill_points/',
            {'allocations': allocations},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        total_occupation = sum(s.occupation_points for s in character.skills.all())
        total_interest = sum(s.interest_points for s in character.skills.all())
        self.assertEqual(total_occupation, 140)
        self.assertEqual(total_interest, 20)

    def test_ccfolia_export(self):
        """Test CCFOLIA JSON export"""
        character = create_test_character(self.user, name='CCFOLIA Test', str_value=13)
        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name='Test Skill',
            base_value=5,
            occupation_points=70
        )

        response = self.client.get(f'/api/accounts/character-sheets/{character.id}/ccfolia_json/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['kind'], 'character')
        self.assertEqual(data['data']['name'], 'CCFOLIA Test')
        self.assertEqual(data['data']['params'][0]['label'], 'STR')
        self.assertEqual(data['data']['params'][0]['value'], '13')
        self.assertIn('Test Skill', data['data']['commands'])

    def test_combat_summary(self):
        """Test combat summary endpoint"""
        character = create_test_character(self.user, name='Combat Test', str_value=16, siz_value=17)

        CharacterEquipment.objects.create(
            character_sheet=character,
            item_type='weapon',
            name='Test Weapon',
            damage='1D10',
            attacks_per_round=2
        )

        response = self.client.get(f'/api/accounts/character-sheets/{character.id}/combat_summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['damage_bonus'], character.sixth_edition_data.damage_bonus)
        self.assertEqual(response.data['weapons_count'], 1)

    def test_authentication_required(self):
        """Test endpoints require authentication"""
        self.client.logout()

        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.get('/api/accounts/character-sheets/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.post('/api/accounts/character-sheets/create_6th_edition/', {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_character_deletion(self):
        """Test character deletion and cascades"""
        character = create_test_character(self.user, name='Delete Test')

        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name='Test Skill',
            base_value=5
        )
        CharacterEquipment.objects.create(
            character_sheet=character,
            item_type='item',
            name='Test Item'
        )

        response = self.client.delete(f'/api/accounts/character-sheets/{character.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(CharacterSheet.objects.filter(id=character.id).exists())
        self.assertFalse(CharacterSkill.objects.filter(character_sheet=character).exists())
        self.assertFalse(CharacterEquipment.objects.filter(character_sheet=character).exists())


class Character6thIntegrationTestCase(TransactionTestCase):
    """Integration tests for complete workflows"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_complete_character_creation_workflow(self):
        """Test complete character creation workflow"""
        character_data = {
            'name': 'Complete Workflow Test',
            'age': 30,
            'gender': 'female',
            'occupation': 'Doctor',
            'birthplace': 'Osaka',
            'residence': 'Kyoto',
            'str_value': 13,
            'con_value': 14,
            'pow_value': 15,
            'dex_value': 12,
            'app_value': 11,
            'siz_value': 16,
            'int_value': 17,
            'edu_value': 18
        }

        response = self.client.post('/api/accounts/character-sheets/create_6th_edition/', character_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character_id = response.data['id']

        skills = [
            {'skill_name': 'Medicine', 'base_value': 5, 'occupation_points': 80, 'interest_points': 0},
            {'skill_name': 'First Aid', 'base_value': 30, 'occupation_points': 50, 'interest_points': 0},
            {'skill_name': 'Psychology', 'base_value': 5, 'occupation_points': 40, 'interest_points': 10},
            {'skill_name': 'Library Use', 'base_value': 25, 'occupation_points': 0, 'interest_points': 30},
        ]

        for skill in skills:
            response = self.client.post(
                f'/api/accounts/character-sheets/{character_id}/skills/',
                skill,
                format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        equipment = [
            {
                'item_type': 'weapon',
                'name': 'Pistol',
                'damage': '1D10',
                'attacks_per_round': 2,
                'weight': '0.5'
            },
            {
                'item_type': 'armor',
                'name': 'Kevlar Vest',
                'armor_points': 8,
                'weight': '3.0'
            },
            {
                'item_type': 'item',
                'name': 'Medical Kit',
                'weight': '2.0',
                'quantity': 1
            }
        ]

        for item in equipment:
            response = self.client.post(
                f'/api/accounts/character-sheets/{character_id}/equipment/',
                item,
                format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        background_data = {
            'personal_description': 'Test background',
            'ideals_and_beliefs': 'Science first',
            'significant_people': 'Mentor',
            'meaningful_locations': 'University lab',
            'treasured_possessions': 'Old stethoscope',
            'traits': 'Calm and careful'
        }

        response = self.client.post(
            f'/api/accounts/character-sheets/{character_id}/background/',
            background_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(f'/api/accounts/character-sheets/{character_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        character = response.data
        self.assertEqual(character['name'], 'Complete Workflow Test')
        self.assertEqual(len(character['skills']), 4)
        self.assertEqual(len(character['equipment']), 3)
        self.assertTrue(CharacterBackground.objects.filter(character_sheet_id=character_id).exists())

    def test_character_growth_workflow(self):
        """Test character growth through sessions"""
        character = create_test_character(self.user, name='Growth Test')

        GrowthRecord.objects.create(
            character_sheet=character,
            session_date='2024-01-01',
            scenario_name='Test Scenario',
            sanity_gained=2,
            sanity_lost=5,
            experience_gained=10
        )

        response = self.client.get(f'/api/accounts/character-sheets/{character.id}/growth_summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        summary = response.data
        self.assertEqual(summary['total_sessions'], 1)
        self.assertEqual(summary['total_sanity_lost'], 5)
        self.assertEqual(summary['total_sanity_gained'], 2)


class Character6thErrorHandlingTestCase(APITestCase):
    """Test error handling and edge cases"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_invalid_ability_values(self):
        """Test validation of ability values"""
        data = {
            'name': 'Invalid Test',
            'age': 25,
            'str_value': 0,
            'con_value': 10,
            'pow_value': 10,
            'dex_value': 10,
            'app_value': 10,
            'siz_value': 10,
            'int_value': 10,
            'edu_value': 10
        }

        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.post('/api/accounts/character-sheets/create_6th_edition/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_skill_overallocation(self):
        """Test prevention of skill point over-allocation"""
        character = create_test_character(self.user, name='Overallocation Test', edu_value=10)
        skill = CharacterSkill.objects.create(
            character_sheet=character,
            skill_name='Test Skill',
            base_value=5
        )

        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.post(
                f'/api/accounts/character-sheets/{character.id}/allocate_skill_points/',
                {
                    'skill_id': skill.id,
                    'occupation_points': 999,
                    'interest_points': 0
                },
                format='json'
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_skill_id(self):
        """Test allocate endpoint requires skill_id"""
        character = create_test_character(self.user, name='Missing Skill Id Test')

        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.post(
                f'/api/accounts/character-sheets/{character.id}/allocate_skill_points/',
                {'occupation_points': 10, 'interest_points': 0},
                format='json'
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_large_data_handling(self):
        """Test handling of large amounts of data"""
        character = create_test_character(self.user, name='Large Data Test', edu_value=10)

        skills = [
            CharacterSkill.objects.create(
                character_sheet=character,
                skill_name=f'Skill {i}',
                base_value=5
            )
            for i in range(50)
        ]

        allocations = [
            {'skill_id': skill.id, 'occupation_points': 1, 'interest_points': 0}
            for skill in skills
        ]

        response = self.client.post(
            f'/api/accounts/character-sheets/{character.id}/batch_allocate_skill_points/',
            {'allocations': allocations},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        skill_count = CharacterSkill.objects.filter(character_sheet=character).count()
        self.assertEqual(skill_count, 50)

    def test_file_upload_validation(self):
        """Test image upload validation"""
        character = create_test_character(self.user, name='Image Test')

        with patch('django.core.files.uploadedfile.SimpleUploadedFile') as mock_file:
            mock_file.return_value.size = 10 * 1024 * 1024

            with self.assertLogs('django.request', level='WARNING'):
                response = self.client.post(
                    f'/api/accounts/character-sheets/{character.id}/images/',
                    {'image': mock_file.return_value}
                )

            self.assertIn(
                response.status_code,
                [status.HTTP_400_BAD_REQUEST, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE]
            )


class Character6thPerformanceTestCase(TestCase):
    """Test performance with large datasets"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_bulk_character_operations(self):
        """Test performance with many characters"""
        characters = []
        for i in range(20):
            char = CharacterSheet(
                user=self.user,
                name=f'Character {i}',
                age=25,
                edition='6th',
                str_value=10, con_value=10, pow_value=10, dex_value=10,
                app_value=10, siz_value=10, int_value=10, edu_value=10,
                hit_points_max=10,
                hit_points_current=10,
                magic_points_max=10,
                magic_points_current=10,
                sanity_starting=50,
                sanity_max=99,
                sanity_current=50
            )
            characters.append(char)

        CharacterSheet.objects.bulk_create(characters)

        with self.assertNumQueries(1):
            chars = CharacterSheet.objects.filter(user=self.user).select_related('sixth_edition_data')
            list(chars)

    def test_skill_calculation_performance(self):
        """Test performance of skill calculations"""
        character = create_test_character(self.user, name='Performance Test')

        skills = []
        for i in range(100):
            skill = CharacterSkill(
                character_sheet=character,
                skill_name=f'Skill {i}',
                base_value=5,
                occupation_points=1
            )
            skills.append(skill)

        CharacterSkill.objects.bulk_create(skills)

        import time
        start = time.time()

        total_occupation = sum(s.occupation_points for s in character.skills.all())
        total_interest = sum(s.interest_points for s in character.skills.all())

        elapsed = time.time() - start
        self.assertLess(elapsed, 1.0)


# Import the django test command to ensure proper test discovery
from django.core.management import call_command
