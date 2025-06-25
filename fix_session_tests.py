#!/usr/bin/env python3
"""
セッション連携テストファイルの自動修正スクリプト
CharacterSheet6thの参照とCharacterSheet初期化の問題を修正
"""

import re

def fix_character_sheet_creation(content):
    """CharacterSheetの初期化を修正"""
    
    # 1. CharacterSheet6th -> CharacterSheet の置換
    content = content.replace('CharacterSheet6th', 'CharacterSheet')
    
    # 2. 古い形式のCharacterSheet初期化を新しい形式に変換
    # パターン1: STR=12, CON=14, ... 形式
    old_pattern = r'CharacterSheet\.objects\.create\((.*?)(?:STR|str)=(\d+),\s*(?:CON|con)=(\d+),\s*(?:POW|pow)=(\d+),\s*(?:DEX|dex)=(\d+),\s*(?:APP|app)=(\d+),\s*(?:SIZ|siz)=(\d+),\s*(?:INT|int)=(\d+),\s*(?:EDU|edu)=(\d+)(.*?)\)'
    
    def replace_old_style(match):
        before = match.group(1)
        str_val = match.group(2)
        con_val = match.group(3)
        pow_val = match.group(4)
        dex_val = match.group(5)
        app_val = match.group(6)
        siz_val = match.group(7)
        int_val = match.group(8)
        edu_val = match.group(9)
        after = match.group(10)
        
        # afterから不要なフィールドを削除
        after = re.sub(r',\s*hp_max=\d+', '', after)
        after = re.sub(r',\s*hp_current=(\d+)', r',\n            hit_points_current=\1', after)
        after = re.sub(r',\s*mp_max=\d+', '', after)
        after = re.sub(r',\s*mp_current=(\d+)', r',\n            magic_points_current=\1', after)
        after = re.sub(r',\s*san_max=\d+', '', after)
        after = re.sub(r',\s*san_current=(\d+)', r',\n            sanity_current=\1', after)
        
        # デフォルト値を追加
        if 'edition=' not in before:
            before += "\n            edition='6th',"
        if 'player_name=' not in before:
            before += "\n            player_name=self.player.username if hasattr(self, 'player') else 'test',"
        if 'age=' not in before:
            before += "\n            age=25,"
        if 'occupation=' not in before:
            before += "\n            occupation='探偵',"
            
        # 新しい形式を構築
        new_format = f"""CharacterSheet.objects.create({before}
            str_value={str_val},
            con_value={con_val},
            pow_value={pow_val},
            dex_value={dex_val},
            app_value={app_val},
            siz_value={siz_val},
            int_value={int_val},
            edu_value={edu_val}{after})"""
        
        return new_format
    
    content = re.sub(old_pattern, replace_old_style, content, flags=re.DOTALL)
    
    # 3. system -> game_system, user -> created_by の置換
    content = re.sub(r"system='クトゥルフ神話TRPG'", "game_system='coc'", content)
    content = re.sub(r"(\s+)user=(self\.\w+)", r"\1created_by=\2", content)
    
    # 4. actual_hours -> duration_minutes の変換
    content = re.sub(r'actual_hours=(\d+)', lambda m: f'duration_minutes={int(m.group(1)) * 60}', content)
    
    # 5. scheduled_date -> date の置換
    content = content.replace('scheduled_date=', 'date=')
    
    # 6. status値の修正
    content = content.replace("status='recruiting'", "status='planned'")
    content = content.replace("status='in_progress'", "status='ongoing'")
    
    # 7. character_sheet -> character_name の置換（SessionParticipant）
    content = re.sub(
        r'SessionParticipant\.objects\.create\((.*?)character_sheet=(self\.char\w*|char\w*)(.*?)\)',
        lambda m: f"SessionParticipant.objects.create({m.group(1)}character_name={m.group(2)}.name{m.group(3)})",
        content,
        flags=re.DOTALL
    )
    
    # 8. max_participants の削除
    content = re.sub(r',\s*max_participants=\d+', '', content)
    
    # 9. estimated_hours の削除
    content = re.sub(r',\s*estimated_hours=\d+', '', content)
    
    # 10. status='approved' や status='pending' の削除（SessionParticipant）
    content = re.sub(r",\s*status='(approved|pending)'", '', content)
    
    return content

# ファイルを読み込み
with open('/mnt/c/Users/endke/Workspace/iaia/accounts/test_session_integration.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修正を適用
fixed_content = fix_character_sheet_creation(content)

# ファイルに書き込み
with open('/mnt/c/Users/endke/Workspace/iaia/accounts/test_session_integration.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("修正が完了しました。")