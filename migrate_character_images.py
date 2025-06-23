#!/usr/bin/env python3
"""
キャラクター画像データの移行スクリプト
古いcharacter_imageフィールドから新しいCharacterImageモデルへデータを移行
"""

import os
import sys
import django
from django.db import transaction

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from accounts.models import CharacterSheet, CharacterImage
from django.core.files.base import ContentFile
import shutil


def migrate_character_images():
    """既存のcharacter_imageデータをCharacterImageモデルに移行"""
    
    print("=== キャラクター画像データの移行開始 ===")
    
    # character_imageフィールドに画像があるキャラクターを取得
    characters_with_old_images = CharacterSheet.objects.filter(
        character_image__isnull=False
    ).exclude(character_image='')
    
    total_count = characters_with_old_images.count()
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"移行対象キャラクター数: {total_count}")
    
    for character in characters_with_old_images:
        try:
            # 既にCharacterImageが存在するか確認
            if character.images.exists():
                print(f"  [スキップ] {character.name} (ID: {character.id}) - 既に新形式の画像が存在")
                skipped_count += 1
                continue
            
            # character_imageファイルが実際に存在するか確認
            if not character.character_image or not character.character_image.file:
                print(f"  [エラー] {character.name} (ID: {character.id}) - 画像ファイルが見つかりません")
                error_count += 1
                continue
            
            with transaction.atomic():
                # 新しいCharacterImageレコードを作成
                try:
                    # ファイルを読み込んで新しいCharacterImageに保存
                    with character.character_image.open('rb') as f:
                        file_content = f.read()
                        file_name = os.path.basename(character.character_image.name)
                        
                        # CharacterImageインスタンスを作成
                        new_image = CharacterImage(
                            character_sheet=character,
                            is_main=True,
                            order=0
                        )
                        
                        # ファイルを保存
                        new_image.image.save(file_name, ContentFile(file_content), save=True)
                        
                        print(f"  [成功] {character.name} (ID: {character.id}) - 画像を移行しました")
                        migrated_count += 1
                        
                except Exception as e:
                    print(f"  [エラー] {character.name} (ID: {character.id}) - ファイル処理エラー: {str(e)}")
                    error_count += 1
                    
        except Exception as e:
            print(f"  [エラー] {character.name} (ID: {character.id}) - 移行エラー: {str(e)}")
            error_count += 1
    
    # 結果サマリー
    print("\n=== 移行結果 ===")
    print(f"総対象数: {total_count}")
    print(f"移行成功: {migrated_count}")
    print(f"スキップ: {skipped_count}")
    print(f"エラー: {error_count}")
    
    if migrated_count > 0:
        print("\n移行が完了しました。古いcharacter_imageフィールドのデータは残されています。")
        print("動作確認後、必要に応じて古いデータを削除してください。")
    
    return migrated_count, skipped_count, error_count


def cleanup_old_images(dry_run=True):
    """古いcharacter_imageフィールドをクリア（オプション）"""
    
    print("\n=== 古い画像フィールドのクリーンアップ ===")
    
    if dry_run:
        print("【ドライラン】実際の削除は行いません")
    
    # CharacterImageが存在するキャラクターの古いフィールドをクリア
    characters_to_clean = CharacterSheet.objects.filter(
        images__isnull=False,
        character_image__isnull=False
    ).distinct()
    
    clean_count = 0
    
    for character in characters_to_clean:
        if character.images.exists() and character.character_image:
            if dry_run:
                print(f"  [ドライラン] {character.name} (ID: {character.id}) - 古い画像フィールドをクリア予定")
            else:
                # 古い画像ファイルを削除
                if character.character_image:
                    character.character_image.delete(save=False)
                    character.character_image = None
                    character.save()
                    print(f"  [実行] {character.name} (ID: {character.id}) - 古い画像フィールドをクリア")
            clean_count += 1
    
    print(f"\nクリーンアップ対象: {clean_count}件")
    
    if dry_run and clean_count > 0:
        print("\n実際にクリーンアップを実行するには、cleanup_old_images(dry_run=False)を実行してください")
    
    return clean_count


if __name__ == '__main__':
    # 移行実行
    migrate_character_images()
    
    # クリーンアップのドライラン
    print("\n" + "="*50 + "\n")
    cleanup_old_images(dry_run=True)
    
    print("\n完了しました。")