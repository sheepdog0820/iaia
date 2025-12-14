"""
Google OAuth認証ビュー（8000番ポート統一版）
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
import logging
import json

from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


def google_login(request):
    """Google OAuth認証開始ページ"""
    # Google OAuth2フローの設定
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            }
        },
        scopes=['openid', 'email', 'profile']
    )
    
    # リダイレクトURIを設定（8000番ポート）
    flow.redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    
    # 認証URLを生成
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    
    # stateをセッションに保存（CSRF対策）
    request.session['oauth_state'] = state
    
    context = {
        'authorization_url': authorization_url,
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID[:20] + '...',
    }
    
    return render(request, 'accounts/google_login.html', context)


def google_callback(request):
    """Google OAuth認証コールバック"""
    # エラーチェック
    error = request.GET.get('error')
    if error:
        messages.error(request, f'Google認証エラー: {error}')
        return redirect('login')
    
    # 認証コードを取得
    code = request.GET.get('code')
    if not code:
        messages.error(request, '認証コードが取得できませんでした')
        return redirect('login')
    
    # stateの検証（CSRF対策）
    state = request.GET.get('state')
    saved_state = request.session.get('oauth_state')
    
    # デバッグ情報をログに記録
    logger.info(f"OAuth callback - Received state: {state}")
    logger.info(f"OAuth callback - Saved state: {saved_state}")
    logger.info(f"OAuth callback - Session key: {request.session.session_key}")
    
    if not saved_state:
        logger.warning("No saved state in session!")
        # 開発環境では警告のみ表示して処理を続行
        if settings.DEBUG:
            messages.warning(request, 'セッション警告: stateが保存されていません（開発モード）')
        else:
            messages.error(request, 'セキュリティエラー: 無効なstate')
            return redirect('login')
    elif state != saved_state:
        logger.warning(f"State mismatch! Received: {state}, Saved: {saved_state}")
        # 開発環境では警告のみ表示して処理を続行
        if settings.DEBUG:
            messages.warning(request, 'セッション警告: stateが一致しません（開発モード）')
        else:
            messages.error(request, 'セキュリティエラー: 無効なstate')
            return redirect('login')
    
    try:
        # Google OAuth2フローの設定
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                }
            },
            scopes=['openid', 'email', 'profile'],
            state=state
        )
        
        # リダイレクトURIを設定
        flow.redirect_uri = request.build_absolute_uri(reverse('google_callback'))
        
        # 認証コードをアクセストークンに交換
        flow.fetch_token(code=code)
        
        # 認証情報を取得
        credentials = flow.credentials
        
        # IDトークンの検証
        idinfo = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID
        )
        
        # ユーザー情報を取得
        email = idinfo.get('email')
        if not email:
            messages.error(request, 'メールアドレスが取得できませんでした')
            return redirect('login')
        
        # ユーザーの取得または作成
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'nickname': idinfo.get('name', email.split('@')[0]),
            }
        )
        
        # 既存ユーザーの情報更新
        if not created and not user.nickname:
            user.nickname = idinfo.get('name', email.split('@')[0])
            user.save()
        
        # ログイン
        login(request, user)
        
        if created:
            messages.success(request, f'新規アカウントを作成しました: {email}')
        else:
            messages.success(request, f'ログインしました: {email}')
        
        # 認証成功ページへリダイレクト
        return redirect('google_auth_success')
        
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        messages.error(request, f'認証エラー: {str(e)}')
        return redirect('login')


def google_auth_success(request):
    """認証成功ページ"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # APIトークンを生成（必要な場合）
    from rest_framework.authtoken.models import Token
    token, created = Token.objects.get_or_create(user=request.user)
    
    context = {
        'user': request.user,
        'api_token': token.key,
        'is_new_token': created,
    }
    
    return render(request, 'accounts/google_auth_success.html', context)


def google_auth_test(request):
    """Google認証テストページ（開発用）"""
    context = {
        'google_auth_url': reverse('google_login'),
        'api_endpoint': '/api/auth/google/',
        'redirect_uri': request.build_absolute_uri(reverse('google_callback')),
    }
    
    return render(request, 'accounts/google_auth_test.html', context)