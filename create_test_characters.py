#!/usr/bin/env python3
"""
テストキャラクターデータ作成スクリプト
クトゥルフ神話TRPG 6版・7版のテストキャラクターを作成
"""

import os
import sys
import django
import random

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from accounts.models import (
    CustomUser, CharacterSheet, CharacterSheet6th,
    CharacterSkill, CharacterEquipment
)

# 色付きテキスト出力
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def create_test_characters():
    """テストキャラクターを作成"""
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}テストキャラクターデータ作成開始{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    
    # テストユーザーを取得または作成
    test_users = []
    for i in range(3):
        username = f'player{i+1}'
        user, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'nickname': f'プレイヤー{i+1}',
                'trpg_history': 'クトゥルフ神話TRPGを中心に活動'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            print(f"{Colors.OKGREEN}✅ ユーザー作成: {username}{Colors.ENDC}")
        else:
            print(f"{Colors.OKBLUE}📌 既存ユーザー: {username}{Colors.ENDC}")
        test_users.append(user)
    
    # 6版キャラクターの作成
    print(f"\n{Colors.OKCYAN}【6版キャラクター作成】{Colors.ENDC}")
    
    sixth_characters = [
        {
            'name': '藤原 誠司',
            'occupation': '私立探偵',
            'age': 35,
            'gender': '男性',
            'birthplace': '東京都',
            'residence': '横浜市',
            'mental_disorder': '',
            'abilities': {
                'str': 12, 'con': 14, 'pow': 13, 'dex': 15,
                'app': 11, 'siz': 13, 'int': 16, 'edu': 15
            },
            'skills': [
                ('目星', '探索系', 25, 30, 10),
                ('聞き耳', '探索系', 20, 25, 5),
                ('図書館', '探索系', 25, 30, 0),
                ('心理学', '知識系', 10, 30, 0),
                ('説得', '対人系', 15, 20, 0),
                ('拳銃', '戦闘系', 20, 40, 0),
            ]
        },
        {
            'name': '佐藤 美咲',
            'occupation': 'ジャーナリスト',
            'age': 28,
            'gender': '女性',
            'birthplace': '大阪府',
            'residence': '東京都',
            'mental_disorder': '軽度の閉所恐怖症',
            'abilities': {
                'str': 9, 'con': 11, 'pow': 15, 'dex': 13,
                'app': 14, 'siz': 10, 'int': 17, 'edu': 16
            },
            'skills': [
                ('言いくるめ', '対人系', 5, 40, 0),
                ('信用', '対人系', 15, 30, 0),
                ('図書館', '探索系', 25, 30, 0),
                ('コンピューター', '技術系', 1, 40, 0),
                ('写真術', '技術系', 10, 30, 0),
                ('心理学', '知識系', 10, 20, 0),
            ]
        },
        {
            'name': '山田 太郎',
            'occupation': '医師',
            'age': 42,
            'gender': '男性',
            'birthplace': '京都府',
            'residence': '東京都',
            'mental_disorder': '',
            'abilities': {
                'str': 10, 'con': 12, 'pow': 14, 'dex': 11,
                'app': 12, 'siz': 12, 'int': 18, 'edu': 18
            },
            'skills': [
                ('医学', '知識系', 5, 60, 0),
                ('応急手当', '技術系', 30, 20, 0),
                ('生物学', '知識系', 1, 40, 0),
                ('化学', '知識系', 1, 30, 0),
                ('心理学', '知識系', 10, 20, 0),
                ('説得', '対人系', 15, 10, 10),
            ]
        }
    ]
    
    for i, char_data in enumerate(sixth_characters):
        user = test_users[i % len(test_users)]
        
        # 既存のキャラクターチェック
        existing = CharacterSheet.objects.filter(
            user=user,
            name=char_data['name'],
            edition='6th'
        ).first()
        
        if existing:
            print(f"{Colors.WARNING}⚠️  既存キャラクター: {char_data['name']} (スキップ){Colors.ENDC}")
            continue
        
        # キャラクターシート作成（能力値は×5で保存）
        character = CharacterSheet.objects.create(
            user=user,
            edition='6th',
            name=char_data['name'],
            player_name=user.nickname,
            age=char_data['age'],
            gender=char_data['gender'],
            occupation=char_data['occupation'],
            birthplace=char_data['birthplace'],
            residence=char_data['residence'],
            str_value=char_data['abilities']['str'] * 5,
            con_value=char_data['abilities']['con'] * 5,
            pow_value=char_data['abilities']['pow'] * 5,
            dex_value=char_data['abilities']['dex'] * 5,
            app_value=char_data['abilities']['app'] * 5,
            siz_value=char_data['abilities']['siz'] * 5,
            int_value=char_data['abilities']['int'] * 5,
            edu_value=char_data['abilities']['edu'] * 5,
            notes=f'{char_data["occupation"]}として活動する探索者',
            is_active=True
        )
        
        # 6版固有データ
        CharacterSheet6th.objects.create(
            character_sheet=character,
            mental_disorder=char_data['mental_disorder']
        )
        
        # スキル作成
        for skill_name, category, base, occupation, interest in char_data['skills']:
            CharacterSkill.objects.create(
                character_sheet=character,
                skill_name=skill_name,
                category=category,
                base_value=base,
                occupation_points=occupation,
                interest_points=interest
            )
        
        # 装備追加
        if char_data['occupation'] == '私立探偵':
            CharacterEquipment.objects.create(
                character_sheet=character,
                item_type='weapon',
                name='コルト.38リボルバー',
                skill_name='拳銃',
                damage='1D10',
                base_range='15m',
                attacks_per_round=2,
                ammo=6,
                malfunction_number=100
            )
        elif char_data['occupation'] == '医師':
            CharacterEquipment.objects.create(
                character_sheet=character,
                item_type='item',
                name='医療鞄',
                description='応急手当と医学ロールに+20%ボーナス'
            )
        
        print(f"{Colors.OKGREEN}✅ 6版キャラクター作成: {char_data['name']} ({char_data['occupation']}){Colors.ENDC}")
    
    # 7版キャラクターの作成
    print(f"\n{Colors.OKCYAN}【7版キャラクター作成】{Colors.ENDC}")
    
    seventh_characters = [
        {
            'name': 'エドワード・ピアース',
            'occupation': '考古学者',
            'age': 38,
            'gender': '男性',
            'birthplace': 'ボストン',
            'residence': 'アーカム',
            'luck_points': 60,
            'abilities': {
                'str': 50, 'con': 60, 'pow': 65, 'dex': 55,
                'app': 45, 'siz': 70, 'int': 80, 'edu': 85
            },
            'backstory': {
                'personal_description': '眼鏡をかけた痩せ型の男性。常に古い革の鞄を持ち歩く',
                'ideology_beliefs': '知識こそが人類を救う唯一の道',
                'significant_people': '恩師のアームステッド教授',
                'meaningful_locations': 'ミスカトニック大学の図書館',
                'treasured_possessions': '恩師から譲り受けた古代の護符',
                'traits': '慎重で思慮深いが、古代の謎には目がない',
                'injuries_scars': '左手に古代遺跡で負った火傷の跡',
                'phobias_manias': '蛇恐怖症'
            },
            'skills': [
                ('考古学', '知識系', 1, 70, 0),
                ('図書館利用', '探索系', 20, 40, 0),
                ('目星', '探索系', 25, 30, 0),
                ('歴史', '知識系', 5, 40, 0),
                ('他の言語（ラテン語）', '言語系', 1, 50, 0),
                ('オカルト', '知識系', 5, 20, 10),
            ]
        },
        {
            'name': 'サラ・ウィリアムズ',
            'occupation': '作家',
            'age': 32,
            'gender': '女性',
            'birthplace': 'ニューヨーク',
            'residence': 'アーカム',
            'luck_points': 75,
            'abilities': {
                'str': 40, 'con': 55, 'pow': 75, 'dex': 60,
                'app': 70, 'siz': 55, 'int': 75, 'edu': 70
            },
            'backstory': {
                'personal_description': '赤毛で緑の瞳を持つ魅力的な女性',
                'ideology_beliefs': '真実は小説よりも奇なり',
                'significant_people': '失踪した兄',
                'meaningful_locations': '兄と過ごした実家の屋根裏部屋',
                'treasured_possessions': '兄の形見の万年筆',
                'traits': '好奇心旺盛で行動的',
                'injuries_scars': 'なし',
                'phobias_manias': '暗所恐怖症（軽度）'
            },
            'skills': [
                ('芸術/製作（執筆）', '技術系', 5, 60, 0),
                ('心理学', '対人系', 10, 40, 0),
                ('説得', '対人系', 10, 30, 0),
                ('図書館利用', '探索系', 20, 30, 0),
                ('目星', '探索系', 25, 20, 10),
                ('聞き耳', '探索系', 20, 20, 10),
            ]
        }
    ]
    
    for i, char_data in enumerate(seventh_characters):
        user = test_users[(i + 1) % len(test_users)]
        
        # 既存のキャラクターチェック
        existing = CharacterSheet.objects.filter(
            user=user,
            name=char_data['name'],
            edition='7th'
        ).first()
        
        if existing:
            print(f"{Colors.WARNING}⚠️  既存キャラクター: {char_data['name']} (スキップ){Colors.ENDC}")
            continue
        
        # キャラクターシート作成（7版は能力値そのまま）
        character = CharacterSheet.objects.create(
            user=user,
            edition='7th',
            name=char_data['name'],
            player_name=user.nickname,
            age=char_data['age'],
            gender=char_data['gender'],
            occupation=char_data['occupation'],
            birthplace=char_data['birthplace'],
            residence=char_data['residence'],
            str_value=char_data['abilities']['str'],
            con_value=char_data['abilities']['con'],
            pow_value=char_data['abilities']['pow'],
            dex_value=char_data['abilities']['dex'],
            app_value=char_data['abilities']['app'],
            siz_value=char_data['abilities']['siz'],
            int_value=char_data['abilities']['int'],
            edu_value=char_data['abilities']['edu'],
            notes=f'{char_data["occupation"]}として活動する探索者',
            is_active=True
        )
        
        # 7版固有データ
        backstory = char_data['backstory']
        CharacterSheet7th.objects.create(
            character_sheet=character,
            luck_points=char_data['luck_points'],
            personal_description=backstory['personal_description'],
            ideology_beliefs=backstory['ideology_beliefs'],
            significant_people=backstory['significant_people'],
            meaningful_locations=backstory['meaningful_locations'],
            treasured_possessions=backstory['treasured_possessions'],
            traits=backstory['traits'],
            injuries_scars=backstory['injuries_scars'],
            phobias_manias=backstory['phobias_manias']
        )
        
        # スキル作成
        for skill_name, category, base, occupation, interest in char_data['skills']:
            CharacterSkill.objects.create(
                character_sheet=character,
                skill_name=skill_name,
                category=category,
                base_value=base,
                occupation_points=occupation,
                interest_points=interest
            )
        
        print(f"{Colors.OKGREEN}✅ 7版キャラクター作成: {char_data['name']} ({char_data['occupation']}){Colors.ENDC}")
    
    # バージョン管理のテスト（成長したキャラクター）
    print(f"\n{Colors.OKCYAN}【キャラクター成長バージョン作成】{Colors.ENDC}")
    
    # 藤原誠司の成長版を作成
    base_char = CharacterSheet.objects.filter(name='藤原 誠司', edition='6th').first()
    if base_char and not base_char.versions.exists():
        # セッション後の成長版
        grown_char = base_char.create_new_version(
            version_note='狂気の山脈シナリオクリア後',
            session_count=base_char.session_count + 1,
            copy_skills=True
        )
        
        # 正気度減少
        grown_char.sanity_current = grown_char.sanity_current - 10
        grown_char.save()
        
        # クトゥルフ神話技能追加
        CharacterSkill.objects.create(
            character_sheet=grown_char,
            skill_name='クトゥルフ神話',
            category='知識系',
            base_value=0,
            occupation_points=0,
            interest_points=0,
            other_points=5
        )
        
        # 精神的障害を追加
        if hasattr(grown_char, 'sixth_edition_data'):
            grown_char.sixth_edition_data.mental_disorder = '軽度の妄想症（古代の存在に監視されている）'
            grown_char.sixth_edition_data.save()
        
        print(f"{Colors.OKGREEN}✅ 成長版作成: {grown_char.name} v{grown_char.version}{Colors.ENDC}")
    
    # 統計表示
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}作成完了統計{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    
    total_chars = CharacterSheet.objects.count()
    sixth_chars = CharacterSheet.objects.filter(edition='6th').count()
    seventh_chars = CharacterSheet.objects.filter(edition='7th').count()
    total_skills = CharacterSkill.objects.count()
    
    print(f"{Colors.OKBLUE}総キャラクター数: {total_chars}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}  - 6版: {sixth_chars}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}  - 7版: {seventh_chars}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}総技能数: {total_skills}{Colors.ENDC}")
    
    # 各ユーザーのキャラクター表示
    print(f"\n{Colors.OKCYAN}【ユーザー別キャラクター】{Colors.ENDC}")
    for user in test_users:
        chars = CharacterSheet.objects.filter(user=user)
        print(f"\n{Colors.BOLD}{user.nickname} ({user.username}):{Colors.ENDC}")
        for char in chars:
            skill_count = char.skills.count()
            print(f"  - {char.name} ({char.edition}) - {char.occupation} - 技能数: {skill_count}")

if __name__ == '__main__':
    create_test_characters()
    print(f"\n{Colors.OKGREEN}テストデータ作成完了！{Colors.ENDC}")