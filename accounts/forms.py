from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.contrib.auth import authenticate
from .models import CustomUser
from .character_models import CharacterSheet, CharacterSheet6th


class MultipleFileInput(forms.ClearableFileInput):
    """複数ファイル対応のカスタムウィジェット"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """複数ファイル対応のカスタムフィールド"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class CustomLoginForm(AuthenticationForm):
    """カスタムログインフォーム"""
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ユーザー名またはメールアドレス',
            'autofocus': True
        }),
        label='ユーザー名またはメールアドレス'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード'
        }),
        label='パスワード'
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='ログイン状態を保持する'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if '@' in username:
            # メールアドレスでの認証を試行
            try:
                user = CustomUser.objects.get(email=username)
                return user.username
            except CustomUser.DoesNotExist:
                pass
        return username


class CustomSignUpForm(UserCreationForm):
    """カスタムサインアップフォーム"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'メールアドレス'
        }),
        label='メールアドレス'
    )
    
    nickname = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ニックネーム（任意）'
        }),
        label='ニックネーム'
    )
    
    trpg_history = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'TRPG歴やゲーム経験について（任意）'
        }),
        label='TRPG歴'
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'nickname', 'password1', 'password2', 'trpg_history')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'ユーザー名'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'パスワード'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'パスワード（確認）'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('このメールアドレスは既に使用されています。')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.nickname = self.cleaned_data.get('nickname', '')
        user.trpg_history = self.cleaned_data.get('trpg_history', '')
        if commit:
            user.save()
        return user


class CustomPasswordResetForm(PasswordResetForm):
    """カスタムパスワードリセットフォーム"""
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'メールアドレス'
        }),
        label='メールアドレス'
    )


class ProfileEditForm(forms.ModelForm):
    """プロフィール編集フォーム"""
    class Meta:
        model = CustomUser
        fields = ['nickname', 'email', 'first_name', 'last_name', 'trpg_history', 'profile_image']
        widgets = {
            'nickname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ニックネーム'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'メールアドレス'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '名前'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '姓'
            }),
            'trpg_history': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'TRPG歴やゲーム経験について'
            }),
            'profile_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'nickname': 'ニックネーム',
            'email': 'メールアドレス',
            'first_name': '名前',
            'last_name': '姓',
            'trpg_history': 'TRPG歴',
            'profile_image': 'プロフィール画像'
        }


class CharacterSheet6thForm(forms.ModelForm):
    """クトゥルフ神話TRPG 6版探索者作成フォーム"""
    
    # 6版固有フィールド
    mental_disorder = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '精神的障害の詳細（任意）'
        }),
        label='精神的障害'
    )
    
    # 複数画像アップロード
    character_images = MultipleFileField(
        required=False,
        label='キャラクター画像（複数選択可能）'
    )
    
    # 派生ステータスフィールドをオプショナルに（自動計算されるため）
    hit_points_max = forms.IntegerField(required=False)
    hit_points_current = forms.IntegerField(required=False)
    magic_points_max = forms.IntegerField(required=False)
    magic_points_current = forms.IntegerField(required=False)
    sanity_starting = forms.IntegerField(required=False)
    sanity_max = forms.IntegerField(required=False)
    sanity_current = forms.IntegerField(required=False)
    
    class Meta:
        model = CharacterSheet
        fields = [
            'name', 'player_name', 'age', 'gender', 'occupation', 
            'birthplace', 'residence', 'str_value', 'con_value', 
            'pow_value', 'dex_value', 'app_value', 'siz_value', 
            'int_value', 'edu_value', 'notes',
            'hit_points_max', 'hit_points_current', 'magic_points_max', 
            'magic_points_current', 'sanity_starting', 'sanity_max', 'sanity_current'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '探索者名',
                'required': True
            }),
            'player_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'プレイヤー名'
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 15,
                'max': 90,
                'placeholder': '年齢'
            }),
            'gender': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '性別'
            }),
            'occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '職業'
            }),
            'birthplace': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '出身地'
            }),
            'residence': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '現住所'
            }),
            'str_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 1,
                'max': 999,
                'placeholder': 'STR',
                'required': True
            }),
            'con_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 1,
                'max': 999,
                'placeholder': 'CON',
                'required': True
            }),
            'pow_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 1,
                'max': 999,
                'placeholder': 'POW',
                'required': True
            }),
            'dex_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 1,
                'max': 999,
                'placeholder': 'DEX',
                'required': True
            }),
            'app_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 1,
                'max': 999,
                'placeholder': 'APP',
                'required': True
            }),
            'siz_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 1,
                'max': 999,
                'placeholder': 'SIZ',
                'required': True
            }),
            'int_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 1,
                'max': 999,
                'placeholder': 'INT',
                'required': True
            }),
            'edu_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 1,
                'max': 999,
                'placeholder': 'EDU',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '探索者の背景や特徴'
            }),
            'hit_points_max': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True
            }),
            'hit_points_current': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '現在HP'
            }),
            'magic_points_max': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True
            }),
            'magic_points_current': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '現在MP'
            }),
            'sanity_starting': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True
            }),
            'sanity_max': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True
            }),
            'sanity_current': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '現在正気度'
            })
        }
        labels = {
            'name': '探索者名',
            'player_name': 'プレイヤー名',
            'age': '年齢',
            'gender': '性別',
            'occupation': '職業',
            'birthplace': '出身地',
            'residence': '現住所',
            'str_value': '筋力(STR)',
            'con_value': '体力(CON)',
            'pow_value': '精神力(POW)',
            'dex_value': '敏捷性(DEX)',
            'app_value': '外見(APP)',
            'siz_value': '体格(SIZ)',
            'int_value': '知性(INT)',
            'edu_value': '教育(EDU)',
            'notes': 'メモ',
            'hit_points_max': '最大HP',
            'hit_points_current': '現在HP',
            'magic_points_max': '最大MP',
            'magic_points_current': '現在MP',
            'sanity_starting': '初期正気度',
            'sanity_max': '最大正気度',
            'sanity_current': '現在正気度'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # プレイヤー名の初期値設定
        if self.user and not self.instance.pk:
            self.initial['player_name'] = self.user.nickname or self.user.username
    
    def clean(self):
        cleaned_data = super().clean()
        
        # 副次ステータスが計算されていることを確認
        # HP最大値が設定されていない場合は計算
        if 'hit_points_max' not in cleaned_data or not cleaned_data['hit_points_max']:
            con = cleaned_data.get('con_value', 10)
            siz = cleaned_data.get('siz_value', 13)
            import math
            cleaned_data['hit_points_max'] = math.ceil((con + siz) / 2)
        
        # MP最大値が設定されていない場合は計算
        if 'magic_points_max' not in cleaned_data or not cleaned_data['magic_points_max']:
            pow_val = cleaned_data.get('pow_value', 10)
            cleaned_data['magic_points_max'] = pow_val
        
        # SAN開始値を計算（常に計算する）
        pow_val = cleaned_data.get('pow_value', 10)
        cleaned_data['sanity_starting'] = pow_val * 5
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"POW: {pow_val}, Calculated SAN starting: {cleaned_data['sanity_starting']}")
        
        # 現在値フィールドのデフォルト値設定
        # 値が明示的に設定されていない場合のみデフォルト値を設定
        if 'hit_points_current' not in cleaned_data or cleaned_data['hit_points_current'] is None:
            cleaned_data['hit_points_current'] = cleaned_data.get('hit_points_max', 11)
        
        if 'magic_points_current' not in cleaned_data or cleaned_data['magic_points_current'] is None:
            cleaned_data['magic_points_current'] = cleaned_data.get('magic_points_max', 10)
        
        if 'sanity_max' not in cleaned_data or cleaned_data['sanity_max'] is None:
            cleaned_data['sanity_max'] = cleaned_data.get('sanity_starting', 50)
        
        if 'sanity_current' not in cleaned_data or cleaned_data['sanity_current'] is None:
            cleaned_data['sanity_current'] = cleaned_data.get('sanity_starting', 50)
        
        return cleaned_data
    
    def save(self, commit=True):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"CharacterSheet6thForm.save called with commit={commit}")
        logger.info(f"Form files: {self.files}")
        logger.info(f"Form data contains character_images: {'character_images' in self.files}")
        
        instance = super().save(commit=False)
        instance.edition = '6th'  # 強制的に6版に設定
        if self.user:
            instance.user = self.user
        
        # 現在値を取得（0も有効値として扱う）
        hit_points_current_value = self.cleaned_data.get('hit_points_current')
        if hit_points_current_value is not None:
            instance.hit_points_current = hit_points_current_value
        else:
            instance.hit_points_current = instance.hit_points_max
        
        magic_points_current_value = self.cleaned_data.get('magic_points_current')
        if magic_points_current_value is not None:
            instance.magic_points_current = magic_points_current_value
        else:
            instance.magic_points_current = instance.magic_points_max
        
        # SANの値設定
        sanity_current_value = self.cleaned_data.get('sanity_current')
        sanity_max_value = self.cleaned_data.get('sanity_max')
        
        if not self.instance.pk:  # 新規作成の場合
            # 現在値が明示的に設定されている場合はそれを使用
            if sanity_current_value is not None:
                instance.sanity_current = sanity_current_value
            else:
                instance.sanity_current = instance.sanity_starting
            
            if sanity_max_value is not None:
                instance.sanity_max = sanity_max_value
            else:
                instance.sanity_max = instance.sanity_starting
        else:  # 編集の場合
            if sanity_current_value is not None:
                instance.sanity_current = sanity_current_value
                
            if sanity_max_value is not None:
                instance.sanity_max = sanity_max_value
        
        if commit:
            instance.save()
            
            # 6版固有データの保存/更新
            sixth_data, created = CharacterSheet6th.objects.get_or_create(
                character_sheet=instance,
                defaults={'mental_disorder': self.cleaned_data.get('mental_disorder', '')}
            )
            if not created:
                sixth_data.mental_disorder = self.cleaned_data.get('mental_disorder', '')
                sixth_data.save()
            
            # 技能データの処理（フロントエンドから送信されたhidden inputを処理）
            self._save_skill_data(instance)
            
            # 複数画像の処理
            self._save_character_images(instance)
        
        return instance
    
    def _save_skill_data(self, character_sheet):
        """技能データの保存処理"""
        from .character_models import CharacterSkill
        
        # 既存の技能データを削除
        CharacterSkill.objects.filter(character_sheet=character_sheet).delete()
        
        # skill_データを探してCharacterSkillを作成
        skill_names = set()
        for key, value in self.data.items():
            if key.startswith('skill_') and key.endswith('_name'):
                skill_id = key.replace('skill_', '').replace('_name', '')
                skill_names.add((skill_id, value))
        
        for skill_id, skill_name in skill_names:
            base_value = self.data.get(f'skill_{skill_id}_base', 0)
            occupation_points = self.data.get(f'skill_{skill_id}_occupation', 0)
            interest_points = self.data.get(f'skill_{skill_id}_interest', 0)
            bonus_points = self.data.get(f'skill_{skill_id}_bonus', 0)
            
            # 数値変換とデフォルト値設定
            try:
                base_value = int(base_value) if base_value else 0
                occupation_points = int(occupation_points) if occupation_points else 0
                interest_points = int(interest_points) if interest_points else 0
                bonus_points = int(bonus_points) if bonus_points else 0
            except (ValueError, TypeError):
                continue  # 無効な値はスキップ
            
            # 何かしらのポイントが設定されている場合のみ保存
            if base_value > 0 or occupation_points > 0 or interest_points > 0 or bonus_points > 0:
                CharacterSkill.objects.create(
                    character_sheet=character_sheet,
                    skill_name=skill_name,
                    base_value=base_value,
                    occupation_points=occupation_points,
                    interest_points=interest_points,
                    other_points=bonus_points
                )
    
    def _save_character_images(self, character_sheet):
        """複数画像の保存処理"""
        from .character_models import CharacterImage
        import logging
        logger = logging.getLogger(__name__)
        
        # フォームから複数画像を取得
        logger.info(f"Available files in form: {list(self.files.keys())}")
        images = self.files.getlist('character_images')
        logger.info(f"Images from getlist: {images}")
        if not images:
            # 単一ファイルとして試す
            single_image = self.files.get('character_images')
            if single_image:
                images = [single_image]
                logger.info(f"Single image found: {single_image}")
            else:
                logger.info(f"No images to save for character_sheet {character_sheet.id}")
                return
        
        # 既存の画像がない場合のみ保存（重複エラーを防ぐ）
        existing_images = CharacterImage.objects.filter(character_sheet=character_sheet)
        if existing_images.exists():
            logger.warning(f"Images already exist for character_sheet {character_sheet.id}. Skipping image save.")
            return
        
        logger.info(f"Saving {len(images)} images for character_sheet {character_sheet.id}")
        
        # 複数画像を保存
        for index, image_file in enumerate(images):
            try:
                CharacterImage.objects.create(
                    character_sheet=character_sheet,
                    image=image_file,
                    is_main=(index == 0),  # 最初の画像をメインに設定
                    order=index
                )
                logger.info(f"Image {index} saved successfully")
            except Exception as e:
                logger.error(f"Error saving image {index}: {str(e)}")
                raise