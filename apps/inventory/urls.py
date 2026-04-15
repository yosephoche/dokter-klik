from django.urls import path
from . import views

urlpatterns = [
    path('', views.DrugListCreateView.as_view(), name='drug-list'),
    path('<uuid:pk>/', views.DrugDetailView.as_view(), name='drug-detail'),
    path('<uuid:pk>/stock/', views.StockAdjustView.as_view(), name='drug-stock'),
]
