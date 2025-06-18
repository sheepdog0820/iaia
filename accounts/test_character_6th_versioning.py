"""
クトゥルフ神話TRPG 6版 バージョン管理機能テスト
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import CharacterSheet, CharacterSheet6th, CharacterSkill

User = get_user_model()


class CharacterVersioningTestCase(TestCase):
    """キャラクターバージョン管理機能のテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 元になるキャラクター
        self.base_character = CharacterSheet.objects.create(
            user=self.user,
            name='田中太郎',
            edition='6th',
            age=25,
            str_value=60,
            con_value=70,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=75,
            edu_value=80,
            version=1
        )
    
    def test_version_creation(self):
        """新バージョン作成テスト"""
        # 新バージョンを作成するメソッドをテスト
        new_version = self.base_character.create_new_version(
            version_note="第2セッション後の成長"
        )
        
        self.assertEqual(new_version.version, 2)
        self.assertEqual(new_version.parent_sheet, self.base_character)
        self.assertEqual(new_version.name, self.base_character.name)
        self.assertEqual(new_version.user, self.base_character.user)
    
    def test_version_note_field(self):
        """バージョンメモフィールドのテスト"""
        # バージョンメモフィールドが存在することを確認
        self.base_character.version_note = "初期作成バージョン"
        self.base_character.save()
        
        self.assertEqual(self.base_character.version_note, "初期作成バージョン")
    
    def test_get_version_history(self):
        """バージョン履歴取得テスト"""
        # 複数バージョンを作成
        version_2 = self.base_character.create_new_version("セッション1後")
        version_3 = version_2.create_new_version("セッション2後")
        
        # 履歴取得
        history = self.base_character.get_version_history()
        
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0], self.base_character)  # 最初のバージョン
        self.assertEqual(history[1], version_2)
        self.assertEqual(history[2], version_3)
    
    def test_get_latest_version(self):
        """最新バージョン取得テスト"""
        version_2 = self.base_character.create_new_version("セッション1後")
        version_3 = version_2.create_new_version("セッション2後")
        
        latest = self.base_character.get_latest_version()
        self.assertEqual(latest, version_3)
        self.assertEqual(latest.version, 3)
    
    def test_copy_skills_to_new_version(self):
        """技能のコピーテスト"""
        # 元バージョンに技能を追加
        original_skill = CharacterSkill.objects.create(
            character_sheet=self.base_character,
            skill_name='目星',
            category='探索系',
            base_value=25,
            occupation_points=40,
            interest_points=20,
            bonus_points=5
        )
        
        # 新バージョン作成
        new_version = self.base_character.create_new_version(
            "セッション後の成長",
            copy_skills=True
        )
        
        # 技能がコピーされていることを確認
        copied_skills = new_version.skills.all()
        self.assertEqual(copied_skills.count(), 1)
        
        copied_skill = copied_skills.first()
        self.assertEqual(copied_skill.skill_name, original_skill.skill_name)
        self.assertEqual(copied_skill.base_value, original_skill.base_value)
        self.assertEqual(copied_skill.occupation_points, original_skill.occupation_points)
    
    def test_version_comparison(self):
        """バージョン間比較テスト"""
        # 技能成長のシミュレーション
        CharacterSkill.objects.create(
            character_sheet=self.base_character,
            skill_name='目星',
            base_value=25,
            occupation_points=40,
            interest_points=20
        )
        
        # 新バージョンで技能成長
        new_version = self.base_character.create_new_version("技能成長後")
        new_skill = CharacterSkill.objects.create(
            character_sheet=new_version,
            skill_name='目星',
            base_value=25,
            occupation_points=40,
            interest_points=20,
            bonus_points=10  # 成長分
        )
        
        # 比較機能のテスト
        differences = self.base_character.compare_with_version(new_version)
        self.assertIn('skills', differences)
    
    def test_version_rollback(self):
        """バージョンロールバックテスト"""
        # 複数バージョンを作成
        version_2 = self.base_character.create_new_version("バージョン2")
        version_3 = version_2.create_new_version("バージョン3")
        
        # バージョン2にロールバック
        rolled_back = version_3.rollback_to_version(version_2)
        
        self.assertEqual(rolled_back.version, 4)  # 新しいバージョン番号
        self.assertEqual(rolled_back.parent_sheet, version_3)
    
    def test_version_tree_structure(self):
        """バージョンツリー構造のテスト"""
        # 分岐バージョンの作成
        branch_a = self.base_character.create_new_version("ブランチA")
        branch_b = self.base_character.create_new_version("ブランチB")
        
        # ルートバージョンの確認
        self.assertEqual(branch_a.get_root_version(), self.base_character)
        self.assertEqual(branch_b.get_root_version(), self.base_character)
        
        # 子バージョンの確認
        children = self.base_character.get_child_versions()
        self.assertEqual(len(children), 2)
        self.assertIn(branch_a, children)
        self.assertIn(branch_b, children)


class CharacterVersionMetadataTestCase(TestCase):
    """キャラクターバージョンメタデータのテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='テストキャラクター',
            edition='6th',
            age=25,
            str_value=60,
            con_value=70,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=75,
            edu_value=80
        )
    
    def test_version_metadata_preservation(self):
        """バージョンメタデータの保持テスト"""
        # メタデータ設定
        self.character.version_note = "初期作成"
        self.character.session_count = 0
        self.character.save()
        
        # 新バージョン作成
        new_version = self.character.create_new_version(
            "第1セッション後",
            session_count=1
        )
        
        self.assertEqual(new_version.version_note, "第1セッション後")
        self.assertEqual(new_version.session_count, 1)
    
    def test_version_statistics(self):
        """バージョン統計のテスト"""
        # 複数バージョンを作成
        for i in range(1, 6):
            self.character.create_new_version(f"セッション{i}後")
        
        # 統計取得
        stats = self.character.get_version_statistics()
        
        self.assertEqual(stats['total_versions'], 6)  # 元バージョン + 5個
        self.assertEqual(stats['latest_version'], 6)
    
    def test_version_export_data(self):
        """バージョンデータエクスポートテスト"""
        # 技能データを追加
        CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='目星',
            base_value=25,
            occupation_points=40
        )
        
        # エクスポートデータの取得
        export_data = self.character.export_version_data()
        
        self.assertIn('character_info', export_data)
        self.assertIn('skills', export_data)
        self.assertIn('version_info', export_data)
        self.assertEqual(export_data['character_info']['name'], 'テストキャラクター')


class CharacterVersionValidationTestCase(TestCase):
    """キャラクターバージョンバリデーションのテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='テストキャラクター',
            edition='6th',
            age=25,
            str_value=60,
            con_value=70,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=75,
            edu_value=80
        )
    
    def test_version_note_length_validation(self):
        """バージョンメモの長さ制限テスト"""
        # 長すぎるメモ
        long_note = "x" * 1001  # 1000文字超
        
        with self.assertRaises(ValidationError):
            new_version = self.character.create_new_version(long_note)
    
    def test_version_sequence_validation(self):
        """バージョン番号の連続性テスト"""
        version_2 = self.character.create_new_version("バージョン2")
        
        # バージョン番号が正しく設定されている
        self.assertEqual(version_2.version, 2)
        
        # 同じバージョン番号での作成を防ぐ
        with self.assertRaises(ValidationError):
            CharacterSheet.objects.create(
                user=self.user,
                name='テストキャラクター',
                edition='6th',
                age=25,
                str_value=60,
                con_value=70,
                pow_value=55,
                dex_value=65,
                app_value=50,
                siz_value=60,
                int_value=75,
                edu_value=80,
                version=2,  # 重複バージョン
                parent_sheet=self.character
            )
    
    def test_circular_reference_prevention(self):
        """循環参照の防止テスト"""
        version_2 = self.character.create_new_version("バージョン2")
        
        # 循環参照を作ろうとすると失敗する
        with self.assertRaises(ValidationError):
            self.character.parent_sheet = version_2
            self.character.save()