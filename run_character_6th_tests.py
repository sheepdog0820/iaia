#!/usr/bin/env python3
"""
Run all Character Sheet 6th Edition tests

This script runs the comprehensive test suite for the Call of Cthulhu 6th Edition
character sheet functionality, including:
- Unit tests (models, calculations)
- Integration tests (API, workflows)
- UI tests (templates, forms)
"""

import os
import sys
import django
from django.core.management import call_command
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()


def run_tests():
    """Run all character 6th edition tests"""
    
    print("=" * 80)
    print("CALL OF CTHULHU 6TH EDITION CHARACTER SHEET - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()
    
    test_modules = [
        # Existing tests
        ('accounts.test_character_6th', 'Original Character 6th Tests'),
        ('accounts.test_character_integration', 'Character Integration Tests'),
        
        # New comprehensive tests
        ('accounts.test_character_6th_comprehensive', 'Comprehensive Unit Tests'),
        ('tests.integration.test_character_6th_integration', 'Comprehensive Integration Tests'),
        ('tests.ui.test_character_6th_ui', 'UI and Template Tests'),
    ]
    
    results = {}
    total_tests = 0
    failed_tests = 0
    
    for module, description in test_modules:
        print(f"\n{'=' * 60}")
        print(f"Running: {description}")
        print(f"Module: {module}")
        print("=" * 60)
        
        try:
            # Run tests with detailed output
            from django.test.utils import get_runner
            from django.test.runner import DiscoverRunner
            
            TestRunner = get_runner(settings)
            test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
            failures = test_runner.run_tests([module])
            
            if failures == 0:
                print(f"✅ {description}: ALL TESTS PASSED")
                results[module] = 'PASSED'
            else:
                print(f"❌ {description}: {failures} TESTS FAILED")
                results[module] = f'FAILED ({failures})'
                failed_tests += failures
                
        except Exception as e:
            print(f"❌ Error running {module}: {str(e)}")
            results[module] = f'ERROR: {str(e)}'
            failed_tests += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for module, result in results.items():
        status_icon = "✅" if result == 'PASSED' else "❌"
        print(f"{status_icon} {module}: {result}")
    
    print("\n" + "=" * 80)
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED! 🎉")
        print("Character Sheet 6th Edition is fully tested and working correctly.")
    else:
        print(f"❌ {failed_tests} TESTS FAILED")
        print("Please fix the failing tests before proceeding.")
    print("=" * 80)
    
    return 0 if failed_tests == 0 else 1


def run_coverage_report():
    """Run tests with coverage report"""
    print("\n" + "=" * 80)
    print("RUNNING TESTS WITH COVERAGE")
    print("=" * 80)
    
    try:
        import coverage
        
        # Create coverage instance
        cov = coverage.Coverage(source=['accounts'])
        cov.start()
        
        # Run tests
        exit_code = run_tests()
        
        # Stop coverage
        cov.stop()
        cov.save()
        
        # Generate report
        print("\n" + "=" * 80)
        print("COVERAGE REPORT")
        print("=" * 80)
        cov.report()
        
        # Generate HTML report
        cov.html_report(directory='htmlcov')
        print("\nDetailed HTML coverage report generated in 'htmlcov' directory")
        
        return exit_code
        
    except ImportError:
        print("Coverage module not installed. Run: pip install coverage")
        return 1


if __name__ == '__main__':
    # Check for coverage flag
    if '--coverage' in sys.argv:
        exit_code = run_coverage_report()
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)