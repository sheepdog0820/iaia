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
        'edu_value': 10,
        'hit_points_max': 10,
        'hit_points_current': 10,
        'magic_points_max': 10,
        'magic_points_current': 10,
        'sanity_starting': 50,
        'sanity_max': 50,
        'sanity_current': 50
    }
    defaults.update(kwargs)
    return CharacterSheet.objects.create(user=user, **defaults)


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
            character = CharacterSheet.objects.create(
                user=self.user,
                name=f"HP Test {con}/{siz}",
                age=25,
                str_value=10, con_value=con, pow_value=10, dex_value=10,
                app_value=10, siz_value=siz, int_value=10, edu_value=10
            )
            self.assertEqual(character.hp_max, expected_hp)
            self.assertEqual(character.hp_current, expected_hp)
            
    def test_mp_calculation(self):
        """Test MP = POW"""
        test_cases = [3, 8, 12, 16, 18]
        
        for pow_val in test_cases:
            character = CharacterSheet.objects.create(
                user=self.user,
                name=f"MP Test POW={pow_val}",
                age=25,
                str_value=10, con_value=10, pow_value=pow_val, dex_value=10,
                app_value=10, siz_value=10, int_value=10, edu_value=10
            )
            self.assertEqual(character.mp_max, pow_val)
            self.assertEqual(character.mp_current, pow_val)
            
    def test_san_calculation(self):
        """Test SAN = POW × 5"""
        test_cases = [
            (3, 15),   # 3 × 5 = 15
            (10, 50),  # 10 × 5 = 50
            (15, 75),  # 15 × 5 = 75
            (18, 90),  # 18 × 5 = 90
        ]
        
        for pow_val, expected_san in test_cases:
            character = CharacterSheet.objects.create(
                user=self.user,
                name=f"SAN Test POW={pow_val}",
                age=25,
                str_value=10, con_value=10, pow_value=pow_val, dex_value=10,
                app_value=10, siz_value=10, int_value=10, edu_value=10
            )
            self.assertEqual(character.san_starting, expected_san)
            self.assertEqual(character.san_max, expected_san)
            self.assertEqual(character.san_current, expected_san)
            
    def test_idea_luck_know_calculation(self):
        """Test 6th edition specific calculations"""
        character = CharacterSheet.objects.create(
            user=self.user,
            name="Derived Stats Test",
            age=25,
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17
        )
        
        char_6th = CharacterSheet6th.objects.get(character_sheet=character)
        
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
            character = CharacterSheet.objects.create(
                user=self.user,
                name=f"DB Test STR={str_val} SIZ={siz_val}",
                age=25,
                str_value=str_val, con_value=10, pow_value=10, dex_value=10,
                app_value=10, siz_value=siz_val, int_value=10, edu_value=10
            )
            char_6th = CharacterSheet6th.objects.get(character_sheet=character)
            self.assertEqual(char_6th.damage_bonus, expected_db)
            
    def test_occupation_points_calculation(self):
        """Test occupation point calculations for all types"""
        # Create character with specific abilities
        character = CharacterSheet.objects.create(
            user=self.user,
            name="Occupation Points Test",
            age=25,
            str_value=12, con_value=13, pow_value=14, dex_value=15,
            app_value=16, siz_value=11, int_value=17, edu_value=18,
            occupation="医師"  # Type 1: EDU × 20
        )
        
        # Type 1: EDU × 20
        points = character.calculate_occupation_points()
        self.assertEqual(points, 18 * 20)  # 360
        
        # Type 2: (EDU + APP) × 10
        character.occupation = "エンターテイナー"
        points = character.calculate_occupation_points()
        self.assertEqual(points, (18 + 16) * 10)  # 340
        
        # Type 3: (EDU or STR) × 20
        character.occupation = "兵士"
        points = character.calculate_occupation_points()
        self.assertEqual(points, max(18, 12) * 20)  # 360 (EDU is higher)
        
        # Type 4: (EDU or CON) × 20
        character.occupation = "エンジニア"
        points = character.calculate_occupation_points()
        self.assertEqual(points, max(18, 13) * 20)  # 360
        
        # Type 5: (EDU or DEX) × 20
        character.occupation = "スポーツ選手"
        points = character.calculate_occupation_points()
        self.assertEqual(points, max(18, 15) * 20)  # 360
        
        # Type 6: (DEX + APP) × 10
        character.occupation = "ディレッタント"
        points = character.calculate_occupation_points()
        self.assertEqual(points, (15 + 16) * 10)  # 310
        
        # Type 7: (INT or APP) × 10 + EDU × 10
        character.occupation = "作家"
        points = character.calculate_occupation_points()
        self.assertEqual(points, max(17, 16) * 10 + 18 * 10)  # 170 + 180 = 350
        
        # Type 8: (DEX or STR) × 10 + EDU × 10
        character.occupation = "トライブ・メンバー"
        points = character.calculate_occupation_points()
        self.assertEqual(points, max(15, 12) * 10 + 18 * 10)  # 150 + 180 = 330
        
    def test_hobby_points_calculation(self):
        """Test hobby points = INT × 10"""
        test_cases = [3, 8, 12, 16, 18]
        
        for int_val in test_cases:
            character = CharacterSheet.objects.create(
                user=self.user,
                name=f"Hobby Test INT={int_val}",
                age=25,
                str_value=10, con_value=10, pow_value=10, dex_value=10,
                app_value=10, siz_value=10, int_value=int_val, edu_value=10
            )
            self.assertEqual(character.hobby_points, int_val * 10)


class Character6thSkillManagementTestCase(TestCase):
    """Test skill allocation and management"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name="Skill Test Character",
            age=25,
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17,
            occupation="医師"  # EDU × 20 = 340 points
        )
        
    def test_skill_creation_and_validation(self):
        """Test skill creation with valid point allocations"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name="医学",
            base_value=5,
            occupation_points=70,
            interest_points=20,
            bonus_points=0,
            other_points=0
        )
        
        # Total should be base + all points
        self.assertEqual(skill.total_value, 5 + 70 + 20 + 0 + 0)  # 95
        
        # Points cannot be negative
        skill.occupation_points = -10
        with self.assertRaises(ValidationError):
            skill.full_clean()
            
        # Total cannot exceed 99 for regular skills
        skill.occupation_points = 94
        skill.interest_points = 0
        skill.base_value = 5
        skill.full_clean()  # Total = 99, should be valid
        
        skill.occupation_points = 95
        with self.assertRaises(ValidationError) as cm:
            skill.full_clean()
        self.assertIn('技能値の合計は99を超えることはできません', str(cm.exception))
        
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
        hobby_available = self.character.hobby_points - total_interest
        
        self.assertEqual(occupation_available, 340 - 140)  # 200
        self.assertEqual(hobby_available, 160 - 60)        # 100
        
    def test_cthulhu_mythos_special_case(self):
        """Test Cthulhu Mythos skill cannot use occupation/interest points"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name="クトゥルフ神話",
            base_value=0,
            occupation_points=0,
            interest_points=0,
            bonus_points=5,  # Only bonus points allowed
            other_points=10   # And other points
        )
        skill.full_clean()  # Should be valid
        
        # Try to add occupation points
        skill.occupation_points = 10
        with self.assertRaises(ValidationError) as cm:
            skill.full_clean()
        self.assertIn('クトゥルフ神話技能には職業ポイント・興味ポイントを割り当てることはできません', str(cm.exception))
        
        # Try to add interest points
        skill.occupation_points = 0
        skill.interest_points = 10
        with self.assertRaises(ValidationError) as cm:
            skill.full_clean()
        self.assertIn('クトゥルフ神話技能には職業ポイント・興味ポイントを割り当てることはできません', str(cm.exception))
        
    def test_san_max_reduction_with_cthulhu_mythos(self):
        """Test SAN max = 99 - Cthulhu Mythos"""
        # Initial SAN max should be POW × 5
        self.assertEqual(self.character.san_max, 14 * 5)  # 70
        
        # Add Cthulhu Mythos skill
        cthulhu_skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name="クトゥルフ神話",
            base_value=0,
            bonus_points=15
        )
        
        # Refresh and check SAN max
        self.character.refresh_from_db()
        expected_san_max = 99 - cthulhu_skill.total_value
        self.assertEqual(self.character.calculate_san_max(), expected_san_max)


class Character6thEquipmentTestCase(TestCase):
    """Test equipment and inventory management"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name="Equipment Test",
            age=25,
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17
        )
        
    def test_equipment_creation(self):
        """Test equipment creation and validation"""
        weapon = CharacterEquipment.objects.create(
            character_sheet=self.character,
            equipment_type='weapon',
            name="拳銃 (.38リボルバー)",
            damage="1D10",
            attacks_per_round=2,
            weight=Decimal('0.5'),
            quantity=1
        )
        
        self.assertEqual(weapon.total_weight, Decimal('0.5'))
        
        # Test armor
        armor = CharacterEquipment.objects.create(
            character_sheet=self.character,
            equipment_type='armor',
            name="革のジャケット",
            armor_value=1,
            weight=Decimal('2.0'),
            quantity=1
        )
        
        self.assertEqual(armor.armor_value, 1)
        
        # Test item with quantity
        item = CharacterEquipment.objects.create(
            character_sheet=self.character,
            equipment_type='item',
            name="弾薬",
            weight=Decimal('0.1'),
            quantity=20
        )
        
        self.assertEqual(item.total_weight, Decimal('2.0'))  # 0.1 × 20
        
    def test_movement_penalty_calculation(self):
        """Test movement penalty based on total weight"""
        # Add various items
        items = [
            ("重い荷物", Decimal('10'), 1),
            ("テント", Decimal('5'), 1),
            ("食料", Decimal('2'), 3),
            ("水", Decimal('1'), 5),
        ]
        
        for name, weight, qty in items:
            CharacterEquipment.objects.create(
                character_sheet=self.character,
                equipment_type='item',
                name=name,
                weight=weight,
                quantity=qty
            )
            
        # Calculate total weight
        total_weight = CharacterEquipment.objects.filter(
            character_sheet=self.character
        ).aggregate(
            total=models.Sum(models.F('weight') * models.F('quantity'))
        )['total']
        
        self.assertEqual(total_weight, Decimal('26'))  # 10 + 5 + 6 + 5
        
        # Check movement penalty (example: -1 per 10kg)
        penalty = int(total_weight // 10)
        self.assertEqual(penalty, 2)


class Character6thVersioningTestCase(TestCase):
    """Test character versioning functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.original = CharacterSheet.objects.create(
            user=self.user,
            name="Original Character",
            age=25,
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17
        )
        
    def test_create_version(self):
        """Test creating a new version of a character"""
        # Create skills for original
        CharacterSkill.objects.create(
            character_sheet=self.original,
            skill_name="医学",
            base_value=5,
            occupation_points=70
        )
        
        # Create version
        version = self.original.create_version()
        
        # Check version properties
        self.assertEqual(version.parent_sheet, self.original)
        self.assertEqual(version.version_number, 2)
        self.assertEqual(version.name, self.original.name)
        self.assertEqual(version.age, self.original.age)
        
        # Check skills are copied
        original_skills = CharacterSkill.objects.filter(character_sheet=self.original)
        version_skills = CharacterSkill.objects.filter(character_sheet=version)
        self.assertEqual(original_skills.count(), version_skills.count())
        
        # Check 6th edition data is copied
        original_6th = CharacterSheet6th.objects.get(character_sheet=self.original)
        version_6th = CharacterSheet6th.objects.get(character_sheet=version)
        self.assertEqual(original_6th.damage_bonus, version_6th.damage_bonus)
        
    def test_version_hierarchy(self):
        """Test multiple versions and hierarchy"""
        v2 = self.original.create_version()
        v3 = v2.create_version()
        
        # Check version numbers
        self.assertEqual(self.original.version_number, 1)
        self.assertEqual(v2.version_number, 2)
        self.assertEqual(v3.version_number, 3)
        
        # Check parent relationships
        self.assertIsNone(self.original.parent_sheet)
        self.assertEqual(v2.parent_sheet, self.original)
        self.assertEqual(v3.parent_sheet, v2)
        
        # Get all versions
        versions = self.original.get_all_versions()
        self.assertEqual(len(versions), 3)
        
    def test_circular_reference_prevention(self):
        """Test prevention of circular version references"""
        v2 = self.original.create_version()
        
        # Try to set original's parent to v2 (circular)
        self.original.parent_sheet = v2
        with self.assertRaises(ValidationError):
            self.original.full_clean()


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
            'occupation': '医師',
            'birthplace': '東京',
            'residence': '横浜',
            'str_value': 13,
            'con_value': 12,
            'pow_value': 14,
            'dex_value': 11,
            'app_value': 10,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 17
        }
        
        response = self.client.post('/api/characters/create_6th_edition/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check character was created
        character = CharacterSheet.objects.get(id=response.data['id'])
        self.assertEqual(character.name, 'API Test Character')
        self.assertEqual(character.user, self.user)
        
        # Check 6th edition data was created
        char_6th = CharacterSheet6th.objects.get(character_sheet=character)
        self.assertIsNotNone(char_6th)
        self.assertEqual(char_6th.idea_roll, 16 * 5)
        
    def test_character_list_permissions(self):
        """Test character list shows only user's characters"""
        # Create characters for both users
        char1 = CharacterSheet.objects.create(
            user=self.user, name="My Character", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        char2 = CharacterSheet.objects.create(
            user=self.other_user, name="Other Character", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        response = self.client.get('/api/characters/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], "My Character")
        
    def test_public_character_access(self):
        """Test public character visibility"""
        # Create private character
        private_char = CharacterSheet.objects.create(
            user=self.other_user, name="Private Character", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10,
            is_public=False
        )
        
        # Create public character
        public_char = CharacterSheet.objects.create(
            user=self.other_user, name="Public Character", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10,
            is_public=True
        )
        
        # Try to access private character
        response = self.client.get(f'/api/characters/{private_char.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Try to access public character
        response = self.client.get(f'/api/characters/{public_char.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Public Character")
        
    def test_skill_points_allocation_api(self):
        """Test skill point allocation endpoints"""
        character = CharacterSheet.objects.create(
            user=self.user, name="Skill API Test", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=16,
            occupation="医師"
        )
        
        # Check skill points summary
        response = self.client.get(f'/api/characters/{character.id}/skill_points_summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['occupation_points']['total'], 16 * 20)  # 320
        self.assertEqual(response.data['hobby_points']['total'], 10 * 10)       # 100
        
        # Allocate skill points
        data = {
            'skill_name': '医学',
            'base_value': 5,
            'occupation_points': 70,
            'interest_points': 20
        }
        response = self.client.post(
            f'/api/characters/{character.id}/allocate_skill_points/',
            data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check skill was created
        skill = CharacterSkill.objects.get(
            character_sheet=character,
            skill_name='医学'
        )
        self.assertEqual(skill.occupation_points, 70)
        self.assertEqual(skill.interest_points, 20)
        self.assertEqual(skill.total_value, 95)
        
    def test_batch_skill_allocation(self):
        """Test batch skill point allocation"""
        character = CharacterSheet.objects.create(
            user=self.user, name="Batch Skill Test", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=16,
            occupation="医師"
        )
        
        data = {
            'skills': [
                {
                    'skill_name': '医学',
                    'base_value': 5,
                    'occupation_points': 70,
                    'interest_points': 0
                },
                {
                    'skill_name': '応急手当',
                    'base_value': 30,
                    'occupation_points': 40,
                    'interest_points': 0
                },
                {
                    'skill_name': '心理学',
                    'base_value': 5,
                    'occupation_points': 30,
                    'interest_points': 20
                }
            ]
        }
        
        response = self.client.post(
            f'/api/characters/{character.id}/batch_allocate_skill_points/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check all skills were created
        skills = CharacterSkill.objects.filter(character_sheet=character)
        self.assertEqual(skills.count(), 3)
        
        # Verify total points used
        total_occupation = sum(s.occupation_points for s in skills)
        total_interest = sum(s.interest_points for s in skills)
        self.assertEqual(total_occupation, 140)  # 70 + 40 + 30
        self.assertEqual(total_interest, 20)     # 0 + 0 + 20
        
    def test_ccfolia_export(self):
        """Test CCFOLIA JSON export"""
        character = CharacterSheet.objects.create(
            user=self.user, name="CCFOLIA Test", age=25,
            str_value=13, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=15, int_value=16, edu_value=17,
            occupation="医師"
        )
        
        # Add some skills
        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name="医学",
            base_value=5,
            occupation_points=70
        )
        
        response = self.client.get(f'/api/characters/{character.id}/ccfolia_json/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check CCFOLIA format
        data = response.json()
        self.assertEqual(data['name'], 'CCFOLIA Test')
        self.assertEqual(data['params'][0]['label'], 'STR')
        self.assertEqual(data['params'][0]['value'], 13)
        self.assertIn('医学', [s['name'] for s in data['skills']])
        
    def test_combat_summary(self):
        """Test combat summary endpoint"""
        character = CharacterSheet.objects.create(
            user=self.user, name="Combat Test", age=25,
            str_value=16, con_value=12, pow_value=14, dex_value=11,
            app_value=10, siz_value=17, int_value=10, edu_value=10
        )
        
        # Add weapons
        CharacterEquipment.objects.create(
            character_sheet=character,
            equipment_type='weapon',
            name="拳銃",
            damage="1D10",
            attacks_per_round=2
        )
        
        response = self.client.get(f'/api/characters/{character.id}/combat_summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['damage_bonus'], '+1D4')  # STR+SIZ=33
        self.assertEqual(len(response.data['weapons']), 1)
        
    def test_authentication_required(self):
        """Test endpoints require authentication"""
        self.client.logout()
        
        # Test list endpoint
        response = self.client.get('/api/characters/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test create endpoint
        response = self.client.post('/api/characters/create_6th_edition/', {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_character_deletion(self):
        """Test character deletion and cascades"""
        character = CharacterSheet.objects.create(
            user=self.user, name="Delete Test", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        # Add related data
        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name="医学",
            base_value=5
        )
        CharacterEquipment.objects.create(
            character_sheet=character,
            equipment_type='item',
            name="Test Item"
        )
        
        # Delete character
        response = self.client.delete(f'/api/characters/{character.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check cascades
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
        # Step 1: Create character
        character_data = {
            'name': 'Complete Workflow Test',
            'age': 30,
            'gender': 'female',
            'occupation': '医師',
            'birthplace': '大阪',
            'residence': '京都',
            'str_value': 13,
            'con_value': 14,
            'pow_value': 15,
            'dex_value': 12,
            'app_value': 11,
            'siz_value': 16,
            'int_value': 17,
            'edu_value': 18
        }
        
        response = self.client.post('/api/characters/create_6th_edition/', character_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character_id = response.data['id']
        
        # Step 2: Add skills
        skills_data = {
            'skills': [
                {'skill_name': '医学', 'base_value': 5, 'occupation_points': 80, 'interest_points': 0},
                {'skill_name': '応急手当', 'base_value': 30, 'occupation_points': 50, 'interest_points': 0},
                {'skill_name': '心理学', 'base_value': 5, 'occupation_points': 40, 'interest_points': 10},
                {'skill_name': '図書館', 'base_value': 25, 'occupation_points': 0, 'interest_points': 30},
            ]
        }
        
        response = self.client.post(
            f'/api/characters/{character_id}/batch_allocate_skill_points/',
            skills_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 3: Add equipment
        equipment_data = [
            {
                'equipment_type': 'weapon',
                'name': '拳銃',
                'damage': '1D10',
                'attacks_per_round': 2,
                'weight': '0.5'
            },
            {
                'equipment_type': 'armor',
                'name': '防弾チョッキ',
                'armor_value': 8,
                'weight': '3.0'
            },
            {
                'equipment_type': 'item',
                'name': '医療キット',
                'weight': '2.0',
                'quantity': 1
            }
        ]
        
        for item in equipment_data:
            response = self.client.post(
                f'/api/characters/{character_id}/equipment/',
                item
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
        # Step 4: Add background
        background_data = {
            'description': 'テスト用の背景情報',
            'personal_data': '家族構成: 独身',
            'ideology_beliefs': '科学を信じる',
            'important_people': '恩師の山田教授',
            'meaningful_locations': '大学の研究室',
            'treasured_possessions': '恩師からもらった聴診器',
            'traits': '慎重で理性的'
        }
        
        response = self.client.post(
            f'/api/characters/{character_id}/background/',
            background_data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 5: Verify complete character
        response = self.client.get(f'/api/characters/{character_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        character = response.data
        self.assertEqual(character['name'], 'Complete Workflow Test')
        self.assertEqual(len(character['skills']), 4)
        self.assertEqual(len(character['equipment']), 3)
        self.assertIsNotNone(character['background'])
        
    def test_character_growth_workflow(self):
        """Test character growth through sessions"""
        # Create initial character
        character = CharacterSheet.objects.create(
            user=self.user, name="Growth Test", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        # Create initial skills
        skill1 = CharacterSkill.objects.create(
            character_sheet=character,
            skill_name="聞き耳",
            base_value=25,
            occupation_points=20
        )
        
        # Simulate session participation
        growth1 = GrowthRecord.objects.create(
            character_sheet=character,
            session_date='2024-01-01',
            session_title='初めてのセッション',
            changes={'skills': {'聞き耳': {'before': 45, 'after': 47}}}
        )
        
        # Update skill
        skill1.other_points += 2
        skill1.save()
        
        # Create version after growth
        v2 = character.create_version()
        v2.session_count = 1
        v2.save()
        
        # Add more growth
        growth2 = GrowthRecord.objects.create(
            character_sheet=v2,
            session_date='2024-01-15',
            session_title='2回目のセッション',
            changes={
                'skills': {'聞き耳': {'before': 47, 'after': 50}},
                'san': {'before': 50, 'after': 45}
            }
        )
        
        # Check growth summary
        response = self.client.get(f'/api/characters/{v2.id}/growth_summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        summary = response.data
        self.assertEqual(summary['total_sessions'], 1)
        self.assertEqual(summary['version_count'], 2)
        self.assertEqual(len(summary['growth_records']), 1)  # Only v2's records


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
            'str_value': 0,  # Invalid: below minimum
            'con_value': 10,
            'pow_value': 10,
            'dex_value': 10,
            'app_value': 10,
            'siz_value': 10,
            'int_value': 10,
            'edu_value': 10
        }
        
        response = self.client.post('/api/characters/create_6th_edition/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('str_value', response.data)
        
    def test_skill_overallocation(self):
        """Test prevention of skill point over-allocation"""
        character = CharacterSheet.objects.create(
            user=self.user, name="Overallocation Test", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10,
            occupation="医師"  # EDU × 20 = 200 points
        )
        
        # Try to allocate more than available
        data = {
            'skill_name': '医学',
            'base_value': 5,
            'occupation_points': 250,  # More than available
            'interest_points': 0
        }
        
        response = self.client.post(
            f'/api/characters/{character.id}/allocate_skill_points/',
            data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_concurrent_modification(self):
        """Test handling of concurrent modifications"""
        character = CharacterSheet.objects.create(
            user=self.user, name="Concurrent Test", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        # Simulate concurrent skill creation
        skill_data = {
            'skill_name': '医学',
            'base_value': 5,
            'occupation_points': 50,
            'interest_points': 0
        }
        
        # Create skill in database directly
        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name='医学',
            base_value=5,
            occupation_points=30
        )
        
        # Try to create same skill via API
        response = self.client.post(
            f'/api/characters/{character.id}/allocate_skill_points/',
            skill_data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_large_data_handling(self):
        """Test handling of large amounts of data"""
        character = CharacterSheet.objects.create(
            user=self.user, name="Large Data Test", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        # Create many skills
        skills_data = {
            'skills': [
                {
                    'skill_name': f'スキル{i}',
                    'base_value': 5,
                    'occupation_points': 1,
                    'interest_points': 0
                }
                for i in range(50)  # 50 skills
            ]
        }
        
        response = self.client.post(
            f'/api/characters/{character.id}/batch_allocate_skill_points/',
            skills_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all were created
        skill_count = CharacterSkill.objects.filter(character_sheet=character).count()
        self.assertEqual(skill_count, 50)
        
    def test_file_upload_validation(self):
        """Test image upload validation"""
        character = CharacterSheet.objects.create(
            user=self.user, name="Image Test", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        # Test with mock file
        with patch('django.core.files.uploadedfile.SimpleUploadedFile') as mock_file:
            mock_file.return_value.size = 10 * 1024 * 1024  # 10MB
            
            response = self.client.post(
                f'/api/characters/{character.id}/images/',
                {'image': mock_file.return_value}
            )
            
            # Should fail if file is too large
            self.assertIn(response.status_code, 
                         [status.HTTP_400_BAD_REQUEST, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE])


class Character6thPerformanceTestCase(TestCase):
    """Test performance with large datasets"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_bulk_character_operations(self):
        """Test performance with many characters"""
        # Create multiple characters
        characters = []
        for i in range(20):
            char = CharacterSheet(
                user=self.user,
                name=f"Character {i}",
                age=25,
                str_value=10, con_value=10, pow_value=10, dex_value=10,
                app_value=10, siz_value=10, int_value=10, edu_value=10
            )
            characters.append(char)
            
        # Bulk create
        CharacterSheet.objects.bulk_create(characters)
        
        # Test query performance
        with self.assertNumQueries(3):  # Reasonable number of queries
            chars = CharacterSheet.objects.filter(user=self.user).select_related('sheet_6th')
            list(chars)  # Force evaluation
            
    def test_skill_calculation_performance(self):
        """Test performance of skill calculations"""
        character = CharacterSheet.objects.create(
            user=self.user, name="Performance Test", age=25,
            str_value=10, con_value=10, pow_value=10, dex_value=10,
            app_value=10, siz_value=10, int_value=10, edu_value=10
        )
        
        # Create many skills
        skills = []
        for i in range(100):
            skill = CharacterSkill(
                character_sheet=character,
                skill_name=f"Skill {i}",
                base_value=5,
                occupation_points=1
            )
            skills.append(skill)
            
        CharacterSkill.objects.bulk_create(skills)
        
        # Test calculation performance
        import time
        start = time.time()
        
        total_occupation = sum(s.occupation_points for s in character.skills.all())
        total_interest = sum(s.interest_points for s in character.skills.all())
        
        elapsed = time.time() - start
        self.assertLess(elapsed, 1.0)  # Should complete within 1 second


# Import the django test command to ensure proper test discovery
from django.core.management import call_command