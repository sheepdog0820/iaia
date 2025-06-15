#!/usr/bin/env python
"""
現在ログインしているユーザーにデモデータを関連付けるスクリプト
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


def assign_demo_data_to_mock_users():
    """モックログインユーザーにデモデータを割り当て"""
    print("モックログインユーザーにデモデータを割り当て中...")
    
    # モックログインで作成されるユーザーを取得
    mock_users = User.objects.filter(
        email__in=['demo.google@example.com', 'demo.twitter@example.com']
    )
    
    if not mock_users.exists():
        print("モックログインユーザーが見つかりません。先にログインしてください。")
        return
    
    # 既存のデモグループとデータを取得
    try:
        demo_group = CustomGroup.objects.get(name='クトゥルフ研究会')
    except CustomGroup.DoesNotExist:
        print("デモグループが見つかりません。先にcreate_demo_data.pyを実行してください。")
        return
    
    # 既存のシナリオを取得
    scenarios = Scenario.objects.filter(title__in=['忌まわしき鞍部', '死体安置所', 'モサカルの咆哮'])
    
    # 既存のセッションを取得
    sessions = TRPGSession.objects.filter(title__icontains='セッション')
    
    now = timezone.now()
    
    for user in mock_users:
        print(f"ユーザー {user.nickname or user.username} にデータを割り当て中...")
        
        # グループメンバーに追加
        demo_group.members.add(user)
        print(f"  - グループに追加しました")
        
        # セッション参加者として追加
        for session in sessions[:3]:  # 最初の3つのセッションに参加
            participant, created = SessionParticipant.objects.get_or_create(
                session=session,
                user=user,
                defaults={
                    'role': 'player',
                    'character_name': f'探索者{user.nickname or user.username}'
                }
            )
            if created:
                print(f"  - セッション '{session.title}' に参加者として追加")
        
        # プレイ履歴を追加
        for i, scenario in enumerate(scenarios):
            history, created = PlayHistory.objects.get_or_create(
                scenario=scenario,
                user=user,
                played_date=now - timedelta(days=7 * (i + 1)),
                defaults={
                    'role': 'player',
                    'notes': f'{scenario.title}を楽しくプレイしました！'
                }
            )
            if created:
                print(f"  - プレイ履歴 '{scenario.title}' を追加")
    
    print("\n✅ モックログインユーザーへのデータ割り当てが完了しました！")
    print("ホームページを再読み込みして確認してください。")


if __name__ == '__main__':
    try:
        assign_demo_data_to_mock_users()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)