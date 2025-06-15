from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.contrib.auth import authenticate
from .models import CustomUser, CharacterSheet, CharacterSheet6th


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
    
    class Meta:
        model = CharacterSheet
        fields = [
            'name', 'player_name', 'age', 'gender', 'occupation', 
            'birthplace', 'residence', 'str_value', 'con_value', 
            'pow_value', 'dex_value', 'app_value', 'siz_value', 
            'int_value', 'edu_value', 'notes'
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
                'min': 3,
                'max': 18,
                'placeholder': 'STR',
                'required': True
            }),
            'con_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 3,
                'max': 18,
                'placeholder': 'CON',
                'required': True
            }),
            'pow_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 3,
                'max': 18,
                'placeholder': 'POW',
                'required': True
            }),
            'dex_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 3,
                'max': 18,
                'placeholder': 'DEX',
                'required': True
            }),
            'app_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 3,
                'max': 18,
                'placeholder': 'APP',
                'required': True
            }),
            'siz_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 8,
                'max': 18,
                'placeholder': 'SIZ',
                'required': True
            }),
            'int_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 3,
                'max': 18,
                'placeholder': 'INT',
                'required': True
            }),
            'edu_value': forms.NumberInput(attrs={
                'class': 'form-control ability-input',
                'min': 3,
                'max': 18,
                'placeholder': 'EDU',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '探索者の背景や特徴'
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
        
        # 6版の能力値範囲チェック
        ability_fields = ['str_value', 'con_value', 'pow_value', 'dex_value', 
                         'app_value', 'int_value', 'edu_value']
        for field in ability_fields:
            value = cleaned_data.get(field)
            if value is not None and (value < 3 or value > 18):
                self.add_error(field, f'{self.fields[field].label}は3-18の範囲で入力してください（6版ルール）')
        
        # SIZの特別範囲チェック
        siz_value = cleaned_data.get('siz_value')
        if siz_value is not None and (siz_value < 8 or siz_value > 18):
            self.add_error('siz_value', '体格(SIZ)は8-18の範囲で入力してください（6版ルール）')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.edition = '6th'  # 強制的に6版に設定
        if self.user:
            instance.user = self.user
        
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
        
        return instance