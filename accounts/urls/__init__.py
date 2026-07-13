from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from .. import export_views, statistics_views, views
from ..views.admin_views import AdminUserViewSet
from ..views.character_image_views import CharacterImageBackgroundRemovalView, CharacterImageViewSet
from ..views.character_views import GrowthRecordViewSet
from ..views.dev_login_view import DevLoginView
from ..views.user_profile_view import UserProfileView

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"groups", views.GroupViewSet, basename="group")
router.register(r"friends", views.FriendViewSet, basename="friend")
router.register(r"invitations", views.GroupInvitationViewSet, basename="invitation")
router.register(r"character-sheets", views.CharacterSheetViewSet, basename="character-sheet")
router.register(r"dice-roll-settings", views.DiceRollSettingViewSet, basename="dice-roll-setting")
# Character skills and equipment are now handled as nested resources
router.register(r"admin/users", AdminUserViewSet, basename="admin-user")

CHARACTER_IMAGE_LIST_ACTIONS = {"get": "list", "post": "create"}
CHARACTER_IMAGE_DETAIL_ACTIONS = {
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
}
CHARACTER_IMAGE_SET_MAIN_ACTIONS = {"post": "set_main", "patch": "set_main"}
CHARACTER_IMAGE_REORDER_ACTIONS = {"patch": "reorder"}
CHARACTER_IMAGE_DOWNLOAD_ACTIONS = {"get": "download"}


def character_image_urlpatterns(parameter_name, route_name_prefix):
    base_path = f"character-sheets/<int:{parameter_name}>/images"
    return [
        path(
            f"{base_path}/",
            CharacterImageViewSet.as_view(CHARACTER_IMAGE_LIST_ACTIONS),
            name=f"{route_name_prefix}-list",
        ),
        path(
            f"{base_path}/download/",
            CharacterImageViewSet.as_view(CHARACTER_IMAGE_DOWNLOAD_ACTIONS),
            name=f"{route_name_prefix}-download",
        ),
        path(
            f"{base_path}/<int:pk>/",
            CharacterImageViewSet.as_view(CHARACTER_IMAGE_DETAIL_ACTIONS),
            name=f"{route_name_prefix}-detail",
        ),
        path(
            f"{base_path}/<int:pk>/set_main/",
            CharacterImageViewSet.as_view(CHARACTER_IMAGE_SET_MAIN_ACTIONS),
            name=f"{route_name_prefix}-set-main",
        ),
        path(
            f"{base_path}/reorder/",
            CharacterImageViewSet.as_view(CHARACTER_IMAGE_REORDER_ACTIONS),
            name=f"{route_name_prefix}-reorder",
        ),
    ]


urlpatterns = [
    # Authentication URLs
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("signup/", views.CustomSignUpView.as_view(), name="signup"),
    # Development login (DEBUG only)
    path("dev-login/", DevLoginView.as_view(), name="dev_login"),
    # Web URLs for frontend pages (before router to avoid conflicts)
    path(
        "groups/view/",
        method_decorator(login_required, name="dispatch")(TemplateView).as_view(template_name="groups/management.html"),
        name="groups_view",
    ),
    path(
        "statistics/view/",
        method_decorator(login_required, name="dispatch")(TemplateView).as_view(
            template_name="statistics/tindalos_metrics.html"
        ),
        name="statistics_view",
    ),
    path(
        "character/create/",
        method_decorator(login_required, name="dispatch")(TemplateView).as_view(
            template_name="accounts/character_sheet.html"
        ),
        name="character_create",
    ),
    path("character/create/6th/", views.Character6thCreateView.as_view(), name="character_create_6th"),
    path("character/create/7th/", views.Character7thCreateView.as_view(), name="character_create_7th"),
    # Character Sheet Web Views
    path("character/list/", views.CharacterListView.as_view(), name="character_list"),
    path(
        "character/6th/<int:character_id>/",
        login_required(views.Character6thDetailView.as_view()),
        name="character_detail_6th",
    ),
    path(
        "character/<int:character_id>/",
        login_required(views.CharacterDetailRedirectView.as_view()),
        name="character_detail",
    ),
    # API URLs
    path(
        "groups/<int:group_id>/invite-links/",
        views.GroupInviteLinkCreateView.as_view(),
        name="group_invite_link_create",
    ),
    path(
        "groups/<int:group_id>/invite-links/<int:invite_link_id>/",
        views.GroupInviteLinkRevokeView.as_view(),
        name="group_invite_link_revoke",
    ),
    path("", include(router.urls)),
    # Profile URLs
    path("users/<int:user_id>/profile/", UserProfileView.as_view(), name="user_profile"),
    path("profile/", views.ProfileEditView.as_view(), name="profile_detail"),
    path("profile/edit/", views.ProfileEditView.as_view(), name="profile_edit"),
    path("profile/delete/", views.AccountDeleteView.as_view(), name="account_delete"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("billing/", views.BillingPageView.as_view(), name="billing"),
    path("billing/success/", views.BillingSuccessView.as_view(), name="billing_success"),
    path("billing/cancel/", views.BillingCancelView.as_view(), name="billing_cancel"),
    # Social Auth Mock URLs
    path("demo/", views.demo_login_page, name="demo_login"),
    path("mock-social/<str:provider>/", views.mock_social_login, name="mock_social_login"),
    # Statistics APIs
    path("statistics/simple/", statistics_views.SimpleTindalosMetricsView.as_view(), name="statistics_simple"),
    path("statistics/tindalos/", statistics_views.TindalosMetricsView.as_view(), name="tindalos_metrics"),
    path(
        "statistics/tindalos/<int:year>/", statistics_views.TindalosMetricsView.as_view(), name="tindalos_metrics_year"
    ),
    path(
        "statistics/tindalos/detailed/",
        statistics_views.DetailedTindalosMetricsView.as_view(),
        name="tindalos_metrics_detailed",
    ),
    path("statistics/ranking/", statistics_views.UserRankingView.as_view(), name="user_ranking"),
    path("statistics/groups/", statistics_views.GroupStatisticsView.as_view(), name="group_statistics"),
    # Export APIs
    path("export/formats/", export_views.ExportFormatsView.as_view(), name="export_formats"),
    path("export/statistics/", export_views.StatisticsExportView.as_view(), name="export_statistics"),
    path("export/", export_views.ExportStatisticsView.as_view(), name="export_legacy"),
    # Character Image Management API
    path("character-images/remove-background/", CharacterImageBackgroundRemovalView.as_view(), name="character-image-remove-background"),
    *character_image_urlpatterns("character_sheet_id", "character-images"),
    *character_image_urlpatterns("character_id", "character-image"),
    # Character Skill Management API
    path(
        "character-sheets/<int:character_sheet_id>/skills/",
        views.CharacterSkillViewSet.as_view({"get": "list", "post": "create"}),
        name="character-skill-list",
    ),
    path(
        "character-sheets/<int:character_sheet_id>/skills/bulk_update/",
        views.CharacterSkillViewSet.as_view({"patch": "bulk_update"}),
        name="character-skill-bulk-update",
    ),
    path(
        "character-sheets/<int:character_sheet_id>/skills/<int:pk>/",
        views.CharacterSkillViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="character-skill-detail",
    ),
    # Character Equipment Management API
    path(
        "character-sheets/<int:character_sheet_id>/equipment/",
        views.CharacterEquipmentViewSet.as_view({"get": "list", "post": "create"}),
        name="character-equipment-list",
    ),
    path(
        "character-sheets/<int:character_sheet_id>/equipment/<int:pk>/",
        views.CharacterEquipmentViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="character-equipment-detail",
    ),
    # Growth Record Management API
    path(
        "character-sheets/<int:character_sheet_id>/growth-records/",
        GrowthRecordViewSet.as_view({"get": "list", "post": "create"}),
        name="growth-records-list",
    ),
    path(
        "character-sheets/<int:character_sheet_id>/growth-records/<int:pk>/",
        GrowthRecordViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="growth-records-detail",
    ),
    path(
        "character-sheets/<int:character_sheet_id>/growth-records/<int:pk>/add_skill_growth/",
        GrowthRecordViewSet.as_view({"post": "add_skill_growth"}),
        name="growth-records-add-skill",
    ),
    path(
        "character-sheets/<int:character_sheet_id>/growth-records/summary/",
        GrowthRecordViewSet.as_view({"get": "summary"}),
        name="growth-records-summary",
    ),
    # Background Information API
    path(
        "character-sheets/<int:pk>/background-summary/",
        views.CharacterSheetViewSet.as_view({"get": "background_summary"}),
        name="character-sheet-background-summary",
    ),
    path(
        "character-sheets/<int:pk>/update-background-data/",
        views.CharacterSheetViewSet.as_view({"patch": "update_background_data"}),
        name="character-sheet-update-background-data",
    ),
    path(
        "character-sheets/<int:pk>/growth-summary/",
        views.CharacterSheetViewSet.as_view({"get": "growth_summary"}),
        name="character-sheet-growth-summary",
    ),
    path(
        "character-sheets/<int:pk>/bulk-update-items/",
        views.CharacterSheetViewSet.as_view({"post": "bulk_update_items"}),
        name="character-sheet-bulk-update-items",
    ),
    path(
        "character-sheets/<int:pk>/financial-summary/",
        views.CharacterSheetViewSet.as_view({"get": "financial_summary"}),
        name="character-sheet-financial-summary",
    ),
    path(
        "character-sheets/<int:pk>/update-financial-data/",
        views.CharacterSheetViewSet.as_view({"patch": "update_financial_data"}),
        name="character-sheet-update-financial-data",
    ),
    path(
        "character-sheets/<int:pk>/inventory-summary/",
        views.CharacterSheetViewSet.as_view({"get": "inventory_summary"}),
        name="character-sheet-inventory-summary",
    ),
    path(
        "character-sheets/<int:pk>/allocate-skill-points/",
        views.CharacterSheetViewSet.as_view({"post": "allocate_skill_points"}),
        name="character-sheet-allocate-skill-points",
    ),
    path(
        "character-sheets/<int:pk>/batch-allocate-skill-points/",
        views.CharacterSheetViewSet.as_view({"post": "batch_allocate_skill_points"}),
        name="character-sheet-batch-allocate-skill-points",
    ),
    path(
        "character-sheets/<int:pk>/reset-skill-points/",
        views.CharacterSheetViewSet.as_view({"post": "reset_skill_points"}),
        name="character-sheet-reset-skill-points",
    ),
    path(
        "character-sheets/<int:pk>/combat-summary/",
        views.CharacterSheetViewSet.as_view({"get": "combat_summary"}),
        name="character-sheet-combat-summary",
    ),
]
