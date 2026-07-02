"""
Import all views to maintain compatibility
"""

# Base views and mixins
from .base_views import BaseViewSet, PermissionMixin
from .billing_views import (
    BillingCancelView,
    BillingPageView,
    BillingSuccessView,
    CheckoutSessionView,
    PortalSessionView,
    RedeemPremiumCodeView,
    StripeWebhookView,
)

# Character management views
from .character_views import (
    Character6thCreateView,
    Character6thDetailView,
    Character7thCreateView,
    CharacterDetailRedirectView,
    CharacterDetailView,
    CharacterEquipmentViewSet,
    CharacterListView,
    CharacterSheetViewSet,
    CharacterSkillViewSet,
)
from .dice_roll_setting_views import DiceRollSettingViewSet

# Group management views
from .group_views import (
    GroupInvitationViewSet,
    GroupInviteLinkCreateView,
    GroupInviteLinkJoinView,
    GroupInviteLinkLandingView,
    GroupInviteLinkRevokeView,
    GroupViewSet,
)

# User management views
from .user_views import (
    AccountDeleteView,
    AddFriendView,
    CustomLoginView,
    CustomLogoutView,
    CustomSignUpView,
    DashboardView,
    FriendViewSet,
    ProfileEditView,
    ProfileView,
    UserViewSet,
    demo_login_page,
    mock_social_login,
)

# For backward compatibility, also provide imports at the module level
__all__ = [
    "BaseViewSet",
    "PermissionMixin",
    "UserViewSet",
    "FriendViewSet",
    "ProfileView",
    "AddFriendView",
    "CustomLoginView",
    "CustomSignUpView",
    "CustomLogoutView",
    "ProfileEditView",
    "DashboardView",
    "AccountDeleteView",
    "mock_social_login",
    "demo_login_page",
    "GroupViewSet",
    "GroupInvitationViewSet",
    "GroupInviteLinkCreateView",
    "GroupInviteLinkRevokeView",
    "GroupInviteLinkLandingView",
    "GroupInviteLinkJoinView",
    "CharacterSheetViewSet",
    "CharacterSkillViewSet",
    "CharacterEquipmentViewSet",
    "CharacterListView",
    "CharacterDetailView",
    "CharacterDetailRedirectView",
    "Character6thDetailView",
    "Character6thCreateView",
    "Character7thCreateView",
    "DiceRollSettingViewSet",
    "BillingPageView",
    "BillingSuccessView",
    "BillingCancelView",
    "CheckoutSessionView",
    "PortalSessionView",
    "RedeemPremiumCodeView",
    "StripeWebhookView",
]
