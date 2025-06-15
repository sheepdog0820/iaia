from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
import random
from accounts.models import CustomUser, Group, GroupMembership, Friend, GroupInvitation
from scenarios.models import Scenario, ScenarioNote, PlayHistory
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo


class Command(BaseCommand):
    help = 'Arkham Nexus用のテストデータを作成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='作成するユーザー数（デフォルト: 10）'
        )
        parser.add_argument(
            '--sessions',
            type=int,
            default=50,
            help='作成するセッション数（デフォルト: 50）'
        )
        parser.add_argument(
            '--scenarios',
            type=int,
            default=20,
            help='作成するシナリオ数（デフォルト: 20）'
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.SUCCESS('🦑 Arkham Nexusテストデータ作成開始...'))
            
            # テストデータ削除（既存のテストデータをクリア）
            self.clear_test_data()
            
            # ユーザー作成
            users = self.create_users(options['users'])
            self.stdout.write(f'✅ ユーザー {len(users)}人を作成しました')
            
            # シナリオ作成
            scenarios = self.create_scenarios(users, options['scenarios'])
            self.stdout.write(f'✅ シナリオ {len(scenarios)}個を作成しました')
            
            # グループ作成
            groups = self.create_groups(users)
            self.stdout.write(f'✅ グループ {len(groups)}個を作成しました')
            
            # フレンド関係作成
            self.create_friendships(users)
            self.stdout.write('✅ フレンド関係を作成しました')
            
            # セッション作成
            sessions = self.create_sessions(users, groups, scenarios, options['sessions'])
            self.stdout.write(f'✅ セッション {len(sessions)}個を作成しました')
            
            # プレイ履歴作成
            self.create_play_histories(sessions, scenarios)
            self.stdout.write('✅ プレイ履歴を作成しました')
            
            # グループ招待作成
            self.create_group_invitations(users, groups)
            self.stdout.write('✅ グループ招待を作成しました')
            
            self.stdout.write(
                self.style.SUCCESS('🎭 Arkham Nexusテストデータ作成完了！深淵の準備が整いました。')
            )

    def clear_test_data(self):
        """既存のテストデータを削除"""
        # テストユーザーのみ削除（admin以外）
        test_users = CustomUser.objects.exclude(is_superuser=True).exclude(username='admin')
        for user in test_users:
            user.delete()

    def create_users(self, count):
        """テストユーザーを作成"""
        japanese_names = [
            '田中探偵', '佐藤研究者', '鈴木記者', '高橋教授', '渡辺学生',
            '伊藤医師', '山本画家', '中村警官', '小林作家', '加藤司書',
            '吉田考古学者', '山田心理学者', '佐々木神父', '松本軍人', '井上商人'
        ]
        
        users = []
        for i in range(count):
            nickname = japanese_names[i % len(japanese_names)]
            if i >= len(japanese_names):
                nickname += f'{i - len(japanese_names) + 1}'
                
            user = CustomUser.objects.create_user(
                username=f'testuser{i+1}',
                email=f'test{i+1}@arkham.nexus',
                password='testpass123',
                nickname=nickname,
                trpg_history=self.generate_trpg_history()
            )
            users.append(user)
        
        return users

    def generate_trpg_history(self):
        """TRPG履歴をランダム生成"""
        histories = [
            'CoC歴3年。ハンドアウトGMが得意です。',
            'TRPGは大学のサークルで始めました。PLメインです。',
            'インセイン、CoC、DoDをよくプレイします。',
            'GMもPLもどちらも好きです。ホラー系シナリオが好み。',
            '最近TRPGを始めた初心者です。よろしくお願いします。',
            'クトゥルフ神話TRPG一筋10年です。',
            'シナリオ作成もしています。オリジナルシナリオ多数あり。',
            'オンセ・オフセどちらも参加します。',
        ]
        return random.choice(histories)

    def create_scenarios(self, users, count):
        """テストシナリオを作成"""
        scenario_data = [
            {
                'title': '図書館の怪談',
                'game_system': 'coc',
                'difficulty': 'beginner',
                'estimated_duration': 'short',
                'summary': '古い図書館で起こる不可解な現象。初心者向けの短編シナリオ。',
                'author': '田中太郎',
                'recommended_players': '3-4人'
            },
            {
                'title': '呪われた洋館',
                'game_system': 'coc',
                'difficulty': 'intermediate',
                'estimated_duration': 'medium',
                'summary': '山奥の洋館に隠された恐ろしい秘密を暴く中編シナリオ。',
                'author': '山田花子',
                'recommended_players': '4-5人'
            },
            {
                'title': '深海からの呼び声',
                'game_system': 'coc',
                'difficulty': 'advanced',
                'estimated_duration': 'long',
                'summary': '海底遺跡の調査が思わぬ惨劇を招く長編シナリオ。',
                'author': '佐藤一郎',
                'recommended_players': '4-6人'
            },
            {
                'title': '学園の七不思議',
                'game_system': 'insane',
                'difficulty': 'beginner',
                'estimated_duration': 'short',
                'summary': '学校で起こる怪現象をインセインで描く学園ホラー。',
                'author': '鈴木美咲',
                'recommended_players': '3-5人'
            },
            {
                'title': 'ドラゴンの財宝',
                'game_system': 'dnd',
                'difficulty': 'intermediate',
                'estimated_duration': 'medium',
                'summary': 'ドラゴンの住む洞窟で財宝を求める冒険。',
                'author': 'John Smith',
                'recommended_players': '4-6人'
            },
            {
                'title': '魔剣の伝説',
                'game_system': 'sw',
                'difficulty': 'advanced',
                'estimated_duration': 'campaign',
                'summary': '伝説の魔剣を巡る壮大な冒険キャンペーン。',
                'author': '高橋勇',
                'recommended_players': '5-6人'
            },
            {
                'title': '病院の夜勤',
                'game_system': 'coc',
                'difficulty': 'intermediate',
                'estimated_duration': 'medium',
                'summary': '夜勤中の病院で起こる奇怪な事件。',
                'author': '看護師田中',
                'recommended_players': '3-4人'
            },
            {
                'title': '消えた研究者',
                'game_system': 'coc',
                'difficulty': 'advanced',
                'estimated_duration': 'long',
                'summary': '南極調査隊の失踪事件の真相を追う。',
                'author': '極地研究所',
                'recommended_players': '4-5人'
            },
            {
                'title': '街の噂',
                'game_system': 'insane',
                'difficulty': 'beginner',
                'estimated_duration': 'short',
                'summary': '都市伝説をテーマにした現代ホラー。',
                'author': '都市伝説マニア',
                'recommended_players': '3-4人'
            },
            {
                'title': '古代遺跡の謎',
                'game_system': 'coc',
                'difficulty': 'expert',
                'estimated_duration': 'campaign',
                'summary': '古代文明の遺跡で眠る邪神の封印。',
                'author': '考古学者協会',
                'recommended_players': '4-6人'
            }
        ]
        
        scenarios = []
        for i in range(count):
            data = scenario_data[i % len(scenario_data)]
            if i >= len(scenario_data):
                data = data.copy()
                data['title'] += f' {i - len(scenario_data) + 1}'
            
            scenario = Scenario.objects.create(
                title=data['title'],
                game_system=data['game_system'],
                difficulty=data['difficulty'],
                estimated_duration=data['estimated_duration'],
                summary=data['summary'],
                author=data['author'],
                recommended_players=data['recommended_players'],
                url=f'https://booth.pm/scenario/{i+1}' if random.choice([True, False]) else '',
                created_by=random.choice(users)
            )
            scenarios.append(scenario)
        
        return scenarios

    def create_groups(self, users):
        """テストグループを作成"""
        group_names = [
            'クトゥルフ探索隊',
            'アーカム市TRPG愛好会',
            'ルルイエ深海調査団',
            'ミスカトニック大学TRPG部',
            'ダンウィッチ村民会',
            'インスマス漁業組合'
        ]
        
        groups = []
        for i, name in enumerate(group_names):
            group = Group.objects.create(
                name=name,
                description=f'{name}の説明です。一緒にTRPGを楽しみましょう！',
                visibility=random.choice(['private', 'public']),
                created_by=users[i % len(users)]
            )
            
            # グループ作成者を管理者として追加
            GroupMembership.objects.create(
                user=group.created_by,
                group=group,
                role='admin'
            )
            
            # ランダムにメンバーを追加
            member_count = random.randint(3, 8)
            available_users = [u for u in users if u != group.created_by]
            selected_members = random.sample(available_users, min(member_count, len(available_users)))
            
            for user in selected_members:
                GroupMembership.objects.create(
                    user=user,
                    group=group,
                    role='member'
                )
            
            groups.append(group)
        
        return groups

    def create_friendships(self, users):
        """フレンド関係を作成"""
        for user in users:
            # 各ユーザーに2-5人のフレンドを作成
            friend_count = random.randint(2, 5)
            potential_friends = [u for u in users if u != user]
            friends = random.sample(potential_friends, min(friend_count, len(potential_friends)))
            
            for friend in friends:
                # 双方向のフレンド関係（重複チェック）
                if not Friend.objects.filter(user=user, friend=friend).exists():
                    Friend.objects.create(user=user, friend=friend)
                if not Friend.objects.filter(user=friend, friend=user).exists():
                    Friend.objects.create(user=friend, friend=user)

    def create_sessions(self, users, groups, scenarios, count):
        """テストセッションを作成"""
        sessions = []
        current_date = timezone.now()
        
        for i in range(count):
            # 過去6ヶ月から未来1ヶ月の範囲でセッション日時を設定
            days_offset = random.randint(-180, 30)
            session_date = current_date + timedelta(days=days_offset)
            
            # 時間を設定（19:00-22:00の範囲）
            hour = random.randint(19, 21)
            session_date = session_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            group = random.choice(groups)
            gm = random.choice(list(group.members.all()))
            
            # セッションステータス決定
            if days_offset < -1:
                status = 'completed'
                duration = random.randint(120, 360)  # 2-6時間
            elif days_offset < 0:
                status = random.choice(['completed', 'ongoing'])
                duration = random.randint(120, 360) if status == 'completed' else 0
            else:
                status = 'planned'
                duration = 0
            
            session = TRPGSession.objects.create(
                title=f'{random.choice(scenarios).title} セッション{i+1}',
                description=f'楽しいTRPGセッションです！参加者募集中。',
                date=session_date,
                location=random.choice(['オンライン(Discord)', '渋谷TRPG cafe', '新宿ゲームショップ', 'オンライン(Zoom)', '秋葉原ボードゲームカフェ']),
                youtube_url=f'https://youtube.com/watch?v=demo{i+1}' if random.choice([True, False, False]) else '',
                status=status,
                visibility=random.choice(['group', 'public', 'private']),
                gm=gm,
                group=group,
                duration_minutes=duration
            )
            
            # GMを参加者として追加
            SessionParticipant.objects.create(
                session=session,
                user=gm,
                role='gm',
                character_name=f'GM_{gm.nickname}',
                character_sheet_url=f'https://charasheet.vampire-blood.net/{random.randint(100000, 999999)}' if random.choice([True, False]) else ''
            )
            
            # PLを追加
            group_members = list(group.members.exclude(id=gm.id))
            pl_count = min(random.randint(2, 5), len(group_members))
            pls = random.sample(group_members, pl_count)
            
            character_names = [
                '田中刑事', '佐藤記者', '鈴木学生', '高橋教授', '渡辺医師',
                '伊藤研究者', '山本探偵', '中村司書', '小林画家', '加藤神父'
            ]
            
            for j, pl in enumerate(pls):
                SessionParticipant.objects.create(
                    session=session,
                    user=pl,
                    role='player',
                    character_name=character_names[j % len(character_names)],
                    character_sheet_url=f'https://charasheet.vampire-blood.net/{random.randint(100000, 999999)}' if random.choice([True, False]) else ''
                )
            
            sessions.append(session)
        
        return sessions

    def create_play_histories(self, sessions, scenarios):
        """プレイ履歴を作成"""
        for session in sessions:
            if session.status == 'completed':
                scenario = random.choice(scenarios)
                
                for participant in session.sessionparticipant_set.all():
                    PlayHistory.objects.create(
                        scenario=scenario,
                        user=participant.user,
                        session=session,
                        played_date=session.date,
                        role=participant.role,
                        notes=random.choice([
                            'とても楽しいセッションでした！',
                            'ハラハラドキドキの展開でした。',
                            'キャラクターの成長を感じられました。',
                            'また参加したいです。',
                            'GMの演出が素晴らしかった。',
                            '他のPLとの連携が良かった。'
                        ]) if random.choice([True, False]) else ''
                    )

    def create_group_invitations(self, users, groups):
        """グループ招待を作成"""
        for group in groups:
            # いくつかの招待を作成
            invitation_count = random.randint(0, 3)
            group_members = set(group.members.all())
            non_members = [u for u in users if u not in group_members]
            
            if len(non_members) > 0:
                invitees = random.sample(non_members, min(invitation_count, len(non_members)))
                admin = group.groupmembership_set.filter(role='admin').first().user
                
                for invitee in invitees:
                    GroupInvitation.objects.create(
                        group=group,
                        inviter=admin,
                        invitee=invitee,
                        status=random.choice(['pending', 'pending', 'accepted', 'declined']),
                        message=f'{group.name}へのご招待です。一緒にTRPGを楽しみましょう！'
                    )