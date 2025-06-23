"""
テストキャラクター作成コマンド
新しいCharacterImageモデルを使用したキャラクターデータを作成
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from accounts.models import CharacterSheet, CharacterSheet6th, CharacterSkill, CharacterImage
from PIL import Image, ImageDraw, ImageFont
import io
import random

User = get_user_model()


class Command(BaseCommand):
    help = '新しい構造でテストキャラクターを作成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='testuser',
            help='キャラクターを作成するユーザー名'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='作成するキャラクター数'
        )

    def create_character_image(self, text, color=(100, 100, 100), size=(400, 600)):
        """キャラクター画像を生成"""
        # 背景色をランダムに
        bg_colors = [
            (240, 248, 255),  # AliceBlue
            (255, 250, 240),  # FloralWhite
            (240, 255, 240),  # HoneyDew
            (255, 240, 245),  # LavenderBlush
            (255, 255, 240),  # LightYellow
        ]
        bg_color = random.choice(bg_colors)
        
        # 画像作成
        img = Image.new('RGB', size, bg_color)
        draw = ImageDraw.Draw(img)
        
        # キャラクターアイコンを描画（シンプルな人型）
        icon_color = color
        # 頭
        head_radius = 60
        head_center = (size[0] // 2, 150)
        draw.ellipse(
            [head_center[0] - head_radius, head_center[1] - head_radius,
             head_center[0] + head_radius, head_center[1] + head_radius],
            fill=icon_color
        )
        
        # 体
        body_width = 120
        body_height = 200
        body_top = head_center[1] + head_radius
        draw.rectangle(
            [size[0] // 2 - body_width // 2, body_top,
             size[0] // 2 + body_width // 2, body_top + body_height],
            fill=icon_color
        )
        
        # テキスト
        text_y = size[1] - 100
        # フォントサイズを適切に設定（システムデフォルトフォント使用）
        try:
            # テキストのバウンディングボックスを取得
            bbox = draw.textbbox((0, 0), text)
            text_width = bbox[2] - bbox[0]
            text_x = (size[0] - text_width) // 2
            draw.text((text_x, text_y), text, fill=(50, 50, 50))
        except:
            # フォールバック
            draw.text((size[0] // 2 - 50, text_y), text, fill=(50, 50, 50))
        
        # バイト列に変換
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        
        return output

    def create_additional_images(self, character_name, count=2):
        """追加の画像を生成（装備品、スキルカードなど）"""
        images = []
        image_types = [
            ("装備品", (200, 300), (150, 100, 50)),
            ("スキルカード", (300, 200), (50, 100, 150)),
            ("背景設定", (250, 250), (100, 150, 100)),
        ]
        
        for i in range(count):
            img_type, size, color = random.choice(image_types)
            img = Image.new('RGB', size, (255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            # 枠線
            draw.rectangle([10, 10, size[0]-10, size[1]-10], outline=color, width=3)
            
            # タイトル
            title = f"{character_name}の{img_type}"
            try:
                draw.text((20, 20), title, fill=color)
            except:
                pass
            
            output = io.BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            
            images.append((f"{img_type}_{i+1}.png", output))
        
        return images

    def handle(self, *args, **options):
        username = options['username']
        count = options['count']

        # ユーザー取得または作成
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'nickname': f'テストユーザー{username}'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'ユーザー {username} を作成しました'))

        # テストキャラクターのデータ
        test_characters = [
            {
                'name': '現代の探索者',
                'occupation': 'ジャーナリスト',
                'age': 28,
                'gender': '女性',
                'birthplace': '東京都',
                'residence': '東京都渋谷区',
                'abilities': {
                    'str': 11, 'con': 13, 'pow': 14, 'dex': 12,
                    'app': 13, 'siz': 11, 'int': 15, 'edu': 16
                },
                'skills': [
                    ('言いくるめ', 5, 30, 15),
                    ('図書館', 25, 40, 10),
                    ('写真術', 10, 35, 5),
                    ('心理学', 10, 30, 10),
                    ('目星', 25, 25, 15),
                ],
                'color': (100, 150, 200)
            },
            {
                'name': '古書店の店主',
                'occupation': '古物商',
                'age': 45,
                'gender': '男性',
                'birthplace': '京都府',
                'residence': '東京都文京区',
                'abilities': {
                    'str': 9, 'con': 11, 'pow': 17, 'dex': 10,
                    'app': 10, 'siz': 12, 'int': 16, 'edu': 18
                },
                'skills': [
                    ('オカルト', 5, 45, 20),
                    ('歴史', 20, 40, 10),
                    ('図書館', 25, 35, 10),
                    ('値切り', 5, 30, 15),
                    ('目星', 25, 20, 10),
                ],
                'color': (150, 100, 50)
            },
            {
                'name': '私立探偵',
                'occupation': '探偵',
                'age': 35,
                'gender': 'その他',
                'birthplace': '大阪府',
                'residence': '東京都新宿区',
                'abilities': {
                    'str': 13, 'con': 14, 'pow': 13, 'dex': 15,
                    'app': 11, 'siz': 13, 'int': 14, 'edu': 13
                },
                'skills': [
                    ('隠れる', 10, 35, 15),
                    ('聞き耳', 20, 40, 10),
                    ('忍び歩き', 10, 35, 15),
                    ('追跡', 10, 30, 10),
                    ('拳銃', 20, 25, 5),
                ],
                'color': (100, 100, 100)
            },
        ]

        created_count = 0
        
        with transaction.atomic():
            for i in range(count):
                char_data = test_characters[i % len(test_characters)]
                
                # ユニークな名前にする
                char_name = f"{char_data['name']}_{i+1}"
                
                # 既存チェック
                if CharacterSheet.objects.filter(user=user, name=char_name).exists():
                    self.stdout.write(
                        self.style.WARNING(f'キャラクター {char_name} は既に存在します')
                    )
                    continue
                
                # キャラクターシート作成
                character = CharacterSheet.objects.create(
                    user=user,
                    edition='6th',
                    name=char_name,
                    player_name=user.nickname or user.username,
                    age=char_data['age'],
                    gender=char_data['gender'],
                    occupation=char_data['occupation'],
                    birthplace=char_data['birthplace'],
                    residence=char_data['residence'],
                    # 6版は3-18の値で保存
                    str_value=char_data['abilities']['str'],
                    con_value=char_data['abilities']['con'],
                    pow_value=char_data['abilities']['pow'],
                    dex_value=char_data['abilities']['dex'],
                    app_value=char_data['abilities']['app'],
                    siz_value=char_data['abilities']['siz'],
                    int_value=char_data['abilities']['int'],
                    edu_value=char_data['abilities']['edu'],
                    notes=f'テストキャラクター（{char_data["occupation"]}）',
                    status='alive',
                    is_active=True
                )
                
                # 6版固有データ
                CharacterSheet6th.objects.create(
                    character_sheet=character,
                    mental_disorder=''
                )
                
                # スキルデータ
                for skill_name, base, occ, interest in char_data['skills']:
                    CharacterSkill.objects.create(
                        character_sheet=character,
                        skill_name=skill_name,
                        base_value=base,
                        occupation_points=occ,
                        interest_points=interest,
                        other_points=0
                    )
                
                # メイン画像を作成
                main_image_data = self.create_character_image(
                    char_name, 
                    char_data['color']
                )
                main_image = CharacterImage.objects.create(
                    character_sheet=character,
                    is_main=True,
                    order=0
                )
                main_image.image.save(
                    f"{char_name}_main.png",
                    ContentFile(main_image_data.read()),
                    save=True
                )
                
                # 追加画像を作成
                additional_images = self.create_additional_images(char_name, 2)
                for idx, (filename, image_data) in enumerate(additional_images):
                    additional_image = CharacterImage.objects.create(
                        character_sheet=character,
                        is_main=False,
                        order=idx + 1
                    )
                    additional_image.image.save(
                        f"{char_name}_{filename}",
                        ContentFile(image_data.read()),
                        save=True
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'キャラクター {char_name} を作成しました（画像3枚付き）'
                    )
                )
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n合計 {created_count} 体のキャラクターを作成しました'
            )
        )