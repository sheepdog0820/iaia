"""
共通インポート - コード重複の共通化
"""

# Django core imports
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, FormView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import models
from django.db.models import Q, Sum, Count, Avg
from django.http import Http404
from django.core.exceptions import ValidationError

# Django REST Framework imports
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError

# Third-party imports
from allauth.socialaccount.models import SocialAccount

# Local imports - models
from ..models import CustomUser, Friend, Group, GroupMembership, GroupInvitation
from ..character_models import CharacterSheet, CharacterSheet6th, CharacterSkill, CharacterEquipment, CharacterImage, CharacterBackground, GrowthRecord, SkillGrowthRecord

# Local imports - serializers
from ..serializers import (
    UserSerializer, FriendSerializer, GroupSerializer, GroupMembershipSerializer,
    GroupInvitationSerializer, FriendDetailSerializer,
    CharacterSheetSerializer, CharacterSheetCreateSerializer,
    CharacterSheetListSerializer, CharacterSheetUpdateSerializer,
    CharacterSkillSerializer, CharacterEquipmentSerializer,
    CharacterSheet6thSerializer
)

# Local imports - forms
from ..forms import CustomLoginForm, CustomSignUpForm, ProfileEditForm, CharacterSheet6thForm

# Local imports - mixins and utilities
from .mixins import (
    UserOwnershipMixin, CharacterSheetAccessMixin, CharacterNestedResourceMixin,
    ErrorHandlerMixin, GroupAccessMixin, CommonQuerysetMixin, BulkOperationMixin
)
from ..utils.statistics import (
    SessionStatistics, CharacterStatistics, GroupStatistics, 
    ExportStatistics, TindalosMetrics
)

# Common variables
User = get_user_model()

# Common choices and constants
SKILL_CATEGORIES = [
    ('探索系', '探索系'),
    ('対人系', '対人系'),
    ('戦闘系', '戦闘系'),
    ('知識系', '知識系'),
    ('技術系', '技術系'),
    ('行動系', '行動系'),
    ('言語系', '言語系'),
    ('特殊・その他', '特殊・その他'),
]

CHARACTER_EDITIONS = [
    ('6th', '6版'),
]

GROUP_VISIBILITY_CHOICES = [
    ('public', '公開'),
    ('private', 'プライベート'),
]

GROUP_ROLE_CHOICES = [
    ('admin', '管理者'),
    ('member', 'メンバー'),
]