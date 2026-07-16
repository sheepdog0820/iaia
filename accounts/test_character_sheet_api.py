"""
キャラクターシートAPI テストスクリプト

実装したキャラクターシートREST APIの動作テスト
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .character_models import (
    CharacterBackground,
    CharacterSheet,
    CharacterSheet6th,
    CharacterSheet7th,
    CharacterSkill6th,
    CharacterSkill7th,
)

User = get_user_model()


class CharacterSheetAPITest(APITestCase):
    """キャラクターシートAPI統合テスト"""

    def setUp(self):
        """テストデータ準備"""
        # テストユーザー作成
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123", nickname="テストユーザー"
        )

        # 認証
        self.client.force_authenticate(user=self.user)

        # テスト用キャラクターシートデータ
        # 6版は3d6の値（3-18）を使用
        self.character_data_6th = {
            "edition": "6th",
            "name": "テスト探索者6版",
            "player_name": "テストプレイヤー",
            "age": 28,
            "gender": "男性",
            "occupation": "私立探偵",
            "birthplace": "東京",
            "residence": "横浜",
            "str_value": 13,  # 3d6の値
            "con_value": 14,  # 3d6の値
            "pow_value": 15,  # 3d6の値
            "dex_value": 16,  # 3d6の値
            "app_value": 12,  # 3d6の値
            "siz_value": 13,  # 3d6の値
            "int_value": 17,  # 3d6の値
            "edu_value": 16,  # 3d6の値
            "hit_points_current": 14,  # (CON14 + SIZ13) / 2 = 13.5 → 14
            "magic_points_current": 15,  # POW15
            "sanity_current": 75,  # POW15 * 5
            "notes": "6版テストキャラクター",
        }

        self.character_data_7th = {
            "edition": "7th",
            "name": "テスト探索者7版",
            "player_name": "テストプレイヤー",
            "age": 25,
            "gender": "女性",
            "occupation": "大学生",
            "birthplace": "大阪",
            "residence": "京都",
            "str_value": 60,
            "con_value": 65,
            "pow_value": 70,
            "dex_value": 85,
            "app_value": 80,
            "siz_value": 55,
            "int_value": 90,
            "edu_value": 85,
            "hit_points_current": 12,
            "magic_points_current": 14,
            "sanity_current": 70,
            "notes": "7版テストキャラクター",
            "seventh_edition_data": {
                "luck_points": 75,
                "personal_description": "好奇心旺盛な大学生",
                "ideology_beliefs": "真実を追求する",
                "significant_people": "指導教授",
                "meaningful_locations": "大学図書館",
                "treasured_possessions": "祖母の指輪",
                "traits": "几帳面",
                "injuries_scars": "なし",
                "phobias_manias": "高所恐怖症",
            },
        }

    def create_test_gif(self, filename="test.gif"):
        gif_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01"
            b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01"
            b"\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        return SimpleUploadedFile(filename, gif_bytes, content_type="image/gif")

    def create_character(self, data=None, **kwargs):
        """Create a registry and its authoritative edition detail for tests."""
        values = dict(data or kwargs)
        values.pop("user", None)
        edition = values.pop("edition")
        values.pop("seventh_edition_data", None)
        registry = CharacterSheet.objects.create(user=self.user, edition=edition)
        detail_model = CharacterSheet6th if edition == "6th" else CharacterSheet7th
        detail = detail_model(character_sheet=registry, **values)
        stats = detail.calculate_derived_stats()
        detail.hit_points_max = detail.hit_points_current = stats["hit_points_max"]
        detail.magic_points_max = detail.magic_points_current = stats["magic_points_max"]
        detail.sanity_starting = detail.sanity_current = stats["sanity_starting"]
        detail.sanity_max = stats["sanity_max"]
        detail.save()
        return registry

    def test_create_character_rejects_invalid_skills_data_without_partial_character(self):
        data = dict(self.character_data_6th)
        data["name"] = "Invalid Skills JSON PC"
        data["skills_data"] = "[{invalid"

        response = self.client.post("/api/accounts/character-sheets/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("skills_data", str(response.data))
        self.assertFalse(CharacterSheet.objects.by_system_name("Invalid Skills JSON PC").exists())

    def test_create_character_rejects_invalid_skill_without_partial_character(self):
        data = dict(self.character_data_6th)
        data["name"] = "Invalid Skill PC"
        data["skills_data"] = json.dumps(
            [
                {
                    "skill_name": "Invalid Skill",
                    "base_value": -1,
                    "occupation_points": 0,
                    "interest_points": 0,
                    "bonus_points": 0,
                    "other_points": 0,
                }
            ]
        )

        response = self.client.post("/api/accounts/character-sheets/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("skills_data", str(response.data))
        self.assertFalse(CharacterSheet.objects.by_system_name("Invalid Skill PC", user=self.user).exists())
        self.assertFalse(CharacterSkill6th.objects.filter(skill_name="Invalid Skill").exists())
        self.assertFalse(CharacterSkill7th.objects.filter(skill_name="Invalid Skill").exists())

    def test_create_version_copies_full_skill_data(self):
        data = dict(self.character_data_6th)
        data["name"] = "Version Source PC"
        character = self.create_character(data)
        category = "探索系"
        character.system_data.skills.model.objects.create(
            character_sheet=character.system_data,
            skill_name="Custom Version Skill",
            category=category,
            base_value=10,
            occupation_points=5,
            interest_points=3,
            bonus_points=7,
            other_points=2,
            notes="growth memo",
        )

        response = self.client.post(
            f"/api/accounts/character-sheets/{character.id}/create_version/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_sheet = CharacterSheet.objects.get(id=response.data["id"])
        copied_skill = new_sheet.system_data.skills.get(skill_name="Custom Version Skill")
        self.assertEqual(copied_skill.category, category)
        self.assertEqual(copied_skill.bonus_points, 7)
        self.assertEqual(copied_skill.other_points, 2)
        self.assertEqual(copied_skill.notes, "growth memo")

    def test_create_version_copies_security_and_related_data(self):
        data = dict(self.character_data_6th)
        data["name"] = "Complete Version Source"
        character = self.create_character(data)
        allowed_user = User.objects.create_user(username="allowed", password="testpass123")
        character.access_scope = "link"
        detail = character.system_data
        detail.secret_ho_info = "secret handout"
        detail.recommended_skills = ["Spot Hidden"]
        detail.occupation_skills = ["Library Use"]
        detail.save()
        character.save()
        character.allowed_users.add(allowed_user)
        CharacterBackground.objects.create(character_sheet=character, personal_history="A long history")
        gif = b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        character.system_data.images.model.objects.create(
            character_sheet=character.system_data,
            image=SimpleUploadedFile("main.gif", gif, content_type="image/gif"),
            is_main=True,
            order=0,
        )
        character.system_data.images.model.objects.create(
            character_sheet=character.system_data,
            image=SimpleUploadedFile("sub.gif", gif, content_type="image/gif"),
            order=1,
        )

        response = self.client.post(
            f"/api/accounts/character-sheets/{character.id}/create_version/",
            {"version_note": "after session", "user": allowed_user.id, "version": 999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_sheet = CharacterSheet.objects.get(id=response.data["id"])
        self.assertEqual(new_sheet.user, self.user)
        self.assertEqual(new_sheet.system_data.version, 2)
        self.assertEqual(new_sheet.system_data.parent_data.character_sheet, character)
        self.assertEqual(new_sheet.access_scope, "link")
        self.assertEqual(new_sheet.system_data.secret_ho_info, "secret handout")
        self.assertEqual(new_sheet.system_data.recommended_skills, ["Spot Hidden"])
        self.assertEqual(new_sheet.system_data.occupation_skills, ["Library Use"])
        self.assertEqual(list(new_sheet.allowed_users.all()), [allowed_user])
        self.assertNotEqual(new_sheet.share_token, character.share_token)
        self.assertEqual(new_sheet.background_info.personal_history, "A long history")
        self.assertEqual(
            list(new_sheet.system_data.images.values_list("order", "is_main")),
            [(0, True), (1, False)],
        )

    def test_create_version_rejects_invalid_version_input(self):
        character = self.create_character(self.character_data_6th)

        response = self.client.post(
            f"/api/accounts/character-sheets/{character.id}/create_version/",
            {"version_note": "x" * 1001, "copy_skills": "not-a-boolean"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CharacterSheet.objects.filter(sixth_edition_data__parent_data__character_sheet=character).exists())

    def test_create_version_rolls_back_when_skill_copy_fails(self):
        data = dict(self.character_data_6th)
        data["name"] = "Rollback Source PC"
        character = self.create_character(data)
        character.system_data.skills.model.objects.create(
            character_sheet=character.system_data,
            skill_name="Rollback Skill",
            base_value=10,
        )

        with patch(
            "accounts.character_models.CharacterSkill6th.objects.create",
            side_effect=RuntimeError("copy failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    f"/api/accounts/character-sheets/{character.id}/create_version/",
                    {},
                    format="json",
                )

        self.assertFalse(CharacterSheet.objects.filter(sixth_edition_data__parent_data__character_sheet=character).exists())

    def test_create_6th_edition_character(self):
        """6版キャラクターシート作成テスト"""
        url = "/api/accounts/character-sheets/"
        response = self.client.post(url, self.character_data_6th, format="json")

        # デバッグ出力

        if response.status_code != status.HTTP_201_CREATED:
            # Fail the test with detailed error message
            self.fail(f"Character creation failed with status {response.status_code}: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["edition"], "6th")
        self.assertEqual(response.data["name"], "テスト探索者6版")

        # データベースでも確認
        character = CharacterSheet.objects.get(id=response.data["id"])
        self.assertEqual(character.edition, "6th")
        self.assertEqual(character.system_data.hit_points_max, 14)  # ceil((CON14 + SIZ13) / 2) = 14
        self.assertEqual(character.system_data.magic_points_max, 15)  # POW15

        return response.data["id"]

    def test_create_6th_edition_character_with_image(self):
        """6版キャラクター作成（画像付き）のテスト"""
        data = dict(self.character_data_6th)
        data["character_images"] = self.create_test_gif("test.gif")

        response = self.client.post(
            "/api/accounts/character-sheets/create_6th_edition/",
            data,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character = CharacterSheet.objects.get(id=response.data["id"])
        self.assertTrue(character.system_data.images.exists())

    def test_create_6th_edition_character_with_non_default_occupation_point_method(self):
        """6版作成APIは選択された職業技能ポイント方式で技能超過を判定する"""
        data = dict(self.character_data_6th)
        data.update(
            {
                "name": "6th DEX method PC",
                "edu_value": 10,
                "dex_value": 18,
                "occupation_point_method": "edu10dex10",
                "skills": [
                    {
                        "skill_name": "回避",
                        "base_value": 36,
                        "occupation_points": 280,
                        "interest_points": 0,
                        "other_points": 0,
                    }
                ],
            }
        )

        response = self.client.post(
            "/api/accounts/character-sheets/create_6th_edition/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character = CharacterSheet.objects.get(id=response.data["id"])
        self.assertEqual(character.system_data.occupation_point_method, "edu10dex10")
        self.assertEqual(character.system_data.calculate_occupation_points(), 280)
        self.assertEqual(character.system_data.calculate_used_occupation_points(), 280)

    def test_create_6th_edition_rejects_normal_user_over_image_limit(self):
        """通常ユーザーは作成APIで3枚以上の画像を添付できない"""
        data = dict(self.character_data_6th)
        data["name"] = "通常ユーザー画像上限"
        data["character_images"] = [self.create_test_gif(f"normal-limit-{i}.gif") for i in range(3)]

        response = self.client.post(
            "/api/accounts/character-sheets/create_6th_edition/",
            data,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("最大2枚", str(response.data))
        self.assertFalse(CharacterSheet.objects.by_system_name("通常ユーザー画像上限", user=self.user).exists())

    def test_create_7th_edition_allows_ten_images_for_premium_user(self):
        """プレミアムユーザーは作成APIで10枚まで画像を添付できる"""
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        data = {key: value for key, value in self.character_data_7th.items() if key != "seventh_edition_data"}
        data["name"] = "プレミアム画像10枚"
        data["character_images"] = [self.create_test_gif(f"premium-create-{i}.gif") for i in range(10)]

        response = self.client.post(
            "/api/accounts/character-sheets/create_7th_edition/",
            data,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character = CharacterSheet.objects.get(id=response.data["id"])
        self.assertEqual(character.system_data.images.count(), 10)

    def test_create_6th_edition_character_with_equipment(self):
        """6版作成APIで武器・防具・アイテムを同時登録できる"""
        data = dict(self.character_data_6th)
        data["equipment"] = [
            {
                "item_type": "weapon",
                "name": "Pistol",
                "skill_name": "拳銃",
                "damage": "1D10",
                "base_range": "15m",
                "attacks_per_round": 2,
                "ammo": 8,
                "malfunction_number": 100,
                "quantity": 1,
                "weight": 0.5,
                "description": "Test weapon",
            },
            {
                "item_type": "armor",
                "name": "Kevlar Vest",
                "armor_points": 8,
                "quantity": 1,
                "weight": 3.0,
                "description": "Test armor",
            },
            {
                "item_type": "item",
                "name": "Flashlight",
                "quantity": 1,
                "weight": 0.2,
                "description": "Test item",
            },
        ]

        response = self.client.post(
            "/api/accounts/character-sheets/create_6th_edition/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character_id = response.data["id"]
        equipment = CharacterSheet.objects.get(pk=character_id).system_data.equipment

        self.assertEqual(equipment.count(), 3)
        pistol = equipment.get(name="Pistol")
        self.assertEqual(pistol.item_type, "weapon")
        self.assertAlmostEqual(pistol.weight, 0.5, places=3)
        vest = equipment.get(name="Kevlar Vest")
        self.assertEqual(vest.item_type, "armor")
        self.assertAlmostEqual(vest.weight, 3.0, places=3)
        flashlight = equipment.get(name="Flashlight")
        self.assertEqual(flashlight.item_type, "item")
        self.assertAlmostEqual(flashlight.weight, 0.2, places=3)

    def test_create_7th_edition_character(self):
        """7版キャラクターシート作成テスト"""
        url = "/api/accounts/character-sheets/create_7th_edition/"
        response = self.client.post(url, self.character_data_7th, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["edition"], "7th")
        self.assertEqual(response.data["name"], "テスト探索者7版")
        self.assertEqual(response.data["character_7th"]["damage_bonus"], "+0")
        self.assertEqual(response.data["character_7th"]["build"], 0)
        self.assertEqual(response.data["character_7th"]["move_rate"], 9)
        self.assertEqual(response.data["character_7th"]["dodge"], 42)
        self.assertIsNone(response.data["character_6th"])

        character = CharacterSheet.objects.get(id=response.data["id"])
        self.assertEqual(character.edition, "7th")
        detail = character.system_data
        self.assertEqual(detail.hit_points_max, (detail.con_value + detail.siz_value) // 10)
        self.assertEqual(detail.magic_points_max, detail.pow_value // 5)
        self.assertEqual(detail.sanity_starting, detail.pow_value)
        self.assertEqual(character.system_data.calculate_occupation_points(), character.system_data.edu_value * 4)
        self.assertEqual(detail.calculate_hobby_points(), detail.int_value * 2)
        self.assertEqual(detail.calculate_damage_bonus_7th(), "+0")
        self.assertEqual(detail.calculate_build_7th(), 0)
        self.assertEqual(detail.calculate_move_rate_7th(), 9)
        self.assertFalse(CharacterSheet6th.objects.filter(character_sheet=character).exists())

    def test_7th_edition_boundary_derived_stats_are_official_percentile_values(self):
        """7版派生値はパーセンテージ能力値をそのまま扱う"""
        character = self.create_character(
            user=self.user,
            edition="7th",
            name="7th Boundary",
            age=25,
            str_value=40,
            con_value=45,
            pow_value=55,
            dex_value=70,
            app_value=50,
            siz_value=75,
            int_value=65,
            edu_value=80,
        )

        detail = character.system_data
        self.assertEqual(detail.hit_points_max, 12)
        self.assertEqual(detail.magic_points_max, 11)
        self.assertEqual(detail.sanity_starting, 55)
        self.assertEqual(detail.sanity_max, 99)
        self.assertEqual(detail.calculate_damage_bonus_7th(), "+0")
        self.assertEqual(detail.calculate_build_7th(), 0)
        self.assertEqual(detail.calculate_move_rate_7th(), 7)
        self.assertEqual(CharacterSheet.get_7th_skill_base_value(detail, "回避"), 35)
        self.assertEqual(CharacterSheet.get_7th_skill_base_value(detail, "母国語"), 80)

    def test_create_7th_edition_character_with_skills_uses_7th_point_rules(self):
        """7版APIは技能を保存し、職業/趣味ポイントを7版基準で計算できる"""
        data = dict(self.character_data_7th)
        data["skills"] = [
            {
                "skill_name": "回避",
                "base_value": 42,
                "occupation_points": 20,
                "interest_points": 3,
                "other_points": 0,
                "current_value": 65,
            },
            {
                "skill_name": "母国語",
                "base_value": 85,
                "occupation_points": 0,
                "interest_points": 0,
                "other_points": 0,
                "current_value": 85,
            },
        ]

        response = self.client.post(
            "/api/accounts/character-sheets/create_7th_edition/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character = CharacterSheet.objects.get(id=response.data["id"])
        self.assertEqual(character.system_data.skills.count(), 2)
        self.assertEqual(character.system_data.calculate_occupation_points(), 340)
        self.assertEqual(character.system_data.calculate_hobby_points(), 180)
        self.assertEqual(character.system_data.calculate_used_occupation_points(), 20)
        self.assertEqual(character.system_data.calculate_used_hobby_points(), 3)

    def test_create_7th_edition_character_with_non_default_occupation_point_method(self):
        """7版作成APIはEDU×4以外の職業技能ポイント方式で保存できる"""
        data = dict(self.character_data_7th)
        data.update(
            {
                "name": "7th DEX method PC",
                "edu_value": 50,
                "dex_value": 90,
                "occupation_point_method": "edu2dex2",
                "skills": [
                    {
                        "skill_name": "回避",
                        "base_value": 45,
                        "occupation_points": 280,
                        "interest_points": 0,
                        "other_points": 0,
                        "current_value": 325,
                    }
                ],
            }
        )

        response = self.client.post(
            "/api/accounts/character-sheets/create_7th_edition/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character = CharacterSheet.objects.get(id=response.data["id"])
        self.assertEqual(character.system_data.occupation_point_method, "edu2dex2")
        self.assertEqual(character.system_data.calculate_occupation_points(), 280)
        self.assertEqual(character.system_data.calculate_used_occupation_points(), 280)
        self.assertEqual(response.data["character_7th"]["occupation_points"], 280)

    def test_update_7th_edition_character_with_non_default_occupation_point_method_allows_skill_sync(self):
        """7版編集時も保存済みの職業技能ポイント方式で技能同期できる"""
        data = dict(self.character_data_7th)
        data.update({"name": "7th edit method PC", "edu_value": 50, "dex_value": 90})
        create_response = self.client.post(
            "/api/accounts/character-sheets/create_7th_edition/",
            data,
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        character_id = create_response.data["id"]

        patch_response = self.client.patch(
            f"/api/accounts/character-sheets/{character_id}/",
            {"occupation_point_method": "edu2dex2"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        skill_response = self.client.post(
            f"/api/accounts/character-sheets/{character_id}/skills/",
            {
                "skill_name": "回避",
                "base_value": 45,
                "occupation_points": 280,
                "interest_points": 0,
                "other_points": 0,
            },
            format="json",
        )

        self.assertEqual(skill_response.status_code, status.HTTP_201_CREATED)
        character = CharacterSheet.objects.get(id=character_id)
        self.assertEqual(character.system_data.occupation_point_method, "edu2dex2")
        self.assertEqual(character.system_data.calculate_used_occupation_points(), 280)

    def test_create_7th_edition_character_with_equipment(self):
        """7版作成APIで武器・防具・アイテムを同時登録できる"""
        data = dict(self.character_data_7th)
        data["equipment"] = [
            {
                "item_type": "weapon",
                "name": "Pistol",
                "skill_name": "Handgun",
                "damage": "1D10",
                "base_range": "15m",
                "attacks_per_round": 1,
                "ammo": 8,
                "malfunction_number": 100,
                "quantity": 1,
                "weight": 0.5,
                "description": "Test weapon",
            },
            {
                "item_type": "armor",
                "name": "Kevlar Vest",
                "armor_points": 2,
                "quantity": 1,
                "weight": 3.0,
                "description": "Test armor",
            },
            {
                "item_type": "item",
                "name": "Flashlight",
                "quantity": 1,
                "weight": 0.2,
                "description": "Test item",
            },
        ]

        response = self.client.post(
            "/api/accounts/character-sheets/create_7th_edition/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character_id = response.data["id"]
        equipment = CharacterSheet.objects.get(pk=character_id).system_data.equipment

        self.assertEqual(equipment.count(), 3)
        pistol = equipment.get(name="Pistol")
        self.assertEqual(pistol.item_type, "weapon")
        self.assertAlmostEqual(pistol.weight, 0.5, places=3)
        vest = equipment.get(name="Kevlar Vest")
        self.assertEqual(vest.item_type, "armor")
        self.assertAlmostEqual(vest.weight, 3.0, places=3)
        flashlight = equipment.get(name="Flashlight")
        self.assertEqual(flashlight.item_type, "item")
        self.assertAlmostEqual(flashlight.weight, 0.2, places=3)

    def test_list_character_sheets(self):
        """キャラクターシート一覧取得テスト"""
        # まずキャラクター作成
        self.client.post("/api/accounts/character-sheets/", self.character_data_6th, format="json")
        # 7版は現在サポートされていないため、6版のみでテスト

        url = "/api/accounts/character-sheets/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_character_sheet_detail(self):
        """キャラクターシート詳細取得テスト"""
        # キャラクター作成
        create_response = self.client.post("/api/accounts/character-sheets/", self.character_data_6th, format="json")
        character_id = create_response.data["id"]

        url = f"/api/accounts/character-sheets/{character_id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], character_id)
        self.assertIn("abilities", response.data)
        self.assertIn("skills", response.data)
        self.assertIn("equipment", response.data)

    def test_update_character_sheet(self):
        """キャラクターシート更新テスト"""
        # キャラクター作成
        create_response = self.client.post("/api/accounts/character-sheets/", self.character_data_6th, format="json")
        character_id = create_response.data["id"]

        # 更新データ
        update_data = {
            "name": "更新された探索者",
            "age": 30,
            "hit_points_current": 10,
            "sanity_current": 65,
            "notes": "更新されたメモ",
        }

        url = f"/api/accounts/character-sheets/{character_id}/"
        response = self.client.patch(url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "更新された探索者")
        self.assertEqual(response.data["age"], 30)
        self.assertEqual(response.data["hit_points_current"], 10)

    def test_patch_recalculates_6th_derived_stats_when_abilities_change(self):
        """6版は能力値更新時に最大値と6版固有ロールを再計算する"""
        character = self.create_character(
            user=self.user,
            edition="6th",
            name="再計算6版",
            age=28,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
        )

        response = self.client.patch(
            f"/api/accounts/character-sheets/{character.id}/",
            {
                "con_value": 18,
                "pow_value": 12,
                "siz_value": 16,
                "int_value": 14,
                "edu_value": 13,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        character.refresh_from_db()
        sixth = character.sixth_edition_data
        self.assertEqual(character.system_data.hit_points_max, 17)
        self.assertEqual(character.system_data.hit_points_current, 17)
        self.assertEqual(character.system_data.magic_points_max, 12)
        self.assertEqual(character.system_data.magic_points_current, 12)
        self.assertEqual(character.system_data.sanity_starting, 60)
        self.assertEqual(character.system_data.sanity_current, 60)
        self.assertEqual(sixth.idea_roll, 70)
        self.assertEqual(sixth.luck_roll, 60)
        self.assertEqual(sixth.know_roll, 65)
        self.assertEqual(sixth.damage_bonus, "+1D4")

    def test_patch_preserves_manual_current_values_during_recalculation(self):
        """現在HP/MP/SANが手入力済みなら最大値再計算時も保持する"""
        character = self.create_character(
            user=self.user,
            edition="6th",
            name="手入力保持6版",
            age=28,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
        )
        detail = character.system_data
        detail.hit_points_current = 7
        detail.magic_points_current = 3
        detail.sanity_current = 22
        detail.save(update_fields=["hit_points_current", "magic_points_current", "sanity_current"])

        response = self.client.patch(
            f"/api/accounts/character-sheets/{character.id}/",
            {
                "con_value": 18,
                "pow_value": 12,
                "siz_value": 16,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        character.refresh_from_db()
        self.assertEqual(character.system_data.hit_points_max, 17)
        self.assertEqual(character.system_data.hit_points_current, 7)
        self.assertEqual(character.system_data.magic_points_max, 12)
        self.assertEqual(character.system_data.magic_points_current, 3)
        self.assertEqual(character.system_data.sanity_starting, 60)
        self.assertEqual(character.system_data.sanity_current, 22)

    def test_patch_recalculates_7th_derived_stats_when_abilities_change(self):
        """7版は能力値更新時に7版式の最大HP/MP/SANへ再計算する"""
        character = self.create_character(
            user=self.user,
            edition="7th",
            name="再計算7版",
            age=35,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=50,
        )

        response = self.client.patch(
            f"/api/accounts/character-sheets/{character.id}/",
            {
                "con_value": 80,
                "pow_value": 70,
                "siz_value": 60,
                "str_value": 90,
                "dex_value": 80,
                "age": 45,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        character.refresh_from_db()
        self.assertEqual(character.system_data.hit_points_max, 14)
        self.assertEqual(character.system_data.hit_points_current, 14)
        self.assertEqual(character.system_data.magic_points_max, 14)
        self.assertEqual(character.system_data.magic_points_current, 14)
        self.assertEqual(character.system_data.sanity_starting, 70)
        self.assertEqual(character.system_data.sanity_current, 70)
        self.assertEqual(character.system_data.calculate_build_7th(), 1)
        self.assertEqual(character.system_data.calculate_move_rate_7th(), 8)

    def test_delete_character_sheet(self):
        """キャラクターシート削除テスト"""
        # キャラクター作成
        create_response = self.client.post("/api/accounts/character-sheets/", self.character_data_6th, format="json")
        character_id = create_response.data["id"]

        url = f"/api/accounts/character-sheets/{character_id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 削除確認
        self.assertFalse(CharacterSheet.objects.filter(id=character_id).exists())

    def test_create_character_version(self):
        """キャラクターシートバージョン作成テスト"""
        # 元キャラクター作成
        create_response = self.client.post("/api/accounts/character-sheets/", self.character_data_6th, format="json")
        original_id = create_response.data["id"]

        # バージョン作成
        version_data = {"hit_points_current": 8, "sanity_current": 60, "notes": "バージョン2のメモ"}

        url = f"/api/accounts/character-sheets/{original_id}/create_version/"
        response = self.client.post(url, version_data, format="json")

        # デバッグ出力

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["version"], 2)
        version = CharacterSheet.objects.get(id=response.data["id"])
        self.assertEqual(version.system_data.parent_data.character_sheet_id, original_id)
        self.assertEqual(response.data["hit_points_current"], 8)

    def test_create_character_version_copies_equipment_weight(self):
        """create_version が装備(weight含む)を引き継ぐ"""
        data = dict(self.character_data_6th)
        data["equipment"] = [
            {
                "item_type": "weapon",
                "name": "Pistol",
                "damage": "1D10",
                "attacks_per_round": 2,
                "quantity": 1,
                "weight": 0.5,
            },
            {
                "item_type": "armor",
                "name": "Kevlar Vest",
                "armor_points": 2,
                "quantity": 1,
                "weight": 3.0,
            },
            {
                "item_type": "item",
                "name": "Flashlight",
                "quantity": 2,
                "weight": 0.2,
            },
        ]

        create_response = self.client.post(
            "/api/accounts/character-sheets/create_6th_edition/",
            data,
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        original_id = create_response.data["id"]

        original_equipment = list(CharacterSheet.objects.get(pk=original_id).system_data.equipment.all())
        self.assertEqual(len(original_equipment), 3)

        response = self.client.post(
            f"/api/accounts/character-sheets/{original_id}/create_version/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_id = response.data["id"]

        new_equipment = CharacterSheet.objects.get(pk=new_id).system_data.equipment
        self.assertEqual(new_equipment.count(), 3)

        for item in original_equipment:
            copied = new_equipment.get(name=item.name, item_type=item.item_type)
            self.assertEqual(copied.quantity, item.quantity)
            self.assertEqual(copied.armor_points, item.armor_points)
            self.assertEqual(copied.damage, item.damage)
            self.assertEqual(copied.attacks_per_round, item.attacks_per_round)
            self.assertEqual(copied.ammo, item.ammo)
            self.assertEqual(copied.malfunction_number, item.malfunction_number)
            self.assertAlmostEqual(copied.weight, item.weight, places=3)

    def test_filter_by_edition(self):
        """版別フィルタリングテスト"""
        # 両版のキャラクター作成
        self.client.post("/api/accounts/character-sheets/", self.character_data_6th, format="json")
        self.client.post("/api/accounts/character-sheets/create_7th_edition/", self.character_data_7th, format="json")

        # 6版のみ取得
        url = "/api/accounts/character-sheets/by_edition/?edition=6th"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["edition"], "6th")

        # 7版のみ取得
        url = "/api/accounts/character-sheets/by_edition/?edition=7th"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["edition"], "7th")

    def test_character_skills(self):
        """キャラクタースキルテスト"""
        # キャラクター作成
        create_response = self.client.post("/api/accounts/character-sheets/", self.character_data_6th, format="json")
        character_id = create_response.data["id"]

        # スキル追加
        skill_data = {
            "skill_name": "目星",
            "base_value": 25,
            "occupation_points": 40,
            "interest_points": 10,
            "other_points": 0,
        }

        url = f"/api/accounts/character-sheets/{character_id}/skills/"
        response = self.client.post(url, skill_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["skill_name"], "目星")
        self.assertEqual(response.data["current_value"], 75)  # 25+40+10+0

        # スキル一覧取得
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_character_equipment(self):
        """キャラクター装備テスト"""
        # キャラクター作成
        create_response = self.client.post("/api/accounts/character-sheets/", self.character_data_6th, format="json")
        character_id = create_response.data["id"]

        # 装備追加
        equipment_data = {
            "item_type": "weapon",
            "name": ".38リボルバー",
            "skill_name": "拳銃",
            "damage": "1d10",
            "base_range": "15m",
            "attacks_per_round": 3,
            "ammo": 6,
            "malfunction_number": 100,
            "description": "一般的な回転式拳銃",
            "quantity": 1,
        }

        url = f"/api/accounts/character-sheets/{character_id}/equipment/"
        response = self.client.post(url, equipment_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], ".38リボルバー")
        self.assertEqual(response.data["item_type"], "weapon")

        # 装備一覧取得
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
