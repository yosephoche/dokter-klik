"""ICD-10 search URL."""
from django.urls import path
from .views import ICD10SearchView

urlpatterns = [
    path('', ICD10SearchView.as_view(), name='icd10-search'),
]
