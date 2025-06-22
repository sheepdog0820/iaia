"""
Base views and common imports for accounts app
"""
from .common_imports import *


class BaseViewSet(viewsets.ModelViewSet):
    """Base ViewSet with common functionality"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Override to filter by user"""
        return super().get_queryset().filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set user on creation"""
        serializer.save(user=self.request.user)


class PermissionMixin:
    """Mixin for common permission checks"""
    
    def check_admin_permission(self, group, user):
        """Check if user has admin permission for group"""
        from ..models import GroupMembership
        membership = GroupMembership.objects.filter(
            group=group, user=user, role='admin'
        ).first()
        if not membership:
            raise PermissionDenied("この操作には管理者権限が必要です")
        return membership
    
    def check_group_access(self, group, user):
        """Check if user can access group"""
        if group.visibility == 'public':
            return True
        return group.members.filter(id=user.id).exists()