from django.urls import path
from . import views

urlpatterns = [
    path('', views.ClinicDetailView.as_view(), name='clinic-detail'),
    path('schedules/', views.DoctorScheduleListView.as_view(), name='schedule-list'),
]
