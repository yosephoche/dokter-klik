"""Queue management browser URL patterns."""
from django.urls import path
from .web_views import (
    QueueManagePageView,
    QueueManagementPartialView,
    QueueEntryCreateView,
    QueueOnlineRegisterView,
    QueueOnlineConfirmView,
)

urlpatterns = [
    path('manage/', QueueManagePageView.as_view(), name='queue-manage-web'),
    path('htmx/', QueueManagementPartialView.as_view(), name='queue-list-partial'),
    path('htmx/create/', QueueEntryCreateView.as_view(), name='queue-entry-create'),
    path('daftar/<slug:clinic_slug>/', QueueOnlineRegisterView.as_view(), name='queue-online-register'),
    path('daftar/<slug:clinic_slug>/konfirmasi/<uuid:entry_pk>/', QueueOnlineConfirmView.as_view(), name='queue-online-confirm'),
]
