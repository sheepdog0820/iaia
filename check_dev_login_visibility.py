#!/usr/bin/env python
"""
開発用ログインリンクの表示状態を確認するスクリプト
"""

import os
import sys
import django

# Django設定をロード
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

print("=== 開発用ログイン機能の状態確認 ===")
print(f"DEBUG設定: {settings.DEBUG}")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print()

if settings.DEBUG:
    print("✅ 開発用ログインリンクは表示されます")
    print()
    print("以下の場所でリンクが利用可能:")
    print("1. ナビゲーションバー（未ログイン時）")
    print("2. ホームページ（未ログイン時）")
    print("3. ログイン画面の下部")
    print("4. ユーザーメニュー（ログイン時）")
else:
    print("❌ 開発用ログインリンクは表示されません（本番モード）")

print()
print("=== テストユーザー情報 ===")

# テストユーザーの存在確認
test_usernames = [
    'keeper1', 'keeper2',
    'investigator1', 'investigator2', 'investigator3',
    'investigator4', 'investigator5', 'investigator6',
    'admin'
]

existing_users = []
missing_users = []

for username in test_usernames:
    try:
        user = User.objects.get(username=username)
        existing_users.append(f"{username} ({user.nickname or 'ニックネームなし'})")
    except User.DoesNotExist:
        missing_users.append(username)

if existing_users:
    print("✅ 利用可能なテストユーザー:")
    for user in existing_users:
        print(f"   - {user}")

if missing_users:
    print()
    print("❌ 存在しないテストユーザー:")
    for user in missing_users:
        print(f"   - {user}")
    print()
    print("テストデータを作成するには以下を実行:")
    print("python manage.py create_session_test_data")

print()
print("=== アクセス方法 ===")
print("開発用ログインページ: http://localhost:8000/accounts/dev-login/")
print("（DEBUG=Trueの場合のみアクセス可能）")