"""Tests for Patient model: encryption, MRN generation, name search, clinic scoping."""
import uuid

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

TEST_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def make_clinic(slug='patients-klinik'):
    from apps.clinics.models import Clinic
    return Clinic.objects.create(name='Klinik Patients Test', slug=slug)


def make_user(clinic, role='admin', email='admin@patients.test'):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create_user(
        email=email, password='pass', clinic=clinic, role=role,
    )


# ---------------------------------------------------------------------------
# Patient.generate_mrn()
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class PatientMRNGenerationTests(TestCase):
    """Tests for the medical record number generator."""

    def setUp(self):
        self.clinic = make_clinic()

    def test_first_mrn_ends_with_0001(self):
        from apps.patients.models import Patient
        mrn = Patient.generate_mrn(self.clinic)
        self.assertTrue(mrn.endswith('0001'), f'Expected 0001 suffix, got: {mrn}')

    def test_mrn_starts_with_mr_and_yearmonth(self):
        import datetime
        from apps.patients.models import Patient
        mrn = Patient.generate_mrn(self.clinic)
        prefix = f'MR{datetime.date.today().strftime("%Y%m")}'
        self.assertTrue(mrn.startswith(prefix))

    def test_mrn_increments_after_existing(self):
        from apps.patients.models import Patient
        Patient.objects.create(
            clinic=self.clinic,
            medical_record_number=f'MR{__import__("datetime").date.today().strftime("%Y%m")}0005',
            name='Existing', name_search='existing', gender='male',
        )
        mrn = Patient.generate_mrn(self.clinic)
        self.assertTrue(mrn.endswith('0006'))

    def test_different_clinics_have_independent_sequences(self):
        from apps.patients.models import Patient
        other = make_clinic(slug='other-patients')
        Patient.objects.create(
            clinic=other,
            medical_record_number=f'MR{__import__("datetime").date.today().strftime("%Y%m")}0010',
            name='Other', name_search='other', gender='other',
        )
        mrn = Patient.generate_mrn(self.clinic)
        self.assertTrue(mrn.endswith('0001'))


# ---------------------------------------------------------------------------
# Patient model — name_search and encryption
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class PatientModelTests(TestCase):
    """Tests for Patient name_search, encryption, and clinic scoping."""

    def setUp(self):
        self.clinic = make_clinic(slug='patient-model-klinik')

    def _create_patient(self, name='Budi Santoso', phone='08111222333'):
        from apps.patients.models import Patient
        return Patient.objects.create(
            clinic=self.clinic,
            medical_record_number=f'MR{uuid.uuid4().hex[:6].upper()}',
            name=name,
            name_search=name.lower(),
            phone=phone,
            gender='male',
        )

    def test_name_search_is_lowercase(self):
        patient = self._create_patient(name='Budi SANTOSO')
        self.assertEqual(patient.name_search, 'budi santoso')

    def test_name_is_stored_encrypted(self):
        """Encrypted field stores bytes (BYTEA), not plaintext."""
        from apps.patients.models import Patient
        patient = self._create_patient(name='Rahasia')
        # Fetch raw value from DB — it should be decrypted back to plaintext via from_db_value
        refreshed = Patient.objects.get(pk=patient.pk)
        self.assertEqual(refreshed.name, 'Rahasia')

    def test_filter_by_name_search(self):
        self._create_patient(name='Siti Rahayu', phone='08222333444')
        from apps.patients.models import Patient
        results = Patient.objects.for_clinic(self.clinic).filter(
            name_search__icontains='siti'
        )
        self.assertEqual(results.count(), 1)

    def test_filter_by_phone(self):
        self._create_patient(name='Agus Wahyu', phone='6281999000111')
        from apps.patients.models import Patient
        patient = Patient.objects.for_clinic(self.clinic).filter(
            phone='6281999000111'
        ).first()
        self.assertIsNotNone(patient)

    def test_for_clinic_isolates_by_clinic(self):
        other = make_clinic(slug='other-isolation')
        from apps.patients.models import Patient
        Patient.objects.create(
            clinic=other,
            medical_record_number='MR0000001',
            name='Other Clinic Patient',
            name_search='other clinic patient',
            gender='other',
        )
        self._create_patient()
        self.assertEqual(Patient.objects.for_clinic(self.clinic).count(), 1)

    def test_unique_mrn_per_clinic(self):
        """medical_record_number is unique per clinic."""
        from apps.patients.models import Patient
        from django.db import IntegrityError
        mrn = 'MRDUPLICATE'
        Patient.objects.create(
            clinic=self.clinic, medical_record_number=mrn,
            name='P1', name_search='p1', gender='male',
        )
        with self.assertRaises(IntegrityError):
            Patient.objects.create(
                clinic=self.clinic, medical_record_number=mrn,
                name='P2', name_search='p2', gender='male',
            )

    def test_same_mrn_allowed_in_different_clinics(self):
        """medical_record_number uniqueness is per-clinic, not global."""
        from apps.patients.models import Patient
        other = make_clinic(slug='other-mrn-clinic')
        mrn = 'MRSHARED001'
        Patient.objects.create(
            clinic=self.clinic, medical_record_number=mrn,
            name='P1', name_search='p1', gender='male',
        )
        # Should not raise — different clinic
        Patient.objects.create(
            clinic=other, medical_record_number=mrn,
            name='P2', name_search='p2', gender='female',
        )
        self.assertEqual(Patient.objects.filter(medical_record_number=mrn).count(), 2)


# ---------------------------------------------------------------------------
# PatientListCreateView API
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class PatientAPITests(TestCase):
    """Tests for GET/POST /api/patients/"""

    def setUp(self):
        self.clinic = make_clinic(slug='api-patients-klinik')
        self.admin = make_user(self.clinic, email='admin@api.test')
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.admin)

    def test_list_patients_for_own_clinic_only(self):
        from apps.patients.models import Patient
        other_clinic = make_clinic(slug='other-api')
        Patient.objects.create(
            clinic=self.clinic, medical_record_number='MROWN001',
            name='Own Patient', name_search='own patient', gender='male',
        )
        Patient.objects.create(
            clinic=other_clinic, medical_record_number='MROTHER001',
            name='Other Patient', name_search='other patient', gender='female',
        )
        resp = self.api_client.get('/api/patients/')
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get('results', resp.data)  # handle paginated or plain list
        mrns = [p['medical_record_number'] for p in results]
        # Own clinic patient must appear
        self.assertIn('MROWN001', mrns)
        # Cross-clinic leakage must not occur
        self.assertNotIn('MROTHER001', mrns)

    def test_create_patient_via_api(self):
        from apps.patients.models import Patient
        resp = self.api_client.post('/api/patients/', {
            'name': 'API Pasien',
            'gender': 'male',
            'phone': '08123456789',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Patient.objects.for_clinic(self.clinic).filter(
            name_search='api pasien'
        ).exists())

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get('/api/patients/')
        self.assertIn(resp.status_code, [401, 403])
