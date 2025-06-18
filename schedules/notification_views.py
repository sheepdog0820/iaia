"""
TRPGセッション管理システム - ハンドアウト通知API

ハンドアウト通知の一覧取得、既読管理、設定管理のAPIを提供します。
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from .models import HandoutNotification, UserNotificationPreferences
from .notifications import HandoutNotificationService
from .serializers import (
    HandoutNotificationSerializer, 
    UserNotificationPreferencesSerializer
)


class HandoutNotificationPagination(PageNumberPagination):
    """ハンドアウト通知用ページネーション"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class HandoutNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ハンドアウト通知ViewSet"""
    
    serializer_class = HandoutNotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HandoutNotificationPagination
    
    def get_queryset(self):
        """ユーザーの通知のみを取得"""
        return HandoutNotification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """通知一覧取得（未読フィルター対応）"""
        queryset = self.get_queryset()
        
        # 未読フィルター
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def mark_read(self, request, pk=None):
        """通知を既読にマーク"""
        notification = get_object_or_404(
            HandoutNotification,
            id=pk,
            recipient=request.user
        )
        
        notification.mark_as_read()
        
        return Response({
            'status': 'success',
            'message': '通知を既読にマークしました'
        })
    
    @action(detail=False, methods=['patch'])
    def mark_all_read(self, request):
        """全通知を既読にマーク"""
        updated_count = HandoutNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'status': 'success',
            'message': f'{updated_count}件の通知を既読にマークしました',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """未読通知数を取得"""
        count = HandoutNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return Response({
            'unread_count': count
        })


class UserNotificationPreferencesViewSet(viewsets.ModelViewSet):
    """ユーザー通知設定ViewSet"""
    
    serializer_class = UserNotificationPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """現在のユーザーの通知設定を取得"""
        return UserNotificationPreferences.get_or_create_for_user(
            self.request.user
        )
    
    def list(self, request, *args, **kwargs):
        """通知設定一覧（実際は現在のユーザーの設定のみ）"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """通知設定取得"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """通知設定更新"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'status': 'success',
            'message': '通知設定を更新しました',
            'data': serializer.data
        })
    
    def partial_update(self, request, *args, **kwargs):
        """通知設定部分更新"""
        return self.update(request, *args, **kwargs)


class HandoutNotificationAPIView:
    """ハンドアウト通知関連のユーティリティビュー"""
    
    @staticmethod
    def send_test_notification(request):
        """テスト通知送信（開発用）"""
        if not request.user.is_authenticated:
            return Response(
                {'error': '認証が必要です'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # テスト通知作成
        notification = HandoutNotification.objects.create(
            handout_id=0,  # テスト用ダミー
            recipient=request.user,
            sender=request.user,
            notification_type='handout_created',
            message='これはテスト通知です',
            is_read=False
        )
        
        serializer = HandoutNotificationSerializer(notification)
        return Response({
            'status': 'success',
            'message': 'テスト通知を送信しました',
            'notification': serializer.data
        })