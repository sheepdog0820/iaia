#!/usr/bin/env python
import os
import secrets
import sys
from pathlib import Path

import django

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Django設定の初期化
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tableno.settings")
django.setup()

from accounts.models import CustomUser

# スーパーユーザーが存在しない場合のみ作成
if not CustomUser.objects.filter(is_superuser=True).exists():
    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@arkham.nexus")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or secrets.token_urlsafe(18)
    admin_user = CustomUser.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        nickname="深淵の管理者",
    )
    print(f'✅ スーパーユーザー "{username}" を作成しました')
    print(f"   ユーザー名: {username}")
    print(f"   パスワード: {password}")
    print("   このパスワードは再表示されません。安全な場所に保存してください。")
else:
    print("ℹ️  スーパーユーザーは既に存在します")
