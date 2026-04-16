"""Auth browser (session) URL patterns."""
from django.urls import path
from .web_views import LoginWebView, LogoutWebView

urlpatterns = [
    path('login/', LoginWebView.as_view(), name='auth-login-web'),
    path('logout/', LogoutWebView.as_view(), name='auth-logout-web'),
]
