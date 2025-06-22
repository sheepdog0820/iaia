#!/usr/bin/env python3
"""
JavaScriptの構文をより詳細にチェック
"""

import re

with open('templates/accounts/character_sheet_6th.html', 'r', encoding='utf-8') as f:
    content = f.read()

# <script>タグの内容を抽出
script_match = re.search(r'<script>\s*\n(.*?)</script>', content, re.DOTALL)
if not script_match:
    print("Script tag not found")
    exit(1)

script_content = script_match.group(1)
lines = script_content.split('\n')

# 3052行目がどこにあるか計算
html_lines = content.split('\n')
script_start = next(i for i, line in enumerate(html_lines) if '<script>' in line and 'type=' not in line) + 2
relative_line = 3052 - script_start

print(f"Script starts at line {script_start}")
print(f"Line 3052 is relative line {relative_line} in the script")
print(f"\nContent around line 3052:")

# 前後の行を表示
start = max(0, relative_line - 10)
end = min(len(lines), relative_line + 10)

for i in range(start, end):
    line_num = script_start + i
    prefix = ">>>" if line_num == 3052 else "   "
    print(f"{prefix} {line_num}: {lines[i]}")

# 閉じられていないブロックを探す
print("\n=== Unclosed blocks check ===")
stack = []
for i, line in enumerate(lines[:relative_line+1]):
    line_num = script_start + i
    
    # 簡易的なブロック検出
    if '{' in line and '}' not in line:
        # テンプレートリテラル内でないことを確認
        if '`' not in line and '${' not in line:
            stack.append((line_num, line.strip()))
    elif '}' in line and '{' not in line:
        if stack:
            stack.pop()
    
    # functionやifなどのブロック開始を検出
    if re.match(r'\s*(function|if|for|while|try|catch)\s*\(', line):
        if '{' not in line:
            print(f"Warning: Line {line_num} starts a block but no {{ found")

if stack:
    print("\nUnclosed blocks:")
    for line_num, content in stack[-5:]:  # 最後の5つ
        print(f"  Line {line_num}: {content}")

# エラーがある可能性のある行を検出
print("\n=== Potential issues ===")
for i in range(max(0, relative_line-20), min(len(lines), relative_line+5)):
    line = lines[i]
    line_num = script_start + i
    
    # 連続する閉じ括弧
    if '}}' in line and '`' not in line:
        print(f"Line {line_num}: Double closing braces: {line.strip()}")
    
    # セミコロンの後の閉じ括弧
    if ';}' in line:
        print(f"Line {line_num}: Semicolon before closing brace: {line.strip()}")