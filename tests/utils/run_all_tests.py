#!/usr/bin/env python
"""
統合テストランナー
すべてのテストカテゴリを順次実行し、結果をレポート
"""

import os
import subprocess
import sys
from datetime import datetime

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def run_test_category(category, description):
    """特定カテゴリのテストを実行"""
    print(f"\n{'=' * 60}")
    print(f"実行中: {description}")
    print(f"{'=' * 60}")

    start_time = datetime.now()

    cmd = [sys.executable, "manage.py", "test", f"tests.{category}", "--verbosity=2"]

    result = subprocess.run(cmd, cwd=project_root)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    return {"category": category, "description": description, "success": result.returncode == 0, "duration": duration}


def main():
    """メイン実行関数"""
    print("タブレノ テストスイート実行")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # テストカテゴリの定義
    test_categories = [
        ("unit", "単体テスト"),
        ("integration", "統合テスト"),
        ("system", "システムテスト"),
        ("ui", "UIテスト"),
    ]

    results = []

    # 各カテゴリのテストを実行
    for category, description in test_categories:
        result = run_test_category(category, description)
        results.append(result)

    # 結果サマリーの表示
    print(f"\n{'=' * 60}")
    print("テスト実行結果サマリー")
    print(f"{'=' * 60}")

    total_duration = sum(r["duration"] for r in results)
    success_count = sum(1 for r in results if r["success"])

    for result in results:
        status = "✅ 成功" if result["success"] else "❌ 失敗"
        print(f"{result['description']:<20} {status} ({result['duration']:.2f}秒)")

    print(f"\n総実行時間: {total_duration:.2f}秒")
    print(f"成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

    # 終了コードの決定
    if success_count == len(results):
        print("\n🎉 すべてのテストが成功しました！")
        sys.exit(0)
    else:
        print("\n⚠️  一部のテストが失敗しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()
