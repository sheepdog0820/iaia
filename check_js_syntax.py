#!/usr/bin/env python3
"""
JavaScriptの構文エラーをチェックするスクリプト
"""

import re

def check_javascript_syntax(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 基本的な括弧のバランスチェック
    brace_count = 0
    paren_count = 0
    bracket_count = 0
    in_string = False
    string_char = None
    
    issues = []
    
    for i, line in enumerate(lines, 1):
        # コメントを除去（簡易版）
        if '//' in line and not in_string:
            line = line[:line.index('//')]
        
        for j, char in enumerate(line):
            # 文字列の開始/終了を追跡
            if char in ['"', "'", '`'] and (j == 0 or line[j-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            
            # 文字列内でなければ括弧をカウント
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count < 0:
                        issues.append(f"Line {i}: 余分な '}}' があります")
                elif char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count < 0:
                        issues.append(f"Line {i}: 余分な ')' があります")
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count < 0:
                        issues.append(f"Line {i}: 余分な ']' があります")
    
    # 最終的なバランスチェック
    if brace_count != 0:
        issues.append(f"中括弧 {{}} のバランスが取れていません: {brace_count}")
    if paren_count != 0:
        issues.append(f"括弧 () のバランスが取れていません: {paren_count}")
    if bracket_count != 0:
        issues.append(f"角括弧 [] のバランスが取れていません: {bracket_count}")
    
    # 特定の構文パターンをチェック
    for i, line in enumerate(lines, 1):
        # 連続するセミコロン
        if ';;' in line:
            issues.append(f"Line {i}: 連続するセミコロン")
        
        # else の後の {
        if re.search(r'else\s*[^{]', line) and 'else if' not in line:
            if i < len(lines) and '{' not in lines[i]:
                issues.append(f"Line {i}: elseの後に {{ がありません")
    
    return issues

# HTMLファイル内のJavaScriptを抽出して確認
def extract_and_check_javascript(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # <script>タグ内のJavaScriptを抽出
    script_matches = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    
    all_issues = []
    
    for i, script in enumerate(script_matches, 1):
        lines = script.split('\n')
        print(f"\n=== Script Block {i} ===")
        print(f"行数: {len(lines)}")
        
        # 構文チェック
        issues = check_javascript_syntax_from_string(script)
        if issues:
            all_issues.extend([(i, issue) for issue in issues])
    
    return all_issues

def check_javascript_syntax_from_string(content):
    lines = content.split('\n')
    
    brace_count = 0
    paren_count = 0
    bracket_count = 0
    in_string = False
    string_char = None
    
    issues = []
    
    for i, line in enumerate(lines, 1):
        # コメントを除去（簡易版）
        if '//' in line and not in_string:
            line = line[:line.index('//')]
        
        for j, char in enumerate(line):
            # 文字列の開始/終了を追跡
            if char in ['"', "'", '`'] and (j == 0 or line[j-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            
            # 文字列内でなければ括弧をカウント
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count < 0:
                        issues.append(f"Line {i}: 余分な '}}' があります (累積: {brace_count})")
                elif char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count < 0:
                        issues.append(f"Line {i}: 余分な ')' があります")
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count < 0:
                        issues.append(f"Line {i}: 余分な ']' があります")
    
    # 最終的なバランスチェック
    if brace_count != 0:
        issues.append(f"中括弧 {{}} のバランスが取れていません: {brace_count}")
    if paren_count != 0:
        issues.append(f"括弧 () のバランスが取れていません: {paren_count}")
    if bracket_count != 0:
        issues.append(f"角括弧 [] のバランスが取れていません: {bracket_count}")
    
    return issues

# メイン処理
print("=== JavaScriptスクリプトエラーチェック ===")
issues = extract_and_check_javascript('templates/accounts/character_sheet_6th.html')

if issues:
    print("\n🚨 発見された問題:")
    for script_num, issue in issues:
        print(f"  Script {script_num}: {issue}")
else:
    print("\n✅ 構文エラーは見つかりませんでした")

# 3052行目周辺を詳細チェック
print("\n=== 3052行目周辺の詳細チェック ===")
with open('templates/accounts/character_sheet_6th.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
for i in range(max(0, 3050-10), min(len(lines), 3055)):
    print(f"{i+1:4d}: {lines[i].rstrip()}")