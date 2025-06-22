#!/usr/bin/env python3
"""
キャラクター作成画面のJavaScriptエラーチェック
"""

import re

# HTMLファイルを読み込む
with open('templates/accounts/character_sheet_6th.html', 'r', encoding='utf-8') as f:
    content = f.read()

# getElementById呼び出しを抽出
get_element_pattern = r'getElementById\([\'"]([^\'\"]+)[\'"]\)'
element_ids = re.findall(get_element_pattern, content)

# HTML内のid属性を抽出
id_pattern = r'id=[\'"]([^\'\"]+)[\'"]'
defined_ids = re.findall(id_pattern, content)

# 不足している要素を特定
missing_elements = []
for elem_id in element_ids:
    if elem_id not in defined_ids:
        missing_elements.append(elem_id)

# 結果を表示
print("=== JavaScript要素チェック結果 ===")
print(f"JavaScript内で参照されている要素: {len(element_ids)}個")
print(f"HTML内で定義されている要素: {len(defined_ids)}個")

if missing_elements:
    print(f"\n❌ 不足している要素 ({len(set(missing_elements))}個):")
    for elem in sorted(set(missing_elements)):
        print(f"  - {elem}")
else:
    print("\n✅ すべての要素が正しく定義されています！")

# onclick/onchangeハンドラーで使用される関数を確認
onclick_pattern = r'on(?:click|change)=[\'"]([^\'\"]+)\([^)]*\)'
onclick_functions = re.findall(onclick_pattern, content)

# JavaScript内で定義されている関数を抽出
function_pattern = r'function\s+(\w+)\s*\('
defined_functions = re.findall(function_pattern, content)

# 不足している関数を特定
missing_functions = []
for func in onclick_functions:
    # 関数名のみを抽出（引数を除く）
    func_name = func.split('(')[0].strip()
    if func_name and func_name not in defined_functions:
        missing_functions.append(func_name)

print(f"\n=== JavaScript関数チェック結果 ===")
print(f"イベントハンドラーで呼び出される関数: {len(onclick_functions)}個")
print(f"定義されている関数: {len(defined_functions)}個")

if missing_functions:
    print(f"\n❌ 不足している関数 ({len(set(missing_functions))}個):")
    for func in sorted(set(missing_functions)):
        print(f"  - {func}")
else:
    print("\n✅ すべての関数が正しく定義されています！")

# 重複定義のチェック
duplicate_functions = []
func_counts = {}
for func in defined_functions:
    func_counts[func] = func_counts.get(func, 0) + 1
    
for func, count in func_counts.items():
    if count > 1:
        duplicate_functions.append((func, count))

if duplicate_functions:
    print(f"\n⚠️  重複定義されている関数:")
    for func, count in duplicate_functions:
        print(f"  - {func}: {count}回定義")