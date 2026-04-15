"""Public queue display URLs (browser views)."""
from django.urls import path
from . import views

urlpatterns = [
    path('live/<slug:clinic_slug>/', views.QueueLiveView.as_view(), name='queue-live'),
    path('live/<slug:clinic_slug>/partial/', views.QueueLivePartialView.as_view(), name='queue-live-partial'),
]
