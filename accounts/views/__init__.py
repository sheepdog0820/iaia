"""
Import all views to maintain compatibility
"""
# Base views and mixins
from .base_views import BaseViewSet, PermissionMixin

# User management views
from .user_views import (
    UserViewSet, FriendViewSet, ProfileView, AddFriendView,
    CustomLoginView, CustomSignUpView, CustomLogoutView,
    ProfileEditView, DashboardView, AccountDeleteView, mock_social_login, demo_login_page
)

# Group management views
from .group_views import GroupViewSet, GroupInvitationViewSet

# Character management views
from .character_views import (
    CharacterSheetViewSet, CharacterSkillViewSet, CharacterEquipmentViewSet,
    CharacterListView, CharacterDetailView, CharacterEditView, Character6thCreateView
)

# For backward compatibility, also provide imports at the module level
__all__ = [
    'BaseViewSet', 'PermissionMixin',
    'UserViewSet', 'FriendViewSet', 'ProfileView', 'AddFriendView',
    'CustomLoginView', 'CustomSignUpView', 'CustomLogoutView',
    'ProfileEditView', 'DashboardView', 'AccountDeleteView', 'mock_social_login', 'demo_login_page',
    'GroupViewSet', 'GroupInvitationViewSet',
    'CharacterSheetViewSet', 'CharacterSkillViewSet', 'CharacterEquipmentViewSet',
    'CharacterListView', 'CharacterDetailView', 'CharacterEditView', 'Character6thCreateView'
]
