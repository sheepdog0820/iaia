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

# Import user models
from .user_models import CustomUser, Friend

# Import group models  
from .group_models import Group, GroupMembership, GroupInvitation

# Import character models from parent module (to avoid circular imports)
try:
    from ..character_models import (
        CharacterSheet,
        CharacterSheet6th,
        CharacterSkill,
        CharacterEquipment,
        CharacterDiceRollSetting,
        CharacterImage,
        CharacterVersionManager,
        CharacterExportManager,
        CharacterSyncManager
    )
except ImportError:
    # Fallback for migration/test scenarios
    pass

# Make all models available at package level
__all__ = [
    'TimestampedModel',
    'CustomUser', 
    'Friend',
    'Group',
    'GroupMembership', 
    'GroupInvitation',
    'CharacterSheet',
    'CharacterSheet6th',
    'CharacterSkill',
    'CharacterEquipment',
    'CharacterDiceRollSetting',
    'CharacterImage',
    'CharacterVersionManager',
    'CharacterExportManager',
    'CharacterSyncManager',
]