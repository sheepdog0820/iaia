"""
GMハンドアウト管理機能
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import TRPGSession, SessionParticipant, HandoutInfo
from .serializers import HandoutInfoSerializer, SessionParticipantSerializer


class GMHandoutManagementView(APIView):
    """GM専用ハンドアウト管理ビュー"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        """ハンドアウト管理画面の表示"""
        session = get_object_or_404(TRPGSession, id=session_id)
        
        # GM権限チェック
        if session.gm != request.user:
            if 'application/json' in request.headers.get('Accept', ''):
                return Response({'error': 'GM権限が必要です'}, status=status.HTTP_403_FORBIDDEN)
            else:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("GM権限が必要です")
        
        if 'application/json' in request.headers.get('Accept', ''):
            return self._get_json_response(session)
        else:
            return self._get_html_response(request, session)
    
    def _get_json_response(self, session):
        """JSON形式でハンドアウト管理データを返す"""
        participants = SessionParticipant.objects.filter(session=session).select_related('user')
        handouts = HandoutInfo.objects.filter(session=session).select_related('participant__user')
        
        # 参加者ごとにハンドアウトを整理
        participant_handouts = {}
        for participant in participants:
            participant_handouts[participant.id] = {
                'participant': SessionParticipantSerializer(participant).data,
                'handouts': []
            }
        
        # ハンドアウトを参加者別に分類
        for handout in handouts:
            participant_id = handout.participant.id
            if participant_id in participant_handouts:
                participant_handouts[participant_id]['handouts'].append(
                    HandoutInfoSerializer(handout).data
                )
        
        return Response({
            'session_id': session.id,
            'session_title': session.title,
            'participants': list(participant_handouts.values()),
            'handout_count': handouts.count()
        })
    
    def _get_html_response(self, request, session):
        """HTML形式でハンドアウト管理画面を返す"""
        participants = SessionParticipant.objects.filter(session=session).select_related('user')
        handouts = HandoutInfo.objects.filter(session=session).select_related('participant__user')
        
        context = {
            'session': session,
            'participants': participants,
            'handouts': handouts,
            'handout_count': handouts.count()
        }
        
        return render(request, 'schedules/gm_handout_management.html', context)


class HandoutManagementViewSet(viewsets.ModelViewSet):
    """ハンドアウト管理API"""
    serializer_class = HandoutInfoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # GMとしてのセッションのハンドアウト、または自分宛のハンドアウト
        return HandoutInfo.objects.filter(
            Q(session__gm=user) | Q(participant__user=user)
        ).distinct().select_related('session', 'participant__user')
    
    def perform_create(self, serializer):
        """ハンドアウト作成（GM権限チェック）"""
        session = serializer.validated_data['session']
        if session.gm != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("GM権限が必要です")
        serializer.save()
    
    def perform_update(self, serializer):
        """ハンドアウト更新（GM権限チェック）"""
        instance = self.get_object()
        if instance.session.gm != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("GM権限が必要です")
        serializer.save()
    
    def perform_destroy(self, instance):
        """ハンドアウト削除（GM権限チェック）"""
        if instance.session.gm != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("GM権限が必要です")
        instance.delete()
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """複数ハンドアウト一括作成"""
        session_id = request.data.get('session_id')
        handouts_data = request.data.get('handouts', [])
        
        if not session_id:
            return Response({'error': 'session_idが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        
        session = get_object_or_404(TRPGSession, id=session_id)
        
        # GM権限チェック
        if session.gm != request.user:
            return Response({'error': 'GM権限が必要です'}, status=status.HTTP_403_FORBIDDEN)
        
        created_handouts = []
        errors = []
        
        for handout_data in handouts_data:
            # handout_dataがdict型であることを確認してからsessionを設定
            if isinstance(handout_data, dict):
                handout_data['session'] = session.id
            else:
                errors.append({
                    'data': handout_data,
                    'errors': {'non_field_errors': ['Invalid data format']}
                })
                continue
                
            serializer = HandoutInfoSerializer(data=handout_data)
            
            if serializer.is_valid():
                handout = serializer.save()
                created_handouts.append(serializer.data)
            else:
                errors.append({
                    'data': handout_data,
                    'errors': serializer.errors
                })
        
        return Response({
            'created': created_handouts,
            'errors': errors,
            'created_count': len(created_handouts),
            'error_count': len(errors)
        }, status=status.HTTP_201_CREATED if created_handouts else status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_session(self, request):
        """セッション別ハンドアウト取得"""
        session_id = request.query_params.get('session_id')
        
        if not session_id:
            return Response({'error': 'session_idが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        
        session = get_object_or_404(TRPGSession, id=session_id)
        
        # アクセス権限チェック
        user = request.user
        if session.gm != user and not session.participants.filter(id=user.id).exists():
            return Response({'error': 'このセッションにアクセスする権限がありません'}, status=status.HTTP_403_FORBIDDEN)
        
        # GMの場合は全てのハンドアウト、参加者の場合は自分のハンドアウトのみ
        if session.gm == user:
            handouts = HandoutInfo.objects.filter(session=session)
        else:
            user_participant = SessionParticipant.objects.filter(session=session, user=user).first()
            if user_participant:
                handouts = HandoutInfo.objects.filter(participant=user_participant)
            else:
                handouts = HandoutInfo.objects.none()
        
        serializer = HandoutInfoSerializer(handouts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def toggle_visibility(self, request):
        """ハンドアウトの公開/秘匿切り替え"""
        handout_id = request.data.get('handout_id')
        
        if not handout_id:
            return Response({'error': 'handout_idが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        
        handout = get_object_or_404(HandoutInfo, id=handout_id)
        
        # GM権限チェック
        if handout.session.gm != request.user:
            return Response({'error': 'GM権限が必要です'}, status=status.HTTP_403_FORBIDDEN)
        
        # 秘匿フラグを切り替え
        handout.is_secret = not handout.is_secret
        handout.save()
        
        serializer = HandoutInfoSerializer(handout)
        return Response({
            'handout': serializer.data,
            'message': f'ハンドアウトを{"秘匿" if handout.is_secret else "公開"}に設定しました'
        })


class HandoutTemplateView(APIView):
    """ハンドアウトテンプレート管理"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """利用可能なハンドアウトテンプレート一覧"""
        templates = [
            {
                'id': 'basic_intro',
                'name': '基本ハンドアウト',
                'description': 'キャラクターの基本情報と導入',
                'template': '''【あなたは〇〇です】

年齢：
職業：
特技：

【導入】
あなたは〇〇〇について調査するために、この場所を訪れました。

【秘密】
あなたには以下の秘密があります。
・〇〇〇

【特殊ルール】
・〇〇〇の場合、〇〇〇してください。'''
            },
            {
                'id': 'investigation',
                'name': '調査ハンドアウト',
                'description': '調査系シナリオ用のハンドアウト',
                'template': '''【調査情報】

目的：〇〇〇を調査する

【手がかり】
・〇〇〇
・〇〇〇

【注意事項】
・〇〇〇には注意してください
・〇〇〇の情報は他の探索者と共有しないでください

【報酬】
成功時：〇〇〇'''
            },
            {
                'id': 'relationship',
                'name': '関係性ハンドアウト',
                'description': 'PC間の関係性を定義',
                'template': '''【あなたと他のPCとの関係】

〇〇（PC名）との関係：
・〇〇〇

〇〇（PC名）との関係：
・〇〇〇

【共通の目的】
あなたたちは〇〇〇のために協力しています。

【秘密の関係】
※他のPCには明かしてはいけません
・〇〇〇'''
            }
        ]
        
        return Response({'templates': templates})
    
    def post(self, request):
        """テンプレートからハンドアウトを生成"""
        template_id = request.data.get('template_id')
        session_id = request.data.get('session_id')
        participant_id = request.data.get('participant_id')
        customizations = request.data.get('customizations', {})
        
        if not all([template_id, session_id, participant_id]):
            return Response(
                {'error': 'template_id, session_id, participant_idが必要です'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session = get_object_or_404(TRPGSession, id=session_id)
        participant = get_object_or_404(SessionParticipant, id=participant_id)
        
        # GM権限チェック
        if session.gm != request.user:
            return Response({'error': 'GM権限が必要です'}, status=status.HTTP_403_FORBIDDEN)
        
        # テンプレート取得（実際の実装では上記のテンプレートを使用）
        templates = {
            'basic_intro': '基本ハンドアウトテンプレート...',
            'investigation': '調査ハンドアウトテンプレート...',
            'relationship': '関係性ハンドアウトテンプレート...'
        }
        
        template_content = templates.get(template_id, '')
        
        # カスタマイズの適用
        for key, value in customizations.items():
            if key not in ['title', 'is_secret']:  # これらはハンドアウト作成時に直接使用
                template_content = template_content.replace(f'{{{{ {key} }}}}', str(value))
        
        # ハンドアウト作成
        handout_data = {
            'session': session.id,
            'participant': participant.id,
            'title': customizations.get('title', f'{participant.user.nickname}のハンドアウト'),
            'content': template_content,
            'is_secret': customizations.get('is_secret', True)
        }
        
        serializer = HandoutInfoSerializer(data=handout_data)
        if serializer.is_valid():
            handout = serializer.save()
            return Response(HandoutInfoSerializer(handout).data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)