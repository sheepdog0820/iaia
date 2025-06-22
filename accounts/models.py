"""
Accounts models

This module imports all models from the models package for backwards compatibility.
The actual model definitions are organized in the models/ subdirectory.
"""

# Import all models from the models package
from .models import *

# Import character models directly from character_models module
from .character_models import (
    CharacterSheet,
    CharacterSheet6th,
    CharacterSkill,
    CharacterEquipment,
    CharacterDiceRollSetting,
    CharacterVersionManager,
    CharacterExportManager,
    CharacterSyncManager
)

# Ensure all models are available at this level for backwards compatibility
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
    'CharacterVersionManager',
    'CharacterExportManager',
    'CharacterSyncManager',
]