#!/usr/bin/env python3
"""
完全テストスイート - Arkham Nexus全機能包括テスト
統合テスト・個別機能テスト・追加機能テストの統合実行
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line


def setup_django():
    """Django環境のセットアップ"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
    django.setup()


def run_complete_test_suite():
    """完全テストスイートの実行"""
    
    print("🌟 Arkham Nexus - Complete Test Suite")
    print("=" * 70)
    print("🧪 包括的テスト実行：統合テスト・機能テスト・追加機能テスト")
    print("=" * 70)
    
    # テストスイートの定義
    test_suites = [
        # 統合テスト
        {
            'category': '統合テスト',
            'tests': [
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
            ]
        },
        # システム統合テスト
        {
            'category': 'システム統合テスト',
            'tests': [
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
                },
            ]
        },
        # 追加機能テスト
        {
            'category': '追加機能テスト',
            'tests': [
                {
                    'name': 'Export Function Tests',
                    'module': 'test_additional_features.ExportFunctionTestCase',
                    'description': 'エクスポート機能のテスト'
                },
                {
                    'name': 'Statistics Function Tests',
                    'module': 'test_additional_features.StatisticsFunctionTestCase',
                    'description': '統計機能のテスト'
                },
                {
                    'name': 'Handout Management Tests',
                    'module': 'test_additional_features.HandoutManagementTestCase',
                    'description': 'ハンドアウト管理機能のテスト'
                },
                {
                    'name': 'Calendar Integration Tests',
                    'module': 'test_additional_features.CalendarIntegrationTestCase',
                    'description': 'カレンダー統合機能のテスト'
                },
            ]
        },
        # 個別機能テスト
        {
            'category': '個別機能テスト',
            'tests': [
                {
                    'name': 'Accounts Authentication Tests',
                    'module': 'accounts.test_authentication',
                    'description': 'アカウント認証機能のテスト'
                },
                {
                    'name': 'Accounts Statistics Tests',
                    'module': 'accounts.test_statistics',
                    'description': 'アカウント統計機能のテスト'
                },
                {
                    'name': 'Schedules Tests',
                    'module': 'schedules.test_schedules',
                    'description': 'スケジュール機能のテスト'
                },
                {
                    'name': 'Scenarios Tests',
                    'module': 'scenarios.test_scenarios',
                    'description': 'シナリオ機能のテスト'
                },
            ]
        }
    ]
    
    # テストスイート実行
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    error_tests = 0
    
    results_by_category = {}
    
    for suite in test_suites:
        category = suite['category']
        tests = suite['tests']
        
        print(f"\n📋 {category}")
        print("-" * 50)
        
        category_results = {
            'passed': [],
            'failed': [],
            'errors': []
        }
        
        for test in tests:
            print(f"\n🧪 Running: {test['name']}")
            print(f"   {test['description']}")
            
            try:
                result = test_runner.run_tests([test['module']])
                total_tests += 1
                
                if result == 0:
                    passed_tests += 1
                    category_results['passed'].append(test['name'])
                    print(f"✅ {test['name']} - PASSED")
                else:
                    failed_tests += 1
                    category_results['failed'].append(test['name'])
                    print(f"❌ {test['name']} - FAILED")
            except Exception as e:
                error_tests += 1
                category_results['errors'].append(test['name'])
                print(f"💥 {test['name']} - ERROR: {str(e)}")
        
        results_by_category[category] = category_results
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 COMPLETE TEST RESULTS SUMMARY")
    print("=" * 70)
    
    # カテゴリ別結果
    for category, results in results_by_category.items():
        print(f"\n📂 {category}")
        
        if results['passed']:
            print(f"  ✅ PASSED ({len(results['passed'])}):")
            for test in results['passed']:
                print(f"    ✓ {test}")
        
        if results['failed']:
            print(f"  ❌ FAILED ({len(results['failed'])}):")
            for test in results['failed']:
                print(f"    ✗ {test}")
        
        if results['errors']:
            print(f"  💥 ERRORS ({len(results['errors'])}):")
            for test in results['errors']:
                print(f"    💥 {test}")
    
    # 総合結果
    print(f"\n📈 OVERALL RESULTS:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {passed_tests}")
    print(f"  Failed: {failed_tests}")
    print(f"  Errors: {error_tests}")
    print(f"  Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    if failed_tests > 0 or error_tests > 0:
        print(f"\n⚠️  Some tests failed or had errors. Please review the output above.")
        return 1
    else:
        print(f"\n🎉 All tests passed successfully!")
        return 0


def run_specific_category(category):
    """特定のカテゴリのテストのみ実行"""
    
    category_map = {
        'integration': [
            'test_integration.UserGroupIntegrationTestCase',
            'test_integration.SessionScenarioIntegrationTestCase',
            'test_integration.AuthenticationAndPermissionIntegrationTestCase',
            'test_integration.EndToEndBusinessFlowTestCase',
        ],
        'system': [
            'test_system_integration.AuthenticationPermissionIntegrationTestCase',
            'test_system_integration.CompleteWorkflowIntegrationTestCase',
            'test_system_integration.DemoLoginIntegrationTestCase',
            'test_system_integration.APIErrorHandlingIntegrationTestCase',
        ],
        'additional': [
            'test_additional_features.ExportFunctionTestCase',
            'test_additional_features.StatisticsFunctionTestCase',
            'test_additional_features.HandoutManagementTestCase',
            'test_additional_features.CalendarIntegrationTestCase',
        ],
        'individual': [
            'accounts.test_authentication',
            'accounts.test_statistics',
            'schedules.test_schedules',
            'scenarios.test_scenarios',
        ]
    }
    
    if category not in category_map:
        print(f"Error: Unknown category '{category}'")
        print(f"Available categories: {', '.join(category_map.keys())}")
        return 1
    
    print(f"🧪 Running {category} tests only")
    print("=" * 50)
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
    
    test_modules = category_map[category]
    
    failed_count = 0
    for module in test_modules:
        print(f"\n🔍 Running: {module}")
        try:
            result = test_runner.run_tests([module])
            if result != 0:
                failed_count += 1
        except Exception as e:
            print(f"Error running {module}: {str(e)}")
            failed_count += 1
    
    print(f"\n📊 Category '{category}' Results:")
    print(f"  Total modules: {len(test_modules)}")
    print(f"  Failed: {failed_count}")
    print(f"  Success rate: {(len(test_modules) - failed_count)/len(test_modules)*100:.1f}%")
    
    return failed_count


def main():
    """メイン実行関数"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command in ['integration', 'system', 'additional', 'individual']:
            setup_django()
            return run_specific_category(command)
        elif command == '--help':
            print("Arkham Nexus Complete Test Suite")
            print("Usage:")
            print("  python test_complete_suite.py                    # Run all tests")
            print("  python test_complete_suite.py integration        # Integration tests only")
            print("  python test_complete_suite.py system             # System integration tests only")
            print("  python test_complete_suite.py additional         # Additional features tests only")
            print("  python test_complete_suite.py individual         # Individual module tests only")
            print("  python test_complete_suite.py --help             # Show this help")
            return 0
        else:
            print(f"Unknown command: {command}")
            print("Use --help for usage information")
            return 1
    
    # デフォルト: 全テストを実行
    setup_django()
    
    print("🚀 Starting Complete Test Suite Execution")
    print("This will run ALL tests including integration, system, additional features, and individual modules")
    print("=" * 70)
    
    return run_complete_test_suite()


if __name__ == '__main__':
    sys.exit(main())