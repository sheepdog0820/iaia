from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.routers import DefaultRouter
from . import views
from . import statistics_views
from . import export_views
from .views.character_image_views import CharacterImageViewSet
from .views.dev_login_view import DevLoginView

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'groups', views.GroupViewSet, basename='group')
router.register(r'friends', views.FriendViewSet, basename='friend')
router.register(r'invitations', views.GroupInvitationViewSet, basename='invitation')
router.register(r'character-sheets', views.CharacterSheetViewSet, basename='character-sheet')
router.register(r'character-skills', views.CharacterSkillViewSet, basename='character-skill')
router.register(r'character-equipment', views.CharacterEquipmentViewSet, basename='character-equipment')

urlpatterns = [
    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('signup/', views.CustomSignUpView.as_view(), name='signup'),
    
    # Development login (DEBUG only)
    path('dev-login/', DevLoginView.as_view(), name='dev_login'),
    
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
    # Character Images endpoints
    path('character-sheets/<int:character_id>/images/', 
         CharacterImageViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='character-image-list'),
    path('character-sheets/<int:character_id>/images/<int:pk>/', 
         CharacterImageViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
         name='character-image-detail'),
    path('character-sheets/<int:character_id>/images/reorder/', 
         CharacterImageViewSet.as_view({'patch': 'reorder'}), 
         name='character-image-reorder'),
    path('character-sheets/<int:character_id>/images/<int:pk>/set-main/', 
         CharacterImageViewSet.as_view({'patch': 'set_main'}), 
         name='character-image-set-main'),
    path('character-sheets/<int:character_id>/images/bulk-upload/', 
         CharacterImageViewSet.as_view({'post': 'bulk_upload'}), 
         name='character-image-bulk-upload'),
    
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
    
    # Character Skill custom endpoints
    path('character-sheets/<int:character_sheet_id>/skills/create_custom_skill/', 
         views.CharacterSkillViewSet.as_view({'post': 'create_custom_skill'}), 
         name='character-sheet-skills-create-custom'),
    path('character-sheets/<int:character_sheet_id>/skills/bulk_update/', 
         views.CharacterSkillViewSet.as_view({'patch': 'bulk_update'}), 
         name='character-sheet-skills-bulk-update'),
    path('character-sheets/<int:character_sheet_id>/skills/skill_categories/', 
         views.CharacterSkillViewSet.as_view({'get': 'skill_categories'}), 
         name='character-sheet-skills-categories'),
    
    # Character Sheet custom endpoints
    path('character-sheets/<int:pk>/ccfolia-json/', 
         views.CharacterSheetViewSet.as_view({'get': 'ccfolia_json'}), 
         name='character-sheet-ccfolia-json'),
    path('character-sheets/<int:pk>/export-version-data/', 
         views.CharacterSheetViewSet.as_view({'get': 'export_version_data'}), 
         name='character-sheet-export-version-data'),
    
    # Skill Point Management endpoints
    path('character-sheets/<int:pk>/skill-points-summary/', 
         views.CharacterSheetViewSet.as_view({'get': 'skill_points_summary'}), 
         name='character-sheet-skill-points-summary'),
    path('character-sheets/<int:pk>/allocate-skill-points/', 
         views.CharacterSheetViewSet.as_view({'post': 'allocate_skill_points'}), 
         name='character-sheet-allocate-skill-points'),
    path('character-sheets/<int:pk>/batch-allocate-skill-points/', 
         views.CharacterSheetViewSet.as_view({'post': 'batch_allocate_skill_points'}), 
         name='character-sheet-batch-allocate-skill-points'),
    path('character-sheets/<int:pk>/reset-skill-points/', 
         views.CharacterSheetViewSet.as_view({'post': 'reset_skill_points'}), 
         name='character-sheet-reset-skill-points'),
    
    # Combat Data Management endpoints
    path('character-sheets/<int:pk>/combat-summary/', 
         views.CharacterSheetViewSet.as_view({'get': 'combat_summary'}), 
         name='character-sheet-combat-summary'),
    
    # Inventory Management endpoints
    path('character-sheets/<int:pk>/financial-summary/', 
         views.CharacterSheetViewSet.as_view({'get': 'financial_summary'}), 
         name='character-sheet-financial-summary'),
    path('character-sheets/<int:pk>/update-financial-data/', 
         views.CharacterSheetViewSet.as_view({'patch': 'update_financial_data'}), 
         name='character-sheet-update-financial-data'),
    path('character-sheets/<int:pk>/inventory-summary/', 
         views.CharacterSheetViewSet.as_view({'get': 'inventory_summary'}), 
         name='character-sheet-inventory-summary'),
    path('character-sheets/<int:pk>/bulk-update-items/', 
         views.CharacterSheetViewSet.as_view({'post': 'bulk_update_items'}), 
         name='character-sheet-bulk-update-items'),
    
    # Background Information endpoints
    path('character-sheets/<int:pk>/background-summary/', 
         views.CharacterSheetViewSet.as_view({'get': 'background_summary'}), 
         name='character-sheet-background-summary'),
    path('character-sheets/<int:pk>/update-background-data/', 
         views.CharacterSheetViewSet.as_view({'patch': 'update_background_data'}), 
         name='character-sheet-update-background-data'),
    
    # Growth Record endpoints
    path('character-sheets/<int:pk>/growth-records/', 
         views.CharacterSheetViewSet.as_view({'get': 'growth_records', 'post': 'growth_records'}), 
         name='character-sheet-growth-records'),
    path('character-sheets/<int:pk>/growth-summary/', 
         views.CharacterSheetViewSet.as_view({'get': 'growth_summary'}), 
         name='character-sheet-growth-summary'),
    path('character-sheets/<int:pk>/growth-records/<int:record_id>/add-skill-growth/', 
         views.CharacterSheetViewSet.as_view({'post': 'add_skill_growth'}), 
         name='character-sheet-add-skill-growth'),
    
    # Statistics APIs
    path('statistics/tindalos/', statistics_views.SimpleTindalosMetricsView.as_view(), name='tindalos_metrics'),
    path('statistics/tindalos/detailed/', statistics_views.DetailedTindalosMetricsView.as_view(), name='tindalos_metrics_detailed'),
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