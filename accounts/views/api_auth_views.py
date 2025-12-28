"""
API用認証ビュー（Google OAuth対応）
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
import requests
import logging

from django.conf import settings
from ..serializers import UserSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """
    Google OAuth認証API
    
    3つの認証方式をサポート:
    1. 認証コード (code)
    2. アクセストークン (access_token)
    3. IDトークン (id_token)
    """
    code = request.data.get('code')
    access_token = request.data.get('access_token')
    id_token_str = request.data.get('id_token')
    
    if not any([code, access_token, id_token_str]):
        return Response({
            'error': '認証情報が提供されていません。code、access_token、またはid_tokenのいずれかを送信してください。'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user_info = None
        
        # 1. IDトークンの処理（推奨）
        if id_token_str:
            logger.info("IDトークンで認証を試行")
            try:
                # IDトークンの検証
                idinfo = id_token.verify_oauth2_token(
                    id_token_str,
                    google_requests.Request(),
                    settings.GOOGLE_OAUTH_CLIENT_ID
                )
                
                # 発行元の確認
                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise ValueError('Wrong issuer.')
                
                user_info = {
                    'email': idinfo.get('email'),
                    'given_name': idinfo.get('given_name', ''),
                    'family_name': idinfo.get('family_name', ''),
                    'name': idinfo.get('name', ''),
                    'picture': idinfo.get('picture', ''),
                    'email_verified': idinfo.get('email_verified', False)
                }
                
            except ValueError as e:
                logger.error(f"IDトークン検証エラー: {e}")
                return Response({
                    'error': 'IDトークンの検証に失敗しました'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. アクセストークンの処理
        elif access_token:
            logger.info("アクセストークンで認証を試行")
            # Google APIでユーザー情報を取得
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code != 200:
                return Response({
                    'error': 'アクセストークンが無効です'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            data = response.json()
            user_info = {
                'email': data.get('email'),
                'given_name': data.get('given_name', ''),
                'family_name': data.get('family_name', ''),
                'name': data.get('name', ''),
                'picture': data.get('picture', ''),
                'email_verified': data.get('verified_email', False)
            }
        
        # 3. 認証コードの処理
        elif code:
            logger.info("認証コードで認証を試行")
            # OAuth2フローを使用してトークンを取得
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
            
            # リダイレクトURIを設定（フロントエンドのURL）
            flow.redirect_uri = request.data.get('redirect_uri', 'http://localhost:3000')
            
            try:
                # 認証コードをトークンに交換
                flow.fetch_token(code=code)
                credentials = flow.credentials
                
                # IDトークンから情報を取得
                idinfo = id_token.verify_oauth2_token(
                    credentials.id_token,
                    google_requests.Request(),
                    settings.GOOGLE_OAUTH_CLIENT_ID
                )
                
                user_info = {
                    'email': idinfo.get('email'),
                    'given_name': idinfo.get('given_name', ''),
                    'family_name': idinfo.get('family_name', ''),
                    'name': idinfo.get('name', ''),
                    'picture': idinfo.get('picture', ''),
                    'email_verified': idinfo.get('email_verified', False)
                }
                
            except Exception as e:
                logger.error(f"認証コード交換エラー: {e}")
                return Response({
                    'error': '認証コードの処理に失敗しました'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # メールアドレスの確認
        if not user_info or not user_info.get('email'):
            return Response({
                'error': 'メールアドレスが取得できませんでした'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # メール認証の確認（オプション）
        if not user_info.get('email_verified', True):
            return Response({
                'error': 'メールアドレスが認証されていません'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ユーザーの取得または作成
        email = user_info['email']
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': user_info.get('given_name', ''),
                'last_name': user_info.get('family_name', ''),
                'nickname': user_info.get('name', email.split('@')[0]),
            }
        )
        
        # 既存ユーザーの情報更新（必要に応じて）
        if not created:
            updated = False
            if not user.nickname and user_info.get('name'):
                user.nickname = user_info['name']
                updated = True
            if not user.first_name and user_info.get('given_name'):
                user.first_name = user_info['given_name']
                updated = True
            if not user.last_name and user_info.get('family_name'):
                user.last_name = user_info['family_name']
                updated = True
            
            if updated:
                user.save()
        
        # DRFトークンの生成
        token, _ = Token.objects.get_or_create(user=user)
        
        # レスポンスデータ
        response_data = {
            'token': token.key,
            'user': UserSerializer(user).data,
            'created': created
        }
        
        logger.info(f"Google OAuth認証成功: {email} (新規: {created})")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Google OAuth認証エラー: {e}")
        return Response({
            'error': '認証処理中にエラーが発生しました',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    現在のユーザー情報を取得
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    ログアウト（トークン削除）
    """
    try:
        # トークンを削除
        request.user.auth_token.delete()
        return Response({
            'message': 'ログアウトしました'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'ログアウト処理中にエラーが発生しました'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
