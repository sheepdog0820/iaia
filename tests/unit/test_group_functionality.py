#!/usr/bin/env python3
"""
グループ管理機能のテストスクリプト
"""

import os
import sys
import django
from django.test.utils import get_runner
from django.conf import settings
from django.core.management import execute_from_command_line

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Group, GroupMembership, Friend

User = get_user_model()

def create_test_data():
    """テストデータの作成"""
    print("🎭 グループ機能テストデータ作成中...")
    
    # テストユーザーを作成
    users = []
    for i in range(1, 6):
        user, created = User.objects.get_or_create(
            username=f'groupuser{i}',
            defaults={
                'email': f'groupuser{i}@example.com',
                'nickname': f'グループユーザー{i}',
                'trpg_history': f'TRPG歴{i+2}年'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
        users.append(user)
        print(f"  ✅ ユーザー作成: {user.username} ({user.nickname})")
    
    # フレンド関係を作成
    print("\n👥 フレンド関係作成中...")
    for i, user in enumerate(users):
        for j, friend in enumerate(users):
            if i != j and i < 3:  # 最初の3人が相互フレンド
                Friend.objects.get_or_create(
                    user=user,
                    friend=friend
                )
    
    friend_count = Friend.objects.count()
    print(f"  ✅ フレンド関係: {friend_count}件作成")
    
    # グループを作成
    print("\n🏛️ テストグループ作成中...")
    
    # 公開グループ
    group1, created = Group.objects.get_or_create(
        name='深淵探索同好会',
        defaults={
            'description': 'クトゥルフ神話TRPGを愛する者たちの集い。初心者歓迎！',
            'visibility': 'public',
            'created_by': users[0]
        }
    )
    if created:
        print(f"  ✅ 公開グループ作成: {group1.name}")
        
        # メンバー追加
        for i, user in enumerate(users[:3]):
            role = 'admin' if i == 0 else 'member'
            GroupMembership.objects.get_or_create(
                group=group1,
                user=user,
                defaults={'role': role}
            )
    
    # プライベートグループ
    group2, created = Group.objects.get_or_create(
        name='秘密結社ナイアルラトホテプ',
        defaults={
            'description': '選ばれし者のみが参加できる秘密のサークル',
            'visibility': 'private',
            'created_by': users[1]
        }
    )
    if created:
        print(f"  ✅ プライベートグループ作成: {group2.name}")
        
        # メンバー追加
        for i, user in enumerate(users[1:4]):
            role = 'admin' if i == 0 else 'member'
            GroupMembership.objects.get_or_create(
                group=group2,
                user=user,
                defaults={'role': role}
            )
    
    # 大規模グループ
    group3, created = Group.objects.get_or_create(
        name='TRPGマスターズ・ギルド',
        defaults={
            'description': '経験豊富なGMたちが集まるコミュニティ。技術共有とセッション運営について語り合いましょう。',
            'visibility': 'public',
            'created_by': users[2]
        }
    )
    if created:
        print(f"  ✅ 大規模グループ作成: {group3.name}")
        
        # 全ユーザーを追加
        for i, user in enumerate(users):
            role = 'admin' if i == 2 else 'member'
            GroupMembership.objects.get_or_create(
                group=group3,
                user=user,
                defaults={'role': role}
            )
    
    print(f"\n📊 作成完了:")
    print(f"  👤 ユーザー数: {User.objects.count()}")
    print(f"  🏛️ グループ数: {Group.objects.count()}")
    print(f"  👥 メンバーシップ数: {GroupMembership.objects.count()}")
    print(f"  🤝 フレンド関係数: {Friend.objects.count()}")

def test_group_apis():
    """グループAPIの基本テスト"""
    from django.test import Client
    from django.urls import reverse
    import json
    
    print("\n🧪 グループAPI機能テスト開始...")
    
    client = Client()
    
    # テストユーザーでログイン
    user = User.objects.get(username='groupuser1')
    client.force_login(user)
    
    # グループ一覧取得テスト
    print("  📋 グループ一覧取得テスト...")
    response = client.get('/api/accounts/groups/')
    if response.status_code == 200:
        groups = response.json()
        print(f"    ✅ 参加中グループ: {len(groups)}件取得")
    else:
        print(f"    ❌ エラー: {response.status_code}")
    
    # 公開グループ一覧取得テスト
    print("  🌐 公開グループ一覧取得テスト...")
    response = client.get('/api/accounts/groups/public/')
    if response.status_code == 200:
        public_groups = response.json()
        print(f"    ✅ 公開グループ: {len(public_groups)}件取得")
    else:
        print(f"    ❌ エラー: {response.status_code}")
    
    # グループメンバー取得テスト
    print("  👥 グループメンバー取得テスト...")
    group = Group.objects.first()
    response = client.get(f'/api/accounts/groups/{group.id}/members/')
    if response.status_code == 200:
        members = response.json()
        print(f"    ✅ グループ '{group.name}' のメンバー: {len(members)}人取得")
    else:
        print(f"    ❌ エラー: {response.status_code}")
    
    # フレンド一覧取得テスト
    print("  🤝 フレンド一覧取得テスト...")
    response = client.get('/api/accounts/friends/')
    if response.status_code == 200:
        friends = response.json()
        print(f"    ✅ フレンド: {len(friends)}人取得")
    else:
        print(f"    ❌ エラー: {response.status_code}")
    
    print("  🎯 基本APIテスト完了!")

def test_group_creation():
    """グループ作成テスト"""
    from django.test import Client
    import json
    
    print("\n🏗️ グループ作成テスト...")
    
    client = Client()
    user = User.objects.get(username='groupuser4')
    client.force_login(user)
    
    # 新しいグループを作成
    group_data = {
        'name': 'テスト用新規グループ',
        'description': 'APIテストで作成されたグループです',
        'visibility': 'public'
    }
    
    response = client.post(
        '/api/accounts/groups/',
        json.dumps(group_data),
        content_type='application/json'
    )
    
    if response.status_code == 201:
        created_group = response.json()
        print(f"    ✅ グループ作成成功: {created_group['name']}")
        
        # 作成者が管理者として追加されているかチェック
        group = Group.objects.get(id=created_group['id'])
        membership = GroupMembership.objects.filter(
            group=group, user=user, role='admin'
        ).first()
        
        if membership:
            print("    ✅ 作成者が管理者として自動追加されました")
        else:
            print("    ❌ 作成者の管理者権限設定に問題があります")
            
    else:
        print(f"    ❌ グループ作成失敗: {response.status_code}")
        if hasattr(response, 'json'):
            print(f"        詳細: {response.json()}")

def main():
    """メイン実行関数"""
    print("=" * 50)
    print("🦑 Arkham Nexus - グループ機能テスト")
    print("=" * 50)
    
    # テストデータ作成
    create_test_data()
    
    # API機能テスト
    test_group_apis()
    
    # グループ作成テスト
    test_group_creation()
    
    print("\n" + "=" * 50)
    print("🎉 グループ機能テスト完了!")
    print("💻 ブラウザで http://127.0.0.1:8000/accounts/groups/view/ にアクセスして")
    print("   Cult Circle (グループ管理) を確認してください。")
    print("\n📝 テストログイン情報:")
    print("   ユーザー名: groupuser1 〜 groupuser5")
    print("   パスワード: testpass123")
    print("=" * 50)

if __name__ == '__main__':
    main()