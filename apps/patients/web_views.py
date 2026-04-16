"""Patient web/HTMX views: list page, create form, HTMX partial."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from .models import Patient


class PatientListPageView(LoginRequiredMixin, TemplateView):
    """Full patient list page shell. Data loaded via HTMX partial."""
    template_name = 'patients/list.html'


class PatientListPartialView(LoginRequiredMixin, View):
    """HTMX partial: returns HTML rows of patients filtered by ?q=."""

    def get(self, request):
        q = request.GET.get('q', '').strip()
        qs = Patient.objects.for_clinic(request.user.clinic)
        if q:
            qs = qs.filter(name_search__icontains=q) | qs.filter(
                medical_record_number__istartswith=q
            )
        patients = qs.order_by('name_search')[:50]
        return render(request, 'patients/partials/patient_rows.html',
                      {'patients': patients})


class PatientCreateView(LoginRequiredMixin, View):
    """Create a new patient. GET: form, POST: save + redirect to list."""

    def get(self, request):
        return render(request, 'patients/create.html', {'errors': {}})

    def post(self, request):
        errors = {}

        clinic = request.user.clinic
        if not clinic:
            errors['__all__'] = 'Akun Anda belum terhubung ke klinik. Hubungi administrator.'
            return render(request, 'patients/create.html', {
                'errors': errors,
                'data': request.POST,
            })

        name = request.POST.get('name', '').strip()
        if not name:
            errors['name'] = 'Nama wajib diisi.'

        gender = request.POST.get('gender', '').strip()
        if gender not in ('male', 'female', 'other'):
            errors['gender'] = 'Pilih jenis kelamin.'

        if errors:
            return render(request, 'patients/create.html', {
                'errors': errors,
                'data': request.POST,
            })
        mrn = Patient.generate_mrn(clinic)

        Patient.objects.create(
            clinic=clinic,
            medical_record_number=mrn,
            name=name,
            name_search=name.lower(),
            nik=request.POST.get('nik', '').strip() or None,
            dob=request.POST.get('dob') or None,
            gender=gender,
            phone=request.POST.get('phone', '').strip(),
            address=request.POST.get('address', '').strip(),
            blood_type=request.POST.get('blood_type', '').strip(),
            allergy_notes=request.POST.get('allergy_notes', '').strip(),
        )
        return redirect(reverse('patient-list-web'))
