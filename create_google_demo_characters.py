#!/usr/bin/env python3
"""
Google Demo User用キャラクターデータ作成スクリプト
クトゥルフ神話TRPG 6版・7版のテストキャラクターを作成
"""

import os
import sys
import tempfile

import django
from PIL import Image

# Django設定
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tableno.settings")
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import CharacterEquipment, CharacterSheet, CharacterSheet6th, CharacterSkill, CustomUser


# 色付きテキスト出力
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def create_test_image(filename="demo_character.jpg", size=(400, 600), color="blue"):
    """テスト用キャラクター画像を作成"""
    image = Image.new("RGB", size, color=color)

    # 一時ファイルに保存
    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    image.save(temp_file.name, "JPEG")
    temp_file.close()

    # アップロード用ファイルオブジェクトを作成
    with open(temp_file.name, "rb") as f:
        uploaded_file = SimpleUploadedFile(filename, f.read(), content_type="image/jpeg")

    # 一時ファイルを削除
    os.unlink(temp_file.name)

    return uploaded_file


def create_google_demo_characters():
    """Google Demo User用キャラクターを作成"""
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}Google Demo User用キャラクターデータ作成開始{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")

    # Google Demo Userを取得
    try:
        google_user = CustomUser.objects.get(username="google_user_778860")
        print(f"{Colors.OKGREEN}✅ Google Demo User found: {google_user.username}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}📧 Email: {google_user.email}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}👤 Name: {google_user.first_name} {google_user.last_name}{Colors.ENDC}")
    except CustomUser.DoesNotExist:
        print(f"{Colors.FAIL}❌ Google Demo User not found{Colors.ENDC}")
        return

    # 6版デモキャラクターの作成
    print(f"\n{Colors.OKCYAN}【6版デモキャラクター作成】{Colors.ENDC}")

    sixth_characters = [
        {
            "name": "田中 誠",
            "occupation": "新聞記者",
            "age": 29,
            "gender": "男性",
            "birthplace": "東京都",
            "residence": "東京都",
            "mental_disorder": "",
            "abilities": {"str": 11, "con": 13, "pow": 14, "dex": 15, "app": 12, "siz": 12, "int": 17, "edu": 16},
            "skills": [
                ("目星", "探索系", 25, 40, 15),
                ("聞き耳", "探索系", 20, 35, 10),
                ("図書館", "探索系", 25, 45, 5),
                ("心理学", "知識系", 10, 35, 10),
                ("言いくるめ", "対人系", 5, 40, 15),
                ("信用", "対人系", 15, 30, 5),
                ("コンピューター", "技術系", 1, 45, 10),
                ("写真術", "技術系", 10, 25, 0),
            ],
            "image_color": "darkblue",
        },
        {
            "name": "佐藤 麻美",
            "occupation": "大学院生",
            "age": 24,
            "gender": "女性",
            "birthplace": "神奈川県",
            "residence": "東京都",
            "mental_disorder": "軽度の強迫性障害",
            "abilities": {"str": 9, "con": 12, "pow": 16, "dex": 14, "app": 15, "siz": 10, "int": 18, "edu": 17},
            "skills": [
                ("図書館", "探索系", 25, 50, 10),
                ("コンピューター", "技術系", 1, 40, 20),
                ("オカルト", "知識系", 5, 30, 15),
                ("心理学", "知識系", 10, 35, 10),
                ("英語", "言語系", 1, 40, 15),
                ("学問 (考古学)", "知識系", 1, 45, 5),
                ("説得", "対人系", 15, 25, 5),
                ("目星", "探索系", 25, 25, 10),
            ],
            "image_color": "purple",
        },
        {
            "name": "鈴木 健一",
            "occupation": "警察官",
            "age": 35,
            "gender": "男性",
            "birthplace": "埼玉県",
            "residence": "東京都",
            "mental_disorder": "",
            "abilities": {"str": 15, "con": 16, "pow": 12, "dex": 14, "app": 11, "siz": 14, "int": 13, "edu": 12},
            "skills": [
                ("拳銃", "戦闘系", 20, 50, 15),
                ("こぶし（パンチ）", "戦闘系", 50, 20, 10),
                ("目星", "探索系", 25, 35, 10),
                ("聞き耳", "探索系", 20, 30, 15),
                ("追跡", "探索系", 10, 40, 10),
                ("運転", "技術系", 20, 35, 5),
                ("法律", "知識系", 5, 30, 0),
                ("心理学", "知識系", 10, 25, 10),
            ],
            "image_color": "darkgreen",
        },
    ]

    for i, char_data in enumerate(sixth_characters):
        # 既存のキャラクターチェック
        existing = CharacterSheet.objects.filter(user=google_user, name=char_data["name"], edition="6th").first()

        if existing:
            print(f"{Colors.WARNING}⚠️  既存キャラクター: {char_data['name']} (スキップ){Colors.ENDC}")
            continue

        # テスト画像作成
        character_image = create_test_image(
            f"demo_6th_{char_data['name'].replace(' ', '_')}.jpg", color=char_data["image_color"]
        )

        # キャラクターシート作成（能力値は×5で保存）
        character = CharacterSheet.objects.create(
            user=google_user,
            edition="6th",
            name=char_data["name"],
            player_name=f"{google_user.first_name} {google_user.last_name}",
            age=char_data["age"],
            gender=char_data["gender"],
            occupation=char_data["occupation"],
            birthplace=char_data["birthplace"],
            residence=char_data["residence"],
            str_value=char_data["abilities"]["str"] * 5,
            con_value=char_data["abilities"]["con"] * 5,
            pow_value=char_data["abilities"]["pow"] * 5,
            dex_value=char_data["abilities"]["dex"] * 5,
            app_value=char_data["abilities"]["app"] * 5,
            siz_value=char_data["abilities"]["siz"] * 5,
            int_value=char_data["abilities"]["int"] * 5,
            edu_value=char_data["abilities"]["edu"] * 5,
            character_image=character_image,
            notes=f'Google Demo User用テストキャラクター - {char_data["occupation"]}',
            is_active=True,
        )

        # 6版固有データ
        CharacterSheet6th.objects.create(character_sheet=character, mental_disorder=char_data["mental_disorder"])

        # スキル作成
        for skill_name, category, base, occupation, interest in char_data["skills"]:
            CharacterSkill.objects.create(
                character_sheet=character,
                skill_name=skill_name,
                category=category,
                base_value=base,
                occupation_points=occupation,
                interest_points=interest,
            )

        print(f"{Colors.OKGREEN}✅ 6版キャラクター作成: {char_data['name']} ({char_data['occupation']}){Colors.ENDC}")

    # 7版デモキャラクターの作成
    print(f"\n{Colors.OKCYAN}【7版デモキャラクター作成】{Colors.ENDC}")

    seventh_characters = [
        {
            "name": "マイケル・ジョンソン",
            "occupation": "私立探偵",
            "age": 42,
            "gender": "男性",
            "birthplace": "ニューヨーク",
            "residence": "ボストン",
            "luck_points": 65,
            "abilities": {"str": 55, "con": 65, "pow": 60, "dex": 70, "app": 50, "siz": 60, "int": 75, "edu": 70},
            "backstory": {
                "personal_description": "中年の痩せ型男性。常に着古したトレンチコートを着用",
                "ideology_beliefs": "真実は必ず明かされる",
                "significant_people": "元相棒の刑事ジム・ハリス",
                "meaningful_locations": "最初の事件を解決した古いアパート",
                "treasured_possessions": "父の形見のポケットウォッチ",
                "traits": "執念深く、細部に注意を払う",
                "injuries_scars": "左肩に銃創の跡",
                "phobias_manias": "閉所恐怖症",
            },
            "skills": [
                ("目星", "探索系", 25, 50, 10),
                ("聞き耳", "探索系", 20, 40, 15),
                ("図書館利用", "探索系", 20, 35, 5),
                ("心理学", "対人系", 10, 45, 10),
                ("拳銃", "戦闘系", 20, 40, 15),
                ("運転 (自動車)", "技術系", 20, 30, 10),
                ("法律", "知識系", 5, 35, 10),
                ("追跡", "探索系", 10, 30, 15),
            ],
            "image_color": "brown",
        },
        {
            "name": "エミリー・ホワイト",
            "occupation": "医師",
            "age": 36,
            "gender": "女性",
            "birthplace": "フィラデルフィア",
            "residence": "ボストン",
            "luck_points": 70,
            "abilities": {"str": 45, "con": 60, "pow": 70, "dex": 65, "app": 65, "siz": 55, "int": 85, "edu": 80},
            "backstory": {
                "personal_description": "知的で落ち着いた女性。白衣がトレードマーク",
                "ideology_beliefs": "医学は人類を救う",
                "significant_people": "指導医のドクター・アンダーソン",
                "meaningful_locations": "ハーバード医学部の図書館",
                "treasured_possessions": "医学部卒業時の聴診器",
                "traits": "冷静沈着、分析的思考",
                "injuries_scars": "手術時の小さな傷跡",
                "phobias_manias": "完璧主義的傾向",
            },
            "skills": [
                ("医学", "知識系", 5, 70, 10),
                ("応急手当", "技術系", 30, 40, 0),
                ("生物学", "知識系", 1, 50, 15),
                ("化学", "知識系", 1, 40, 10),
                ("心理学", "対人系", 10, 35, 15),
                ("図書館利用", "探索系", 20, 30, 10),
                ("説得", "対人系", 10, 25, 10),
                ("コンピューター利用", "技術系", 1, 30, 20),
            ],
            "image_color": "lightblue",
        },
    ]

    for i, char_data in enumerate(seventh_characters):
        # 既存のキャラクターチェック
        existing = CharacterSheet.objects.filter(user=google_user, name=char_data["name"], edition="7th").first()

        if existing:
            print(f"{Colors.WARNING}⚠️  既存キャラクター: {char_data['name']} (スキップ){Colors.ENDC}")
            continue

        # テスト画像作成
        character_image = create_test_image(
            f"demo_7th_{char_data['name'].replace(' ', '_')}.jpg", color=char_data["image_color"]
        )

        # キャラクターシート作成（7版は能力値そのまま）
        character = CharacterSheet.objects.create(
            user=google_user,
            edition="7th",
            name=char_data["name"],
            player_name=f"{google_user.first_name} {google_user.last_name}",
            age=char_data["age"],
            gender=char_data["gender"],
            occupation=char_data["occupation"],
            birthplace=char_data["birthplace"],
            residence=char_data["residence"],
            str_value=char_data["abilities"]["str"],
            con_value=char_data["abilities"]["con"],
            pow_value=char_data["abilities"]["pow"],
            dex_value=char_data["abilities"]["dex"],
            app_value=char_data["abilities"]["app"],
            siz_value=char_data["abilities"]["siz"],
            int_value=char_data["abilities"]["int"],
            edu_value=char_data["abilities"]["edu"],
            character_image=character_image,
            notes=f'Google Demo User用テストキャラクター - {char_data["occupation"]}',
            is_active=True,
        )

        # 7版固有データ
        backstory = char_data["backstory"]
        try:
            from django.apps import apps

            character_sheet_7th_model = apps.get_model("accounts", "CharacterSheet7th")
        except LookupError:
            character_sheet_7th_model = None

        if character_sheet_7th_model is not None:
            character_sheet_7th_model.objects.create(
                character_sheet=character,
                luck_points=char_data["luck_points"],
                personal_description=backstory["personal_description"],
                ideology_beliefs=backstory["ideology_beliefs"],
                significant_people=backstory["significant_people"],
                meaningful_locations=backstory["meaningful_locations"],
                treasured_possessions=backstory["treasured_possessions"],
                traits=backstory["traits"],
                injuries_scars=backstory["injuries_scars"],
                phobias_manias=backstory["phobias_manias"],
            )

        # スキル作成
        for skill_name, category, base, occupation, interest in char_data["skills"]:
            CharacterSkill.objects.create(
                character_sheet=character,
                skill_name=skill_name,
                category=category,
                base_value=base,
                occupation_points=occupation,
                interest_points=interest,
            )

        print(f"{Colors.OKGREEN}✅ 7版キャラクター作成: {char_data['name']} ({char_data['occupation']}){Colors.ENDC}")

    # 装備アイテムの追加（6版キャラクター用）
    print(f"\n{Colors.OKCYAN}【装備アイテム追加】{Colors.ENDC}")

    # 田中 誠（記者）の装備
    tanaka = CharacterSheet.objects.filter(user=google_user, name="田中 誠", edition="6th").first()
    if tanaka and not tanaka.equipment.exists():
        CharacterEquipment.objects.create(
            character_sheet=tanaka,
            item_type="item",
            name="デジタルカメラ",
            description="高解像度で証拠写真を撮影可能。写真術技能に+10%ボーナス",
        )
        CharacterEquipment.objects.create(
            character_sheet=tanaka,
            item_type="item",
            name="ノートパソコン",
            description="記事執筆とインターネット調査用。コンピューター技能に+15%ボーナス",
        )
        print(f"{Colors.OKGREEN}✅ 装備追加: {tanaka.name} - 記者用装備{Colors.ENDC}")

    # 鈴木 健一（警察官）の装備
    suzuki = CharacterSheet.objects.filter(user=google_user, name="鈴木 健一", edition="6th").first()
    if suzuki and not suzuki.equipment.exists():
        CharacterEquipment.objects.create(
            character_sheet=suzuki,
            item_type="weapon",
            name="警察官用拳銃（ニューナンブM60）",
            skill_name="拳銃",
            damage="1D10+2",
            base_range="15m",
            attacks_per_round=1,
            ammo=5,
            malfunction_number=100,
        )
        CharacterEquipment.objects.create(
            character_sheet=suzuki,
            item_type="item",
            name="警察手帳",
            description="警察官としての身分証明書。信用技能に+20%ボーナス",
        )
        print(f"{Colors.OKGREEN}✅ 装備追加: {suzuki.name} - 警察官用装備{Colors.ENDC}")

    # 統計表示
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}Google Demo User キャラクター作成完了統計{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")

    google_chars = CharacterSheet.objects.filter(user=google_user)
    sixth_chars = google_chars.filter(edition="6th").count()
    seventh_chars = google_chars.filter(edition="7th").count()
    total_skills = CharacterSkill.objects.filter(character_sheet__user=google_user).count()
    total_equipment = CharacterEquipment.objects.filter(character_sheet__user=google_user).count()

    print(
        f"{Colors.OKBLUE}👤 ユーザー: {google_user.username} ({google_user.first_name} {google_user.last_name}){Colors.ENDC}"
    )
    print(f"{Colors.OKBLUE}📧 Email: {google_user.email}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}🎲 総キャラクター数: {google_chars.count()}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}  - 6版: {sixth_chars}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}  - 7版: {seventh_chars}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}⚔️  総技能数: {total_skills}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}🎒 総装備数: {total_equipment}{Colors.ENDC}")

    # 各キャラクターの詳細表示
    print(f"\n{Colors.OKCYAN}【作成されたキャラクター詳細】{Colors.ENDC}")
    for char in google_chars.order_by("edition", "name"):
        skill_count = char.skills.count()
        equipment_count = char.equipment.count()
        image_info = "画像あり" if char.character_image else "画像なし"

        print(f"\n{Colors.BOLD}{char.name} ({char.edition}版){Colors.ENDC}")
        print(f"  職業: {char.occupation}")
        print(f"  年齢: {char.age}歳")
        print(f"  技能数: {skill_count}")
        print(f"  装備数: {equipment_count}")
        print(f"  画像: {image_info}")

        if char.edition == "6th" and hasattr(char, "sixth_edition_data"):
            mental_disorder = char.sixth_edition_data.mental_disorder
            if mental_disorder:
                print(f"  精神的障害: {mental_disorder}")

        if char.edition == "7th" and hasattr(char, "seventh_edition_data"):
            beliefs = char.seventh_edition_data.ideology_beliefs
            if beliefs:
                print(f"  信念: {beliefs}")


if __name__ == "__main__":
    create_google_demo_characters()
    print(f"\n{Colors.OKGREEN}🐙 Google Demo User用テストデータ作成完了！{Colors.ENDC}")
