"""Auth web views: session-based login/logout for browser (HTMX) flow."""
import datetime

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.middleware.csrf import get_token


class LoginWebView(View):
    """Render login form (GET) and authenticate via Django session (POST)."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(reverse('dashboard'))
        csrf_token = get_token(request)
        return render(request, 'auth/login.html', {
            'csrf_token': csrf_token,
            'now': datetime.date.today(),
        })

    def post(self, request):
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        csrf_token = get_token(request)

        user = authenticate(request, username=email, password=password)
        if user is None or not user.is_active:
            return render(request, 'auth/login.html', {
                'error': 'Email atau password salah.',
                'email': email,
                'csrf_token': csrf_token,
                'now': datetime.date.today(),
            })

        login(request, user)
        next_url = request.GET.get('next') or reverse('dashboard')
        return redirect(next_url)


class LogoutWebView(View):
    """Destroy session and redirect to login. Only POST allowed."""

    def post(self, request):
        logout(request)
        return redirect(reverse('auth-login-web'))
