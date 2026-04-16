"""Browser/HTMX dashboard URL."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import path
from django.views.generic import TemplateView

from .landing_views import LandingPageView
from .web_views import DashboardStatsPartialView


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"


urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path(
        "htmx/stats/",
        DashboardStatsPartialView.as_view(),
        name="dashboard-stats-partial",
    ),
]
