"""
背景情報詳細化システムのテストスイート
クトゥルフ神話TRPG 6版の背景情報詳細化機能をテスト
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CharacterSheet
from .character_models import CharacterSheet6th, CharacterBackground

User = get_user_model()


class BackgroundModelTestCase(TestCase):
    """背景情報モデルのテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Investigator',
            edition='6th',
            age=25,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=60
        )
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
    
    def test_background_model_creation(self):
        """背景情報モデルの作成テスト"""
        background = CharacterBackground.objects.create(
            character_sheet=self.character,
            appearance_description="背が高く痩せ型で、鋭い目をしている",
            beliefs_ideology="科学的合理主義を信じている",
            significant_people="大学時代の恩師、ジョンソン教授",
            meaningful_locations="故郷の図書館",
            treasured_possessions="祖父の懐中時計",
            traits_mannerisms="考え事をするとき眼鏡を外す癖がある"
        )
        
        self.assertEqual(background.character_sheet, self.character)
        self.assertEqual(background.appearance_description, "背が高く痩せ型で、鋭い目をしている")
        self.assertEqual(background.beliefs_ideology, "科学的合理主義を信じている")
        self.assertEqual(background.significant_people, "大学時代の恩師、ジョンソン教授")
        self.assertEqual(background.meaningful_locations, "故郷の図書館")
        self.assertEqual(background.treasured_possessions, "祖父の懐中時計")
        self.assertEqual(background.traits_mannerisms, "考え事をするとき眼鏡を外す癖がある")
    
    def test_background_field_validation(self):
        """背景情報フィールドのバリデーションテスト"""
        # 文字数制限のテスト
        long_text = "a" * 1001  # 1000文字を超える
        
        with self.assertRaises(ValidationError):
            background = CharacterBackground(
                character_sheet=self.character,
                appearance_description=long_text
            )
            background.full_clean()
    
    def test_background_personal_history(self):
        """個人史情報のテスト"""
        background = CharacterBackground.objects.create(
            character_sheet=self.character,
            personal_history="ボストン郊外の小さな町で生まれ育った",
            important_events="18歳の時、謎の失踪事件を目撃した",
            scars_injuries="左手首に古い傷跡がある",
            phobias_manias="暗所恐怖症、古書収集癖"
        )
        
        self.assertEqual(background.personal_history, "ボストン郊外の小さな町で生まれ育った")
        self.assertEqual(background.important_events, "18歳の時、謎の失踪事件を目撃した")
        self.assertEqual(background.scars_injuries, "左手首に古い傷跡がある")
        self.assertEqual(background.phobias_manias, "暗所恐怖症、古書収集癖")
    
    def test_investigator_connections(self):
        """探索者同士の関係性テスト"""
        background = CharacterBackground.objects.create(
            character_sheet=self.character,
            fellow_investigators="同じ大学の研究仲間たち",
            notes_memo="神話的事件の調査記録"
        )
        
        self.assertEqual(background.fellow_investigators, "同じ大学の研究仲間たち")
        self.assertEqual(background.notes_memo, "神話的事件の調査記録")


class BackgroundAPITestCase(APITestCase):
    """背景情報管理APIのテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Investigator',
            edition='6th',
            age=25,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=60
        )
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
    
    def test_get_background_summary_api(self):
        """背景情報サマリー取得APIテスト"""
        # 背景情報を作成
        CharacterBackground.objects.create(
            character_sheet=self.character,
            appearance_description="背の高い男性",
            beliefs_ideology="科学的合理主義",
            significant_people="恩師のジョンソン教授",
            meaningful_locations="故郷の図書館",
            treasured_possessions="祖父の懐中時計",
            traits_mannerisms="眼鏡を外す癖"
        )
        
        response = self.client.get(
            f'/accounts/character-sheets/{self.character.id}/background-summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['appearance_description'], "背の高い男性")
        self.assertEqual(response.data['beliefs_ideology'], "科学的合理主義")
        self.assertEqual(response.data['significant_people'], "恩師のジョンソン教授")
        self.assertEqual(response.data['meaningful_locations'], "故郷の図書館")
        self.assertEqual(response.data['treasured_possessions'], "祖父の懐中時計")
        self.assertEqual(response.data['traits_mannerisms'], "眼鏡を外す癖")
    
    def test_update_background_data_api(self):
        """背景情報更新APIテスト"""
        # 既存の背景情報を作成
        background = CharacterBackground.objects.create(
            character_sheet=self.character,
            appearance_description="初期の容姿"
        )
        
        update_data = {
            'appearance_description': '更新された容姿説明',
            'beliefs_ideology': '新しい信念',
            'significant_people': '重要な人物',
            'meaningful_locations': '意味のある場所',
            'treasured_possessions': '大切な品物',
            'traits_mannerisms': '特徴・癖'
        }
        
        response = self.client.patch(
            f'/accounts/character-sheets/{self.character.id}/update-background-data/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # データが更新されたか確認
        background.refresh_from_db()
        self.assertEqual(background.appearance_description, '更新された容姿説明')
        self.assertEqual(background.beliefs_ideology, '新しい信念')
        self.assertEqual(background.significant_people, '重要な人物')
        self.assertEqual(background.meaningful_locations, '意味のある場所')
        self.assertEqual(background.treasured_possessions, '大切な品物')
        self.assertEqual(background.traits_mannerisms, '特徴・癖')
    
    def test_create_background_if_not_exists(self):
        """背景情報が存在しない場合の作成APIテスト"""
        update_data = {
            'appearance_description': '新規作成された容姿',
            'beliefs_ideology': '新規作成された信念'
        }
        
        response = self.client.patch(
            f'/accounts/character-sheets/{self.character.id}/update-background-data/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 背景情報が作成されたか確認
        background = CharacterBackground.objects.get(character_sheet=self.character)
        self.assertEqual(background.appearance_description, '新規作成された容姿')
        self.assertEqual(background.beliefs_ideology, '新規作成された信念')


class BackgroundIntegrationTestCase(TestCase):
    """背景情報統合テストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Investigator',
            edition='6th',
            age=35,
            occupation='私立探偵',
            str_value=12,
            con_value=14,
            pow_value=15,
            dex_value=13,
            app_value=11,
            siz_value=10,
            int_value=16,
            edu_value=18
        )
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
    
    def test_complete_background_setup(self):
        """完全な背景情報セットアップのテスト"""
        # 完全な背景情報を作成
        background = CharacterBackground.objects.create(
            character_sheet=self.character,
            # パーソナルデータ
            appearance_description="中年の男性、灰色がかった髪と鋭い目。常にトレンチコートを着用",
            beliefs_ideology="真実は必ず明らかになるという信念",
            significant_people="亡き妻、エミリー・ハートウェル",
            meaningful_locations="妻と最初に出会ったボストンの公園",
            treasured_possessions="妻からもらった結婚指輪",
            traits_mannerisms="緊張すると指輪を回す癖がある",
            
            # 経歴
            personal_history="元警察官から私立探偵に転身。妻を神秘的な事件で失った",
            important_events="妻の失踪事件。これが神話的恐怖との最初の接触だった",
            scars_injuries="左肩に銃撃による古い傷。右膝に怪我の跡",
            phobias_manias="暗所恐怖症（妻の失踪現場が地下室だったため）",
            
            # 仲間の探索者
            fellow_investigators="ジョン・スミス（考古学者）、サラ・ジョンソン（医師）",
            
            # その他
            notes_memo="調査記録：アーカムでの一連の失踪事件。神話的要素の可能性あり"
        )
        
        # 全フィールドが正しく保存されているか確認
        self.assertEqual(background.character_sheet, self.character)
        
        # パーソナルデータ確認
        self.assertIn("中年の男性", background.appearance_description)
        self.assertIn("真実は必ず明らかになる", background.beliefs_ideology)
        self.assertIn("エミリー・ハートウェル", background.significant_people)
        self.assertIn("ボストンの公園", background.meaningful_locations)
        self.assertIn("結婚指輪", background.treasured_possessions)
        self.assertIn("指輪を回す", background.traits_mannerisms)
        
        # 経歴確認
        self.assertIn("元警察官", background.personal_history)
        self.assertIn("妻の失踪事件", background.important_events)
        self.assertIn("左肩に銃撃", background.scars_injuries)
        self.assertIn("暗所恐怖症", background.phobias_manias)
        
        # 探索者関係確認
        self.assertIn("ジョン・スミス", background.fellow_investigators)
        self.assertIn("サラ・ジョンソン", background.fellow_investigators)
        
        # メモ確認
        self.assertIn("アーカムでの一連の失踪事件", background.notes_memo)
    
    def test_background_character_consistency(self):
        """背景情報とキャラクター基本情報の整合性テスト"""
        # キャラクターの職業に合わせた背景情報
        background = CharacterBackground.objects.create(
            character_sheet=self.character,
            appearance_description="探偵らしい鋭い観察眼を持つ",
            beliefs_ideology="正義は必ず勝つという信念",
            personal_history="警察官として10年間勤務後、私立探偵として独立",
            important_events="大きな事件を解決して探偵として名を上げた"
        )
        
        # 職業と背景の整合性確認
        self.assertEqual(self.character.occupation, '私立探偵')
        self.assertIn("探偵", background.appearance_description)
        self.assertIn("警察官", background.personal_history)
        self.assertIn("探偵", background.personal_history)