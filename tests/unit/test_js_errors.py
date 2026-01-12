#!/usr/bin/env python3
"""
キャラクター作成画面の JavaScript 参照チェック（手動実行用）

注意:
- Django の `manage.py test` からは実行されない想定です（テストケース未定義）。
- 手動で実行する場合は `python tests/unit/test_js_errors.py` を使用してください。
"""

from __future__ import annotations

import re
from pathlib import Path


def run(template_path: str = "templates/accounts/character_sheet_6th.html") -> int:
    content = Path(template_path).read_text(encoding="utf-8")

    # getElementById 呼び出しを抽出
    element_ids = re.findall(r"getElementById\\(['\\\"]([^'\\\"]+)['\\\"]\\)", content)

    # HTML 内の id 属性を抽出
    defined_ids = re.findall(r"id=['\\\"]([^'\\\"]+)['\\\"]", content)

    missing_elements = sorted({elem_id for elem_id in element_ids if elem_id not in defined_ids})

    print("=== JavaScript要素チェック結果 ===")
    print(f"JavaScript内で参照されている要素: {len(element_ids)}個")
    print(f"HTML内で定義されている要素: {len(defined_ids)}個")

    exit_code = 0
    if missing_elements:
        exit_code = 1
        print(f"\n[NG] 不足している要素 ({len(missing_elements)}個):")
        for elem in missing_elements:
            print(f"  - {elem}")
    else:
        print("\n[OK] すべての要素が正しく定義されています！")

    # onclick/onchange ハンドラーで使用される関数を確認
    onclick_functions = re.findall(r"on(?:click|change)=['\\\"]([^'\\\"]+)\\([^)]*\\)", content)
    defined_functions = re.findall(r"function\\s+(\\w+)\\s*\\(", content)

    missing_functions = sorted(
        {
            func.split("(")[0].strip()
            for func in onclick_functions
            if func.split("(")[0].strip() and func.split("(")[0].strip() not in defined_functions
        }
    )

    print("\n=== JavaScript関数チェック結果 ===")
    print(f"イベントハンドラーで呼び出される関数: {len(onclick_functions)}個")
    print(f"定義されている関数: {len(defined_functions)}個")

    if missing_functions:
        exit_code = 1
        print(f"\n[NG] 不足している関数 ({len(missing_functions)}個):")
        for func in missing_functions:
            print(f"  - {func}")
    else:
        print("\n[OK] すべての関数が正しく定義されています！")

    duplicates = sorted({func for func in defined_functions if defined_functions.count(func) > 1})
    if duplicates:
        exit_code = 1
        print("\n[WARN] 重複定義されている関数:")
        for func in duplicates:
            print(f"  - {func}: {defined_functions.count(func)}回定義")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())
