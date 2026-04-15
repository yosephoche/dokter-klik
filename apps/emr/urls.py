"""EMR visit and SOAP URLs."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.VisitListCreateView.as_view(), name='visit-list'),
    path('<uuid:pk>/', views.VisitDetailView.as_view(), name='visit-detail'),
    path('<uuid:pk>/autosave/', views.VisitAutosaveView.as_view(), name='visit-autosave'),
    path('<uuid:pk>/finalize/', views.VisitFinalizeView.as_view(), name='visit-finalize'),
    path('<uuid:visit_pk>/diagnoses/', views.DiagnosisListCreateView.as_view(), name='diagnosis-list'),
    path('<uuid:visit_pk>/prescriptions/', views.PrescriptionListCreateView.as_view(), name='prescription-list'),
]
