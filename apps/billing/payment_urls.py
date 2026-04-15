"""Payment webhook URLs."""
from django.urls import path
from .views import MidtransWebhookView

urlpatterns = [
    path('midtrans/webhook/', MidtransWebhookView.as_view(), name='midtrans-webhook'),
]
