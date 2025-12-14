#!/usr/bin/env python3
"""
SocialAppデバッグスクリプト
"""
import os
import sys
import django

# Django設定を読み込み
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.db import connection

def debug_socialapps():
    """SocialAppの詳細なデバッグ情報を表示"""
    print("=== SocialAppデバッグ情報 ===\n")
    
    # 1. 直接SQLでSocialAppテーブルを確認
    print("1. データベース内のSocialAppレコード（SQL直接）:")
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM socialaccount_socialapp")
        rows = cursor.fetchall()
        print(f"  レコード数: {len(rows)}")
        for row in rows:
            print(f"  - {row}")
    
    # 2. Django ORMでの確認
    print("\n2. Django ORMでのSocialApp:")
    apps = SocialApp.objects.all()
    print(f"  総数: {apps.count()}")
    for app in apps:
        print(f"  - ID: {app.id}, Provider: {app.provider}, Name: {app.name}")
        print(f"    Client ID: {app.client_id}")
        print(f"    Sites: {list(app.sites.all())}")
    
    # 3. Googleプロバイダーのみフィルタ
    print("\n3. Googleプロバイダーのみ:")
    google_apps = SocialApp.objects.filter(provider='google')
    print(f"  Google App数: {google_apps.count()}")
    for app in google_apps:
        print(f"  - ID: {app.id}, Sites: {list(app.sites.all())}")
    
    # 4. sites関連テーブルの確認
    print("\n4. socialaccount_socialapp_sitesテーブル:")
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM socialaccount_socialapp_sites")
        rows = cursor.fetchall()
        print(f"  レコード数: {len(rows)}")
        for row in rows:
            print(f"  - {row}")
    
    # 5. 現在のサイト情報
    print("\n5. 現在のサイト情報:")
    site = Site.objects.get_current()
    print(f"  ID: {site.id}, Domain: {site.domain}, Name: {site.name}")
    
    # 6. 重複チェック（プロバイダーとサイトの組み合わせ）
    print("\n6. 重複チェック:")
    from django.db.models import Count
    duplicates = SocialApp.objects.values('provider').annotate(count=Count('provider')).filter(count__gt=1)
    if duplicates:
        print("  重複が見つかりました:")
        for dup in duplicates:
            print(f"  - Provider: {dup['provider']}, Count: {dup['count']}")
    else:
        print("  重複なし")

if __name__ == '__main__':
    debug_socialapps()