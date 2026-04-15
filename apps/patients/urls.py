from django.urls import path
from . import views

urlpatterns = [
    path('', views.PatientListCreateView.as_view(), name='patient-list'),
    path('<uuid:pk>/', views.PatientDetailView.as_view(), name='patient-detail'),
]
