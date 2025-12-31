"""
開発用ログインビュー
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.views import View
from django.conf import settings
from django.core.exceptions import PermissionDenied

User = get_user_model()


class DevLoginView(View):
    """開発環境用のクイックログインビュー"""
    
    def get(self, request):
        # 本番環境では使用不可
        if not settings.DEBUG:
            raise PermissionDenied("This feature is only available in development.")
        
        # テストユーザー一覧
        test_users = [
            {
                'category': 'ゲームマスター',
                'users': [
                    {'username': 'keeper1', 'nickname': '深淵の守護者', 'description': '進行中セッション「悪霊の家」のGM'},
                    {'username': 'keeper2', 'nickname': '古き印の管理人', 'description': '完了セッション「ミスカトニック大学の怪異」のGM'},
                ]
            },
            {
                'category': 'プレイヤー（悪霊の家参加者）',
                'users': [
                    {'username': 'investigator1', 'nickname': '真実の探究者', 'description': '枠1: 佐藤健一（私立探偵）- HO1担当'},
                    {'username': 'investigator2', 'nickname': '闇を見つめる者', 'description': '枠2: 田中美咲（医師）- HO2担当'},
                    {'username': 'investigator3', 'nickname': '古文書の解読者', 'description': '枠3: 山田太郎（大学教授）- HO3担当'},
                    {'username': 'investigator4', 'nickname': '深海の調査員', 'description': '枠4: 鈴木花子（古書店主）- HO4担当'},
                ]
            },
            {
                'category': 'その他のプレイヤー',
                'users': [
                    {'username': 'investigator5', 'nickname': '星の観測者', 'description': 'サラ・ウィリアムズ（天文学者）'},
                    {'username': 'investigator6', 'nickname': '遺跡の発掘者', 'description': '高橋一郎（船員）'},
                ]
            },
            {
                'category': '管理者',
                'users': [
                    {'username': 'admin', 'nickname': '管理者', 'description': 'Django管理画面アクセス可能'},
                ]
            }
        ]
        
        context = {
            'test_users': test_users,
            'current_user': request.user if request.user.is_authenticated else None
        }
        
        return render(request, 'accounts/dev_login.html', context)
    
    def post(self, request):
        # 本番環境では使用不可
        if not settings.DEBUG:
            raise PermissionDenied("This feature is only available in development.")
        
        username = request.POST.get('username')
        if not username:
            messages.error(request, 'ユーザー名が指定されていません。')
            return redirect('dev_login')
        
        try:
            user = User.objects.get(username=username)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'{user.nickname or user.username} としてログインしました。')
            
            # 適切なページにリダイレクト
            next_url = request.GET.get('next') or request.POST.get('next') or '/'
            return redirect(next_url)
            
        except User.DoesNotExist:
            messages.error(request, f'ユーザー {username} が見つかりません。')
            return redirect('dev_login')
