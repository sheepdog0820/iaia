#!/usr/bin/env python
"""
自動テスト実行スクリプト
使用方法: python test_runner.py [オプション]
"""

import os
import sys
import django
import subprocess
from django.conf import settings
from django.test.utils import get_runner

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()


def run_tests(test_labels=None, verbosity=2, keepdb=False, failfast=False):
    """
    Djangoテストを実行する
    
    Args:
        test_labels: 実行するテストのラベル（None で全テスト）
        verbosity: 詳細度（0-3）
        keepdb: テストDB保持フラグ
        failfast: 最初の失敗で停止フラグ
    """
    TestRunner = get_runner(settings)
    test_runner = TestRunner(
        verbosity=verbosity,
        interactive=False,
        keepdb=keepdb,
        failfast=failfast
    )
    
    if test_labels is None:
        test_labels = [
            'accounts.test_authentication',
            'schedules.test_schedules',
            'scenarios.test_scenarios'
        ]
    
    failures = test_runner.run_tests(test_labels)
    return failures


def run_coverage_tests():
    """
    カバレッジ付きでテストを実行する
    """
    try:
        import coverage
        
        # カバレッジ開始
        cov = coverage.Coverage()
        cov.start()
        
        # テスト実行
        failures = run_tests(verbosity=1)
        
        # カバレッジ停止
        cov.stop()
        cov.save()
        
        # レポート出力
        print("\n" + "="*50)
        print("COVERAGE REPORT")
        print("="*50)
        cov.report()
        
        # HTMLレポート生成
        cov.html_report(directory='htmlcov')
        print(f"\nHTML coverage report generated in: htmlcov/index.html")
        
        return failures
        
    except ImportError:
        print("Coverage not installed. Running tests without coverage...")
        return run_tests()


def run_linting():
    """
    コード品質チェックを実行する
    """
    print("\n" + "="*50)
    print("RUNNING CODE QUALITY CHECKS")
    print("="*50)
    
    # Flake8チェック（利用可能な場合）
    try:
        result = subprocess.run(['flake8', '.'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Flake8: No issues found")
        else:
            print("✗ Flake8 issues:")
            print(result.stdout)
    except FileNotFoundError:
        print("- Flake8 not installed, skipping...")
    
    # Black フォーマットチェック（利用可能な場合）
    try:
        result = subprocess.run(['black', '--check', '.'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Black: Code formatting is correct")
        else:
            print("✗ Black: Code formatting issues found")
    except FileNotFoundError:
        print("- Black not installed, skipping...")


def run_security_checks():
    """
    セキュリティチェックを実行する
    """
    print("\n" + "="*50)
    print("RUNNING SECURITY CHECKS")
    print("="*50)
    
    # Django security check
    try:
        result = subprocess.run(['python', 'manage.py', 'check', '--deploy'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Django security check: Passed")
        else:
            print("✗ Django security issues:")
            print(result.stdout)
            print(result.stderr)
    except Exception as e:
        print(f"Error running security check: {e}")
    
    # Bandit セキュリティスキャン（利用可能な場合）
    try:
        result = subprocess.run(['bandit', '-r', '.', '-x', './venv/'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Bandit: No security issues found")
        else:
            print("✗ Bandit security issues:")
            print(result.stdout)
    except FileNotFoundError:
        print("- Bandit not installed, skipping...")


def main():
    """
    メイン関数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Run automated tests and checks')
    parser.add_argument('--coverage', action='store_true', 
                       help='Run tests with coverage report')
    parser.add_argument('--lint', action='store_true', 
                       help='Run code quality checks')
    parser.add_argument('--security', action='store_true', 
                       help='Run security checks')
    parser.add_argument('--all', action='store_true', 
                       help='Run all checks (tests, coverage, lint, security)')
    parser.add_argument('--fast', action='store_true', 
                       help='Run tests with failfast option')
    parser.add_argument('--keepdb', action='store_true', 
                       help='Keep test database between runs')
    parser.add_argument('tests', nargs='*', 
                       help='Specific test labels to run')
    
    args = parser.parse_args()
    
    if args.all:
        args.coverage = True
        args.lint = True
        args.security = True
    
    print("ARKHAM NEXUS - AUTOMATED TEST SUITE")
    print("="*50)
    
    # テスト実行
    if args.coverage:
        failures = run_coverage_tests()
    else:
        test_labels = args.tests if args.tests else None
        failures = run_tests(
            test_labels=test_labels,
            failfast=args.fast,
            keepdb=args.keepdb
        )
    
    # コード品質チェック
    if args.lint:
        run_linting()
    
    # セキュリティチェック
    if args.security:
        run_security_checks()
    
    # 結果サマリー
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    if failures:
        print(f"✗ Tests failed: {failures} failure(s)")
        sys.exit(1)
    else:
        print("✓ All tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()