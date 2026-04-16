"""Patient browser URL patterns."""
from django.urls import path
from .web_views import PatientListPageView, PatientListPartialView, PatientCreateView

urlpatterns = [
    path('', PatientListPageView.as_view(), name='patient-list-web'),
    path('htmx/', PatientListPartialView.as_view(), name='patient-list-partial'),
    path('create/', PatientCreateView.as_view(), name='patient-create'),
]
