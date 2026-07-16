"""
Accounts models package

This package contains all models for the accounts app, organized by functionality:
- base_models: Base classes and common imports
- user_models: User and Friend models
- group_models: Group, GroupMembership, GroupInvitation models
- character_models: Character sheet related models (imported from parent)
"""

# Import base models
from .base_models import TimestampedModel
from .billing_models import (
    PremiumAccessCode,
    PremiumAccessCodeRedemption,
    PremiumAuditLog,
    PremiumSubscription,
    StripeWebhookEvent,
)

# Import group models
from .group_models import (
    DiscordDelivery,
    Group,
    GroupDiscordSettings,
    GroupInvitation,
    GroupInviteLink,
    GroupLink,
    GroupLinkShare,
    GroupMembership,
)
from .share_models import ShareLink

# Import user models
from .user_models import CustomUser, Friend

# Import character models from parent module (to avoid circular imports)
try:
    from ..character_models import (
        CharacterDiceRollSetting,
        CharacterEquipment6th,
        CharacterEquipment7th,
        CharacterExportManager,
        CharacterImage6th,
        CharacterImage7th,
        CharacterSheet,
        CharacterSheet6th,
        CharacterSheet7th,
        CharacterSkill6th,
        CharacterSkill7th,
        CharacterSyncManager,
        CharacterVersionManager,
    )
except ImportError:
    # Fallback for migration/test scenarios
    pass

# Make all models available at package level
__all__ = [
    "TimestampedModel",
    "CustomUser",
    "Friend",
    "PremiumSubscription",
    "StripeWebhookEvent",
    "PremiumAccessCode",
    "PremiumAccessCodeRedemption",
    "PremiumAuditLog",
    "Group",
    "GroupMembership",
    "GroupInvitation",
    "GroupInviteLink",
    "GroupDiscordSettings",
    "DiscordDelivery",
    "GroupLink",
    "GroupLinkShare",
    "ShareLink",
    "CharacterSheet",
    "CharacterSheet6th",
    "CharacterSheet7th",
    "CharacterSkill6th",
    "CharacterSkill7th",
    "CharacterEquipment6th",
    "CharacterEquipment7th",
    "CharacterDiceRollSetting",
    "CharacterImage6th",
    "CharacterImage7th",
    "CharacterVersionManager",
    "CharacterExportManager",
    "CharacterSyncManager",
]
