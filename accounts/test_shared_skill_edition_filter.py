from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.character_models import CharacterSheet, CharacterSheet6th, CharacterSheet7th
from accounts.share_serializers import SharedCharacterSheetSerializer


class SharedCharacterSkillEditionFilterTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="skill-filter-user")

    def create_character(self, edition, name):
        character = CharacterSheet.objects.create(user=self.user, edition=edition)
        detail_model = CharacterSheet6th if edition == "6th" else CharacterSheet7th
        detail_model.objects.create(
            character_sheet=character,
            name=name,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=50,
        )
        return character

    def test_seventh_edition_share_excludes_sixth_edition_basic_skills(self):
        character = self.create_character("7th", "7th Investigator")
        character.system_data.skills.create(skill_name="こぶし（パンチ）", base_value=50)
        character.system_data.skills.create(skill_name="近接戦闘（格闘）", base_value=25)
        character.system_data.skills.create(skill_name="オリジナル技能", base_value=10)

        skill_names = {skill["skill_name"] for skill in SharedCharacterSheetSerializer(character).data["skills"]}

        self.assertNotIn("こぶし（パンチ）", skill_names)
        self.assertIn("近接戦闘（格闘）", skill_names)
        self.assertIn("オリジナル技能", skill_names)

    def test_sixth_edition_share_excludes_seventh_edition_basic_skills(self):
        character = self.create_character("6th", "6th Investigator")
        character.system_data.skills.create(skill_name="こぶし（パンチ）", base_value=50)
        character.system_data.skills.create(skill_name="近接戦闘（格闘）", base_value=25)

        skill_names = {skill["skill_name"] for skill in SharedCharacterSheetSerializer(character).data["skills"]}

        self.assertIn("こぶし（パンチ）", skill_names)
        self.assertNotIn("近接戦闘（格闘）", skill_names)
