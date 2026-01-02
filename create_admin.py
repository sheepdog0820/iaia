#!/usr/bin/env python
"""
スーパーユーザーを自動作成するスクリプト
"""
import os
import sys
import django

# Django設定を読み込み
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError

User = get_user_model()

def create_superuser():
    """スーパーユーザーを作成"""
    username = 'admin'
    email = 'admin@arkham.nexus'
    password = 'arkham_admin_2024'
    nickname = 'アーカムの管理者'
    
    if User.objects.filter(username=username).exists():
        print(f'スーパーユーザー "{username}" は既に存在します。')
        return False
    
    try:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            nickname=nickname,
            trpg_history='タブレノの管理者。すべての権限を持つ。'
        )
        print(f'スーパーユーザー "{username}" を作成しました。')
        print(f'Email: {email}')
        print(f'Password: {password}')
        print('セキュリティのため、本番環境では必ずパスワードを変更してください。')
        return True
    except Exception as e:
        print(f'スーパーユーザーの作成に失敗しました: {e}')
        return False

if __name__ == '__main__':
    create_superuser()