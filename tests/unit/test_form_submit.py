#!/usr/bin/env python3
"""
キャラクター作成フォーム送信テスト
"""

import os

import django
import requests
from django.contrib.auth import get_user_model
from django.test import Client

# Django設定の初期化
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tableno.settings")
django.setup()

User = get_user_model()


def test_character_form_submission():
    """キャラクター作成フォームの送信テスト"""
    print("=== キャラクター作成フォーム送信テスト ===")

    # テストクライアント作成
    client = Client()

    # 管理者ユーザーでログイン
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("❌ 管理者ユーザーが見つかりません")
        return

    client.force_login(admin_user)
    print(f"✅ ユーザーログイン成功: {admin_user.username}")

    # キャラクター作成ページにアクセス
    response = client.get("/accounts/character/create/6th/")
    print(f"✅ ページアクセス: {response.status_code}")

    if response.status_code != 200:
        print(f"❌ ページアクセス失敗: {response.status_code}")
        return

    # テストデータ作成（ユニークな名前）
    import time

    unique_name = f"テスト探索者_{int(time.time())}"
    form_data = {
        "name": unique_name,
        "player_name": admin_user.username,
        "age": 25,
        "gender": "男性",
        "occupation": "学生",
        "birthplace": "東京",
        "residence": "東京",
        "str_value": 13,
        "con_value": 12,
        "pow_value": 15,
        "dex_value": 14,
        "app_value": 11,
        "siz_value": 13,
        "int_value": 16,
        "edu_value": 17,
        "notes": "テスト用キャラクター",
        "mental_disorder": "",
        # 技能データ
        "skill_ナビゲート_name": "ナビゲート",
        "skill_ナビゲート_base": "10",
        "skill_ナビゲート_occupation": "60",
        "skill_ナビゲート_interest": "0",
        "skill_ナビゲート_bonus": "0",
        "skill_ナビゲート_total": "70",
        "skill_応急手当_name": "応急手当",
        "skill_応急手当_base": "30",
        "skill_応急手当_occupation": "0",
        "skill_応急手当_interest": "20",
        "skill_応急手当_bonus": "0",
        "skill_応急手当_total": "50",
    }

    print("📝 送信データ:")
    for key, value in form_data.items():
        if key.startswith("skill_") or key in ["name", "str_value", "con_value"]:
            print(f"  {key}: {value}")

    # フォーム送信
    response = client.post("/accounts/character/create/6th/", form_data)
    print(f"📤 フォーム送信結果: {response.status_code}")

    if response.status_code == 302:
        print(f"✅ リダイレクト成功: {response.get('Location', 'no location')}")

        # 作成されたキャラクターを確認
        from accounts.character_models import CharacterSheet

        latest_character = CharacterSheet.objects.filter(user=admin_user).order_by("-created_at").first()
        if latest_character:
            print(f"✅ キャラクター作成成功: {latest_character.name}")
            print(f"  - 能力値: STR={latest_character.str_value}, INT={latest_character.int_value}")

            # 技能データの確認
            skills = latest_character.skills.all()
            print(f"  - 技能数: {skills.count()}")
            for skill in skills:
                if skill.occupation_points > 0 or skill.interest_points > 0:
                    print(f"    {skill.skill_name}: 職業={skill.occupation_points}, 趣味={skill.interest_points}")
        else:
            print("❌ キャラクターが作成されていません")

    elif response.status_code == 200:
        print("❌ フォームエラー - バリデーション失敗の可能性")
        if hasattr(response, "context") and "form" in response.context:
            form = response.context["form"]
            if form.errors:
                print("📋 フォームエラー:")
                for field, errors in form.errors.items():
                    print(f"  {field}: {errors}")
    else:
        print(f"❌ 予期しないレスポンス: {response.status_code}")


if __name__ == "__main__":
    test_character_form_submission()
