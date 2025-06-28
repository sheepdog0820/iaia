#!/usr/bin/env python3
"""
Djangoテストクライアントを使用したキャラクター作成テスト
"""

import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import CharacterSheet

User = get_user_model()

def test_character_creation():
    """キャラクター作成のテスト"""
    
    print("=== Django キャラクター作成テスト ===\n")
    
    # テストクライアント
    client = Client()
    
    # 1. テストユーザーでログイン
    print("1. ログイン処理")
    try:
        user = User.objects.get(username='investigator1')
        client.force_login(user)
        print(f"✅ ユーザー '{user.username}' でログイン成功")
    except User.DoesNotExist:
        print("❌ investigator1 ユーザーが見つかりません")
        return
    
    # 2. キャラクター作成ページへのGETリクエスト
    print("\n2. キャラクター作成ページの取得")
    response = client.get('/accounts/character/create/6th/')
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ ページ取得成功")
    else:
        print("❌ ページ取得失敗")
        return
    
    # 3. キャラクター作成データの準備
    print("\n3. キャラクター作成データの準備")
    
    character_data = {
        'name': 'テスト探索者_Django',
        'player_name': 'テストプレイヤー',
        'age': '25',
        'gender': '男性',
        'occupation': '私立探偵',
        'birthplace': '東京',
        'residence': '横浜',
        
        # 能力値
        'str': '13',
        'con': '14',
        'pow': '15',
        'dex': '12',
        'app': '11',
        'siz': '13',
        'int': '16',
        'edu': '17',
        
        # その他のフィールド（空でも送信）
        'backstory': '',
        'description': '',
        'portrait': '',
        'skills': '',
    }
    
    print(f"送信データ: {len(character_data)}項目")
    
    # 4. POSTリクエストでキャラクター作成
    print("\n4. キャラクター作成リクエスト")
    
    response = client.post('/accounts/character/create/6th/', data=character_data, follow=True)
    
    print(f"ステータスコード: {response.status_code}")
    print(f"リダイレクト先: {response.redirect_chain}")
    
    # レスポンスの内容を確認
    if hasattr(response, 'context') and response.context:
        # フォームエラーの確認
        if 'form' in response.context:
            form = response.context['form']
            if form.errors:
                print("\n❌ フォームエラー:")
                for field, errors in form.errors.items():
                    print(f"  {field}: {errors}")
    
    # 5. 作成されたキャラクターの確認
    print("\n5. キャラクター作成結果の確認")
    
    try:
        created_character = CharacterSheet.objects.filter(
            user=user,
            name='テスト探索者_Django'
        ).first()
        
        if created_character:
            print(f"✅ キャラクター作成成功！")
            print(f"  ID: {created_character.id}")
            print(f"  名前: {created_character.name}")
            print(f"  年齢: {created_character.age}")
            print(f"  職業: {created_character.occupation}")
            print(f"  STR: {created_character.str_value}")
            print(f"  作成日: {created_character.created_at}")
        else:
            print("❌ キャラクターが作成されていません")
            
            # すべてのキャラクターを確認
            all_characters = CharacterSheet.objects.filter(user=user)
            print(f"\nユーザーの全キャラクター数: {all_characters.count()}")
            for char in all_characters[:5]:
                print(f"  - {char.name} (ID: {char.id})")
                
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 6. レスポンス内容の分析
    print("\n6. レスポンス内容の分析")
    
    if response.status_code == 200:
        # ページ内のメッセージを確認
        content = response.content.decode('utf-8')
        
        if 'alert-danger' in content:
            print("❌ エラーメッセージが含まれています")
            
            # エラーメッセージを抽出
            import re
            errors = re.findall(r'<div[^>]*class="[^"]*alert-danger[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)
            for error in errors[:3]:
                print(f"  エラー: {error.strip()[:100]}...")
        
        if 'alert-success' in content:
            print("✅ 成功メッセージが含まれています")
        
        # 必須フィールドの確認
        required_fields = re.findall(r'<[^>]*required[^>]*name="([^"]+)"', content)
        if required_fields:
            print(f"\n必須フィールド: {len(required_fields)}個")
            print(f"  {', '.join(required_fields[:10])}")
    
    print("\n=== テスト完了 ===")

if __name__ == '__main__':
    test_character_creation()