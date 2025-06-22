"""
Backward compatibility import for accounts.views
All views are now organized in the views/ module
"""
# Import all views from the modularized structure for backward compatibility
from .views.user_views import *
from .views.group_views import *
from .views.character_views import *
from .views.base_views import *

# This file maintains backward compatibility while all actual implementations
# are now in the views/ subdirectory following proper modular structure