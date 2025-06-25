#!/usr/bin/env python3
"""
テストデータの確認スクリプト
"""

import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Group
from accounts.character_models import CharacterSheet, CharacterSkill
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo

User = get_user_model()


def print_section(title):
    """セクションタイトルを表示"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def check_users():
    """ユーザー情報を確認"""
    print_section("ユーザー情報")
    
    # GM
    print("\n【GM】")
    keepers = User.objects.filter(username__startswith='keeper')
    for keeper in keepers:
        print(f"  - {keeper.username}: {keeper.nickname}")
    
    # プレイヤー
    print("\n【プレイヤー】")
    investigators = User.objects.filter(username__startswith='investigator')
    for inv in investigators:
        print(f"  - {inv.username}: {inv.nickname}")


def check_groups():
    """グループ情報を確認"""
    print_section("グループ情報")
    
    for group in Group.objects.all():
        print(f"\n【{group.name}】")
        print(f"  作成者: {group.created_by.nickname}")
        print(f"  公開設定: {group.get_visibility_display()}")
        print(f"  メンバー数: {group.members.count()}人")
        print(f"  メンバー: {', '.join([m.nickname for m in group.members.all()[:5]])}")


def check_characters():
    """キャラクター情報を確認"""
    print_section("キャラクター情報")
    
    for user in User.objects.filter(username__startswith='investigator'):
        characters = CharacterSheet.objects.filter(user=user)
        if characters.exists():
            print(f"\n【{user.nickname}のキャラクター】")
            for char in characters:
                print(f"  - {char.name} ({char.occupation}) - {char.age}歳")
                skills = CharacterSkill.objects.filter(character_sheet=char)[:3]
                if skills:
                    skill_list = ', '.join([f"{s.skill_name}:{s.current_value}" for s in skills])
                    print(f"    主要技能: {skill_list}")


def check_sessions():
    """セッション情報を確認"""
    print_section("セッション情報")
    
    for session in TRPGSession.objects.all().order_by('date'):
        print(f"\n【{session.title}】")
        print(f"  GM: {session.gm.nickname}")
        print(f"  日時: {session.date.strftime('%Y-%m-%d %H:%M')}")
        print(f"  状態: {session.get_status_display()}")
        print(f"  場所: {session.location}")
        
        # 参加者
        participants = SessionParticipant.objects.filter(session=session, role='player')
        if participants.exists():
            print(f"  参加者数: {participants.count()}人")
            for p in participants:
                slot_info = f"枠{p.player_slot}" if p.player_slot else "枠なし"
                char_info = f"({p.character_sheet.name})" if p.character_sheet else ""
                print(f"    - {slot_info}: {p.user.nickname} {char_info}")
        
        # ハンドアウト
        handouts = HandoutInfo.objects.filter(session=session)
        if handouts.exists():
            print(f"  ハンドアウト: {handouts.count()}個")
            for ho in handouts:
                print(f"    - HO{ho.handout_number}: {ho.title[:20]}...")


def check_handouts():
    """ハンドアウト詳細を確認"""
    print_section("ハンドアウト詳細")
    
    ongoing_session = TRPGSession.objects.filter(status='ongoing').first()
    if ongoing_session:
        print(f"\n進行中セッション「{ongoing_session.title}」のハンドアウト:")
        handouts = HandoutInfo.objects.filter(session=ongoing_session)
        for ho in handouts:
            print(f"\n  HO{ho.handout_number} (プレイヤー{ho.assigned_player_slot})")
            print(f"  タイトル: {ho.title}")
            print(f"  内容: {ho.content[:50]}...")
            print(f"  秘匿: {'はい' if ho.is_secret else 'いいえ'}")


def main():
    """メイン処理"""
    print("="*60)
    print("  Arkham Nexus テストデータ確認")
    print("="*60)
    
    # 統計情報
    print("\n【統計情報】")
    print(f"  ユーザー総数: {User.objects.count()}人")
    print(f"  グループ数: {Group.objects.count()}個")
    print(f"  キャラクター数: {CharacterSheet.objects.count()}人")
    print(f"  セッション数: {TRPGSession.objects.count()}個")
    print(f"  ハンドアウト数: {HandoutInfo.objects.count()}個")
    
    # 詳細確認
    check_users()
    check_groups()
    check_characters()
    check_sessions()
    check_handouts()
    
    print("\n" + "="*60)
    print("  確認完了")
    print("="*60)


if __name__ == '__main__':
    main()