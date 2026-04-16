"""Clinic web/HTMX views: onboarding, settings, user management."""
import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View

from apps.accounts.models import CustomUser
from .models import Clinic


def _slugify(name: str) -> str:
    """Simple slug generator — lowercase, replace spaces/special chars with hyphens."""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug


def _unique_slug(base_slug: str) -> str:
    """Ensure slug is unique by appending a counter if needed."""
    slug = base_slug
    counter = 1
    while Clinic.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1
    return slug


class ClinicOnboardingView(View):
    """
    Onboarding for users without a clinic.
    Accessible without LoginRequired so the middleware redirect doesn't loop.
    Still requires authentication — non-auth users are redirected to login.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse('auth-login-web'))
        if request.user.clinic_id:
            return redirect(reverse('dashboard'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, 'clinics/onboarding.html', {'errors': {}})

    def post(self, request):
        errors = {}
        name = request.POST.get('name', '').strip()
        if not name:
            errors['name'] = 'Nama klinik wajib diisi.'

        if not errors:
            base_slug = _slugify(name) or 'klinik'
            slug = _unique_slug(base_slug)
            clinic = Clinic.objects.create(
                name=name,
                slug=slug,
                address=request.POST.get('address', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                email=request.POST.get('email', '').strip(),
            )
            user = request.user
            user.clinic = clinic
            user.role = 'owner'
            user.save(update_fields=['clinic', 'role'])
            messages.success(request, f'Klinik "{clinic.name}" berhasil didaftarkan.')
            return redirect(reverse('dashboard'))

        return render(request, 'clinics/onboarding.html', {
            'errors': errors,
            'data': request.POST,
        })


class ClinicSettingsView(LoginRequiredMixin, View):
    """Owner can view and edit their clinic profile."""

    def _check_access(self, request):
        if request.user.role != 'owner' or not request.user.clinic_id:
            return redirect(reverse('dashboard'))
        return None

    def get(self, request):
        denied = self._check_access(request)
        if denied:
            return denied
        return render(request, 'clinics/settings.html', {
            'clinic': request.user.clinic,
            'errors': {},
        })

    def post(self, request):
        denied = self._check_access(request)
        if denied:
            return denied

        clinic = request.user.clinic
        errors = {}
        name = request.POST.get('name', '').strip()
        if not name:
            errors['name'] = 'Nama klinik wajib diisi.'

        consultation_fee_str = request.POST.get('consultation_fee', '0').strip()
        try:
            consultation_fee = Decimal(consultation_fee_str or '0')
        except InvalidOperation:
            errors['consultation_fee'] = 'Biaya konsultasi harus berupa angka.'
            consultation_fee = Decimal('0')

        if errors:
            return render(request, 'clinics/settings.html', {
                'clinic': clinic,
                'errors': errors,
                'data': request.POST,
            })

        clinic.name = name
        clinic.address = request.POST.get('address', '').strip()
        clinic.phone = request.POST.get('phone', '').strip()
        clinic.email = request.POST.get('email', '').strip()
        clinic.consultation_fee = consultation_fee
        clinic.save(update_fields=['name', 'address', 'phone', 'email', 'consultation_fee', 'updated_at'])
        messages.success(request, 'Pengaturan klinik berhasil disimpan.')
        return redirect(reverse('clinic-settings'))


class UserListView(LoginRequiredMixin, View):
    """Owner/Admin can list users in their clinic."""

    def get(self, request):
        if request.user.role not in ('owner', 'admin') or not request.user.clinic_id:
            return redirect(reverse('dashboard'))
        users = CustomUser.objects.filter(clinic=request.user.clinic).order_by('first_name', 'email')
        return render(request, 'clinics/users.html', {'users': users})


class UserCreateView(LoginRequiredMixin, View):
    """Owner can add a new user to their clinic."""

    ALLOWED_ROLES = [
        ('doctor', 'Dokter'),
        ('admin', 'Admin'),
        ('pharmacy', 'Apotek'),
    ]

    def _check_access(self, request):
        if request.user.role != 'owner' or not request.user.clinic_id:
            return redirect(reverse('dashboard'))
        return None

    def get(self, request):
        denied = self._check_access(request)
        if denied:
            return denied
        return render(request, 'clinics/user_create.html', {
            'allowed_roles': self.ALLOWED_ROLES,
            'errors': {},
        })

    def post(self, request):
        denied = self._check_access(request)
        if denied:
            return denied

        errors = {}
        email = request.POST.get('email', '').strip().lower()
        if not email:
            errors['email'] = 'Email wajib diisi.'
        elif CustomUser.objects.filter(email=email).exists():
            errors['email'] = 'Email sudah digunakan.'

        role = request.POST.get('role', '').strip()
        if role not in dict(self.ALLOWED_ROLES):
            errors['role'] = 'Pilih role yang valid.'

        password = request.POST.get('password', '')
        if len(password) < 8:
            errors['password'] = 'Password minimal 8 karakter.'

        if errors:
            return render(request, 'clinics/user_create.html', {
                'allowed_roles': self.ALLOWED_ROLES,
                'errors': errors,
                'data': request.POST,
            })

        CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=request.POST.get('first_name', '').strip(),
            last_name=request.POST.get('last_name', '').strip(),
            role=role,
            clinic=request.user.clinic,
        )
        messages.success(request, f'Pengguna {email} berhasil ditambahkan.')
        return redirect(reverse('clinic-users'))
