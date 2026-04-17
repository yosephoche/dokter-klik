"""WhatsApp booking chatbot — stateless handler with Redis-backed session."""
import datetime
import logging

from django.core.cache import cache

from apps.core.utils import normalize_phone as _normalize_phone

logger = logging.getLogger(__name__)


class BookingChatbot:
    """Handles one incoming WhatsApp message turn for a given clinic and sender.

    Session state is persisted in Django's cache (Redis) keyed by clinic+phone
    with a 30-minute TTL so abandoned conversations expire automatically.

    States:
        idle            → initial state, waits for registration keyword
        awaiting_name   → waiting for the patient's full name
        awaiting_doctor → waiting for doctor selection (only when >1 doctor today)
        awaiting_confirm → waiting for "ya" / "batal" confirmation
    """

    _SESSION_KEY = 'wa_chatbot:{clinic_id}:{phone}'
    _SESSION_TTL = 60 * 30  # 30 minutes

    # Keywords that trigger a new registration flow from any state
    _TRIGGER_WORDS = {'daftar', 'antri', 'halo', 'hai', 'hi', 'hello', 'mulai', 'start'}

    def __init__(self, clinic, sender_phone: str):
        self.clinic = clinic
        self.sender_phone = _normalize_phone(sender_phone)
        self._state = self._load_state()

    # --- Session helpers ---

    def _session_key(self) -> str:
        return self._SESSION_KEY.format(clinic_id=self.clinic.id, phone=self.sender_phone)

    def _load_state(self) -> dict:
        return cache.get(self._session_key(), {'step': 'idle'})

    def _save_state(self) -> None:
        cache.set(self._session_key(), self._state, self._SESSION_TTL)

    def _clear_state(self) -> None:
        cache.delete(self._session_key())

    # --- Main dispatch ---

    def handle(self, message_text: str) -> str:
        """Process one incoming message and return the reply text."""
        text = message_text.strip()
        step = self._state.get('step', 'idle')

        # Any trigger word restarts the flow from any state
        if text.lower() in self._TRIGGER_WORDS:
            return self._start()

        if step == 'idle':
            return self._start()
        elif step == 'awaiting_name':
            return self._handle_name(text)
        elif step == 'awaiting_doctor':
            return self._handle_doctor(text)
        elif step == 'awaiting_confirm':
            return self._handle_confirm(text)
        else:
            return self._start()

    # --- State handlers ---

    def _start(self) -> str:
        self._state = {'step': 'awaiting_name'}
        self._save_state()
        return (
            f'Halo! Selamat datang di *{self.clinic.name}*.\n\n'
            'Silakan ketik *nama lengkap* Anda untuk mendaftar antrean hari ini:'
        )

    def _handle_name(self, text: str) -> str:
        if len(text) < 2:
            return 'Mohon masukkan nama lengkap Anda (minimal 2 karakter).'

        self._state['name'] = text
        doctors = self._get_available_doctors()

        if not doctors:
            # Tidak ada dokter hari ini — tetap buat antrian tanpa dokter
            self._state['step'] = 'awaiting_confirm'
            self._state['doctor_id'] = None
            self._save_state()
            return self._confirm_message(doctor_name=None)

        if len(doctors) == 1:
            doctor = doctors[0]
            self._state['step'] = 'awaiting_confirm'
            self._state['doctor_id'] = str(doctor.id)
            self._save_state()
            return self._confirm_message(doctor_name=doctor.full_name)

        # Multiple doctors — ask for selection
        menu = '\n'.join(
            f'{i + 1}. Dr. {d.full_name}' for i, d in enumerate(doctors)
        )
        self._state['step'] = 'awaiting_doctor'
        self._state['doctor_ids'] = [str(d.id) for d in doctors]
        self._save_state()
        return (
            f'Pilih dokter untuk hari ini:\n\n{menu}\n\n'
            'Balas dengan *nomor* pilihan Anda.'
        )

    def _handle_doctor(self, text: str) -> str:
        from apps.accounts.models import CustomUser

        doctor_ids = self._state.get('doctor_ids', [])
        try:
            idx = int(text.strip()) - 1
            if 0 <= idx < len(doctor_ids):
                doctor = CustomUser.objects.get(pk=doctor_ids[idx])
                self._state['step'] = 'awaiting_confirm'
                self._state['doctor_id'] = str(doctor.id)
                self._save_state()
                return self._confirm_message(doctor_name=doctor.full_name)
        except (ValueError, CustomUser.DoesNotExist):
            pass
        return (
            f'Pilihan tidak valid. Balas dengan angka 1–{len(doctor_ids)} '
            'sesuai daftar dokter di atas.'
        )

    def _handle_confirm(self, text: str) -> str:
        normalized = text.lower().strip()
        if normalized in ('ya', 'yes', 'y', 'iya', 'ok', 'oke', 'yep'):
            return self._create_queue()
        elif normalized in ('batal', 'tidak', 'no', 'cancel', 'ga', 'gak', 'tidak'):
            self._clear_state()
            return (
                'Pendaftaran dibatalkan. '
                'Ketik *DAFTAR* kapan saja untuk mendaftar ulang. 😊'
            )
        return 'Ketik *YA* untuk konfirmasi atau *BATAL* untuk membatalkan.'

    # --- Queue creation ---

    def _create_queue(self) -> str:
        from apps.queue.models import QueueEntry
        from apps.patients.models import Patient
        from apps.accounts.models import CustomUser

        name = self._state.get('name', 'Pasien WA')
        doctor_id = self._state.get('doctor_id')

        doctor = None
        if doctor_id:
            try:
                doctor = CustomUser.objects.get(pk=doctor_id)
            except CustomUser.DoesNotExist:
                pass

        # Lookup or create patient by normalized phone
        patient = Patient.objects.for_clinic(self.clinic).filter(
            phone=self.sender_phone
        ).first()

        if not patient:
            mrn = Patient.generate_mrn(self.clinic)
            patient = Patient.objects.create(
                clinic=self.clinic,
                medical_record_number=mrn,
                name=name,
                name_search=name.lower(),
                phone=self.sender_phone,
                gender='other',
            )
        else:
            if patient.name_search != name.lower():
                patient.name = name
                patient.name_search = name.lower()
                patient.save(update_fields=['name', 'name_search'])

        entry = QueueEntry.create_for_clinic(
            clinic=self.clinic,
            patient=patient,
            doctor=doctor,
            source='whatsapp',
        )

        waiting_ahead = QueueEntry.objects.filter(
            clinic=self.clinic,
            queue_date=entry.queue_date,
            status='waiting',
            queue_number__lt=entry.queue_number,
        ).count()

        self._clear_state()

        doctor_line = f'\nDokter: Dr. {doctor.full_name}' if doctor else ''
        ahead_line = (
            f'{waiting_ahead} orang' if waiting_ahead > 0 else 'Anda berikutnya!'
        )

        return (
            f'✅ *Pendaftaran berhasil!*\n\n'
            f'Nama: {name}{doctor_line}\n'
            f'Nomor antrean: *{entry.queue_number}*\n'
            f'Antrian di depan Anda: {ahead_line}\n\n'
            'Kami akan mengirim notifikasi WhatsApp saat giliran Anda hampir tiba.'
        )

    # --- Helpers ---

    def _confirm_message(self, doctor_name) -> str:
        name = self._state.get('name', '')
        doc_line = f'\nDokter: Dr. {doctor_name}' if doctor_name else ''
        return (
            f'Konfirmasi pendaftaran:\n\n'
            f'Nama: *{name}*{doc_line}\n'
            f'Klinik: {self.clinic.name}\n\n'
            'Ketik *YA* untuk konfirmasi atau *BATAL* untuk membatalkan.'
        )

    def _get_available_doctors(self) -> list:
        """Return list of doctors scheduled for today at this clinic."""
        from apps.clinics.models import DoctorSchedule
        from apps.accounts.models import CustomUser

        today_dow = datetime.date.today().weekday()  # 0=Monday
        doctor_ids = DoctorSchedule.objects.filter(
            clinic=self.clinic,
            day_of_week=today_dow,
            is_active=True,
        ).values_list('doctor_id', flat=True)

        return list(CustomUser.objects.filter(
            pk__in=doctor_ids,
            clinic=self.clinic,
            role='doctor',
            is_active=True,
        ))
