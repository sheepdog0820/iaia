#!/usr/bin/env python
import os
import django

# Django設定の初期化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from accounts.models import CustomUser

# スーパーユーザーが存在しない場合のみ作成
if not CustomUser.objects.filter(is_superuser=True).exists():
    admin_user = CustomUser.objects.create_superuser(
        username='admin',
        email='admin@arkham.nexus',
        password='admin123',
        nickname='深淵の管理者'
    )
    print('✅ スーパーユーザー "admin" を作成しました')
    print('   ユーザー名: admin')
    print('   パスワード: admin123')
else:
    print('ℹ️  スーパーユーザーは既に存在します')