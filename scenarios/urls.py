from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"scenarios", views.ScenarioViewSet, basename="scenario")
router.register(r"scenario-images", views.ScenarioImageViewSet, basename="scenario-image")
router.register(r"notes", views.ScenarioNoteViewSet, basename="note")
router.register(r"history", views.PlayHistoryViewSet, basename="history")

urlpatterns = [
    # API URLs
    path("", include(router.urls)),
    path("archive/", views.ScenarioArchiveView.as_view(), name="scenario_archive"),
    path("statistics/", views.PlayStatisticsView.as_view(), name="play_statistics"),
    # Web URLs
    path("archive/view/", views.ScenarioArchivePageView.as_view(), name="archive_view"),
]
