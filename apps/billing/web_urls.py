"""Billing browser URL patterns."""
from django.urls import path
from .web_views import InvoiceListPageView, InvoiceListPartialView, InvoiceDetailPageView

urlpatterns = [
    path('', InvoiceListPageView.as_view(), name='invoice-list-web'),
    path('htmx/', InvoiceListPartialView.as_view(), name='invoice-list-partial'),
    path('<uuid:pk>/', InvoiceDetailPageView.as_view(), name='invoice-detail-web'),
]
