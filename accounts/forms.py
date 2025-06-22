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
            'hit_points_current': forms.HiddenInput(),
            'magic_points_max': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True
            }),
            'magic_points_current': forms.HiddenInput(),
            'sanity_starting': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True
            }),
            'sanity_max': forms.HiddenInput(),
            'sanity_current': forms.HiddenInput()
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
            'notes': 'メモ'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # プレイヤー名の初期値設定
        if self.user and not self.instance.pk:
            self.initial['player_name'] = self.user.nickname or self.user.username
    
    def clean(self):
        cleaned_data = super().clean()
        
        # 能力値範囲制限を削除 - ユーザーの自由度を向上
        # 6版・7版問わず、幅広い値を許可
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.edition = '6th'  # 強制的に6版に設定
        if self.user:
            instance.user = self.user
        
        # 隠しフィールドから現在値を取得
        # 空文字や '0' の場合も最大値で初期化する
        hit_points_current_value = self.data.get('hit_points_current', '').strip()
        if not hit_points_current_value or hit_points_current_value == '0':
            instance.hit_points_current = instance.hit_points_max
        else:
            instance.hit_points_current = int(hit_points_current_value)
        
        magic_points_current_value = self.data.get('magic_points_current', '').strip()
        if not magic_points_current_value or magic_points_current_value == '0':
            instance.magic_points_current = instance.magic_points_max
        else:
            instance.magic_points_current = int(magic_points_current_value)
        
        sanity_current_value = self.data.get('sanity_current', '').strip()
        if not sanity_current_value or sanity_current_value == '0':
            instance.sanity_current = instance.sanity_starting
        else:
            instance.sanity_current = int(sanity_current_value)
        
        sanity_max_value = self.data.get('sanity_max', '').strip()
        if not sanity_max_value or sanity_max_value == '0':
            instance.sanity_max = instance.sanity_starting
        else:
            instance.sanity_max = int(sanity_max_value)
        
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
        
        # フォームから複数画像を取得
        images = self.files.getlist('character_images')
        if not images:
            return
        
        # 既存の画像を削除（新規作成時）
        if not self.instance.pk:
            CharacterImage.objects.filter(character_sheet=character_sheet).delete()
        
        # 複数画像を保存
        for index, image_file in enumerate(images):
            CharacterImage.objects.create(
                character_sheet=character_sheet,
                image=image_file,
                is_main=(index == 0),  # 最初の画像をメインに設定
                order=index
            )