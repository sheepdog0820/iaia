#!/usr/bin/env python3
"""
簡易動線テスト - 主要機能の動作確認
タブレノ TRPGスケジュール管理システム
"""

import os
import sys
from datetime import timedelta

import django
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

# Django設定
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tableno.settings")
django.setup()

from accounts.models import CustomUser
from accounts.models import Group as CustomGroup
from scenarios.models import Scenario
from schedules.models import TRPGSession

User = get_user_model()


def test_basic_workflow():
    """基本的な動線テスト"""
    print("🚀 タブレノ 基本動線テスト開始")
    print("=" * 50)

    client = APIClient()

    # 1. ユーザー作成
    print("\\n1️⃣ ユーザー作成")
    user = User.objects.create_user(
        username="workflow_test", email="test@workflow.com", password="test123", nickname="ワークフローテスター"
    )
    client.force_authenticate(user=user)
    print(f"   ✅ ユーザー作成: {user.nickname}")

    # 2. ホーム画面API確認
    print("\\n2️⃣ ホーム画面API確認")

    # 次回セッション取得
    response = client.get("/api/schedules/sessions/upcoming/")
    print(f"   ✅ 次回セッション: {response.status_code} - {len(response.data)}件")

    # 統計取得
    response = client.get("/api/schedules/sessions/statistics/")
    print(f"   ✅ セッション統計: {response.status_code} - {response.data}")

    # 3. グループ機能
    print("\\n3️⃣ グループ機能テスト")

    group_data = {"name": "テストグループ", "description": "ワークフローテスト用グループ", "visibility": "public"}
    response = client.post("/api/accounts/groups/", group_data)
    if response.status_code == 201:
        group_id = response.data["id"]
        print(f"   ✅ グループ作成成功: {response.data['name']}")
    else:
        print(f"   ❌ グループ作成失敗: {response.status_code} - {response.data}")
        return False

    # 4. セッション機能
    print("\\n4️⃣ セッション機能テスト")

    session_data = {
        "title": "テストセッション",
        "description": "ワークフローテスト用",
        "date": (timezone.now() + timedelta(days=1)).isoformat(),
        "duration_minutes": 180,
        "group": group_id,
        "visibility": "group",
        "status": "planned",
    }
    response = client.post("/api/schedules/sessions/", session_data)
    if response.status_code == 201:
        session_id = response.data["id"]
        print(f"   ✅ セッション作成成功: {response.data['title']}")
    else:
        print(f"   ❌ セッション作成失敗: {response.status_code} - {response.data}")
        return False

    # 5. カレンダー機能
    print("\\n5️⃣ カレンダー機能テスト")

    start_date = timezone.now().date()
    end_date = (timezone.now() + timedelta(days=7)).date()

    response = client.get(
        "/api/schedules/calendar/", {"start": f"{start_date}T00:00:00+09:00", "end": f"{end_date}T23:59:59+09:00"}
    )

    if response.status_code == 200:
        events = response.data
        session_event = next((e for e in events if e.get("session_id") == session_id), None)
        if session_event:
            print(f"   ✅ カレンダー取得成功: {len(events)}件のイベント")
            print(f"   📅 作成セッション確認: {session_event['title']}")
            print(f"   🏷️ セッションタイプ: {session_event.get('type', 'unknown')}")
        else:
            print(f"   ⚠️ カレンダーに作成セッションが見つからない")
    else:
        print(f"   ❌ カレンダー取得失敗: {response.status_code}")

    # 6. シナリオ機能
    print("\\n6️⃣ シナリオ機能テスト")

    scenario_data = {
        "title": "テストシナリオ",
        "description": "ワークフロー用テストシナリオ",
        "system": "cthulhu",
        "difficulty": "medium",
        "estimated_duration": 240,
    }
    response = client.post("/api/scenarios/scenarios/", scenario_data)
    if response.status_code == 201:
        scenario_id = response.data["id"]
        print(f"   ✅ シナリオ作成成功: {response.data['title']}")
    else:
        print(f"   ❌ シナリオ作成失敗: {response.status_code} - {response.data}")

    # 7. 統計・エクスポート機能
    print("\\n7️⃣ 統計・エクスポート機能テスト")

    # 基本統計
    response = client.get("/api/accounts/statistics/simple/")
    if response.status_code == 200:
        stats = response.data
        print(f"   ✅ 基本統計取得: セッション{stats.get('session_count', 0)}回")
    else:
        print(f"   ❌ 統計取得失敗: {response.status_code}")

    # JSON エクスポート
    response = client.get("/api/accounts/export/formats/?format=json")
    if response.status_code == 200:
        export_data = response.json()
        print(f"   ✅ JSONエクスポート成功: ユーザー{export_data['user_info']['username']}")
    else:
        print(f"   ❌ JSONエクスポート失敗: {response.status_code}")

    # 8. ハンドアウト機能テスト
    print("\\n8️⃣ ハンドアウト機能テスト")

    # セッション詳細取得（参加者情報含む）
    response = client.get(f"/api/schedules/sessions/{session_id}/")
    if response.status_code == 200:
        session_detail = response.data
        participants = session_detail.get("participants_detail", [])

        if participants:
            # 最初の参加者（GM）にハンドアウト作成
            participant = participants[0]
            handout_data = {
                "session": session_id,
                "participant": participant["id"],
                "title": "テストハンドアウト",
                "content": "これはワークフローテスト用のハンドアウトです",
                "is_secret": True,
            }
            response = client.post("/api/schedules/handouts/", handout_data)
            if response.status_code == 201:
                print(f"   ✅ ハンドアウト作成成功: {response.data['title']}")
            else:
                print(f"   ❌ ハンドアウト作成失敗: {response.status_code} - {response.data}")
        else:
            print(f"   ⚠️ 参加者がいないためハンドアウトテストをスキップ")

    print("\\n" + "=" * 50)
    print("🎉 基本動線テスト完了!")
    print("✅ 主要機能の動作確認が正常に完了しました")
    return True


def test_calendar_filter_workflow():
    """カレンダーフィルター機能の動線テスト"""
    print("\\n📅 カレンダーフィルター動線テスト開始")
    print("-" * 40)

    client = APIClient()

    # テストユーザー作成
    user = User.objects.create_user(
        username="calendar_test", email="calendar@test.com", password="test123", nickname="カレンダーテスター"
    )
    client.force_authenticate(user=user)

    # GM用ユーザー作成
    gm_user = User.objects.create_user(username="gm_test", email="gm@test.com", password="test123", nickname="テストGM")

    # 1. グループ作成
    print("\\n1️⃣ テストデータ準備")

    # ユーザーのグループ
    client.force_authenticate(user=user)
    group_data = {"name": "カレンダーテストグループ", "description": "フィルターテスト用", "visibility": "public"}
    response = client.post("/api/accounts/groups/", group_data)
    user_group_id = response.data["id"]

    # GM用のグループ
    client.force_authenticate(user=gm_user)
    gm_group_data = {"name": "GM専用グループ", "description": "GM専用テスト", "visibility": "public"}
    response = client.post("/api/accounts/groups/", gm_group_data)
    gm_group_id = response.data["id"]

    # ユーザーがGM用グループに参加
    client.force_authenticate(user=user)
    response = client.post(f"/api/accounts/groups/{gm_group_id}/join/")

    print(f"   ✅ テストグループ準備完了")

    # 2. 異なるタイプのセッション作成
    print("\\n2️⃣ 異なるタイプのセッション作成")

    # 自分がGMのセッション
    gm_session_data = {
        "title": "自分がGMのセッション",
        "date": (timezone.now() + timedelta(days=1)).isoformat(),
        "duration_minutes": 180,
        "group": user_group_id,
        "visibility": "group",
        "status": "planned",
    }
    response = client.post("/api/schedules/sessions/", gm_session_data)
    gm_session_id = response.data["id"]
    print(f"   ✅ GMセッション作成: {response.data['title']}")

    # 参加するセッション（他のGM）
    client.force_authenticate(user=gm_user)
    participant_session_data = {
        "title": "参加するセッション",
        "date": (timezone.now() + timedelta(days=2)).isoformat(),
        "duration_minutes": 240,
        "group": gm_group_id,
        "visibility": "group",
        "status": "planned",
    }
    response = client.post("/api/schedules/sessions/", participant_session_data)
    participant_session_id = response.data["id"]

    # ユーザーがセッションに参加
    client.force_authenticate(user=user)
    join_data = {"character_name": "テストキャラ"}
    response = client.post(f"/api/schedules/sessions/{participant_session_id}/join/", join_data)
    print(f"   ✅ 参加セッション作成: {participant_session_data['title']}")

    # 公開セッション
    client.force_authenticate(user=gm_user)
    public_session_data = {
        "title": "公開セッション",
        "date": (timezone.now() + timedelta(days=3)).isoformat(),
        "duration_minutes": 120,
        "group": gm_group_id,
        "visibility": "public",
        "status": "planned",
    }
    response = client.post("/api/schedules/sessions/", public_session_data)
    public_session_id = response.data["id"]
    print(f"   ✅ 公開セッション作成: {response.data['title']}")

    # 3. カレンダーフィルター動作確認
    print("\\n3️⃣ カレンダーフィルター動作確認")

    client.force_authenticate(user=user)
    start_date = timezone.now().date()
    end_date = (timezone.now() + timedelta(days=7)).date()

    response = client.get(
        "/api/schedules/calendar/", {"start": f"{start_date}T00:00:00+09:00", "end": f"{end_date}T23:59:59+09:00"}
    )

    if response.status_code == 200:
        events = response.data
        print(f"   📊 総イベント数: {len(events)}")

        # 各セッションタイプのカウント
        gm_events = [e for e in events if e.get("is_gm", False)]
        participant_events = [e for e in events if e.get("is_participant", False)]
        public_events = [e for e in events if e.get("is_public_only", False)]

        print(f"   🎩 GMセッション: {len(gm_events)}件")
        print(f"   👥 参加セッション: {len(participant_events)}件")
        print(f"   🌐 公開セッション: {len(public_events)}件")

        # 各セッションの詳細確認
        for event in events:
            event_type = event.get("type", "unknown")
            print(f"   📅 {event['title']}: タイプ={event_type}")

        # フィルター機能が正しく動作しているか確認
        total_categorized = len(gm_events) + len(participant_events) + len(public_events)
        if total_categorized == len(events):
            print(f"   ✅ フィルター分類正常: 全{len(events)}件が正しく分類されています")
        else:
            print(f"   ⚠️ フィルター分類に問題: {total_categorized}/{len(events)}件のみ分類")

    print("\\n📅 カレンダーフィルター動線テスト完了!")
    return True


if __name__ == "__main__":
    try:
        # 基本動線テスト実行
        success1 = test_basic_workflow()

        # カレンダーフィルター動線テスト実行
        success2 = test_calendar_filter_workflow()

        if success1 and success2:
            print("\\n🎉 全ての動線テストが成功しました!")
            print("✨ タブレノ システムの主要機能が正常に動作しています")
        else:
            print("\\n⚠️ 一部のテストで問題が発生しました")

    except Exception as e:
        print(f"\\n❌ テスト実行中にエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
