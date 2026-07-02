"""
共通インポート - コード重複の共通化
"""

# Third-party imports
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404

# Django core imports
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView

# Django REST Framework imports
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..character_models import (
    CharacterBackground,
    CharacterEquipment,
    CharacterImage,
    CharacterSheet,
    CharacterSheet6th,
    CharacterSkill,
    GrowthRecord,
    SkillGrowthRecord,
)

# Local imports - forms
from ..forms import CharacterSheet6thForm, CustomLoginForm, CustomSignUpForm, ProfileEditForm

# Local imports - models
from ..models import CustomUser, Friend, Group, GroupInvitation, GroupInviteLink, GroupMembership

# Local imports - serializers
from ..serializers import (
    CharacterEquipmentSerializer,
    CharacterSheet6thSerializer,
    CharacterSheetCreateSerializer,
    CharacterSheetListSerializer,
    CharacterSheetSerializer,
    CharacterSheetUpdateSerializer,
    CharacterSkillSerializer,
    FriendDetailSerializer,
    FriendSerializer,
    GroupInvitationSerializer,
    GroupMembershipSerializer,
    GroupSerializer,
    UserSerializer,
)
from ..utils.statistics import (
    CharacterStatistics,
    ExportStatistics,
    GroupStatistics,
    SessionStatistics,
    TindalosMetrics,
)

# Local imports - mixins and utilities
from .mixins import (
    BulkOperationMixin,
    CharacterNestedResourceMixin,
    CharacterSheetAccessMixin,
    CommonQuerysetMixin,
    ErrorHandlerMixin,
    GroupAccessMixin,
    UserOwnershipMixin,
)

# Common variables
User = get_user_model()

# Common choices and constants
SKILL_CATEGORIES = [
    ("探索系", "探索系"),
    ("対人系", "対人系"),
    ("戦闘系", "戦闘系"),
    ("知識系", "知識系"),
    ("技術系", "技術系"),
    ("行動系", "行動系"),
    ("言語系", "言語系"),
    ("特殊・その他", "特殊・その他"),
]

CHARACTER_EDITIONS = [
    ("6th", "6版"),
]

GROUP_VISIBILITY_CHOICES = [
    ("public", "公開"),
    ("private", "プライベート"),
]

GROUP_ROLE_CHOICES = [
    ("admin", "管理者"),
    ("member", "メンバー"),
]
