from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.routers import DefaultRouter
from . import views
from . import statistics_views
from . import export_views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'groups', views.GroupViewSet, basename='group')
router.register(r'friends', views.FriendViewSet, basename='friend')
router.register(r'invitations', views.GroupInvitationViewSet, basename='invitation')
router.register(r'character-sheets', views.CharacterSheetViewSet, basename='character-sheet')
router.register(r'character-skills', views.CharacterSkillViewSet, basename='character-skill')
router.register(r'character-equipment', views.CharacterEquipmentViewSet, basename='character-equipment')

urlpatterns = [
    # Web URLs for frontend pages (before router to avoid conflicts)
    path('groups/view/', 
         method_decorator(login_required, name='dispatch')(TemplateView).as_view(template_name='groups/management.html'), 
         name='groups_view'),
    path('statistics/view/', 
         method_decorator(login_required, name='dispatch')(TemplateView).as_view(template_name='statistics/tindalos_metrics.html'), 
         name='statistics_view'),
    path('character/create/', 
         method_decorator(login_required, name='dispatch')(TemplateView).as_view(template_name='accounts/character_sheet.html'), 
         name='character_create'),
    path('character/create/6th/', 
         views.Character6thCreateView.as_view(), 
         name='character_create_6th'),
    path('character/create/7th/', 
         method_decorator(login_required, name='dispatch')(TemplateView).as_view(template_name='accounts/character_sheet_7th.html'), 
         name='character_create_7th'),
    
    # Character Sheet Web Views
    path('character/list/', views.CharacterListView.as_view(), name='character_list'),
    path('character/<int:character_id>/', views.CharacterDetailView.as_view(), name='character_detail'),
    path('character/<int:character_id>/edit/', views.CharacterEditView.as_view(), name='character_edit'),
    path('character/new/', views.CharacterEditView.as_view(), name='character_new'),
    
    # API URLs
    path('', include(router.urls)),
    path('profile/', views.ProfileView.as_view(), name='api_profile'),
    path('friends/add/', views.AddFriendView.as_view(), name='api_add_friend'),
    
    # Character Sheet nested endpoints  
    path('character-sheets/<int:character_sheet_id>/skills/', 
         views.CharacterSkillViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='character-sheet-skills'),
    path('character-sheets/<int:character_sheet_id>/skills/<int:pk>/', 
         views.CharacterSkillViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
         name='character-sheet-skill-detail'),
    path('character-sheets/<int:character_sheet_id>/equipment/', 
         views.CharacterEquipmentViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='character-sheet-equipment'),
    path('character-sheets/<int:character_sheet_id>/equipment/<int:pk>/', 
         views.CharacterEquipmentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
         name='character-sheet-equipment-detail'),
    
    # Statistics APIs
    path('statistics/tindalos/', statistics_views.SimpleTindalosMetricsView.as_view(), name='tindalos_metrics'),
    path('statistics/ranking/', statistics_views.UserRankingView.as_view(), name='user_ranking'),
    path('statistics/groups/', statistics_views.GroupStatisticsView.as_view(), name='group_statistics'),
    
    # Export APIs (Legacy)
    path('export/', export_views.ExportStatisticsView.as_view(), name='export_legacy'),
    
    # Export APIs (New Specification - ISSUE-002)
    path('export/statistics/', export_views.StatisticsExportView.as_view(), name='export_statistics_new'),
    path('export/formats/', export_views.ExportFormatsView.as_view(), name='export_formats_new'),
    
    # Web URLs
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    
    # Demo/Development URLs
    path('demo/', views.demo_login_page, name='demo_login'),
    path('mock-social/<str:provider>/', views.mock_social_login, name='mock_social_login'),
]