"""
セッションとキャラクターのテストデータを作成するコマンド
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from datetime import timedelta
from accounts.models import Group
from accounts.character_models import CharacterSheet, CharacterSkill
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo, SessionYouTubeLink, SessionImage
import random
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'セッションとキャラクターのテストデータを作成'

    def handle(self, *args, **options):
        self.stdout.write('テストデータの作成を開始します...')
        
        # 既存データの確認
        if TRPGSession.objects.exists():
            self.stdout.write(self.style.WARNING('既にセッションデータが存在します。'))
            if input('既存データを削除して新規作成しますか？ (yes/no): ').lower() != 'yes':
                self.stdout.write('処理を中止しました。')
                return
            
            # 既存データの削除
            HandoutInfo.objects.all().delete()
            SessionParticipant.objects.all().delete()
            TRPGSession.objects.all().delete()
            CharacterSkill.objects.all().delete()
            CharacterSheet.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('既存データを削除しました。'))
        
        # ===== ユーザー作成 =====
        # GM作成
        gm1, _ = User.objects.get_or_create(
            username='keeper1',
            defaults={
                'email': 'keeper1@example.com',
                'nickname': '深淵の守護者',
                'is_staff': True
            }
        )
        if not gm1.check_password('keeper123'):
            gm1.set_password('keeper123')
            gm1.save()
        
        gm2, _ = User.objects.get_or_create(
            username='keeper2',
            defaults={
                'email': 'keeper2@example.com',
                'nickname': '古き印の管理人'
            }
        )
        if not gm2.check_password('keeper123'):
            gm2.set_password('keeper123')
            gm2.save()
        
        # プレイヤー作成
        players = []
        player_names = [
            ('investigator1', '真実の探究者'),
            ('investigator2', '闇を見つめる者'),
            ('investigator3', '古文書の解読者'),
            ('investigator4', '深海の調査員'),
            ('investigator5', '星の観測者'),
            ('investigator6', '遺跡の発掘者')
        ]
        
        for username, nickname in player_names:
            player, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'nickname': nickname
                }
            )
            if not player.check_password('player123'):
                player.set_password('player123')
                player.save()
            players.append(player)
        
        self.stdout.write(self.style.SUCCESS(f'ユーザーを作成しました: GM 2人、プレイヤー {len(players)}人'))
        
        # ===== グループ作成 =====
        group1, _ = Group.objects.get_or_create(
            name='アーカムの探索者たち',
            defaults={
                'created_by': gm1,
                'visibility': 'private',
                'description': '定期的にクトゥルフ神話TRPGをプレイするグループです。'
            }
        )
        group1.members.add(gm1, gm2, *players[:4])
        
        group2, _ = Group.objects.get_or_create(
            name='ミスカトニック大学研究会',
            defaults={
                'created_by': gm2,
                'visibility': 'public',
                'description': '大学を舞台にしたシナリオを中心に活動しています。'
            }
        )
        group2.members.add(gm2, *players[2:])
        
        self.stdout.write(self.style.SUCCESS('グループを作成しました。'))
        
        # ===== キャラクター作成 =====
        characters = []
        character_data = [
            # プレイヤー1のキャラクター
            {
                'user': players[0],
                'name': '佐藤健一',
                'occupation': '私立探偵',
                'age': 32,
                'skills': [('目星', 70), ('聞き耳', 60), ('図書館', 50), ('心理学', 45)]
            },
            {
                'user': players[0],
                'name': 'ジョン・スミス',
                'occupation': '考古学者',
                'age': 45,
                'skills': [('考古学', 80), ('歴史', 70), ('図書館', 65), ('目星', 50)]
            },
            # プレイヤー2のキャラクター
            {
                'user': players[1],
                'name': '田中美咲',
                'occupation': '医師',
                'age': 28,
                'skills': [('医学', 75), ('応急手当', 65), ('生物学', 60), ('薬学', 55)]
            },
            {
                'user': players[1],
                'name': 'エミリー・ブラウン',
                'occupation': 'ジャーナリスト',
                'age': 26,
                'skills': [('言いくるめ', 60), ('説得', 55), ('写真術', 50), ('図書館', 45)]
            },
            # プレイヤー3のキャラクター
            {
                'user': players[2],
                'name': '山田太郎',
                'occupation': '大学教授',
                'age': 52,
                'skills': [('図書館', 85), ('歴史', 75), ('考古学', 70), ('言語学', 65)]
            },
            {
                'user': players[2],
                'name': 'マイケル・ジョーンズ',
                'occupation': '警察官',
                'age': 35,
                'skills': [('拳銃', 60), ('格闘', 55), ('法律', 50), ('心理学', 45)]
            },
            # プレイヤー4のキャラクター
            {
                'user': players[3],
                'name': '鈴木花子',
                'occupation': '古書店主',
                'age': 40,
                'skills': [('図書館', 80), ('歴史', 65), ('オカルト', 70), ('目星', 55)]
            },
            # プレイヤー5のキャラクター
            {
                'user': players[4],
                'name': 'サラ・ウィリアムズ',
                'occupation': '天文学者',
                'age': 30,
                'skills': [('天文学', 85), ('物理学', 70), ('数学', 65), ('機械修理', 50)]
            },
            # プレイヤー6のキャラクター
            {
                'user': players[5],
                'name': '高橋一郎',
                'occupation': '船員',
                'age': 38,
                'skills': [('操縦(船舶)', 75), ('水泳', 65), ('ナビゲート', 60), ('機械修理', 55)]
            }
        ]
        
        for char_info in character_data:
            # 能力値をランダムに生成（6版用）
            character = CharacterSheet.objects.create(
                user=char_info['user'],
                name=char_info['name'],
                occupation=char_info['occupation'],
                age=char_info['age'],
                recommended_skills=[skill_name for skill_name, _ in (char_info.get('skills') or [])],
                edition='6th',
                str_value=random.randint(8, 15),
                con_value=random.randint(8, 15),
                pow_value=random.randint(8, 15),
                dex_value=random.randint(8, 15),
                app_value=random.randint(8, 15),
                siz_value=random.randint(10, 16),
                int_value=random.randint(10, 17),
                edu_value=random.randint(12, 18),
                hit_points_max=random.randint(10, 15),
                hit_points_current=random.randint(10, 15),
                magic_points_max=random.randint(10, 15),
                magic_points_current=random.randint(10, 15),
                sanity_max=random.randint(50, 80),
                sanity_current=random.randint(45, 75),
                sanity_starting=random.randint(50, 80)
            )
            
            # 技能を追加
            for skill_name, value in char_info['skills']:
                try:
                    desired_total = int(value)
                except (TypeError, ValueError):
                    continue

                base_value = character._get_skill_base_value(skill_name)
                if base_value is None:
                    base_value = 0
                try:
                    base_value = int(base_value)
                except (TypeError, ValueError):
                    base_value = 0

                if desired_total < base_value:
                    base_value = desired_total
                    occupation_points = 0
                else:
                    occupation_points = desired_total - base_value

                skill = CharacterSkill(
                    character_sheet=character,
                    skill_name=skill_name,
                    category=character._get_skill_category(skill_name),
                    base_value=base_value,
                    occupation_points=occupation_points,
                    interest_points=0,
                    other_points=0,
                )
                skill.save(skip_point_validation=True)
            
            characters.append(character)
        
        self.stdout.write(self.style.SUCCESS(f'{len(characters)}人のキャラクターを作成しました。'))
        
        # ===== セッション作成 =====
        # セッション1: 進行中のセッション
        session1 = TRPGSession.objects.create(
            title='悪霊の家',
            description='アーカムの郊外にある古い屋敷で起きた失踪事件を調査する。',
            date=timezone.now() - timedelta(hours=1),
            location='オンライン（Discord）',
            gm=gm1,
            group=group1,
            status='ongoing',
            visibility='private',
            duration_minutes=240
        )
        
        # 参加者を追加（4人枠）
        for i in range(4):
            SessionParticipant.objects.create(
                session=session1,
                user=players[i],
                role='player',
                player_slot=i+1,
                character_sheet=characters[i*2]  # 各プレイヤーの1つ目のキャラクター
            )
        
        # ハンドアウトを作成
        handout_contents1 = [
            ('あなたの友人が1週間前から行方不明になっている。最後に目撃されたのは問題の屋敷の近くだった。'),
            ('最近、悪夢にうなされている。夢の中では古い屋敷と不気味な声が聞こえる。'),
            ('あなたの祖父が残した日記に、この屋敷についての不穏な記述がある。'),
            ('地元の新聞社から、屋敷の調査を依頼された。過去にも失踪事件があったという。')
        ]
        handout_recommended_skills1 = [
            '目星, 聞き耳, 図書館',
            '医学, 応急手当, 薬学',
            '図書館, 歴史, 考古学',
            'オカルト, 目星, 図書館',
        ]
        
        for i in range(4):
            participant = SessionParticipant.objects.get(session=session1, player_slot=i+1)
            HandoutInfo.objects.create(
                session=session1,
                participant=participant,
                title=f'HO{i+1}: 個人的な動機',
                content=handout_contents1[i],
                recommended_skills=handout_recommended_skills1[i],
                is_secret=True,
                handout_number=i+1,
                assigned_player_slot=i+1
            )
        
        # セッション2: 予定されているセッション
        session2 = TRPGSession.objects.create(
            title='インスマスからの脱出',
            description='漁村インスマスで目覚めたあなたたちは、恐ろしい真実を知り、脱出を試みる。',
            date=timezone.now() + timedelta(days=3),
            location='秋葉原会議室A',
            gm=gm1,
            group=group1,
            status='planned',
            visibility='private',
            duration_minutes=300
        )
        
        # 2人だけ参加登録済み
        for i in range(2):
            SessionParticipant.objects.create(
                session=session2,
                user=players[i],
                role='player',
                player_slot=i+1,
                character_sheet=characters[i*2+1]  # 各プレイヤーの2つ目のキャラクター
            )

        # セッション2のハンドアウト（参加者分だけ）
        handout_contents2 = [
            'あなたはインスマスの村で目覚めた。記憶が曖昧で、身体には潮の匂いが残っている。',
            'あなたは村の外れで奇妙な儀式を目撃した。誰にも言わない方がよい気がしている。',
        ]
        handout_recommended_skills2 = [
            '考古学, 歴史, 図書館',
            '言いくるめ, 説得, 写真術',
        ]
        for i in range(2):
            participant = SessionParticipant.objects.get(session=session2, player_slot=i+1)
            HandoutInfo.objects.create(
                session=session2,
                participant=participant,
                title=f'HO{i+1}: 目覚め',
                content=handout_contents2[i],
                recommended_skills=handout_recommended_skills2[i],
                is_secret=True,
                handout_number=i+1,
                assigned_player_slot=i+1,
            )
        
        # セッション3: 完了したセッション
        session3 = TRPGSession.objects.create(
            title='ミスカトニック大学の怪異',
            description='大学図書館で発見された禁断の書物を巡る事件。',
            date=timezone.now() - timedelta(days=7),
            location='オンライン（Roll20）',
            gm=gm2,
            group=group2,
            status='completed',
            visibility='public',
            duration_minutes=180
        )
        
        # 参加者を追加
        participants = [players[2], players[3], players[4]]
        session3_character_sheets = [characters[5], characters[6], characters[7]]
        for i, player in enumerate(participants):
            SessionParticipant.objects.create(
                session=session3,
                user=player,
                role='player',
                player_slot=i+1,
                character_sheet=session3_character_sheets[i],
            )

        # セッション3のハンドアウト
        handout_contents3 = [
            'あなたは大学内の警備を担当している。最近、夜間に奇妙な足音が聞こえるという噂がある。',
            'あなたは古書店で禁書の噂を耳にした。依頼を受け、真相を探ることにした。',
            'あなたは星の観測中に異様な座標を記録した。大学の図書館で手がかりを探したい。',
        ]
        handout_recommended_skills3 = [
            '拳銃, 格闘, 法律',
            'オカルト, 図書館, 目星',
            '天文学, 物理学, 数学',
        ]
        for i in range(3):
            participant = SessionParticipant.objects.get(session=session3, player_slot=i+1)
            HandoutInfo.objects.create(
                session=session3,
                participant=participant,
                title=f'HO{i+1}: 秘匿情報',
                content=handout_contents3[i],
                recommended_skills=handout_recommended_skills3[i],
                is_secret=True,
                handout_number=i+1,
                assigned_player_slot=i+1,
            )
        
        # セッション4: 今日の夜のセッション
        session4 = TRPGSession.objects.create(
            title='深海の呼び声',
            description='太平洋での調査航海中、奇妙な信号を受信した調査船の物語。',
            date=timezone.now().replace(hour=20, minute=0) + timedelta(days=0),
            location='オンライン（Discord）',
            gm=gm2,
            group=group2,
            status='planned',
            visibility='public',
            duration_minutes=240
        )
        
        # セッション5: キャンセルされたセッション
        session5 = TRPGSession.objects.create(
            title='狂気山脈にて',
            description='南極探検隊が発見した古代遺跡の調査。',
            date=timezone.now() + timedelta(days=10),
            location='未定',
            gm=gm1,
            group=group1,
            status='cancelled',
            visibility='private',
            duration_minutes=360
        )
        
        self.stdout.write(self.style.SUCCESS(f'{TRPGSession.objects.count()}個のセッションを作成しました。'))
        
        # ===== YouTube動画リンク作成 =====
        # セッション1の動画（進行中セッション）
        youtube_data_session1 = [
            {
                'video_id': 'dQw4w9WgXcQ',
                'title': 'クトゥルフ神話TRPG入門動画',
                'duration': 213,
                'channel': 'TRPG Channel',
                'description': 'セッション前に視聴推奨の入門動画'
            },
            {
                'video_id': '9bZkp7q19f0',
                'title': '悪霊の家 BGM集',
                'duration': 3600,
                'channel': 'Horror BGM',
                'description': 'セッション中に使用するBGM'
            }
        ]
        
        for i, video in enumerate(youtube_data_session1):
            SessionYouTubeLink.objects.create(
                session=session1,
                youtube_url=f"https://youtube.com/watch?v={video['video_id']}",
                video_id=video['video_id'],
                title=video['title'],
                duration_seconds=video['duration'],
                channel_name=video['channel'],
                description=video['description'],
                added_by=gm1,
                order=i+1
            )
        
        # セッション3の動画（完了セッション）
        youtube_data_session3 = [
            {
                'video_id': 'abc123def',
                'title': 'ミスカトニック大学の怪異 リプレイ動画 Part1',
                'duration': 5400,
                'channel': 'アーカムの探索者たち',
                'description': 'セッションのリプレイ動画（前半）'
            },
            {
                'video_id': 'ghi456jkl',
                'title': 'ミスカトニック大学の怪異 リプレイ動画 Part2',
                'duration': 4800,
                'channel': 'アーカムの探索者たち',
                'description': 'セッションのリプレイ動画（後半）'
            },
            {
                'video_id': 'mno789pqr',
                'title': 'セッション振り返り配信',
                'duration': 1800,
                'channel': 'アーカムの探索者たち',
                'description': 'GMとPLによる振り返り雑談'
            }
        ]
        
        for i, video in enumerate(youtube_data_session3):
            SessionYouTubeLink.objects.create(
                session=session3,
                youtube_url=f"https://youtube.com/watch?v={video['video_id']}",
                video_id=video['video_id'],
                title=video['title'],
                duration_seconds=video['duration'],
                channel_name=video['channel'],
                description=video['description'],
                added_by=gm2,
                order=i+1
            )
        
        self.stdout.write(self.style.SUCCESS(f'{SessionYouTubeLink.objects.count()}個のYouTube動画リンクを作成しました。'))
        
        # ===== セッション画像作成 =====
        # ダミー画像の作成（テスト用の小さな画像）
        def create_dummy_image(filename, color):
            """テスト用のダミー画像を作成"""
            # 1x1ピクセルのPNG画像（指定色）
            if color == 'red':
                data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            elif color == 'green':
                data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\xf8\x0f\x00\x00\x01\x01\x00\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            else:  # blue
                data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x00\xf8\x00\x00\x01\x01\x00\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            return ContentFile(data, name=filename)
        
        # セッション1の画像
        session1_images = [
            {
                'title': '悪霊の家 外観',
                'description': 'セッションの舞台となる屋敷の外観イメージ',
                'filename': 'haunted_house_exterior.png',
                'color': 'red'
            },
            {
                'title': '屋敷の見取り図',
                'description': '探索用の屋敷内部マップ',
                'filename': 'house_floorplan.png',
                'color': 'green'
            },
            {
                'title': '重要NPCイメージ',
                'description': '屋敷の元所有者のポートレート',
                'filename': 'npc_portrait.png',
                'color': 'blue'
            }
        ]
        
        for i, img_data in enumerate(session1_images):
            image = SessionImage(
                session=session1,
                title=img_data['title'],
                description=img_data['description'],
                uploaded_by=gm1,
                order=i+1
            )
            image.image.save(
                img_data['filename'],
                create_dummy_image(img_data['filename'], img_data['color'])
            )
            image.save()
        
        # セッション3の画像
        session3_images = [
            {
                'title': 'ミスカトニック大学図書館',
                'description': '事件の発端となった図書館の内部',
                'filename': 'library_interior.png',
                'color': 'blue'
            },
            {
                'title': '禁書の表紙',
                'description': '発見された禁断の書物',
                'filename': 'forbidden_book.png',
                'color': 'red'
            }
        ]
        
        for i, img_data in enumerate(session3_images):
            image = SessionImage(
                session=session3,
                title=img_data['title'],
                description=img_data['description'],
                uploaded_by=gm2,
                order=i+1
            )
            image.image.save(
                img_data['filename'],
                create_dummy_image(img_data['filename'], img_data['color'])
            )
            image.save()
        
        self.stdout.write(self.style.SUCCESS(f'{SessionImage.objects.count()}個のセッション画像を作成しました。'))
        
        # ===== サマリー表示 =====
        self.stdout.write('\n' + self.style.SUCCESS('=== テストデータ作成完了 ==='))
        self.stdout.write(f'ユーザー: {User.objects.count()}人')
        self.stdout.write(f'  - GM: {User.objects.filter(username__startswith="keeper").count()}人')
        self.stdout.write(f'  - プレイヤー: {User.objects.filter(username__startswith="investigator").count()}人')
        self.stdout.write(f'グループ: {Group.objects.count()}個')
        self.stdout.write(f'キャラクター: {CharacterSheet.objects.count()}人')
        self.stdout.write(f'セッション: {TRPGSession.objects.count()}個')
        self.stdout.write(f'  - 進行中: {TRPGSession.objects.filter(status="ongoing").count()}個')
        self.stdout.write(f'  - 予定: {TRPGSession.objects.filter(status="planned").count()}個')
        self.stdout.write(f'  - 完了: {TRPGSession.objects.filter(status="completed").count()}個')
        self.stdout.write(f'  - キャンセル: {TRPGSession.objects.filter(status="cancelled").count()}個')
        self.stdout.write(f'ハンドアウト: {HandoutInfo.objects.count()}個')
        self.stdout.write(f'YouTube動画リンク: {SessionYouTubeLink.objects.count()}個')
        self.stdout.write(f'セッション画像: {SessionImage.objects.count()}個')
        
        self.stdout.write('\n' + self.style.SUCCESS('=== ログイン情報 ==='))
        self.stdout.write('GM1: keeper1 / keeper123')
        self.stdout.write('GM2: keeper2 / keeper123')
        self.stdout.write('プレイヤー: investigator1-6 / player123')
        self.stdout.write('管理者: admin / arkham_admin_2024')
