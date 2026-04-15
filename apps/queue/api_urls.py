"""Queue API URLs."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.QueueListCreateView.as_view(), name='queue-list'),
    path('<uuid:pk>/call/', views.QueueCallView.as_view(), name='queue-call'),
]
