"""Queue management web/HTMX views."""
import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from .models import QueueEntry


class QueueManagePageView(LoginRequiredMixin, TemplateView):
    """Full queue management page shell. Data loaded via HTMX partial."""
    template_name = 'queue/management.html'


class QueueManagementPartialView(LoginRequiredMixin, View):
    """HTMX partial: returns HTML rows of today's queue entries."""

    def get(self, request):
        clinic = request.user.clinic
        date_str = request.GET.get('date')
        try:
            date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
        except ValueError:
            date = datetime.date.today()

        entries = QueueEntry.objects.filter(
            clinic=clinic, queue_date=date
        ).select_related('patient', 'doctor').order_by('queue_number')

        return render(request, 'queue/partials/queue_management_rows.html', {
            'entries': entries,
            'today': date,
        })


class QueueEntryCreateView(LoginRequiredMixin, View):
    """HTMX: create a queue entry (walk-in or by patient). POST only."""

    def post(self, request):
        from apps.patients.models import Patient

        clinic = request.user.clinic
        patient = None
        patient_id = request.POST.get('patient_id', '').strip()
        if patient_id:
            try:
                patient = Patient.objects.for_clinic(clinic).get(pk=patient_id)
            except Patient.DoesNotExist:
                pass

        doctor_id = request.POST.get('doctor_id', '').strip()
        doctor = None
        if doctor_id:
            from apps.accounts.models import CustomUser
            try:
                doctor = CustomUser.objects.get(pk=doctor_id, clinic=clinic, role='doctor')
            except CustomUser.DoesNotExist:
                pass

        source = request.POST.get('source', 'walkin')
        if source not in ('walkin', 'whatsapp', 'online'):
            source = 'walkin'

        next_number = QueueEntry.get_next_number(clinic)
        QueueEntry.objects.create(
            clinic=clinic,
            patient=patient,
            doctor=doctor,
            queue_number=next_number,
            source=source,
            status='waiting',
        )
        # Re-render the full queue list as HTMX partial response
        entries = QueueEntry.objects.filter(
            clinic=clinic, queue_date=datetime.date.today()
        ).select_related('patient', 'doctor').order_by('queue_number')

        return render(request, 'queue/partials/queue_management_rows.html', {
            'entries': entries,
            'today': datetime.date.today(),
        })
