"""Browser/HTMX dashboard URL."""
from django.urls import path
from django.views.generic import TemplateView
from rest_framework.permissions import IsAuthenticated


class DashboardView(TemplateView):
    template_name = 'dashboard/index.html'


urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]
