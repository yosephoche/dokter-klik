"""Queue management web/HTMX views."""
import datetime
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from .models import QueueEntry

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """Normalize phone to digits-only E.164 format without leading +.

    Converts '0812...' → '62812...', strips spaces and dashes.
    """
    digits = ''.join(c for c in phone if c.isdigit())
    if digits.startswith('0'):
        digits = '62' + digits[1:]
    return digits


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

        QueueEntry.create_for_clinic(clinic=clinic, patient=patient, doctor=doctor, source=source)

        today = datetime.date.today()
        entries = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today
        ).select_related('patient', 'doctor').order_by('queue_number')

        return render(request, 'queue/partials/queue_management_rows.html', {
            'entries': entries,
            'today': today,
        })


class QueueOnlineRegisterView(View):
    """Public self-registration form. No auth required."""

    def _get_clinic_and_doctors(self, clinic_slug):
        from apps.clinics.models import Clinic, DoctorSchedule
        clinic = get_object_or_404(Clinic, slug=clinic_slug, is_active=True)
        today_dow = datetime.date.today().weekday()
        doctor_ids = DoctorSchedule.objects.filter(
            clinic=clinic, day_of_week=today_dow, is_active=True
        ).values_list('doctor_id', flat=True)
        from apps.accounts.models import CustomUser
        doctors = list(CustomUser.objects.filter(
            pk__in=doctor_ids, clinic=clinic, role='doctor', is_active=True
        ))
        return clinic, doctors

    def get(self, request, clinic_slug):
        clinic, doctors = self._get_clinic_and_doctors(clinic_slug)
        return render(request, 'queue/online_register.html', {
            'clinic': clinic,
            'doctors': doctors,
            'errors': {},
        })

    def post(self, request, clinic_slug):
        from apps.patients.models import Patient
        from apps.accounts.models import CustomUser

        clinic, doctors = self._get_clinic_and_doctors(clinic_slug)

        name = request.POST.get('name', '').strip()
        phone_raw = request.POST.get('phone', '').strip()
        doctor_id = request.POST.get('doctor_id', '').strip()

        errors = {}
        if len(name) < 2:
            errors['name'] = 'Nama lengkap wajib diisi (minimal 2 karakter).'
        if not phone_raw:
            errors['phone'] = 'Nomor telepon wajib diisi.'

        if errors:
            return render(request, 'queue/online_register.html', {
                'clinic': clinic,
                'doctors': doctors,
                'errors': errors,
                'form': {'name': name, 'phone': phone_raw, 'doctor_id': doctor_id},
            })

        phone = _normalize_phone(phone_raw)

        # Cek apakah sudah punya antrian aktif hari ini
        today = datetime.date.today()
        existing_patient = Patient.objects.for_clinic(clinic).filter(phone=phone).first()
        if existing_patient:
            existing_entry = QueueEntry.objects.filter(
                clinic=clinic,
                patient=existing_patient,
                queue_date=today,
                status='waiting',
            ).first()
            if existing_entry:
                return redirect('queue-online-confirm', clinic_slug=clinic_slug, entry_pk=existing_entry.pk)

        doctor = None
        if doctor_id:
            try:
                doctor = CustomUser.objects.get(pk=doctor_id, clinic=clinic, role='doctor')
            except CustomUser.DoesNotExist:
                pass

        # Lookup or create patient
        if existing_patient:
            patient = existing_patient
            if patient.name_search != name.lower():
                patient.name = name
                patient.name_search = name.lower()
                patient.save(update_fields=['name', 'name_search'])
        else:
            mrn = Patient.generate_mrn(clinic)
            patient = Patient.objects.create(
                clinic=clinic,
                medical_record_number=mrn,
                name=name,
                name_search=name.lower(),
                phone=phone,
                gender='other',
            )

        entry = QueueEntry.create_for_clinic(
            clinic=clinic, patient=patient, doctor=doctor, source='online'
        )
        return redirect('queue-online-confirm', clinic_slug=clinic_slug, entry_pk=entry.pk)


class QueueOnlineConfirmView(View):
    """Public confirmation page after online registration. No auth required."""

    def get(self, request, clinic_slug, entry_pk):
        from apps.clinics.models import Clinic
        clinic = get_object_or_404(Clinic, slug=clinic_slug, is_active=True)
        entry = get_object_or_404(QueueEntry, pk=entry_pk, clinic=clinic)

        today = datetime.date.today()
        waiting_ahead = QueueEntry.objects.filter(
            clinic=clinic,
            queue_date=today,
            status='waiting',
            queue_number__lt=entry.queue_number,
        ).count()

        return render(request, 'queue/online_confirm.html', {
            'clinic': clinic,
            'entry': entry,
            'waiting_ahead': waiting_ahead,
        })
