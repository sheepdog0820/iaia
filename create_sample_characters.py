#!/usr/bin/env python3
"""
サンプルキャラクターシート作成スクリプト
6版・7版両方のキャラクターシートを作成
"""

import os
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from accounts.models import (
    CustomUser, CharacterSheet, CharacterSheet6th,
    CharacterSkill, CharacterEquipment
)
import random


def create_6th_edition_character(user):
    """6版キャラクター作成"""
    
    # 基本キャラクターシート作成
    character = CharacterSheet.objects.create(
        user=user,
        edition='6th',
        name='田中一郎',
        player_name=user.get_full_name() or user.username,
        age=28,
        gender='男性',
        occupation='私立探偵',
        birthplace='東京',
        residence='新宿区',
        # 能力値 (6版基準)
        str_value=70,
        con_value=65,
        pow_value=60,
        dex_value=75,
        app_value=55,
        siz_value=60,
        int_value=80,
        edu_value=75,
        notes='6版サンプルキャラクター - 経験豊富な私立探偵'
    )
    
    # 6版固有データ作成
    sixth_data = CharacterSheet6th.objects.create(
        character_sheet=character,
        mental_disorder='軽度の不眠症'
    )
    
    # 基本スキル追加
    skills_6th = [
        {'name': '図書館', 'base': 25, 'occupation': 40, 'interest': 10},
        {'name': '目星', 'base': 25, 'occupation': 50, 'interest': 0},
        {'name': '聞き耳', 'base': 25, 'occupation': 30, 'interest': 15},
        {'name': '心理学', 'base': 5, 'occupation': 35, 'interest': 0},
        {'name': '説得', 'base': 15, 'occupation': 25, 'interest': 10},
        {'name': '隠れる', 'base': 10, 'occupation': 20, 'interest': 0},
        {'name': '忍び歩き', 'base': 10, 'occupation': 30, 'interest': 0},
        {'name': '拳銃', 'base': 20, 'occupation': 40, 'interest': 0},
        {'name': '運転（自動車）', 'base': 20, 'occupation': 0, 'interest': 25},
        {'name': '写真術', 'base': 10, 'occupation': 20, 'interest': 0},
    ]
    
    for skill_data in skills_6th:
        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name=skill_data['name'],
            base_value=skill_data['base'],
            occupation_points=skill_data['occupation'],
            interest_points=skill_data['interest']
        )
    
    # 装備追加
    equipment_6th = [
        {
            'type': 'weapon',
            'name': '.38口径リボルバー',
            'skill': '拳銃',
            'damage': '1d10',
            'range': '15m',
            'attacks': 1,
            'ammo': 6,
            'malfunction': 100
        },
        {
            'type': 'item',
            'name': 'カメラ',
            'description': 'デジタル一眼レフカメラ',
            'quantity': 1
        },
        {
            'type': 'item',
            'name': '懐中電灯',
            'description': 'LED懐中電灯',
            'quantity': 1
        },
        {
            'type': 'item',
            'name': '手帳',
            'description': '調査用メモ帳',
            'quantity': 1
        },
    ]
    
    for eq_data in equipment_6th:
        if eq_data['type'] == 'weapon':
            CharacterEquipment.objects.create(
                character_sheet=character,
                item_type='weapon',
                name=eq_data['name'],
                skill_name=eq_data['skill'],
                damage=eq_data['damage'],
                base_range=eq_data['range'],
                attacks_per_round=eq_data['attacks'],
                ammo=eq_data['ammo'],
                malfunction_number=eq_data['malfunction']
            )
        else:
            CharacterEquipment.objects.create(
                character_sheet=character,
                item_type='item',
                name=eq_data['name'],
                description=eq_data['description'],
                quantity=eq_data['quantity']
            )
    
    print(f"✅ 6版キャラクター '{character.name}' を作成しました")
    return character


def create_7th_edition_character(user):
    """7版キャラクター作成"""
    
    # 基本キャラクターシート作成
    character = CharacterSheet.objects.create(
        user=user,
        edition='7th',
        name='佐藤花子',
        player_name=user.get_full_name() or user.username,
        age=32,
        gender='女性',
        occupation='ジャーナリスト',
        birthplace='大阪',
        residence='渋谷区',
        # 能力値 (7版基準)
        str_value=55,
        con_value=70,
        pow_value=75,
        dex_value=70,
        app_value=80,
        siz_value=50,
        int_value=85,
        edu_value=80,
        notes='7版サンプルキャラクター - 真実を追い求めるジャーナリスト'
    )
    
    # 7版固有データ作成
    seventh_data = CharacterSheet7th.objects.create(
        character_sheet=character,
        luck_points=65,
        personal_description='真実を追い求める情熱的なジャーナリスト。正義感が強く、困っている人を見過ごせない性格。',
        ideology_beliefs='真実は必ず明らかにされるべきであり、権力の腐敗は許されない。',
        significant_people='恩師である大学教授の山田先生。彼女にジャーナリズムの心を教えてくれた。',
        meaningful_locations='母校の大学図書館。多くの調査をここで行い、真実を追い求める基盤となった場所。',
        treasured_possessions='父から受け継いだ万年筆。初めて記事を書いた時から愛用している。',
        traits='集中力が高く、長時間の調査も苦にならない。細かいことに気づくのが得意。',
        injuries_scars='右手に小さな傷跡。初めての危険な取材で負傷したもの。',
        phobias_manias='閉所恐怖症。狭い場所に長時間いると不安になる。'
    )
    
    # 基本スキル追加（7版）
    skills_7th = [
        {'name': '図書館', 'base': 20, 'occupation': 60, 'interest': 0},
        {'name': '目星', 'base': 25, 'occupation': 40, 'interest': 10},
        {'name': '聞き耳', 'base': 20, 'occupation': 45, 'interest': 0},
        {'name': '心理学', 'base': 10, 'occupation': 50, 'interest': 0},
        {'name': '説得', 'base': 10, 'occupation': 60, 'interest': 0},
        {'name': '魅惑', 'base': 15, 'occupation': 30, 'interest': 15},
        {'name': '威圧', 'base': 15, 'occupation': 20, 'interest': 0},
        {'name': 'コンピューター', 'base': 5, 'occupation': 40, 'interest': 20},
        {'name': '運転（自動車）', 'base': 20, 'occupation': 0, 'interest': 30},
        {'name': '写真術', 'base': 10, 'occupation': 25, 'interest': 10},
        {'name': '英語', 'base': 1, 'occupation': 30, 'interest': 20},
    ]
    
    for skill_data in skills_7th:
        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name=skill_data['name'],
            base_value=skill_data['base'],
            occupation_points=skill_data['occupation'],
            interest_points=skill_data['interest']
        )
    
    # 装備追加（7版）
    equipment_7th = [
        {
            'type': 'item',
            'name': 'ノートパソコン',
            'description': '軽量で高性能なノートパソコン。取材と記事執筆に必須',
            'quantity': 1
        },
        {
            'type': 'item',
            'name': 'デジタルカメラ',
            'description': '高解像度デジタルカメラ。証拠撮影用',
            'quantity': 1
        },
        {
            'type': 'item',
            'name': 'ICレコーダー',
            'description': '小型で高音質のボイスレコーダー',
            'quantity': 1
        },
        {
            'type': 'item',
            'name': 'プレスカード',
            'description': '報道関係者証明書',
            'quantity': 1
        },
        {
            'type': 'item',
            'name': '万年筆',
            'description': '父から受け継いだ宝物の万年筆',
            'quantity': 1
        },
    ]
    
    for eq_data in equipment_7th:
        CharacterEquipment.objects.create(
            character_sheet=character,
            item_type='item',
            name=eq_data['name'],
            description=eq_data['description'],
            quantity=eq_data['quantity']
        )
    
    print(f"✅ 7版キャラクター '{character.name}' を作成しました")
    return character


def create_character_version(original_character):
    """キャラクターのバージョン違いを作成"""
    
    # 元キャラクターをコピーしてバージョン2を作成
    new_character = CharacterSheet.objects.create(
        user=original_character.user,
        edition=original_character.edition,
        name=original_character.name,
        player_name=original_character.player_name,
        age=original_character.age + 1,  # 1歳年を取った設定
        gender=original_character.gender,
        occupation=original_character.occupation,
        birthplace=original_character.birthplace,
        residence=original_character.residence,
        # 能力値は若干成長
        str_value=min(original_character.str_value + random.randint(-2, 5), 90),
        con_value=min(original_character.con_value + random.randint(-2, 5), 90),
        pow_value=min(original_character.pow_value + random.randint(-2, 5), 90),
        dex_value=min(original_character.dex_value + random.randint(-2, 5), 90),
        app_value=min(original_character.app_value + random.randint(-2, 5), 90),
        siz_value=original_character.siz_value,  # 体格は変わらない
        int_value=min(original_character.int_value + random.randint(-1, 3), 90),
        edu_value=min(original_character.edu_value + random.randint(0, 5), 90),
        version=2,
        parent_sheet=original_character,
        notes=f'{original_character.notes}\n\n【バージョン2】経験を積んでスキルアップした版'
    )
    
    # スキルもコピーして成長させる
    for skill in original_character.skills.all():
        growth = random.randint(1, 10)  # 1-10の成長
        new_current = min(skill.current_value + growth, 90)
        
        CharacterSkill.objects.create(
            character_sheet=new_character,
            skill_name=skill.skill_name,
            base_value=skill.base_value,
            occupation_points=skill.occupation_points,
            interest_points=skill.interest_points,
            other_points=skill.other_points + growth
        )
    
    # 装備もコピー
    for equipment in original_character.equipment.all():
        CharacterEquipment.objects.create(
            character_sheet=new_character,
            item_type=equipment.item_type,
            name=equipment.name,
            skill_name=equipment.skill_name,
            damage=equipment.damage,
            base_range=equipment.base_range,
            attacks_per_round=equipment.attacks_per_round,
            ammo=equipment.ammo,
            malfunction_number=equipment.malfunction_number,
            armor_points=equipment.armor_points,
            description=equipment.description,
            quantity=equipment.quantity
        )
    
    # 版固有データもコピー
    if original_character.edition == '6th' and hasattr(original_character, 'sixth_edition_data'):
        CharacterSheet6th.objects.create(
            character_sheet=new_character,
            mental_disorder=original_character.sixth_edition_data.mental_disorder
        )
    elif original_character.edition == '7th' and hasattr(original_character, 'seventh_edition_data'):
        seventh_data = original_character.seventh_edition_data
        CharacterSheet7th.objects.create(
            character_sheet=new_character,
            luck_points=min(seventh_data.luck_points + random.randint(-5, 10), 90),
            personal_description=seventh_data.personal_description,
            ideology_beliefs=seventh_data.ideology_beliefs,
            significant_people=seventh_data.significant_people,
            meaningful_locations=seventh_data.meaningful_locations,
            treasured_possessions=seventh_data.treasured_possessions,
            traits=seventh_data.traits,
            injuries_scars=seventh_data.injuries_scars,
            phobias_manias=seventh_data.phobias_manias
        )
    
    print(f"✅ バージョン2キャラクター '{new_character.name}' v{new_character.version} を作成しました")
    return new_character


def main():
    """メイン処理"""
    print("🎭 サンプルキャラクターシート作成開始...")
    
    # テストユーザーを取得または作成
    user, created = CustomUser.objects.get_or_create(
        username='sample_player',
        defaults={
            'email': 'sample@example.com',
            'nickname': 'サンプルプレイヤー',
            'first_name': '太郎',
            'last_name': '山田',
            'trpg_history': 'TRPG歴5年。主にクトゥルフ神話TRPGをプレイ。'
        }
    )
    
    if created:
        user.set_password('sample123')
        user.save()
        print(f"✅ テストユーザー '{user.username}' を作成しました")
    else:
        print(f"ℹ️  既存ユーザー '{user.username}' を使用します")
    
    # 既存のサンプルキャラクターを削除
    CharacterSheet.objects.filter(user=user).delete()
    print("🗑️  既存のサンプルキャラクターを削除しました")
    
    # 6版キャラクター作成
    char_6th = create_6th_edition_character(user)
    
    # 7版キャラクター作成
    char_7th = create_7th_edition_character(user)
    
    # バージョン違いを作成
    char_6th_v2 = create_character_version(char_6th)
    char_7th_v2 = create_character_version(char_7th)
    
    print(f"\n📊 作成統計:")
    print(f"  - 6版キャラクター: 2個 (v1, v2)")
    print(f"  - 7版キャラクター: 2個 (v1, v2)")
    print(f"  - 総スキル数: {CharacterSkill.objects.filter(character_sheet__user=user).count()}")
    print(f"  - 総装備数: {CharacterEquipment.objects.filter(character_sheet__user=user).count()}")
    
    print("\n✨ サンプルキャラクターシート作成完了！")
    print("管理画面 (/admin) でキャラクターシートを確認できます。")


if __name__ == "__main__":
    main()