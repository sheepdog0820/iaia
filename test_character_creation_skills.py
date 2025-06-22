#!/usr/bin/env python3
"""
キャラクター作成時の技能ポイント処理テストケース

このテストは技能検索・タブ切り替え時のポイント処理問題を検証します。
"""

import re

class CharacterCreationSkillsTestCase:
    """キャラクター作成時の技能ポイント処理テスト"""
    
    def setUp(self):
        """テスト用セットアップ"""
        pass
        
    def test_skill_id_generation(self):
        """技能名からskillIdへの変換テスト"""
        test_cases = [
            ('ナビゲート', 'ナビゲート'),
            ('言いくるめ', '言いくるめ'),
            ('重機械操作', '重機械操作'),
            ('マシンガン', 'マシンガン'),
            ('コンピューター', 'コンピューター'),
            ('応急手当', '応急手当'),
            ('運転(自動車)', '運転_自動車_'),
            ('芸術(絵画)', '芸術_絵画_'),
            ('言語(英語)', '言語_英語_'),
        ]
        
        for skill_name, expected_base in test_cases:
            # JavaScript の処理を Python で再現
            skill_id = ''.join(c if c.isalnum() else '_' for c in skill_name)
            print(f"技能名: '{skill_name}' → skillId: '{skill_id}'")
            
            # 重複チェック
            duplicates = [name for name, _ in test_cases if 
                         ''.join(c if c.isalnum() else '_' for c in name) == skill_id]
            if len(duplicates) > 1:
                print(f"⚠️  重複検出: {duplicates} → 同じskillId: '{skill_id}'")
                
    def test_skill_search_scenario(self):
        """技能検索シナリオのテスト"""
        print("\n=== 技能検索シナリオテスト ===")
        
        # シナリオ: ナビゲートに60ポイント設定 → 検索 → 検索解除
        print("1. ナビゲートに職業技能60ポイント設定")
        print("2. 技能検索で絞り込み")
        print("3. 検索解除して全技能表示")
        print("4. 他の技能にポイントが誤って設定されていないか確認")
        
        # 期待される結果
        expected_skills = {
            'ナビゲート': {'occupation': 60, 'interest': 0, 'bonus': 0},
            '言いくるめ': {'occupation': 0, 'interest': 0, 'bonus': 0},
            '重機械操作': {'occupation': 0, 'interest': 0, 'bonus': 0},
            'マシンガン': {'occupation': 0, 'interest': 0, 'bonus': 0},
        }
        
        print("\n期待される技能ポイント配分:")
        for skill, points in expected_skills.items():
            print(f"  {skill}: 職業={points['occupation']}, 趣味={points['interest']}, ボーナス={points['bonus']}")
            
    def test_tab_switching_scenario(self):
        """タブ切り替えシナリオのテスト"""
        print("\n=== タブ切り替えシナリオテスト ===")
        
        # シナリオ: 戦闘タブで技能設定 → 探索タブに切り替え → 全てタブに戻る
        print("1. 戦闘タブでマシンガンに職業技能40ポイント設定")
        print("2. 探索タブに切り替え")
        print("3. 全てタブに戻る")
        print("4. マシンガンのポイントが保持されているか確認")
        print("5. 他の技能にポイントが誤って設定されていないか確認")
        
    def test_skill_point_calculation(self):
        """技能ポイント合計計算のテスト"""
        print("\n=== 技能ポイント合計計算テスト ===")
        
        # テストケース: 複数技能にポイント設定
        test_skills = {
            'ナビゲート': {'occupation': 60, 'interest': 20},
            '応急手当': {'occupation': 40, 'interest': 0},
            '言いくるめ': {'occupation': 0, 'interest': 30},
        }
        
        # 期待される合計
        expected_occupation_total = 60 + 40 + 0  # 100
        expected_interest_total = 20 + 0 + 30     # 50
        
        print(f"設定予定の技能ポイント:")
        total_occ = 0
        total_int = 0
        for skill, points in test_skills.items():
            occ = points['occupation']
            interest = points['interest']
            total_occ += occ
            total_int += interest
            print(f"  {skill}: 職業={occ}, 趣味={interest}")
            
        print(f"\n期待される合計:")
        print(f"  職業技能合計: {expected_occupation_total}")
        print(f"  趣味技能合計: {expected_interest_total}")
        
        # 実際の計算結果と比較
        assert total_occ == expected_occupation_total, f"職業技能合計不一致: {total_occ} != {expected_occupation_total}"
        assert total_int == expected_interest_total, f"趣味技能合計不一致: {total_int} != {expected_interest_total}"
        
    def test_draft_data_preservation(self):
        """下書きデータ保持テスト"""
        print("\n=== 下書きデータ保持テスト ===")
        
        # シナリオ: 技能設定 → 下書き保存 → 技能検索 → 下書きデータ復元
        print("1. 複数技能にポイント設定")
        print("2. 下書き保存")
        print("3. 技能検索実行")
        print("4. 下書きデータが正しく復元されるか確認")

def run_manual_tests():
    """手動テストケースの実行"""
    print("キャラクター作成 技能ポイント処理テスト")
    print("=" * 50)
    
    test_case = CharacterCreationSkillsTestCase()
    test_case.setUp()
    
    # 各テストを実行
    test_case.test_skill_id_generation()
    test_case.test_skill_search_scenario()
    test_case.test_tab_switching_scenario() 
    test_case.test_skill_point_calculation()
    test_case.test_draft_data_preservation()
    
    print("\n" + "=" * 50)
    print("テスト完了")
    print("\n手動確認項目:")
    print("1. ブラウザで6版キャラクター作成画面を開く")
    print("2. ナビゲートに職業技能60ポイント設定")
    print("3. 技能検索で「ナビ」で検索")
    print("4. 検索をクリア")
    print("5. 言いくるめ、重機械操作、マシンガンにポイントが設定されていないか確認")
    print("6. 職業技能合計が60になっているか確認")

if __name__ == '__main__':
    run_manual_tests()