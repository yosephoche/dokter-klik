"""EMR browser URL patterns."""
from django.urls import path
from .web_views import (
    VisitListPageView, VisitListPartialView,
    SOAPFormView, ICD10SearchPartialView, VisitCreateView,
)

urlpatterns = [
    path('', VisitListPageView.as_view(), name='visit-list-web'),
    path('htmx/', VisitListPartialView.as_view(), name='visit-list-partial'),
    path('create/', VisitCreateView.as_view(), name='visit-create'),
    path('<uuid:pk>/soap/', SOAPFormView.as_view(), name='soap-form'),
    path('htmx/icd10/', ICD10SearchPartialView.as_view(), name='icd10-search-partial'),
]
