"""Tests for queue management: creation, status transitions, recall, online registration."""
import datetime
import uuid
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

TEST_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def make_clinic(name='Klinik Test', slug='klinik-test'):
    from apps.clinics.models import Clinic
    return Clinic.objects.create(name=name, slug=slug)


def make_user(clinic, role='admin', email='admin@klinik.test', password='pass123'):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create_user(
        email=email, password=password, clinic=clinic, role=role,
        first_name='Admin', last_name='Test',
    )


def make_doctor(clinic, email='dr@klinik.test'):
    return make_user(clinic, role='doctor', email=email)


@override_settings(ENCRYPTION_KEY=TEST_KEY)
def make_patient(clinic, name='Budi Santoso', phone='6281234567890'):
    from apps.patients.models import Patient
    return Patient.objects.create(
        clinic=clinic,
        medical_record_number=f'MR{uuid.uuid4().hex[:6].upper()}',
        name=name,
        name_search=name.lower(),
        phone=phone,
        gender='male',
    )


def make_queue_entry(clinic, status='waiting', source='walkin', queue_number=None, patient=None):
    from apps.queue.models import QueueEntry
    if queue_number is None:
        queue_number = QueueEntry.get_next_number(clinic)
    return QueueEntry.objects.create(
        clinic=clinic,
        queue_number=queue_number,
        status=status,
        source=source,
        patient=patient,
    )


# ---------------------------------------------------------------------------
# QueueEntry.create_for_clinic() — atomic number assignment
# ---------------------------------------------------------------------------

class CreateForClinicTests(TestCase):
    """Unit tests for QueueEntry.create_for_clinic() atomic number assignment."""

    def setUp(self):
        self.clinic = make_clinic()

    def test_first_entry_gets_number_one(self):
        from apps.queue.models import QueueEntry
        entry = QueueEntry.create_for_clinic(clinic=self.clinic, source='walkin')
        self.assertEqual(entry.queue_number, 1)

    def test_status_is_waiting(self):
        from apps.queue.models import QueueEntry
        entry = QueueEntry.create_for_clinic(clinic=self.clinic)
        self.assertEqual(entry.status, 'waiting')

    def test_numbers_increment_sequentially(self):
        from apps.queue.models import QueueEntry
        for _ in range(3):
            QueueEntry.create_for_clinic(clinic=self.clinic)
        entry = QueueEntry.create_for_clinic(clinic=self.clinic)
        self.assertEqual(entry.queue_number, 4)

    def test_different_sources_share_same_pool(self):
        """Walk-in, online, and WhatsApp share one sequential number pool."""
        from apps.queue.models import QueueEntry
        e1 = QueueEntry.create_for_clinic(clinic=self.clinic, source='walkin')
        e2 = QueueEntry.create_for_clinic(clinic=self.clinic, source='online')
        e3 = QueueEntry.create_for_clinic(clinic=self.clinic, source='whatsapp')
        self.assertEqual([e1.queue_number, e2.queue_number, e3.queue_number], [1, 2, 3])

    def test_source_is_stored_correctly(self):
        from apps.queue.models import QueueEntry
        entry = QueueEntry.create_for_clinic(clinic=self.clinic, source='online')
        self.assertEqual(entry.source, 'online')

    def test_different_dates_reset_sequence(self):
        """Yesterday's entries do not affect today's sequence."""
        from apps.queue.models import QueueEntry
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        QueueEntry.objects.create(
            clinic=self.clinic, queue_number=10,
            queue_date=yesterday, status='done',
        )
        entry = QueueEntry.create_for_clinic(clinic=self.clinic)
        self.assertEqual(entry.queue_number, 1)

    def test_different_clinics_have_independent_sequences(self):
        from apps.queue.models import QueueEntry
        other = make_clinic(name='Klinik Lain', slug='klinik-lain')
        QueueEntry.create_for_clinic(clinic=self.clinic)
        QueueEntry.create_for_clinic(clinic=self.clinic)
        entry = QueueEntry.create_for_clinic(clinic=other)
        self.assertEqual(entry.queue_number, 1)

    def test_assigns_patient_and_doctor(self):
        from apps.queue.models import QueueEntry
        with self.settings(ENCRYPTION_KEY=TEST_KEY):
            patient = make_patient(self.clinic)
        doctor = make_doctor(self.clinic)
        entry = QueueEntry.create_for_clinic(
            clinic=self.clinic, patient=patient, doctor=doctor
        )
        self.assertEqual(entry.patient, patient)
        self.assertEqual(entry.doctor, doctor)


# ---------------------------------------------------------------------------
# QueueCallView — status transitions
# ---------------------------------------------------------------------------

class QueueCallViewTransitionTests(TestCase):
    """Tests for PATCH /api/queue/<pk>/call/ status transitions."""

    def setUp(self):
        self.clinic = make_clinic()
        self.admin = make_user(self.clinic, email='admin@test.com')
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.admin)

    def _patch(self, entry_id, new_status):
        url = f'/api/queue/{entry_id}/call/'
        return self.api_client.patch(url, {'status': new_status}, format='json')

    def test_waiting_to_called(self):
        entry = make_queue_entry(self.clinic, status='waiting')
        resp = self._patch(entry.id, 'called')
        self.assertEqual(resp.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.status, 'called')
        self.assertIsNotNone(entry.called_at)

    def test_waiting_to_skipped(self):
        entry = make_queue_entry(self.clinic, status='waiting')
        resp = self._patch(entry.id, 'skipped')
        self.assertEqual(resp.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.status, 'skipped')

    def test_called_to_serving(self):
        entry = make_queue_entry(self.clinic, status='called')
        resp = self._patch(entry.id, 'serving')
        self.assertEqual(resp.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.status, 'serving')
        self.assertIsNotNone(entry.serving_at)

    def test_serving_to_done(self):
        entry = make_queue_entry(self.clinic, status='serving')
        resp = self._patch(entry.id, 'done')
        self.assertEqual(resp.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.status, 'done')
        self.assertIsNotNone(entry.done_at)

    # --- Recall mechanism ---

    def test_skipped_to_called_recall(self):
        """Admin can recall a skipped patient — skipped → called transition."""
        entry = make_queue_entry(self.clinic, status='skipped')
        resp = self._patch(entry.id, 'called')
        self.assertEqual(resp.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.status, 'called')

    def test_recall_sets_called_at_timestamp(self):
        """Recall updates called_at so the audit trail is accurate."""
        entry = make_queue_entry(self.clinic, status='skipped')
        self._patch(entry.id, 'called')
        entry.refresh_from_db()
        self.assertIsNotNone(entry.called_at)

    @patch('apps.whatsapp.tasks.send_queue_alert.delay')
    def test_recall_triggers_wa_notification(self, mock_delay):
        """Recall triggers WhatsApp alert for patients near the top of queue."""
        with self.settings(ENCRYPTION_KEY=TEST_KEY):
            patient = make_patient(self.clinic, phone='6281111111111')
        # Three waiting entries before the recalled one
        waiting = make_queue_entry(self.clinic, status='waiting', patient=patient, queue_number=5)
        make_queue_entry(self.clinic, status='waiting', queue_number=6)
        skipped = make_queue_entry(self.clinic, status='skipped', queue_number=4)
        self._patch(skipped.id, 'called')
        # send_queue_alert should be dispatched for waiting patients in top 3
        self.assertTrue(mock_delay.called)

    # --- Invalid transitions ---

    def test_waiting_to_done_is_invalid(self):
        entry = make_queue_entry(self.clinic, status='waiting')
        resp = self._patch(entry.id, 'done')
        self.assertEqual(resp.status_code, 400)

    def test_done_to_called_is_invalid(self):
        entry = make_queue_entry(self.clinic, status='done')
        resp = self._patch(entry.id, 'called')
        self.assertEqual(resp.status_code, 400)

    def test_skipped_to_serving_is_invalid(self):
        entry = make_queue_entry(self.clinic, status='skipped')
        resp = self._patch(entry.id, 'serving')
        self.assertEqual(resp.status_code, 400)

    def test_cannot_access_other_clinics_entry(self):
        other_clinic = make_clinic(name='Klinik Lain', slug='klinik-lain')
        entry = make_queue_entry(other_clinic, status='waiting')
        resp = self._patch(entry.id, 'called')
        self.assertEqual(resp.status_code, 404)

    def test_unauthenticated_returns_401(self):
        entry = make_queue_entry(self.clinic, status='waiting')
        resp = APIClient().patch(f'/api/queue/{entry.id}/call/', {'status': 'called'})
        self.assertIn(resp.status_code, [401, 403])


# ---------------------------------------------------------------------------
# QueueOnlineRegisterView — public self-registration
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class QueueOnlineRegisterViewTests(TestCase):
    """Tests for GET/POST /queue/daftar/<slug>/"""

    def setUp(self):
        self.clinic = make_clinic(slug='test-klinik')
        self.doctor = make_doctor(self.clinic, email='dr@test.com')
        self.url = f'/queue/daftar/{self.clinic.slug}/'

    def _today_schedule(self):
        from apps.clinics.models import DoctorSchedule
        today_dow = datetime.date.today().weekday()
        DoctorSchedule.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            day_of_week=today_dow,
            start_time='08:00',
            end_time='16:00',
            is_active=True,
        )

    def test_get_renders_form_for_active_clinic(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.clinic.name)

    def test_get_shows_doctors_scheduled_today(self):
        self._today_schedule()
        resp = self.client.get(self.url)
        self.assertContains(resp, self.doctor.full_name)

    def test_get_returns_404_for_inactive_clinic(self):
        from apps.clinics.models import Clinic
        inactive = Clinic.objects.create(name='Tutup', slug='tutup', is_active=False)
        resp = self.client.get(f'/queue/daftar/{inactive.slug}/')
        self.assertEqual(resp.status_code, 404)

    def test_post_valid_creates_queue_entry_with_source_online(self):
        from apps.queue.models import QueueEntry
        resp = self.client.post(self.url, {'name': 'Andi Wijaya', 'phone': '08111222333'})
        self.assertEqual(resp.status_code, 302)  # redirect to confirm
        entry = QueueEntry.objects.filter(clinic=self.clinic, source='online').first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.status, 'waiting')

    def test_post_creates_patient_record_for_new_phone(self):
        from apps.patients.models import Patient
        self.client.post(self.url, {'name': 'Siti Rahayu', 'phone': '08222333444'})
        patient = Patient.objects.for_clinic(self.clinic).filter(name_search='siti rahayu').first()
        self.assertIsNotNone(patient)

    def test_post_reuses_existing_patient_with_same_phone(self):
        from apps.patients.models import Patient
        phone = '6281999888777'
        make_patient(self.clinic, name='Existing', phone=phone)
        initial_count = Patient.objects.for_clinic(self.clinic).count()
        self.client.post(self.url, {'name': 'Existing', 'phone': '081999888777'})
        self.assertEqual(Patient.objects.for_clinic(self.clinic).count(), initial_count)

    def test_post_redirects_to_existing_entry_when_phone_already_waiting(self):
        from apps.queue.models import QueueEntry
        from apps.patients.models import Patient
        phone = '6281777666555'
        patient = make_patient(self.clinic, phone=phone)
        existing = make_queue_entry(self.clinic, status='waiting', patient=patient)
        resp = self.client.post(self.url, {'name': patient.name_search.title(), 'phone': '081777666555'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(str(existing.pk), resp['Location'])
        self.assertEqual(QueueEntry.objects.filter(clinic=self.clinic, source='online').count(), 0)

    def test_post_missing_name_returns_form_with_error(self):
        resp = self.client.post(self.url, {'name': '', 'phone': '08123456789'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'wajib diisi')

    def test_post_short_name_returns_form_with_error(self):
        resp = self.client.post(self.url, {'name': 'A', 'phone': '08123456789'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'wajib diisi')

    def test_post_missing_phone_returns_form_with_error(self):
        resp = self.client.post(self.url, {'name': 'Valid Name', 'phone': ''})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'wajib diisi')

    def test_queue_numbers_are_sequential_with_walkin(self):
        """Online registrations share sequence with walk-in entries."""
        from apps.queue.models import QueueEntry
        make_queue_entry(self.clinic, status='waiting', source='walkin', queue_number=1)
        make_queue_entry(self.clinic, status='waiting', source='walkin', queue_number=2)
        self.client.post(self.url, {'name': 'Online User', 'phone': '08555000111'})
        online_entry = QueueEntry.objects.filter(clinic=self.clinic, source='online').last()
        self.assertEqual(online_entry.queue_number, 3)

    def test_post_with_doctor_selection_assigns_doctor(self):
        from apps.queue.models import QueueEntry
        self._today_schedule()
        self.client.post(self.url, {
            'name': 'Pasien Dokter', 'phone': '08333444555',
            'doctor_id': str(self.doctor.id),
        })
        entry = QueueEntry.objects.filter(clinic=self.clinic, source='online').first()
        self.assertEqual(entry.doctor, self.doctor)


# ---------------------------------------------------------------------------
# QueueOnlineConfirmView — confirmation page
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class QueueOnlineConfirmViewTests(TestCase):
    """Tests for GET /queue/daftar/<slug>/konfirmasi/<pk>/"""

    def setUp(self):
        self.clinic = make_clinic(slug='konfirmasi-klinik')

    def test_get_returns_200_with_queue_number(self):
        from apps.queue.models import QueueEntry
        entry = QueueEntry.create_for_clinic(clinic=self.clinic, source='online')
        url = f'/queue/daftar/{self.clinic.slug}/konfirmasi/{entry.pk}/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, str(entry.queue_number))

    def test_shows_waiting_ahead_count(self):
        from apps.queue.models import QueueEntry
        make_queue_entry(self.clinic, status='waiting', queue_number=1)
        make_queue_entry(self.clinic, status='waiting', queue_number=2)
        entry = QueueEntry.create_for_clinic(clinic=self.clinic, source='online')
        url = f'/queue/daftar/{self.clinic.slug}/konfirmasi/{entry.pk}/'
        resp = self.client.get(url)
        self.assertContains(resp, '2')  # 2 entries ahead

    def test_returns_404_for_wrong_clinic(self):
        from apps.queue.models import QueueEntry
        other = make_clinic(name='Wrong', slug='wrong-klinik')
        entry = QueueEntry.create_for_clinic(clinic=other, source='online')
        url = f'/queue/daftar/{self.clinic.slug}/konfirmasi/{entry.pk}/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_contains_link_to_live_display(self):
        from apps.queue.models import QueueEntry
        entry = QueueEntry.create_for_clinic(clinic=self.clinic, source='online')
        url = f'/queue/daftar/{self.clinic.slug}/konfirmasi/{entry.pk}/'
        resp = self.client.get(url)
        self.assertContains(resp, self.clinic.slug)  # live display link includes slug
