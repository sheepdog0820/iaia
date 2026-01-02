#!/usr/bin/env python3
"""
包括的テストランナー - タブレノ統合テストスイート
複数機能連携のSTテスト実行スクリプト
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line


def setup_django():
    """Django環境のセットアップ"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
    django.setup()


def run_integration_tests():
    """統合テストスイートの実行"""
    
    print("🌟 タブレノ - Comprehensive Integration Test Suite")
    print("=" * 60)
    
    # テストクラスの定義
    test_suites = [
        {
            'name': 'User & Group Integration Tests',
            'module': 'test_integration.UserGroupIntegrationTestCase',
            'description': 'ユーザー管理とグループ機能の連携テスト'
        },
        {
            'name': 'Session & Scenario Integration Tests', 
            'module': 'test_integration.SessionScenarioIntegrationTestCase',
            'description': 'セッション管理とシナリオ機能の連携テスト'
        },
        {
            'name': 'Authentication & Permission Tests',
            'module': 'test_integration.AuthenticationAndPermissionIntegrationTestCase', 
            'description': '認証とAPI権限の統合テスト'
        },
        {
            'name': 'End-to-End Business Flow Tests',
            'module': 'test_integration.EndToEndBusinessFlowTestCase',
            'description': 'エンドツーエンドの業務フローテスト'
        },
        {
            'name': 'System Authentication & Permission Tests',
            'module': 'test_system_integration.AuthenticationPermissionIntegrationTestCase',
            'description': 'システム認証と権限制御の統合テスト'
        },
        {
            'name': 'Complete Workflow Integration Tests',
            'module': 'test_system_integration.CompleteWorkflowIntegrationTestCase',
            'description': '完全な業務ワークフロー統合テスト'
        },
        {
            'name': 'Demo Login Integration Tests',
            'module': 'test_system_integration.DemoLoginIntegrationTestCase',
            'description': 'デモログイン機能の統合テスト'
        },
        {
            'name': 'API Error Handling Tests',
            'module': 'test_system_integration.APIErrorHandlingIntegrationTestCase',
            'description': 'APIエラーハンドリングの統合テスト'
        }
    ]
    
    print("\n📋 Test Suites to be executed:")
    for i, suite in enumerate(test_suites, 1):
        print(f"  {i}. {suite['name']}")
        print(f"     {suite['description']}")
    
    print("\n" + "=" * 60)
    
    # 各テストスイートを実行
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
    
    failed_tests = []
    passed_tests = []
    
    for suite in test_suites:
        print(f"\n🧪 Running: {suite['name']}")
        print("-" * 40)
        
        try:
            result = test_runner.run_tests([suite['module']])
            if result == 0:
                passed_tests.append(suite['name'])
                print(f"✅ {suite['name']} - PASSED")
            else:
                failed_tests.append(suite['name'])
                print(f"❌ {suite['name']} - FAILED")
        except Exception as e:
            failed_tests.append(suite['name'])
            print(f"💥 {suite['name']} - ERROR: {str(e)}")
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    print(f"\n✅ PASSED TESTS ({len(passed_tests)}):")
    for test in passed_tests:
        print(f"  ✓ {test}")
    
    if failed_tests:
        print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"  ✗ {test}")
    
    print(f"\n📈 OVERALL RESULTS:")
    print(f"  Total Test Suites: {len(test_suites)}")
    print(f"  Passed: {len(passed_tests)}")
    print(f"  Failed: {len(failed_tests)}")
    print(f"  Success Rate: {len(passed_tests)/len(test_suites)*100:.1f}%")
    
    if failed_tests:
        print(f"\n⚠️  Some tests failed. Please review the output above.")
        return 1
    else:
        print(f"\n🎉 All integration tests passed successfully!")
        return 0


def run_individual_test_modules():
    """個別テストモジュールの実行"""
    
    print("\n🔍 Running Individual Test Modules")
    print("=" * 60)
    
    test_modules = [
        'accounts.test_authentication',
        'accounts.test_statistics', 
        'schedules.test_schedules',
        'scenarios.test_scenarios'
    ]
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=False, keepdb=True)
    
    for module in test_modules:
        print(f"\n📝 Running: {module}")
        try:
            result = test_runner.run_tests([module])
            if result == 0:
                print(f"✅ {module} - PASSED")
            else:
                print(f"❌ {module} - FAILED")
        except Exception as e:
            print(f"💥 {module} - ERROR: {str(e)}")


def main():
    """メイン実行関数"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--integration-only':
            setup_django()
            return run_integration_tests()
        elif command == '--individual-only':
            setup_django()
            run_individual_test_modules()
            return 0
        elif command == '--help':
            print("タブレノ Test Runner")
            print("Usage:")
            print("  python test_runner_comprehensive.py                # Run all tests")
            print("  python test_runner_comprehensive.py --integration-only  # Integration tests only")
            print("  python test_runner_comprehensive.py --individual-only   # Individual module tests only")
            print("  python test_runner_comprehensive.py --help             # Show this help")
            return 0
    
    # デフォルト: 全テストを実行
    setup_django()
    
    print("🚀 Starting Comprehensive Test Execution")
    print("This will run both integration tests and individual module tests")
    print("=" * 60)
    
    # 統合テスト実行
    integration_result = run_integration_tests()
    
    # 個別テストモジュール実行
    run_individual_test_modules()
    
    print("\n" + "=" * 60)
    print("🏁 COMPREHENSIVE TEST EXECUTION COMPLETED")
    print("=" * 60)
    
    if integration_result == 0:
        print("🎊 All tests completed successfully!")
    else:
        print("⚠️  Some integration tests failed. Please review the results.")
    
    return integration_result


if __name__ == '__main__':
    sys.exit(main())