"""Tests for EMR views: ICD-10 search, visit CRUD, finalize, autosave."""
import uuid
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

TEST_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def make_clinic():
    from apps.clinics.models import Clinic
    return Clinic.objects.create(name='Klinik EMR Test', slug='klinik-emr-test')


def make_user(clinic, role='doctor', email='dr@emr.test'):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create_user(
        email=email, password='pass', clinic=clinic, role=role,
        first_name='Dokter', last_name='EMR',
    )


@override_settings(ENCRYPTION_KEY=TEST_KEY)
def make_patient(clinic):
    from apps.patients.models import Patient
    return Patient.objects.create(
        clinic=clinic,
        medical_record_number=f'MR{uuid.uuid4().hex[:6].upper()}',
        name='Pasien EMR',
        name_search='pasien emr',
        phone='08111222333',
        gender='male',
    )


def make_icd10(code='A09', description_id='Diare', description_en='Diarrhoea'):
    from apps.emr.models import ICD10Code
    return ICD10Code.objects.create(
        code=code, description_en=description_en, description_id=description_id,
        is_billable=True,
    )


# ---------------------------------------------------------------------------
# ICD10SearchView
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class ICD10SearchViewTests(TestCase):
    """Tests for GET /api/icd10/?q=<query>"""

    def setUp(self):
        self.clinic = make_clinic()
        self.doctor = make_user(self.clinic)
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.doctor)

        make_icd10('A09', 'Diare akut', 'Acute diarrhoea')
        make_icd10('J00', 'Pilek biasa', 'Common cold')
        make_icd10('K29', 'Gastritis', 'Gastritis')

    def test_query_less_than_2_chars_returns_empty(self):
        resp = self.api_client.get('/api/icd10/?q=A')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

    def test_code_prefix_search_returns_matching_code(self):
        resp = self.api_client.get('/api/icd10/?q=A09')
        self.assertEqual(resp.status_code, 200)
        codes = [item['code'] for item in resp.data]
        self.assertIn('A09', codes)

    def test_description_search_indonesian(self):
        # Query must be >5 chars to avoid being treated as code prefix
        resp = self.api_client.get('/api/icd10/?q=diare akut&lang=id')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) > 0)
        codes = [item['code'] for item in resp.data]
        self.assertIn('A09', codes)

    def test_description_search_english(self):
        # 'diarrhoea' = 9 chars, goes to description search path
        resp = self.api_client.get('/api/icd10/?q=diarrhoea&lang=en')
        self.assertEqual(resp.status_code, 200)
        codes = [item['code'] for item in resp.data]
        self.assertIn('A09', codes)

    def test_non_billable_codes_excluded(self):
        from apps.emr.models import ICD10Code
        ICD10Code.objects.create(
            code='Z99', description_en='Non-billable', description_id='Non-billable',
            is_billable=False,
        )
        resp = self.api_client.get('/api/icd10/?q=Z99')
        codes = [item['code'] for item in resp.data]
        self.assertNotIn('Z99', codes)

    def test_returns_at_most_20_results(self):
        from apps.emr.models import ICD10Code
        for i in range(25):
            ICD10Code.objects.get_or_create(
                code=f'X{i:02d}',
                defaults={'description_en': 'test', 'description_id': 'test', 'is_billable': True},
            )
        resp = self.api_client.get('/api/icd10/?q=test&lang=en')
        self.assertLessEqual(len(resp.data), 20)


# ---------------------------------------------------------------------------
# VisitFinalizeView
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class VisitFinalizeViewTests(TestCase):
    """Tests for POST /api/visits/<pk>/finalize/"""

    def setUp(self):
        self.clinic = make_clinic()
        self.doctor = make_user(self.clinic)
        self.patient = make_patient(self.clinic)
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.doctor)

    def _make_visit(self, status='draft'):
        from apps.emr.models import Visit
        return Visit.objects.create(
            clinic=self.clinic, patient=self.patient, doctor=self.doctor, status=status
        )

    def _finalize(self, visit):
        return self.api_client.post(f'/api/visits/{visit.id}/finalize/')

    def _add_diagnosis(self, visit, code='A09', is_primary=False):
        from apps.emr.models import Diagnosis
        return Diagnosis.objects.create(
            visit=visit,
            icd10_code=code,
            icd10_description_en='Test diagnosis',
            is_primary=is_primary,
        )

    def test_finalize_without_diagnosis_returns_400(self):
        visit = self._make_visit()
        resp = self._finalize(visit)
        self.assertEqual(resp.status_code, 400)

    def test_finalize_without_primary_diagnosis_returns_400(self):
        visit = self._make_visit()
        self._add_diagnosis(visit, is_primary=False)
        resp = self._finalize(visit)
        self.assertEqual(resp.status_code, 400)

    @patch('apps.satusehat.tasks.sync_encounter_to_satusehat.delay')
    def test_finalize_with_primary_diagnosis_returns_200(self, mock_sync):
        visit = self._make_visit()
        self._add_diagnosis(visit, is_primary=True)
        resp = self._finalize(visit)
        self.assertEqual(resp.status_code, 200)

    @patch('apps.satusehat.tasks.sync_encounter_to_satusehat.delay')
    def test_finalize_sets_status_to_finalized(self, mock_sync):
        visit = self._make_visit()
        self._add_diagnosis(visit, is_primary=True)
        self._finalize(visit)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'finalized')

    @patch('apps.satusehat.tasks.sync_encounter_to_satusehat.delay')
    def test_finalize_sets_finalized_at_timestamp(self, mock_sync):
        visit = self._make_visit()
        self._add_diagnosis(visit, is_primary=True)
        self._finalize(visit)
        visit.refresh_from_db()
        self.assertIsNotNone(visit.finalized_at)

    @patch('apps.satusehat.tasks.sync_encounter_to_satusehat.delay')
    def test_finalize_creates_invoice(self, mock_sync):
        from apps.billing.models import Invoice
        visit = self._make_visit()
        self._add_diagnosis(visit, is_primary=True)
        self._finalize(visit)
        self.assertTrue(Invoice.objects.filter(visit=visit).exists())

    @patch('apps.satusehat.tasks.sync_encounter_to_satusehat.delay')
    def test_finalize_queues_satusehat_sync(self, mock_sync):
        visit = self._make_visit()
        self._add_diagnosis(visit, is_primary=True)
        self._finalize(visit)
        mock_sync.assert_called_once_with(str(visit.id))

    @patch('apps.satusehat.tasks.sync_encounter_to_satusehat.delay')
    def test_finalize_is_idempotent(self, mock_sync):
        """Finalizing an already-finalized visit returns 200 without re-processing."""
        visit = self._make_visit(status='finalized')
        resp = self._finalize(visit)
        self.assertEqual(resp.status_code, 200)

    def test_cannot_access_other_clinics_visit(self):
        from apps.clinics.models import Clinic
        from apps.emr.models import Visit
        other_clinic = Clinic.objects.create(name='Other', slug='other-emr')
        other_patient = make_patient(other_clinic)
        other_doctor = make_user(other_clinic, email='dr@other.test')
        other_visit = Visit.objects.create(
            clinic=other_clinic, patient=other_patient, doctor=other_doctor
        )
        resp = self._finalize(other_visit)
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# VisitAutosaveView
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class VisitAutosaveViewTests(TestCase):
    """Tests for PATCH /api/visits/<pk>/autosave/"""

    def setUp(self):
        self.clinic = make_clinic()
        self.doctor = make_user(self.clinic, email='dr2@emr.test')
        self.patient = make_patient(self.clinic)
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.doctor)

    def _make_visit(self, status='draft'):
        from apps.emr.models import Visit
        return Visit.objects.create(
            clinic=self.clinic, patient=self.patient, doctor=self.doctor, status=status
        )

    def test_autosave_updates_soap_fields(self):
        visit = self._make_visit()
        resp = self.api_client.patch(
            f'/api/visits/{visit.id}/autosave/',
            {'soap_subjective': 'Pasien mengeluh pusing'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        visit.refresh_from_db()
        self.assertIn('pusing', visit.soap_subjective)

    def test_autosave_sets_last_autosave_timestamp(self):
        visit = self._make_visit()
        self.api_client.patch(
            f'/api/visits/{visit.id}/autosave/',
            {'soap_subjective': 'test'},
            format='json',
        )
        visit.refresh_from_db()
        self.assertIsNotNone(visit.last_autosave)

    def test_cannot_autosave_finalized_visit(self):
        visit = self._make_visit(status='finalized')
        resp = self.api_client.patch(
            f'/api/visits/{visit.id}/autosave/',
            {'soap_subjective': 'test'},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# DiagnosisListCreateView
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class DiagnosisListCreateViewTests(TestCase):
    """Tests for GET/POST /api/visits/<pk>/diagnoses/"""

    def setUp(self):
        self.clinic = make_clinic()
        self.doctor = make_user(self.clinic, email='dr3@emr.test')
        self.patient = make_patient(self.clinic)
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.doctor)
        from apps.emr.models import Visit
        self.visit = Visit.objects.create(
            clinic=self.clinic, patient=self.patient, doctor=self.doctor
        )

    def test_add_diagnosis_to_draft_visit(self):
        resp = self.api_client.post(
            f'/api/visits/{self.visit.id}/diagnoses/',
            {'icd10_code': 'A09', 'icd10_description_en': 'Diarrhoea', 'is_primary': True},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)

    def test_cannot_add_diagnosis_to_finalized_visit(self):
        self.visit.status = 'finalized'
        self.visit.save()
        resp = self.api_client.post(
            f'/api/visits/{self.visit.id}/diagnoses/',
            {'icd10_code': 'A09', 'icd10_description_en': 'test', 'is_primary': True},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)
