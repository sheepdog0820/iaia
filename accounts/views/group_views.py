"""
Group management views
"""
from .common_imports import *
from .base_views import PermissionMixin
from .mixins import GroupAccessMixin, ErrorHandlerMixin


class GroupViewSet(GroupAccessMixin, ErrorHandlerMixin, PermissionMixin, viewsets.ModelViewSet):
    """Group management ViewSet with permission checks"""
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get groups accessible to current user"""
        # 参加中のグループ + 公開グループ（重複除去）
        return Group.objects.filter(
            Q(members=self.request.user) | Q(visibility='public')
        ).distinct()
    
    def get_object(self):
        """Override to add permission checks"""
        obj = super().get_object()
        
        # アクション別の権限チェック
        action = getattr(self, 'action', None)
        
        # 管理者のみアクセス可能なアクション
        admin_only_actions = ['update', 'partial_update', 'destroy', 'invite', 'remove_member']
        if action in admin_only_actions:
            self.check_admin_permission(obj, self.request.user)
        
        # グループアクセス権チェック
        elif not self.check_group_access(obj, self.request.user):
            raise Http404("Group not found")
        
        return obj
    
    def perform_create(self, serializer):
        """Set creator and add as admin member"""
        group = serializer.save(created_by=self.request.user)
        # Create admin membership
        GroupMembership.objects.create(
            user=self.request.user,
            group=group,
            role='admin'
        )
    
    @action(detail=False, methods=['get'])
    def public(self, request):
        """Get public groups"""
        public_groups = Group.objects.filter(visibility='public')
        query = request.query_params.get('q', '').strip()
        if query:
            public_groups = public_groups.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        serializer = self.get_serializer(public_groups, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def private(self, request):
        """Get user's private groups"""
        private_groups = Group.objects.filter(
            members=request.user,
            visibility='private'
        )
        serializer = self.get_serializer(private_groups, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a public group"""
        group = self.get_object()
        
        if group.visibility != 'public':
            return Response(
                {'error': 'このグループは招待制です'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already a member
        if GroupMembership.objects.filter(user=request.user, group=group).exists():
            return Response(
                {'error': '既にメンバーです'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add as member
        GroupMembership.objects.create(
            user=request.user,
            group=group,
            role='member'
        )
        
        return Response({'success': True}, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def all_groups(self, request):
        """Get all groups (joined + public)"""
        groups = self.get_queryset()
        query = request.query_params.get('q', '').strip()
        if query:
            groups = groups.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search public groups by keyword"""
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response([])
        groups = Group.objects.filter(visibility='public').filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get group members"""
        group = self.get_object()
        memberships = GroupMembership.objects.filter(group=group)
        serializer = GroupMembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def member_characters(self, request, pk=None):
        """Get group members and their available character sheets"""
        group = self.get_object()

        if not group.members.filter(id=request.user.id).exists():
            return Response(
                {'error': 'このグループに参加していません'},
                status=status.HTTP_403_FORBIDDEN
            )

        target_user_id = request.query_params.get('user_id')
        memberships = GroupMembership.objects.filter(group=group).select_related('user')

        if target_user_id:
            memberships = memberships.filter(user_id=target_user_id)
            if not memberships.exists():
                return Response(
                    {'error': '対象ユーザーがグループに存在しません'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        results = []
        for membership in memberships:
            member = membership.user
            character_queryset = CharacterSheet.objects.filter(
                user=member,
                is_active=True
            ).order_by('-updated_at')

            if member.id != request.user.id:
                character_queryset = character_queryset.filter(is_public=True)

            characters = [
                {
                    'id': sheet.id,
                    'name': sheet.name,
                    'edition': sheet.edition,
                    'is_public': sheet.is_public,
                    'is_active': sheet.is_active
                }
                for sheet in character_queryset
            ]

            results.append({
                'user_id': member.id,
                'username': member.username,
                'nickname': member.nickname,
                'role': membership.role,
                'characters': characters
            })

        return Response(results)
    
    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """Invite user to group (admin only)"""
        group = self.get_object()
        
        try:
            GroupInvitation.expire_pending()

            invitee_ids = request.data.get('invitee_ids')
            if isinstance(invitee_ids, str):
                invitee_ids = [invitee_ids]
            message = request.data.get('message', '')
            invitations = []
            skipped = []

            if invitee_ids:
                for raw_id in invitee_ids:
                    try:
                        invitee = CustomUser.objects.get(id=raw_id)
                    except CustomUser.DoesNotExist:
                        skipped.append({'invitee_id': raw_id, 'reason': 'not_found'})
                        continue

                    if GroupMembership.objects.filter(user=invitee, group=group).exists():
                        skipped.append({'invitee_id': raw_id, 'reason': 'already_member'})
                        continue

                    invitation = GroupInvitation.objects.filter(group=group, invitee=invitee).first()
                    if invitation and invitation.status == 'pending':
                        skipped.append({'invitee_id': raw_id, 'reason': 'already_invited'})
                        continue

                    if invitation:
                        invitation.status = 'pending'
                        invitation.inviter = request.user
                        invitation.message = message
                        invitation.created_at = timezone.now()
                        invitation.responded_at = None
                        invitation.save()
                    else:
                        invitation = GroupInvitation.objects.create(
                            group=group,
                            inviter=request.user,
                            invitee=invitee,
                            message=message
                        )

                    invitations.append(invitation)

                serializer = GroupInvitationSerializer(invitations, many=True)
                return Response(
                    {
                        'count': len(invitations),
                        'results': serializer.data,
                        'skipped': skipped
                    },
                    status=status.HTTP_201_CREATED
                )

            username = request.data.get('username')
            user_id = request.data.get('user_id')
            if user_id:
                invitee = CustomUser.objects.get(id=user_id)
            else:
                invitee = CustomUser.objects.get(username=username)

            if GroupMembership.objects.filter(user=invitee, group=group).exists():
                return Response(
                    {'error': '既にメンバーです'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            invitation = GroupInvitation.objects.filter(group=group, invitee=invitee).first()
            if invitation and invitation.status == 'pending':
                return Response(
                    {'error': '既に招待済みです'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if invitation:
                invitation.status = 'pending'
                invitation.inviter = request.user
                invitation.message = message
                invitation.created_at = timezone.now()
                invitation.responded_at = None
                invitation.save()
            else:
                invitation = GroupInvitation.objects.create(
                    group=group,
                    inviter=request.user,
                    invitee=invitee,
                    message=message
                )

            serializer = GroupInvitationSerializer(invitation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'ユーザーが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave group"""
        group = self.get_object()
        
        try:
            membership = GroupMembership.objects.get(user=request.user, group=group)
            membership.delete()
            return Response({'success': True}, status=status.HTTP_200_OK)
        except GroupMembership.DoesNotExist:
            return Response(
                {'error': 'メンバーではありません'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """Remove member from group (admin only)"""
        group = self.get_object()
        
        try:
            username = request.data.get('username')
            user = CustomUser.objects.get(username=username)
            membership = GroupMembership.objects.get(user=user, group=group)
            
            # Cannot remove group creator
            if user == group.created_by:
                return Response(
                    {'error': 'グループ作成者は除名できません'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            membership.delete()
            return Response({'success': True}, status=status.HTTP_200_OK)
            
        except (CustomUser.DoesNotExist, GroupMembership.DoesNotExist):
            return Response(
                {'error': 'メンバーが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )


class GroupInvitationViewSet(viewsets.ModelViewSet):
    """Group invitation management ViewSet"""
    serializer_class = GroupInvitationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get invitations for current user"""
        GroupInvitation.expire_pending()
        return GroupInvitation.objects.filter(invitee=self.request.user)
    
    def perform_create(self, serializer):
        """Set inviter automatically"""
        serializer.save(inviter=self.request.user)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept group invitation"""
        invitation = self.get_object()
        
        if invitation.status != 'pending':
            return Response(
                {'error': '招待は既に処理されています'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if invitation.is_expired:
            invitation.mark_expired()
            return Response(
                {'error': '招待の期限が切れています'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already a member
        if GroupMembership.objects.filter(
            user=invitation.invitee, 
            group=invitation.group
        ).exists():
            return Response(
                {'error': '既にメンバーです'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create membership
        GroupMembership.objects.create(
            user=invitation.invitee,
            group=invitation.group,
            role='member'
        )
        
        # Update invitation status
        invitation.status = 'accepted'
        invitation.responded_at = timezone.now()
        invitation.save()
        
        return Response({'success': True}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline group invitation"""
        invitation = self.get_object()
        
        if invitation.status != 'pending':
            return Response(
                {'error': '招待は既に処理されています'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if invitation.is_expired:
            invitation.mark_expired()
            return Response(
                {'error': '招待の期限が切れています'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update invitation status
        invitation.status = 'declined'
        invitation.responded_at = timezone.now()
        invitation.save()
        
        return Response({'success': True}, status=status.HTTP_200_OK)
