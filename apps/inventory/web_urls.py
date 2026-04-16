"""Inventory browser URL patterns."""
from django.urls import path
from .web_views import DrugListPageView, DrugListPartialView

urlpatterns = [
    path('', DrugListPageView.as_view(), name='drug-list-web'),
    path('htmx/', DrugListPartialView.as_view(), name='drug-list-partial'),
]
