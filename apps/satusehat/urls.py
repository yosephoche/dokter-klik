from django.urls import path
from . import views

urlpatterns = [
    path('logs/', views.SyncLogListView.as_view(), name='satusehat-logs'),
    path('stats/', views.SyncStatsView.as_view(), name='satusehat-stats'),
    path('logs/<uuid:pk>/resync/', views.ManualResyncView.as_view(), name='satusehat-resync'),
]
