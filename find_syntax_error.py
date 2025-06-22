#!/usr/bin/env python3
"""
3052行目付近のSyntaxErrorを特定するスクリプト
"""

import re

# HTMLファイルを読み込み
with open('templates/accounts/character_sheet_6th.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# scriptタグを探す
in_script = False
script_lines = []
script_start_line = 0

for i, line in enumerate(lines):
    if '<script>' in line and not in_script:
        in_script = True
        script_start_line = i + 1
        script_lines = []
    elif '</script>' in line and in_script:
        in_script = False
        # 3052行目を含むscriptブロックかチェック
        if script_start_line <= 3052 <= i + 1:
            print(f"=== 3052行目を含むScriptブロック (行 {script_start_line} - {i + 1}) ===")
            # 相対的な行番号を計算
            relative_line = 3052 - script_start_line
            print(f"3052行目はこのscriptブロックの{relative_line}行目です\n")
            
            # 3052行目周辺を表示
            start = max(0, relative_line - 5)
            end = min(len(script_lines), relative_line + 5)
            
            for j in range(start, end):
                line_num = script_start_line + j
                if line_num == 3052:
                    print(f">>> {line_num}: {script_lines[j].rstrip()}")
                else:
                    print(f"    {line_num}: {script_lines[j].rstrip()}")
            
            # テンプレートリテラルのチェック
            print("\n=== テンプレートリテラルのチェック ===")
            in_template = False
            template_start = 0
            
            for j, line in enumerate(script_lines):
                # バッククォートの検出
                backticks = line.count('`')
                if backticks % 2 == 1:  # 奇数個のバッククォート
                    in_template = not in_template
                    if in_template:
                        template_start = script_start_line + j
                    else:
                        print(f"テンプレートリテラル: 行 {template_start} - {script_start_line + j}")
                
                # 3052行目付近でテンプレート内にいるかチェック
                if script_start_line + j == 3052:
                    if in_template:
                        print(f"⚠️  3052行目はテンプレートリテラル内にあります！")
                        print("これが原因で'}'が正しく解釈されていない可能性があります")
            
            break
    elif in_script:
        script_lines.append(line)

print("\n=== 括弧のバランスチェック ===")
# 全体の括弧バランスをチェック
brace_balance = 0
paren_balance = 0
bracket_balance = 0

for i, line in enumerate(script_lines[:relative_line+1]):
    # 文字列リテラル内を無視する簡易的な方法
    # 実際にはより複雑な処理が必要
    clean_line = re.sub(r'"[^"]*"', '', line)
    clean_line = re.sub(r"'[^']*'", '', clean_line)
    
    brace_balance += clean_line.count('{') - clean_line.count('}')
    paren_balance += clean_line.count('(') - clean_line.count(')')
    bracket_balance += clean_line.count('[') - clean_line.count(']')
    
    if script_start_line + i == 3052:
        print(f"3052行目時点のバランス:")
        print(f"  中括弧 {{}}: {brace_balance}")
        print(f"  括弧 (): {paren_balance}")
        print(f"  角括弧 []: {bracket_balance}")