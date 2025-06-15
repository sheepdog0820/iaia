from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from accounts.models import CustomUser, CharacterSheet, CharacterSheet6th, CharacterSheet7th, CharacterSkill, CharacterEquipment
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
from scenarios.models import Scenario, ScenarioNote, PlayHistory
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create detailed investigator history test data for Call of Cthulhu TRPG 6th/7th Edition ONLY'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-history',
            action='store_true',
            help='Clear existing character sheets and history data',
        )

    def handle(self, *args, **options):
        if options['clear_history']:
            self.stdout.write(self.style.WARNING('Clearing existing character history data...'))
            self.clear_history_data()

        self.stdout.write(self.style.SUCCESS('Creating Call of Cthulhu TRPG investigator history data (6th/7th Edition only)...'))
        
        # 既存ユーザーを取得
        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.ERROR('No users found. Please create sample data first.'))
            return
        
        # キャラクターシート作成
        character_sheets = self.create_character_sheets(users)
        self.stdout.write(f'Created {len(character_sheets)} character sheets')
        
        # 追加シナリオ作成
        additional_scenarios = self.create_additional_scenarios(users)
        self.stdout.write(f'Created {len(additional_scenarios)} additional scenarios')
        
        # 詳細なプレイ履歴作成
        self.create_detailed_play_history(users)
        self.stdout.write('Created detailed play history')
        
        self.stdout.write(self.style.SUCCESS('Investigator history data created successfully!'))

    def clear_history_data(self):
        """キャラクターシートと履歴データをクリア"""
        CharacterEquipment.objects.all().delete()
        CharacterSkill.objects.all().delete()
        CharacterSheet7th.objects.all().delete()
        CharacterSheet6th.objects.all().delete()
        CharacterSheet.objects.all().delete()

    def create_character_sheets(self, users):
        """詳細なキャラクターシートを作成"""
        character_sheets = []
        
        # 6版キャラクター例（クトゥルフ神話TRPG 6版ルール準拠）
        sixth_edition_characters = [
            {
                'name': '高島 静雄',
                'age': 28,
                'occupation': '私立探偵',
                'gender': '男性',
                'edition': '6th',
                'str_value': 13, 'con_value': 14, 'pow_value': 16, 'dex_value': 15,
                'app_value': 12, 'siz_value': 13, 'int_value': 17, 'edu_value': 15,
                'notes': '新宿で私立探偵をしている。オカルト事件を専門とし、数々の怪奇現象を解決してきた。クトゥルフ神話に対する知識も持つ。'
            },
            {
                'name': '佐藤 美香',
                'age': 24,
                'occupation': '医学生',
                'gender': '女性',
                'edition': '6th',
                'str_value': 10, 'con_value': 12, 'pow_value': 15, 'dex_value': 14,
                'app_value': 16, 'siz_value': 11, 'int_value': 18, 'edu_value': 17,
                'notes': '東京大学医学部の学生。解剖学に詳しく、怪奇事件の捜査で医学的見地から貢献する。ミスカトニック大学への留学経験あり。'
            },
            {
                'name': '山田 鉄男',
                'age': 35,
                'occupation': '新聞記者',
                'gender': '男性',
                'edition': '6th',
                'str_value': 14, 'con_value': 13, 'pow_value': 12, 'dex_value': 13,
                'app_value': 11, 'siz_value': 14, 'int_value': 15, 'edu_value': 14,
                'notes': '社会部の記者として活動。スクープを求めて危険なオカルト事件にも首を突っ込む。深きものどもの存在を追っている。'
            }
        ]
        
        # 7版キャラクター例（クトゥルフ神話TRPG 7版ルール準拠）
        seventh_edition_characters = [
            {
                'name': 'ジョン・スミス',
                'age': 32,
                'occupation': 'アンティーク商',
                'gender': '男性',
                'edition': '7th',
                'str_value': 60, 'con_value': 65, 'pow_value': 75, 'dex_value': 70,
                'app_value': 65, 'siz_value': 70, 'int_value': 80, 'edu_value': 85,
                'notes': 'アーカムでアンティーク店を経営。古い品物に宿る謎を解き明かすことが多い。祖父がミスカトニック大学の教授だった。'
            },
            {
                'name': 'エミリー・ジョンソン',
                'age': 26,
                'occupation': '図書館司書',
                'gender': '女性',
                'edition': '7th',
                'str_value': 45, 'con_value': 55, 'pow_value': 85, 'dex_value': 60,
                'app_value': 75, 'siz_value': 50, 'int_value': 90, 'edu_value': 85,
                'notes': 'ミスカトニック大学図書館の司書。禁断の書物ネクロノミコンの断片に精通している。危険な知識の管理に従事。'
            },
            {
                'name': 'ロバート・ブラウン',
                'age': 41,
                'occupation': '元軍人',
                'gender': '男性',
                'edition': '7th',
                'str_value': 85, 'con_value': 80, 'pow_value': 60, 'dex_value': 75,
                'app_value': 55, 'siz_value': 80, 'int_value': 65, 'edu_value': 60,
                'notes': '第一次大戦の退役軍人。西部戦線で目撃した異形の存在について口を閉ざしている。仲間を守るために危険を顧みない。'
            }
        ]
        
        all_characters = sixth_edition_characters + seventh_edition_characters
        
        for i, char_data in enumerate(all_characters):
            user = users[i % len(users)]
            
            # 基本キャラクターシート作成
            char_sheet = CharacterSheet.objects.create(
                user=user,
                edition=char_data['edition'],
                name=char_data['name'],
                player_name=user.nickname,
                age=char_data['age'],
                gender=char_data['gender'],
                occupation=char_data['occupation'],
                birthplace='東京' if char_data['edition'] == '6th' else 'Boston',
                residence='東京' if char_data['edition'] == '6th' else 'Arkham',
                str_value=char_data['str_value'],
                con_value=char_data['con_value'],
                pow_value=char_data['pow_value'],
                dex_value=char_data['dex_value'],
                app_value=char_data['app_value'],
                siz_value=char_data['siz_value'],
                int_value=char_data['int_value'],
                edu_value=char_data['edu_value'],
                notes=char_data['notes']
            )
            
            # 版別データ作成
            if char_data['edition'] == '6th':
                CharacterSheet6th.objects.create(
                    character_sheet=char_sheet,
                    mental_disorder=''
                )
                self.create_6th_edition_skills(char_sheet)
            else:
                CharacterSheet7th.objects.create(
                    character_sheet=char_sheet,
                    luck_points=random.randint(50, 85),
                    personal_description='探索者の詳細な外見描写',
                    ideology_beliefs='正義感が強く、弱者を守ることを信条とする',
                    significant_people='大学時代の恩師であるアーミテージ教授',
                    meaningful_locations='生まれ故郷の小さな教会',
                    treasured_possessions='祖父から受け継いだ銀の十字架',
                    traits='冷静沈着、慎重派',
                    injuries_scars='左腕に古い傷跡',
                    phobias_manias='暗所恐怖症'
                )
                self.create_7th_edition_skills(char_sheet)
            
            # 装備追加
            self.create_character_equipment(char_sheet)
            
            character_sheets.append(char_sheet)
        
        return character_sheets

    def create_6th_edition_skills(self, char_sheet):
        """6版用スキルを作成"""
        skills_data = [
            {'skill_name': '回避', 'base_value': char_sheet.dex_value, 'occupation_points': 30},
            {'skill_name': '隠れる', 'base_value': 10, 'occupation_points': 40, 'interest_points': 20},
            {'skill_name': '聞き耳', 'base_value': 25, 'occupation_points': 50, 'interest_points': 10},
            {'skill_name': '忍び歩き', 'base_value': 10, 'occupation_points': 30, 'interest_points': 15},
            {'skill_name': '図書館', 'base_value': 25, 'occupation_points': 60, 'interest_points': 0},
            {'skill_name': '心理学', 'base_value': 5, 'occupation_points': 40, 'interest_points': 20},
            {'skill_name': '説得', 'base_value': 15, 'occupation_points': 30, 'interest_points': 25},
            {'skill_name': '目星', 'base_value': 25, 'occupation_points': 50, 'interest_points': 10},
            {'skill_name': 'ピストル', 'base_value': 20, 'occupation_points': 40, 'interest_points': 0},
            {'skill_name': '応急手当', 'base_value': 30, 'occupation_points': 0, 'interest_points': 30},
        ]
        
        for skill_data in skills_data:
            CharacterSkill.objects.create(
                character_sheet=char_sheet,
                **skill_data
            )

    def create_7th_edition_skills(self, char_sheet):
        """7版用スキルを作成"""
        skills_data = [
            {'skill_name': '回避', 'base_value': char_sheet.dex_value // 2, 'occupation_points': 30},
            {'skill_name': '隠密', 'base_value': 20, 'occupation_points': 40, 'interest_points': 20},
            {'skill_name': '聞き耳', 'base_value': 20, 'occupation_points': 50, 'interest_points': 10},
            {'skill_name': '忍び歩き', 'base_value': 10, 'occupation_points': 30, 'interest_points': 15},
            {'skill_name': '図書館使用', 'base_value': 20, 'occupation_points': 60, 'interest_points': 0},
            {'skill_name': '心理学', 'base_value': 10, 'occupation_points': 40, 'interest_points': 20},
            {'skill_name': '説得', 'base_value': 10, 'occupation_points': 30, 'interest_points': 25},
            {'skill_name': '目星', 'base_value': 25, 'occupation_points': 50, 'interest_points': 10},
            {'skill_name': '拳銃', 'base_value': 20, 'occupation_points': 40, 'interest_points': 0},
            {'skill_name': '応急手当', 'base_value': 30, 'occupation_points': 0, 'interest_points': 30},
            {'skill_name': 'クトゥルフ神話', 'base_value': 0, 'occupation_points': 0, 'interest_points': 5},
        ]
        
        for skill_data in skills_data:
            CharacterSkill.objects.create(
                character_sheet=char_sheet,
                **skill_data
            )

    def create_character_equipment(self, char_sheet):
        """キャラクター装備を作成"""
        equipment_data = [
            {
                'item_type': 'weapon',
                'name': '.38口径リボルバー',
                'skill_name': 'ピストル' if char_sheet.edition == '6th' else '拳銃',
                'damage': '1d10',
                'base_range': '15m',
                'attacks_per_round': 3,
                'ammo': 6,
                'malfunction_number': 100
            },
            {
                'item_type': 'weapon',
                'name': 'ナイフ',
                'skill_name': 'ナイフ',
                'damage': '1d4+2',
                'base_range': '接触',
                'attacks_per_round': 1
            },
            {
                'item_type': 'item',
                'name': '懐中電灯',
                'description': '夜間の調査に必須のアイテム',
                'quantity': 1
            },
            {
                'item_type': 'item',
                'name': '救急箱',
                'description': '応急手当用の医療用品一式',
                'quantity': 1
            },
            {
                'item_type': 'item',
                'name': '手帳とペン',
                'description': '調査記録用',
                'quantity': 1
            }
        ]
        
        for equipment in equipment_data:
            CharacterEquipment.objects.create(
                character_sheet=char_sheet,
                **equipment
            )

    def create_additional_scenarios(self, users):
        """追加のクトゥルフ神話TRPGシナリオを作成"""
        additional_scenarios_data = [
            {
                'title': '招かれし者たち',
                'author': 'オリジナル',
                'game_system': 'coc',
                'difficulty': 'intermediate',
                'estimated_duration': 'medium',
                'summary': '古い屋敷に招かれた探索者たちが体験する恐怖の一夜。クトゥルフ神話の邪神崇拝と家系の呪いが絡み合う。',
                'player_count': 4,
                'estimated_time': 300,
                'created_by': users[0]
            },
            {
                'title': 'ミスカトニック大学図書館の怪',
                'author': 'オリジナル',
                'game_system': 'coc',
                'difficulty': 'beginner',
                'estimated_duration': 'short',
                'summary': 'ミスカトニック大学図書館で起こる怪奇現象の調査。禁断の書物ネクロノミコンの影響が原因か？',
                'player_count': 3,
                'estimated_time': 180,
                'created_by': users[1]
            },
            {
                'title': 'ダゴン秘密教団',
                'author': 'オリジナル',
                'game_system': 'coc',
                'difficulty': 'advanced',
                'estimated_duration': 'long',
                'summary': '沿岸部の町で起こる連続失踪事件。背後にはダゴンを崇拝する深きものどもの陰謀が。',
                'player_count': 5,
                'estimated_time': 420,
                'created_by': users[2] if len(users) > 2 else users[0]
            },
            {
                'title': 'イスの偉大なる種族の遺産',
                'author': 'オリジナル',
                'game_system': 'coc',
                'difficulty': 'expert',
                'estimated_duration': 'campaign',
                'summary': '古代オーストラリアで発見された遺跡。イスの偉大なる種族の知識が封印された禁断の場所。',
                'player_count': 4,
                'estimated_time': 600,
                'created_by': users[0]
            },
            {
                'title': 'ティンダロスの猟犬',
                'author': 'ケイオシアム社',
                'game_system': 'coc',
                'difficulty': 'advanced',
                'estimated_duration': 'medium',
                'summary': '時間と空間を操る実験が呼び起こした恐怖。角度から現れる猟犬たちから逃れることはできるか？',
                'player_count': 4,
                'estimated_time': 360,
                'created_by': users[1]
            }
        ]
        
        scenarios = []
        for scenario_data in additional_scenarios_data:
            scenario = Scenario.objects.create(**scenario_data)
            scenarios.append(scenario)
        
        return scenarios

    def create_detailed_play_history(self, users):
        """詳細なプレイ履歴を作成"""
        scenarios = list(Scenario.objects.all())
        character_sheets = list(CharacterSheet.objects.all())
        
        # 過去2年間の履歴を作成
        for user in users:
            num_sessions = random.randint(8, 15)  # ユーザーごとに8-15セッション
            
            for i in range(num_sessions):
                # ランダムな過去の日付
                played_date = timezone.now() - timedelta(days=random.randint(30, 730))
                scenario = random.choice(scenarios)
                role = random.choice(['gm', 'player'])
                
                # キャラクターシート情報
                char_sheet = None
                if role == 'player':
                    user_sheets = [cs for cs in character_sheets if cs.user == user]
                    if user_sheets:
                        char_sheet = random.choice(user_sheets)
                
                # 詳細なメモを作成
                if role == 'gm':
                    notes = f'{scenario.title}のGMを担当。プレイヤーは{random.randint(3, 5)}名。' \
                           f'セッション時間: {random.randint(180, 420)}分。' \
                           f'結果: {"成功" if random.choice([True, False]) else "失敗"}。' \
                           f'印象的な場面: {"クライマックスでの大成功" if random.choice([True, False]) else "予想外の展開"}。'
                else:
                    sanity_loss = random.randint(0, 20)
                    survival = random.choice([True, False])
                    notes = f'{scenario.title}に{char_sheet.name if char_sheet else "キャラクター"}で参加。' \
                           f'正気度減少: {sanity_loss}。' \
                           f'生存: {"はい" if survival else "いいえ"}。' \
                           f'MVP: {"獲得" if random.choice([True, False]) else "なし"}。' \
                           f'印象: {"とても楽しかった" if random.choice([True, False]) else "難しかった"}。'
                
                # 重複チェック
                if not PlayHistory.objects.filter(
                    user=user,
                    scenario=scenario,
                    played_date__date=played_date.date()
                ).exists():
                    PlayHistory.objects.create(
                        scenario=scenario,
                        user=user,
                        played_date=played_date,
                        role=role,
                        notes=notes
                    )