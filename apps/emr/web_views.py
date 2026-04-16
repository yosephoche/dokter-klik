"""EMR web/HTMX views: SOAP form page, visit list, ICD-10 search partial."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from .models import Visit, ICD10Code


class VisitListPageView(LoginRequiredMixin, TemplateView):
    """Full visit list page shell. Data loaded via HTMX partial."""
    template_name = 'emr/visit_list.html'


class VisitListPartialView(LoginRequiredMixin, View):
    """HTMX partial: returns HTML rows of visits scoped to clinic."""

    def get(self, request):
        qs = Visit.objects.for_clinic(request.user.clinic).select_related(
            'patient', 'doctor'
        )
        patient_id = request.GET.get('patient')
        if patient_id:
            qs = qs.filter(patient_id=patient_id)

        # Doctors only see their own visits
        if request.user.role == 'doctor':
            qs = qs.filter(doctor=request.user)

        visits = qs.order_by('-visit_date')[:50]
        return render(request, 'emr/partials/visit_rows.html', {'visits': visits})


class SOAPFormView(LoginRequiredMixin, View):
    """Full SOAP form page. Fetches visit + patient from clinic scope."""

    def get(self, request, pk):
        qs = Visit.objects.for_clinic(request.user.clinic).prefetch_related(
            'diagnoses', 'prescriptions'
        )
        # Doctors only see their own visits
        if request.user.role == 'doctor':
            qs = qs.filter(doctor=request.user)

        visit = get_object_or_404(qs, pk=pk)
        return render(request, 'emr/soap_form.html', {
            'visit': visit,
            'patient': visit.patient,
        })


class VisitCreateView(LoginRequiredMixin, View):
    """POST: create a new Visit for a patient and redirect to its SOAP form."""

    def post(self, request):
        from apps.patients.models import Patient

        clinic = request.user.clinic
        patient_id = request.POST.get('patient_id', '').strip()

        try:
            patient = Patient.objects.for_clinic(clinic).get(pk=patient_id)
        except (Patient.DoesNotExist, ValueError):
            return redirect(reverse('patient-list-web'))

        visit = Visit.objects.create(
            clinic=clinic,
            patient=patient,
            doctor=request.user,
            status='draft',
        )
        return redirect(reverse('soap-form', kwargs={'pk': visit.pk}))


class ICD10SearchPartialView(LoginRequiredMixin, View):
    """HTMX partial: ICD-10 search results as HTML dropdown items."""

    def get(self, request):
        q = request.GET.get('q', '').strip()
        lang = request.GET.get('lang', 'id')

        if len(q) < 2:
            return render(request, 'emr/partials/icd10_results.html', {'results': []})

        qs = ICD10Code.objects.filter(is_billable=True)
        if q[0].isalpha() and len(q) <= 5:
            qs = qs.filter(code__istartswith=q.upper())
        else:
            search_field = 'description_id' if lang == 'id' else 'description_en'
            qs = qs.filter(**{f'{search_field}__icontains': q})

        results = qs[:20]
        return render(request, 'emr/partials/icd10_results.html', {
            'results': results,
            'lang': lang,
        })
