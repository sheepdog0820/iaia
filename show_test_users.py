#!/usr/bin/env python
import os
import django

# Django設定の初期化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from accounts.models import CustomUser

print('🦑 Arkham Nexus - テストユーザー一覧')
print('=' * 50)

# 管理者ユーザー
admin_users = CustomUser.objects.filter(is_superuser=True)
print('📋 管理者ユーザー:')
for user in admin_users:
    print(f'   ユーザー名: {user.username}')
    print(f'   パスワード: admin123')
    print(f'   ニックネーム: {user.nickname}')
    print()

# テストユーザー
test_users = CustomUser.objects.filter(is_superuser=False)[:10]
print('👥 テストユーザー（最初の10人）:')
for user in test_users:
    print(f'   ユーザー名: {user.username}')
    print(f'   パスワード: testpass123')
    print(f'   ニックネーム: {user.nickname}')
    print(f'   メールアドレス: {user.email}')
    print()

print('🔗 アクセス方法:')
print('1. サーバー起動: python manage.py runserver')
print('2. ブラウザで http://127.0.0.1:8000/ にアクセス')
print('3. 上記のユーザー名・パスワードでログイン')
print('4. または http://127.0.0.1:8000/accounts/demo/ でデモログインも可能')
print()

print('📊 統計データアクセス:')
print('- Tindalos Metrics: ナビゲーションの「Tindalos Metrics」リンク')
print('- または直接 http://127.0.0.1:8000/api/accounts/statistics/view/')
print()

print('🎮 機能テスト:')
print('- カレンダー: http://127.0.0.1:8000/api/schedules/calendar/view/')
print('- セッション管理: http://127.0.0.1:8000/api/schedules/sessions/view/')
print('- シナリオアーカイブ: http://127.0.0.1:8000/api/scenarios/archive/view/')
print('- グループ管理: http://127.0.0.1:8000/api/accounts/groups/view/')