from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.routers import DefaultRouter
from .. import views
from .. import statistics_views
from .. import export_views
from ..views.character_image_views import CharacterImageViewSet
from ..views.character_views import GrowthRecordViewSet
from ..views.dev_login_view import DevLoginView
from ..views.admin_views import AdminUserViewSet

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'groups', views.GroupViewSet, basename='group')
router.register(r'friends', views.FriendViewSet, basename='friend')
router.register(r'invitations', views.GroupInvitationViewSet, basename='invitation')
router.register(r'character-sheets', views.CharacterSheetViewSet, basename='character-sheet')
router.register(r'dice-roll-settings', views.DiceRollSettingViewSet, basename='dice-roll-setting')
# Character skills and equipment are now handled as nested resources
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')

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
    
    # Profile URLs
    path('profile/', views.ProfileEditView.as_view(), name='profile_detail'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('profile/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Social Auth Mock URLs
    path('demo/', 
         method_decorator(login_required, name='dispatch')(TemplateView).as_view(template_name='accounts/demo_login.html'), 
         name='demo_login'),
    path('mock-social/<str:provider>/', 
         method_decorator(login_required, name='dispatch')(TemplateView).as_view(template_name='accounts/mock_social.html'), 
         name='mock_social_login'),
    
    
    # Statistics APIs
    path('statistics/tindalos/', statistics_views.TindalosMetricsView.as_view(), name='tindalos_metrics'),
    path('statistics/tindalos/<int:year>/', statistics_views.TindalosMetricsView.as_view(), name='tindalos_metrics_year'),
    path('statistics/ranking/', statistics_views.UserRankingView.as_view(), name='user_ranking'),
    path('statistics/groups/', statistics_views.GroupStatisticsView.as_view(), name='group_statistics'),
    
    # Export APIs
    path('export/formats/', export_views.ExportFormatsView.as_view(), name='export_formats'),
    path('export/statistics/', export_views.ExportStatisticsView.as_view(), name='export_statistics'),
    
    # Character Image Management API
    path('character-sheets/<int:character_sheet_id>/images/', 
         CharacterImageViewSet.as_view({
             'get': 'list',
             'post': 'create'
         }), 
         name='character-images-list'),
    path('character-sheets/<int:character_sheet_id>/images/<int:pk>/', 
         CharacterImageViewSet.as_view({
             'get': 'retrieve',
             'put': 'update',
             'patch': 'partial_update',
             'delete': 'destroy'
         }), 
         name='character-images-detail'),
    path('character-sheets/<int:character_sheet_id>/images/<int:pk>/set_main/', 
         CharacterImageViewSet.as_view({'post': 'set_main'}), 
         name='character-images-set-main'),
    path('character-sheets/<int:character_sheet_id>/images/reorder/', 
         CharacterImageViewSet.as_view({'post': 'reorder'}), 
         name='character-images-reorder'),
    
    # Character Skill Management API
    path('character-sheets/<int:character_sheet_id>/skills/', 
        views.CharacterSkillViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }), 
        name='character-skill-list'),
    path('character-sheets/<int:character_sheet_id>/skills/<int:pk>/', 
        views.CharacterSkillViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }), 
        name='character-skill-detail'),
    
    # Character Equipment Management API
    path('character-sheets/<int:character_sheet_id>/equipment/', 
        views.CharacterEquipmentViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }), 
        name='character-equipment-list'),
    path('character-sheets/<int:character_sheet_id>/equipment/<int:pk>/', 
        views.CharacterEquipmentViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }), 
        name='character-equipment-detail'),
    
    # Growth Record Management API
    path('character-sheets/<int:character_sheet_id>/growth-records/', 
         GrowthRecordViewSet.as_view({
             'get': 'list',
             'post': 'create'
         }), 
         name='growth-records-list'),
    path('character-sheets/<int:character_sheet_id>/growth-records/<int:pk>/', 
         GrowthRecordViewSet.as_view({
             'get': 'retrieve',
             'put': 'update',
             'patch': 'partial_update',
             'delete': 'destroy'
         }), 
         name='growth-records-detail'),
    path('character-sheets/<int:character_sheet_id>/growth-records/<int:pk>/add_skill_growth/', 
         GrowthRecordViewSet.as_view({'post': 'add_skill_growth'}), 
         name='growth-records-add-skill'),
    path('character-sheets/<int:character_sheet_id>/growth-records/summary/', 
         GrowthRecordViewSet.as_view({'get': 'summary'}), 
         name='growth-records-summary'),
]
