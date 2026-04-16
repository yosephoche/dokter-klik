"""Clinic web URL patterns."""
from django.urls import path
from .web_views import ClinicOnboardingView, ClinicSettingsView, UserListView, UserCreateView

urlpatterns = [
    path('onboarding/', ClinicOnboardingView.as_view(), name='clinic-onboarding'),
    path('settings/', ClinicSettingsView.as_view(), name='clinic-settings'),
    path('users/', UserListView.as_view(), name='clinic-users'),
    path('users/tambah/', UserCreateView.as_view(), name='clinic-user-create'),
]
