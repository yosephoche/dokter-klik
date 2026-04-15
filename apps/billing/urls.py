"""Invoice API URLs."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='invoice-list'),
    path('<uuid:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('<uuid:pk>/pay/cash/', views.PayCashView.as_view(), name='invoice-pay-cash'),
    path('<uuid:pk>/pay/qris/', views.PayQRISView.as_view(), name='invoice-pay-qris'),
]
