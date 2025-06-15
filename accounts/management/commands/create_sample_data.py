from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from accounts.models import CustomUser, Friend, Group, GroupMembership
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
from scenarios.models import Scenario, ScenarioNote, PlayHistory
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for Arkham Nexus'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating sample data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Creating sample data...'))
        
        # ユーザー作成
        users = self.create_users()
        self.stdout.write(f'Created {len(users)} users')
        
        # グループ作成
        groups = self.create_groups(users)
        self.stdout.write(f'Created {len(groups)} groups')
        
        # フレンド関係作成
        self.create_friendships(users)
        self.stdout.write('Created friendships')
        
        # シナリオ作成
        scenarios = self.create_scenarios(users)
        self.stdout.write(f'Created {len(scenarios)} scenarios')
        
        # セッション作成
        sessions = self.create_sessions(users, groups, scenarios)
        self.stdout.write(f'Created {len(sessions)} sessions')
        
        # プレイ履歴作成
        self.create_play_history(users, scenarios, sessions)
        self.stdout.write('Created play history')
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))

    def clear_data(self):
        """既存データをクリア（スーパーユーザー以外）"""
        PlayHistory.objects.all().delete()
        HandoutInfo.objects.all().delete()
        SessionParticipant.objects.all().delete()
        TRPGSession.objects.all().delete()
        ScenarioNote.objects.all().delete()
        Scenario.objects.all().delete()
        Friend.objects.all().delete()
        GroupMembership.objects.all().delete()
        Group.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def create_users(self):
        """サンプルユーザーを作成"""
        users_data = [
            {
                'username': 'azathoth_gm', 
                'email': 'azathoth@arkham.nexus',
                'nickname': 'アザトース',
                'trpg_history': 'クトゥルフ神話TRPG歴15年。主にGMを担当し、数々の探索者を狂気へと導いてきた。'
            },
            {
                'username': 'nyarlathotep', 
                'email': 'nyarla@arkham.nexus',
                'nickname': 'ニャルラトホテプ',
                'trpg_history': 'TRPG歴10年。様々なシステムをプレイするが、特にクトゥルフ神話が好き。'
            },
            {
                'username': 'cthulhu_player', 
                'email': 'cthulhu@arkham.nexus',
                'nickname': 'クトゥルフ信者',
                'trpg_history': 'TRPG初心者。最近クトゥルフ神話TRPGにハマった新米探索者。'
            },
            {
                'username': 'shub_niggurath', 
                'email': 'shub@arkham.nexus',
                'nickname': 'シュブ＝ニグラス',
                'trpg_history': 'TRPG歴8年。D&Dからクトゥルフまで幅広くプレイ。キャラロール重視。'
            },
            {
                'username': 'yog_sothoth', 
                'email': 'yog@arkham.nexus',
                'nickname': 'ヨグ＝ソトース',
                'trpg_history': 'TRPG歴12年。ルールマスターとして知られ、複雑なシナリオを好む。'
            },
            {
                'username': 'hastur_dm', 
                'email': 'hastur@arkham.nexus',
                'nickname': 'ハスター',
                'trpg_history': 'TRPG歴20年のベテラン。クトゥルフ以外にもD&D、サイバーパンクなど多数。'
            }
        ]
        
        users = []
        for user_data in users_data:
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password='arkham2024',
                nickname=user_data['nickname'],
                trpg_history=user_data['trpg_history']
            )
            users.append(user)
        
        return users

    def create_groups(self, users):
        """サンプルグループを作成"""
        groups_data = [
            {
                'name': 'アーカム市調査団',
                'description': 'アーカム市を拠点とする探索者グループ。主にクトゥルフ神話TRPGをプレイ。',
                'created_by': users[0]
            },
            {
                'name': 'ミスカトニック大学同好会',
                'description': 'ミスカトニック大学の学生・職員によるTRPGサークル。',
                'created_by': users[1]
            },
            {
                'name': 'ダンウィッチ探検隊',
                'description': 'ダンウィッチ周辺の怪奇現象を調査する探索者たち。',
                'created_by': users[5]
            }
        ]
        
        groups = []
        for group_data in groups_data:
            group = Group.objects.create(**group_data)
            groups.append(group)
            
            # グループメンバーシップ作成
            GroupMembership.objects.create(
                user=group_data['created_by'],
                group=group,
                role='admin'
            )
            
            # 他のメンバーも追加
            other_users = [u for u in users if u != group_data['created_by']]
            for user in random.sample(other_users, min(3, len(other_users))):
                GroupMembership.objects.create(
                    user=user,
                    group=group,
                    role='member'
                )
        
        return groups

    def create_friendships(self, users):
        """フレンド関係を作成"""
        for i, user in enumerate(users):
            # 各ユーザーに2-3人の友達を作成
            potential_friends = [u for u in users if u != user]
            friends = random.sample(potential_friends, random.randint(2, 3))
            
            for friend in friends:
                # 既に友達関係がある場合はスキップ
                if not Friend.objects.filter(user=user, friend=friend).exists():
                    Friend.objects.create(user=user, friend=friend)

    def create_scenarios(self, users):
        """サンプルシナリオを作成"""
        scenarios_data = [
            {
                'title': '悪霊の家',
                'author': '内山靖二郎',
                'game_system': 'coc',
                'summary': 'プレイヤーたちは不動産屋に雇われ、売りに出されている古い屋敷の調査を依頼される。',
                'player_count': 4,
                'estimated_time': 240,
                'created_by': users[0]
            },
            {
                'title': 'クトゥルフ2015',
                'author': '内山靖二郎',
                'game_system': 'coc',
                'summary': '現代を舞台にしたクトゥルフ神話の入門シナリオ。',
                'player_count': 3,
                'estimated_time': 180,
                'created_by': users[1]
            },
            {
                'title': '死者のストーカー',
                'author': 'コスモス',
                'game_system': 'coc',
                'summary': '探索者たちの前に現れる謎の追跡者の正体を暴くシナリオ。',
                'player_count': 5,
                'estimated_time': 300,
                'created_by': users[0]
            },
            {
                'title': '血塗られた書物',
                'author': 'オリジナル',
                'game_system': 'coc',
                'summary': '古書店で発見された禁断の書物から始まる恐怖のシナリオ。',
                'player_count': 4,
                'estimated_time': 360,
                'created_by': users[5]
            },
            {
                'title': '忌まわしき狩人',
                'author': 'ケイオシアム',
                'game_system': 'coc',
                'summary': '森で起こる連続失踪事件の謎を解くホラーシナリオ。',
                'player_count': 4,
                'estimated_time': 270,
                'created_by': users[1]
            }
        ]
        
        scenarios = []
        for scenario_data in scenarios_data:
            scenario = Scenario.objects.create(**scenario_data)
            scenarios.append(scenario)
            
            # シナリオメモも作成
            if random.choice([True, False]):
                ScenarioNote.objects.create(
                    scenario=scenario,
                    user=scenario_data['created_by'],
                    title='GMメモ',
                    content=f'{scenario.title}の進行上の注意点やアレンジポイント',
                    is_private=True
                )
        
        return scenarios

    def create_sessions(self, users, groups, scenarios):
        """サンプルセッションを作成"""
        sessions = []
        
        # 過去のセッション
        for i in range(8):
            date = timezone.now() - timedelta(days=random.randint(7, 365))
            scenario = random.choice(scenarios)
            group = random.choice(groups)
            gm = random.choice([m.user for m in group.groupmembership_set.all()])
            
            session = TRPGSession.objects.create(
                title=f'{scenario.title} #{i+1}',
                description=f'{scenario.title}のセッション',
                date=date,
                location='オンライン（Discord）',
                youtube_url=f'https://www.youtube.com/watch?v=example{i}' if random.choice([True, False]) else '',
                status='completed',
                visibility='group',
                gm=gm,
                group=group,
                duration_minutes=random.randint(180, 420)
            )
            sessions.append(session)
            
            # セッション参加者を追加
            SessionParticipant.objects.create(
                session=session,
                user=gm,
                role='gm'
            )
            
            # PLを追加
            group_members = [m.user for m in group.groupmembership_set.all() if m.user != gm]
            participants = random.sample(group_members, min(scenario.player_count, len(group_members)))
            
            for participant in participants:
                SessionParticipant.objects.create(
                    session=session,
                    user=participant,
                    role='player',
                    character_name=f'{participant.nickname}のPC',
                    character_sheet_url='https://charasheet.vampire-blood.net/example'
                )
        
        # 未来のセッション
        for i in range(3):
            date = timezone.now() + timedelta(days=random.randint(1, 30))
            scenario = random.choice(scenarios)
            group = random.choice(groups)
            gm = random.choice([m.user for m in group.groupmembership_set.all()])
            
            session = TRPGSession.objects.create(
                title=f'{scenario.title} - 新セッション',
                description=f'{scenario.title}の新しいセッション',
                date=date,
                location='オンライン（Discord）',
                status='planned',
                visibility='group',
                gm=gm,
                group=group,
                duration_minutes=scenario.estimated_time
            )
            sessions.append(session)
            
            # GMを参加者として追加
            SessionParticipant.objects.create(
                session=session,
                user=gm,
                role='gm'
            )
        
        return sessions

    def create_play_history(self, users, scenarios, sessions):
        """プレイ履歴を作成"""
        completed_sessions = [s for s in sessions if s.status == 'completed']
        
        for session in completed_sessions:
            participants = SessionParticipant.objects.filter(session=session)
            scenario = random.choice(scenarios)  # セッションに対応するシナリオを選択
            
            for participant in participants:
                # 重複チェック
                if not PlayHistory.objects.filter(
                    user=participant.user,
                    session=session
                ).exists():
                    PlayHistory.objects.create(
                        scenario=scenario,
                        user=participant.user,
                        session=session,
                        played_date=session.date,
                        role=participant.role,
                        notes=f'{scenario.title}をプレイ。{participant.role}として参加。'
                    )