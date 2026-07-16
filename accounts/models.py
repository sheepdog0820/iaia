"""
Accounts models

This module imports all models from the models package for backwards compatibility.
The actual model definitions are organized in the models/ subdirectory.
"""

# Import character models directly from character_models module
from .character_models import (
    CharacterDiceRollSetting,
    CharacterExportManager,
    CharacterSheet,
    CharacterSheet6th,
    CharacterSyncManager,
    CharacterVersionManager,
)

# Import all models from the models package
from .models import *

# Ensure all models are available at this level for backwards compatibility
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
    "CharacterSheet",
    "CharacterSheet6th",
    "CharacterDiceRollSetting",
    "CharacterVersionManager",
    "CharacterExportManager",
    "CharacterSyncManager",
]
