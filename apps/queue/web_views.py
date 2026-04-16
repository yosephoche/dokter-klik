"""Queue management web/HTMX views."""
import datetime
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from .models import QueueEntry

logger = logging.getLogger(__name__)


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
        if not clinic:
            return HttpResponse('Akun belum terhubung ke klinik.', status=400)

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

        today = datetime.date.today()
        for attempt in range(3):
            try:
                with transaction.atomic():
                    # Lock today's entries for this clinic to prevent concurrent numbering
                    agg = QueueEntry.objects.select_for_update().filter(
                        clinic=clinic, queue_date=today
                    ).aggregate(Max('queue_number'))
                    next_number = (agg['queue_number__max'] or 0) + 1
                    QueueEntry.objects.create(
                        clinic=clinic,
                        patient=patient,
                        doctor=doctor,
                        queue_number=next_number,
                        source=source,
                        status='waiting',
                    )
                break
            except IntegrityError:
                logger.warning(
                    'Queue number collision for clinic %s, attempt %d/3',
                    clinic.id, attempt + 1,
                )
                if attempt == 2:
                    raise

        # Re-render the full queue list as HTMX partial response
        entries = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today
        ).select_related('patient', 'doctor').order_by('queue_number')

        return render(request, 'queue/partials/queue_management_rows.html', {
            'entries': entries,
            'today': today,
        })
