#!/usr/bin/env python
"""
スーパーユーザーを自動作成するスクリプト
"""

import os
import secrets
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import django

# Django設定を読み込み
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tableno.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError

User = get_user_model()


def create_superuser():
    """スーパーユーザーを作成"""
    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@arkham.nexus")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or secrets.token_urlsafe(18)
    nickname = "アーカムの管理者"

    if User.objects.filter(username=username).exists():
        print(f'スーパーユーザー "{username}" は既に存在します。')
        return False

    try:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            nickname=nickname,
            trpg_history="タブレノの管理者。すべての権限を持つ。",
        )
        print(f'スーパーユーザー "{username}" を作成しました。')
        print(f"Email: {email}")
        print(f"Password: {password}")
        print("このパスワードは再表示されません。安全な場所に保存してください。")
        print("本番環境では DJANGO_SUPERUSER_PASSWORD を安全なSecretから指定してください。")
        return True
    except Exception as e:
        print(f"スーパーユーザーの作成に失敗しました: {e}")
        return False


if __name__ == "__main__":
    create_superuser()
