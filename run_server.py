#!/usr/bin/env python
"""
Arkham Nexus 開発サーバー起動スクリプト
"""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
    
    print('🦑' * 20)
    print('     Arkham Nexus - TRPG管理システム')
    print('🦑' * 20)
    print()
    print('📋 準備完了：')
    print('  ✅ データベース設定完了')
    print('  ✅ テストデータ作成完了')
    print('  ✅ 統計システム実装完了')
    print('  ✅ グループ管理API実装完了')
    print()
    print('🔗 アクセス情報：')
    print('  メインページ: http://127.0.0.1:8000/')
    print('  管理画面: http://127.0.0.1:8000/admin/')
    print('  デモログイン: http://127.0.0.1:8000/accounts/demo/')
    print()
    print('👤 ログイン情報：')
    print('  管理者: admin / admin123')
    print('  テストユーザー: testuser1 / testpass123')
    print('  （testuser1〜testuser15まで利用可能）')
    print()
    print('🎮 主要機能：')
    print('  📅 Chrono Abyss (カレンダー)')
    print('  📜 R\'lyeh Log (セッション管理)')
    print('  📚 Mythos Archive (シナリオアーカイブ)')
    print('  👥 Cult Circle (グループ管理)')
    print('  📊 Tindalos Metrics (統計ダッシュボード)')
    print()
    print('🚀 サーバーを起動しています...')
    print('   Ctrl+C で停止')
    print()
    
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'runserver'])
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc