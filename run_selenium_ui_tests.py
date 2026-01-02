#!/usr/bin/env python3
"""
キャラクターシート6版のSelenium UIテストを実行
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

# テスト実行
if __name__ == '__main__':
    print("=== キャラクターシート6版 Selenium UI テスト ===\n")
    
    # テストランナーの設定
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True, keepdb=True)
    
    # テストの実行
    test_labels = [
        'tests.ui.test_character_6th_ui.Character6thTemplateRenderingTest',
        'tests.ui.test_character_6th_ui.Character6thFormValidationTest',
        'tests.ui.test_character_6th_ui.Character6thAccessibilityTest',
        'tests.ui.test_character_6th_ui.Character6thErrorHandlingUITest',
    ]
    
    print("実行するテスト:")
    for label in test_labels:
        print(f"  - {label}")
    print()
    
    failures = test_runner.run_tests(test_labels)
    
    if failures:
        print(f"\n❌ {failures} 個のテストが失敗しました")
        sys.exit(1)
    else:
        print("\n✅ すべてのテストが成功しました！")
        sys.exit(0)