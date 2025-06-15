#!/usr/bin/env python
"""
デモデータ作成スクリプト
ホームページのアクティビティ表示用のテストデータを作成します。
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Group as CustomGroup
from schedules.models import TRPGSession, SessionParticipant
from scenarios.models import Scenario, PlayHistory

User = get_user_model()


def create_demo_data():
    """デモデータの作成"""
    print("デモデータを作成中...")
    
    # ユーザーの取得または作成
    try:
        demo_user = User.objects.get(username='demo_user')
        print("既存のデモユーザーを使用します")
    except User.DoesNotExist:
        demo_user = User.objects.create_user(
            username='demo_user',
            email='demo@example.com',
            password='demo123',
            nickname='デモユーザー'
        )
        print("デモユーザーを作成しました")
    
    try:
        gm_user = User.objects.get(username='demo_gm')
    except User.DoesNotExist:
        gm_user = User.objects.create_user(
            username='demo_gm',
            email='gm@example.com',
            password='gm123',
            nickname='デモGM'
        )
        print("デモGMを作成しました")
    
    # グループの作成
    demo_group, created = CustomGroup.objects.get_or_create(
        name='クトゥルフ研究会',
        defaults={
            'description': 'クトゥルフ神話TRPGを楽しむグループです',
            'created_by': demo_user,
            'visibility': 'public'
        }
    )
    if created:
        print("デモグループを作成しました")
    
    # グループメンバーの追加
    demo_group.members.add(demo_user, gm_user)
    
    # シナリオの作成
    scenarios_data = [
        {
            'title': '忌まわしき鞍部',
            'summary': 'クトゥルフ神話TRPGの定番シナリオ',
            'author': 'デモ作者',
            'created_by': gm_user,
            'recommended_players': '2-4人',
            'player_count': 3,
            'estimated_time': 240,
            'difficulty': 'intermediate',
            'estimated_duration': 'medium',
            'game_system': 'coc'
        },
        {
            'title': '死体安置所',
            'summary': '短時間で楽しめるシナリオ',
            'author': 'デモ作者',
            'created_by': gm_user,
            'recommended_players': '2-3人',
            'player_count': 2,
            'estimated_time': 180,
            'difficulty': 'beginner',
            'estimated_duration': 'short',
            'game_system': 'coc'
        },
        {
            'title': 'モサカルの咆哮',
            'summary': '上級者向けの難易度の高いシナリオ',
            'author': 'デモ作者',
            'created_by': gm_user,
            'recommended_players': '3-5人',
            'player_count': 4,
            'estimated_time': 360,
            'difficulty': 'advanced',
            'estimated_duration': 'long',
            'game_system': 'coc'
        }
    ]
    
    created_scenarios = []
    for scenario_data in scenarios_data:
        scenario, created = Scenario.objects.get_or_create(
            title=scenario_data['title'],
            defaults=scenario_data
        )
        created_scenarios.append(scenario)
        if created:
            print(f"シナリオ '{scenario.title}' を作成しました")
    
    # セッションの作成
    now = timezone.now()
    sessions_data = [
        {
            'title': '定期セッション - 忌まわしき鞍部',
            'description': '定期開催のセッションです',
            'date': now + timedelta(days=3),
            'location': 'Discord',
            'gm': gm_user,
            'group': demo_group,
            'duration_minutes': 240,
            'status': 'planned',
            'visibility': 'public'
        },
        {
            'title': '短時間セッション - 死体安置所',
            'description': '平日夜の短時間セッション',
            'date': now + timedelta(days=7),
            'location': 'ボイスチャット',
            'gm': gm_user,
            'group': demo_group,
            'duration_minutes': 180,
            'status': 'planned',
            'visibility': 'public'
        },
        {
            'title': '週末特別セッション - モサカルの咆哮',
            'description': '週末の長時間特別セッション',
            'date': now + timedelta(days=14),
            'location': 'Discord',
            'gm': gm_user,
            'group': demo_group,
            'duration_minutes': 360,
            'status': 'planned',
            'visibility': 'public'
        }
    ]
    
    created_sessions = []
    for session_data in sessions_data:
        session, created = TRPGSession.objects.get_or_create(
            title=session_data['title'],
            gm=session_data['gm'],
            defaults=session_data
        )
        created_sessions.append(session)
        if created:
            print(f"セッション '{session.title}' を作成しました")
    
    # セッション参加者の追加
    for session in created_sessions:
        participant, created = SessionParticipant.objects.get_or_create(
            session=session,
            user=demo_user,
            defaults={
                'role': 'player',
                'character_name': f'探索者{demo_user.nickname}'
            }
        )
        if created:
            print(f"'{session.title}' にプレイヤーを追加しました")
    
    # プレイ履歴の作成
    play_history_data = [
        {
            'scenario': created_scenarios[0],
            'user': demo_user,
            'played_date': now - timedelta(days=7),
            'role': 'player',
            'notes': '非常に楽しいセッションでした！'
        },
        {
            'scenario': created_scenarios[1],
            'user': demo_user,
            'played_date': now - timedelta(days=14),
            'role': 'player',
            'notes': '短時間で濃密な体験でした'
        },
        {
            'scenario': created_scenarios[2],
            'user': gm_user,
            'played_date': now - timedelta(days=21),
            'role': 'gm',
            'notes': 'GMとして楽しくセッションできました'
        }
    ]
    
    for history_data in play_history_data:
        history, created = PlayHistory.objects.get_or_create(
            scenario=history_data['scenario'],
            user=history_data['user'],
            played_date=history_data['played_date'],
            defaults=history_data
        )
        if created:
            print(f"プレイ履歴 '{history.scenario.title}' を作成しました")
    
    print("\n✅ デモデータの作成が完了しました！")
    print(f"作成されたデータ:")
    print(f"- ユーザー: {User.objects.count()}人")
    print(f"- グループ: {CustomGroup.objects.count()}個")
    print(f"- シナリオ: {Scenario.objects.count()}個")
    print(f"- セッション: {TRPGSession.objects.count()}個")
    print(f"- プレイ履歴: {PlayHistory.objects.count()}件")
    print(f"\nホームページで確認してください: http://localhost:8000/")


if __name__ == '__main__':
    try:
        create_demo_data()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)