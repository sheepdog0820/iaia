#!/usr/bin/env python3
"""
Google Demo User用キャラクターデータ修正スクリプト
6版キャラクターに基礎技能を追加し、7版キャラクターを削除
"""

import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from accounts.models import (
    CustomUser, CharacterSheet, CharacterSkill
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

def get_base_skills_6th():
    """6版基礎技能一覧を返す"""
    return [
        # 戦闘技能
        ('こぶし（パンチ）', '戦闘系', 50),
        ('頭突き', '戦闘系', 10),
        ('キック', '戦闘系', 25),
        ('組み付き', '戦闘系', 25),
        ('投擲', '戦闘系', 25),
        ('マーシャルアーツ', '戦闘系', 1),
        ('拳銃', '戦闘系', 20),
        ('サブマシンガン', '戦闘系', 15),
        ('ショットガン', '戦闘系', 30),
        ('マシンガン', '戦闘系', 15),
        ('ライフル', '戦闘系', 25),
        
        # 探索技能
        ('応急手当', '探索系', 30),
        ('聞き耳', '探索系', 25),
        ('忍び歩き', '探索系', 10),
        ('隠れる', '探索系', 10),
        ('目星', '探索系', 25),
        ('追跡', '探索系', 10),
        ('登攀', '探索系', 40),
        ('図書館', '探索系', 25),
        ('鍵開け', '探索系', 1),
        
        # 対人技能
        ('言いくるめ', '対人系', 5),
        ('信用', '対人系', 15),
        ('説得', '対人系', 15),
        ('母国語（日本語）', '言語系', None),  # EDU×5
        
        # 行動技能
        ('運転', '行動系', 20),
        ('機械修理', '技術系', 20),
        ('重機械操作', '技術系', 1),
        ('乗馬', '行動系', 5),
        ('水泳', '行動系', 25),
        ('跳躍', '行動系', 25),
        
        # 知識技能
        ('経理', '知識系', 10),
        ('図書館', '知識系', 25),
        ('コンピューター', '技術系', 1),
        ('電子工学', '技術系', 1),
        ('物理学', '知識系', 1),
        ('地質学', '知識系', 1),
        ('化学', '知識系', 1),
        ('生物学', '知識系', 1),
        ('薬学', '知識系', 1),
        ('医学', '知識系', 5),
        ('オカルト', '知識系', 5),
        ('人類学', '知識系', 1),
        ('考古学', '知識系', 1),
        ('歴史', '知識系', 20),
        ('法律', '知識系', 5),
        ('心理学', '知識系', 5),
        ('精神分析', '知識系', 1),
        ('クトゥルフ神話', '知識系', 0),
        
        # 技術技能
        ('写真術', '技術系', 10),
        ('芸術', '技術系', 5),
        ('変装', '技術系', 1),
        ('忍び足', '技術系', 10),
        ('回避', '戦闘系', None),  # DEX×5
    ]

def fix_google_demo_characters():
    """Google Demo User用キャラクターデータを修正"""
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}Google Demo User キャラクターデータ修正開始{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")
    
    # Google Demo Userを取得
    try:
        google_user = CustomUser.objects.get(username='google_user_778860')
        print(f"{Colors.OKGREEN}✅ Google Demo User found: {google_user.username}{Colors.ENDC}")
    except CustomUser.DoesNotExist:
        print(f"{Colors.FAIL}❌ Google Demo User not found{Colors.ENDC}")
        return
    
    # 既存の6版キャラクター一覧
    sixth_characters = CharacterSheet.objects.filter(user=google_user, edition='6th')
    print(f"\n{Colors.OKCYAN}【6版キャラクター確認】{Colors.ENDC}")
    print(f"対象キャラクター数: {sixth_characters.count()}")
    
    for char in sixth_characters:
        print(f"  - {char.name} ({char.occupation})")
        current_skills = char.skills.count()
        print(f"    現在の技能数: {current_skills}")
    
    # 基礎技能を追加
    print(f"\n{Colors.OKCYAN}【基礎技能追加】{Colors.ENDC}")
    base_skills = get_base_skills_6th()
    
    for char in sixth_characters:
        print(f"\n{Colors.BOLD}--- {char.name} ---{Colors.ENDC}")
        
        added_count = 0
        for skill_name, category, base_value in base_skills:
            # 既存技能をチェック
            existing_skill = char.skills.filter(skill_name=skill_name).first()
            if existing_skill:
                continue  # 既に存在する場合はスキップ
            
            # 特別な計算が必要な技能
            if base_value is None:
                if skill_name == '母国語（日本語）':
                    base_value = char.edu_value  # 内部値なのでそのまま
                elif skill_name == '回避':
                    base_value = char.dex_value  # 内部値なのでそのまま
                else:
                    base_value = 0
            
            # 基礎技能を追加
            CharacterSkill.objects.create(
                character_sheet=char,
                skill_name=skill_name,
                category=category,
                base_value=base_value,
                occupation_points=0,
                interest_points=0,
                bonus_points=0,
                other_points=0
            )
            added_count += 1
        
        print(f"  追加した基礎技能数: {added_count}")
        print(f"  合計技能数: {char.skills.count()}")
    
    # 統計表示
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}修正完了統計{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")
    
    for char in sixth_characters:
        skill_count = char.skills.count()
        base_skills_count = char.skills.filter(occupation_points=0, interest_points=0, bonus_points=0, other_points=0).count()
        custom_skills_count = skill_count - base_skills_count
        
        print(f"\n{Colors.BOLD}{char.name} ({char.edition}版){Colors.ENDC}")
        print(f"  職業: {char.occupation}")
        print(f"  年齢: {char.age}歳")
        print(f"  総技能数: {skill_count}")
        print(f"    - 基礎技能: {base_skills_count}")
        print(f"    - カスタム技能: {custom_skills_count}")
        
        # 主要技能TOP5を表示
        top_skills = char.skills.order_by('-current_value')[:5]
        print("  主要技能TOP5:")
        for skill in top_skills:
            print(f"    - {skill.skill_name}: {skill.current_value}%")
    
    print(f"\n{Colors.OKGREEN}🐙 Google Demo User キャラクター修正完了！{Colors.ENDC}")

if __name__ == '__main__':
    fix_google_demo_characters()