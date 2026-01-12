from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'scenarios', views.ScenarioViewSet, basename='scenario')
router.register(r'scenario-images', views.ScenarioImageViewSet, basename='scenario-image')
router.register(r'notes', views.ScenarioNoteViewSet, basename='note')
router.register(r'history', views.PlayHistoryViewSet, basename='history')

urlpatterns = [
    # API URLs
    path('', include(router.urls)),
    path('archive/', views.ScenarioArchiveView.as_view(), name='scenario_archive'),
    path('statistics/', views.PlayStatisticsView.as_view(), name='play_statistics'),
    
    # Web URLs
    path('archive/view/', TemplateView.as_view(template_name='scenarios/archive.html'), name='archive_view'),
]
