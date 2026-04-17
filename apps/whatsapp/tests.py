"""Tests for WhatsApp chatbot state machine and client."""
import uuid
from unittest.mock import patch, MagicMock

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

TEST_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def make_clinic(slug='wa-klinik'):
    from apps.clinics.models import Clinic
    return Clinic.objects.create(
        name='Klinik WA Test',
        slug=slug,
        whatsapp_phone_number_id='1234567890',
        is_active=True,
    )


def make_doctor(clinic, email='dr.wa@test.com'):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create_user(
        email=email, password='pass', clinic=clinic, role='doctor',
        first_name='Dokter', last_name='Test',
    )


def make_schedule(clinic, doctor):
    """Create a DoctorSchedule for today's day of week."""
    import datetime
    from apps.clinics.models import DoctorSchedule
    today_dow = datetime.date.today().weekday()
    return DoctorSchedule.objects.create(
        clinic=clinic,
        doctor=doctor,
        day_of_week=today_dow,
        start_time='08:00',
        end_time='16:00',
        is_active=True,
    )


# ---------------------------------------------------------------------------
# BookingChatbot state machine
# ---------------------------------------------------------------------------

@override_settings(ENCRYPTION_KEY=TEST_KEY)
class BookingChatbotIdleTests(TestCase):
    """Tests for chatbot trigger and idle state handling."""

    def setUp(self):
        self.clinic = make_clinic()
        self.phone = '6281234567890'

    def _chatbot(self):
        from apps.whatsapp.chatbot import BookingChatbot
        return BookingChatbot(clinic=self.clinic, sender_phone=self.phone)

    @patch('django.core.cache.cache.get', return_value={'step': 'idle'})
    @patch('django.core.cache.cache.set')
    def test_trigger_word_daftar_starts_flow(self, mock_set, mock_get):
        bot = self._chatbot()
        reply = bot.handle('daftar')
        self.assertIn('nama lengkap', reply.lower())

    @patch('django.core.cache.cache.get', return_value={'step': 'idle'})
    @patch('django.core.cache.cache.set')
    def test_trigger_word_halo_starts_flow(self, mock_set, mock_get):
        bot = self._chatbot()
        reply = bot.handle('halo')
        self.assertIn('nama lengkap', reply.lower())

    @patch('django.core.cache.cache.get', return_value={'step': 'awaiting_name'})
    @patch('django.core.cache.cache.set')
    def test_trigger_word_in_awaiting_state_restarts(self, mock_set, mock_get):
        """Even mid-conversation, trigger words restart the flow."""
        bot = self._chatbot()
        reply = bot.handle('daftar')
        self.assertIn('nama lengkap', reply.lower())


@override_settings(ENCRYPTION_KEY=TEST_KEY)
class BookingChatbotNameTests(TestCase):
    """Tests for name collection state."""

    def setUp(self):
        self.clinic = make_clinic(slug='wa-name-klinik')
        self.phone = '6281234567891'

    def _chatbot(self, step='awaiting_name', extra=None):
        from apps.whatsapp.chatbot import BookingChatbot
        state = {'step': step}
        if extra:
            state.update(extra)
        with patch('django.core.cache.cache.get', return_value=state), \
             patch('django.core.cache.cache.set'), \
             patch('django.core.cache.cache.delete'):
            bot = BookingChatbot(clinic=self.clinic, sender_phone=self.phone)
            return bot

    def test_short_name_returns_error(self):
        bot = self._chatbot()
        with patch('django.core.cache.cache.set'):
            reply = bot.handle('A')
        self.assertIn('nama lengkap', reply.lower())

    def test_valid_name_with_no_doctors_goes_to_confirm(self):
        """If no doctors scheduled today, chatbot still asks for confirmation before creating."""
        bot = self._chatbot()
        with patch('django.core.cache.cache.set'):
            reply = bot.handle('Budi Santoso')
        # No doctors → goes to awaiting_confirm (no doctor line in message)
        self.assertIn('konfirmasi', reply.lower())

    def test_valid_name_with_one_doctor_goes_to_confirm(self):
        """With exactly one doctor, no selection step — go straight to confirm."""
        doctor = make_doctor(self.clinic)
        make_schedule(self.clinic, doctor)
        bot = self._chatbot()
        with patch('django.core.cache.cache.set'):
            reply = bot.handle('Dewi Lestari')
        self.assertIn('konfirmasi', reply.lower())

    def test_valid_name_with_multiple_doctors_shows_selection(self):
        """With multiple doctors, chatbot shows numbered doctor list."""
        dr1 = make_doctor(self.clinic, email='dr1@test.com')
        dr2 = make_doctor(self.clinic, email='dr2@test.com')
        make_schedule(self.clinic, dr1)
        make_schedule(self.clinic, dr2)
        bot = self._chatbot()
        with patch('django.core.cache.cache.set'):
            reply = bot.handle('Agus Wahyu')
        self.assertIn('1.', reply)
        self.assertIn('2.', reply)


@override_settings(ENCRYPTION_KEY=TEST_KEY)
class BookingChatbotDoctorSelectionTests(TestCase):
    """Tests for doctor selection state."""

    def setUp(self):
        self.clinic = make_clinic(slug='wa-doctor-klinik')
        self.phone = '6281234567892'
        self.dr1 = make_doctor(self.clinic, email='dr1@doc.test')
        self.dr2 = make_doctor(self.clinic, email='dr2@doc.test')

    def _chatbot(self):
        from apps.whatsapp.chatbot import BookingChatbot
        state = {
            'step': 'awaiting_doctor',
            'name': 'Test Patient',
            'doctor_ids': [str(self.dr1.id), str(self.dr2.id)],
        }
        with patch('django.core.cache.cache.get', return_value=state), \
             patch('django.core.cache.cache.set'), \
             patch('django.core.cache.cache.delete'):
            return BookingChatbot(clinic=self.clinic, sender_phone=self.phone)

    def test_valid_selection_moves_to_confirm(self):
        bot = self._chatbot()
        with patch('django.core.cache.cache.set'):
            reply = bot.handle('1')
        self.assertIn('konfirmasi', reply.lower())

    def test_invalid_selection_returns_error(self):
        bot = self._chatbot()
        with patch('django.core.cache.cache.set'):
            reply = bot.handle('99')
        self.assertIn('tidak valid', reply.lower())

    def test_non_numeric_selection_returns_error(self):
        bot = self._chatbot()
        with patch('django.core.cache.cache.set'):
            reply = bot.handle('ya')
        self.assertIn('tidak valid', reply.lower())


@override_settings(ENCRYPTION_KEY=TEST_KEY)
class BookingChatbotConfirmTests(TestCase):
    """Tests for confirmation state."""

    def setUp(self):
        self.clinic = make_clinic(slug='wa-confirm-klinik')
        self.phone = '6281234567893'

    def _chatbot(self, doctor_id=None):
        from apps.whatsapp.chatbot import BookingChatbot
        state = {
            'step': 'awaiting_confirm',
            'name': 'Siti Rahayu',
            'doctor_id': doctor_id,
        }
        with patch('django.core.cache.cache.get', return_value=state), \
             patch('django.core.cache.cache.set'), \
             patch('django.core.cache.cache.delete'):
            return BookingChatbot(clinic=self.clinic, sender_phone=self.phone)

    def test_ya_creates_queue_entry(self):
        from apps.queue.models import QueueEntry
        bot = self._chatbot()
        with patch('django.core.cache.cache.delete'), \
             patch('django.core.cache.cache.set'):
            reply = bot.handle('ya')
        self.assertIn('berhasil', reply.lower())
        entry = QueueEntry.objects.filter(clinic=self.clinic, source='whatsapp').first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.status, 'waiting')

    def test_iya_creates_queue_entry(self):
        """Alternative confirmation word 'iya' is accepted."""
        from apps.queue.models import QueueEntry
        bot = self._chatbot()
        with patch('django.core.cache.cache.delete'), \
             patch('django.core.cache.cache.set'):
            bot.handle('iya')
        self.assertTrue(QueueEntry.objects.filter(clinic=self.clinic, source='whatsapp').exists())

    def test_ya_creates_patient_for_new_phone(self):
        from apps.patients.models import Patient
        bot = self._chatbot()
        with patch('django.core.cache.cache.delete'), \
             patch('django.core.cache.cache.set'):
            bot.handle('ya')
        patient = Patient.objects.for_clinic(self.clinic).filter(phone=self.phone).first()
        self.assertIsNotNone(patient)
        self.assertEqual(patient.name_search, 'siti rahayu')

    def test_ya_reuses_existing_patient(self):
        """Second registration with same phone reuses existing patient record."""
        from apps.patients.models import Patient
        Patient.objects.create(
            clinic=self.clinic,
            medical_record_number='MR202401TEST',
            name='Siti Rahayu',
            name_search='siti rahayu',
            phone=self.phone,
            gender='female',
        )
        bot = self._chatbot()
        with patch('django.core.cache.cache.delete'), \
             patch('django.core.cache.cache.set'):
            bot.handle('ya')
        self.assertEqual(
            Patient.objects.for_clinic(self.clinic).filter(phone=self.phone).count(), 1
        )

    def test_batal_clears_state_and_returns_cancel_message(self):
        bot = self._chatbot()
        with patch('django.core.cache.cache.delete') as mock_delete, \
             patch('django.core.cache.cache.set'):
            reply = bot.handle('batal')
        mock_delete.assert_called_once()
        self.assertIn('batal', reply.lower())

    def test_ambiguous_response_asks_again(self):
        bot = self._chatbot()
        with patch('django.core.cache.cache.set'), \
             patch('django.core.cache.cache.get', return_value={
                 'step': 'awaiting_confirm', 'name': 'Test', 'doctor_id': None
             }):
            reply = bot.handle('mungkin')
        self.assertIn('ya', reply.lower())

    def test_queue_number_appears_in_reply(self):
        from apps.queue.models import QueueEntry
        bot = self._chatbot()
        with patch('django.core.cache.cache.delete'), \
             patch('django.core.cache.cache.set'):
            reply = bot.handle('ya')
        entry = QueueEntry.objects.filter(clinic=self.clinic, source='whatsapp').first()
        self.assertIn(str(entry.queue_number), reply)

    def test_source_is_whatsapp(self):
        from apps.queue.models import QueueEntry
        bot = self._chatbot()
        with patch('django.core.cache.cache.delete'), \
             patch('django.core.cache.cache.set'):
            bot.handle('ya')
        entry = QueueEntry.objects.filter(clinic=self.clinic).first()
        self.assertEqual(entry.source, 'whatsapp')


# ---------------------------------------------------------------------------
# Phone normalization
# ---------------------------------------------------------------------------

class PhoneNormalizationTests(TestCase):
    """Tests for _normalize_phone() utility."""

    def _normalize(self, phone):
        from apps.whatsapp.chatbot import _normalize_phone
        return _normalize_phone(phone)

    def test_local_0_prefix_converted_to_62(self):
        self.assertEqual(self._normalize('081234567890'), '6281234567890')

    def test_already_62_prefix_unchanged(self):
        self.assertEqual(self._normalize('6281234567890'), '6281234567890')

    def test_strips_non_digits(self):
        self.assertEqual(self._normalize('+62-812-3456-7890'), '6281234567890')

    def test_meta_e164_format_unchanged(self):
        self.assertEqual(self._normalize('628123456789'), '628123456789')


# ---------------------------------------------------------------------------
# WhatsAppClient.send_text_message()
# ---------------------------------------------------------------------------

@override_settings(WHATSAPP_ENABLED=False)
class WhatsAppClientSendTextDisabledTests(TestCase):
    """Tests for send_text_message() when WA is disabled."""

    def _client(self):
        from apps.whatsapp.client import WhatsAppClient
        clinic = MagicMock()
        clinic.whatsapp_phone_number_id = '1234567890'
        clinic.whatsapp_access_token = 'token'
        return WhatsAppClient(clinic)

    def test_returns_skipped_when_disabled(self):
        result = self._client().send_text_message(to='6281234567890', body='Halo')
        self.assertEqual(result, {'skipped': True})


@override_settings(WHATSAPP_ENABLED=True)
class WhatsAppClientSendTextEnabledTests(TestCase):
    """Tests for send_text_message() when WA is enabled."""

    def _client(self, phone_number_id='1234567890', token='test-token'):
        from apps.whatsapp.client import WhatsAppClient
        clinic = MagicMock()
        clinic.whatsapp_phone_number_id = phone_number_id
        clinic.whatsapp_access_token = token
        return WhatsAppClient(clinic)

    @patch('requests.post')
    def test_sends_text_message_to_meta_api(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'messages': [{'id': 'wamid.xxx'}]}
        mock_post.return_value.raise_for_status = lambda: None

        self._client().send_text_message(to='081234567890', body='Test reply')

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]['json']
        self.assertEqual(payload['type'], 'text')
        self.assertEqual(payload['text']['body'], 'Test reply')
        self.assertEqual(payload['to'], '6281234567890')  # normalized

    @patch('requests.post')
    def test_normalizes_phone_from_0_prefix(self, mock_post):
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {}

        self._client().send_text_message(to='081234567890', body='test')

        payload = mock_post.call_args[1]['json']
        self.assertEqual(payload['to'], '6281234567890')

    @patch('requests.post')
    def test_raises_error_on_http_failure(self, mock_post):
        import requests
        from apps.whatsapp.client import WhatsAppAPIError
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError(
            response=MagicMock(text='Bad Request')
        )
        with self.assertRaises(WhatsAppAPIError):
            self._client().send_text_message(to='081234567890', body='test')


# ---------------------------------------------------------------------------
# WhatsApp Webhook — dispatch to Celery
# ---------------------------------------------------------------------------

class WhatsAppWebhookDispatchTests(TestCase):
    """Tests for POST /webhooks/whatsapp/ — immediate 200 OK + Celery dispatch."""

    @patch('apps.whatsapp.tasks.process_whatsapp_message.delay')
    def test_text_message_dispatches_celery_task(self, mock_delay):
        payload = {
            'entry': [{
                'changes': [{
                    'value': {
                        'metadata': {'phone_number_id': '1234567890'},
                        'messages': [{'type': 'text', 'from': '6281234567890',
                                       'text': {'body': 'daftar'}}],
                    }
                }]
            }]
        }
        resp = self.client.post(
            '/webhooks/whatsapp/',
            data=payload,
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        mock_delay.assert_called_once_with('1234567890', '6281234567890', 'daftar')

    @patch('apps.whatsapp.tasks.process_whatsapp_message.delay')
    def test_non_text_message_is_ignored(self, mock_delay):
        """Image/audio/location messages don't trigger the chatbot."""
        payload = {
            'entry': [{
                'changes': [{
                    'value': {
                        'metadata': {'phone_number_id': '1234567890'},
                        'messages': [{'type': 'image', 'from': '6281234567890'}],
                    }
                }]
            }]
        }
        resp = self.client.post(
            '/webhooks/whatsapp/',
            data=payload,
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        mock_delay.assert_not_called()

    @patch('apps.whatsapp.tasks.process_whatsapp_message.delay')
    def test_empty_payload_returns_200(self, mock_delay):
        resp = self.client.post(
            '/webhooks/whatsapp/',
            data={},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        mock_delay.assert_not_called()

    def test_get_webhook_verification(self):
        import django.conf
        token = django.conf.settings.WHATSAPP_VERIFY_TOKEN or 'test-token'
        with self.settings(WHATSAPP_VERIFY_TOKEN=token):
            resp = self.client.get(
                '/webhooks/whatsapp/',
                {'hub.mode': 'subscribe', 'hub.verify_token': token, 'hub.challenge': 'abc123'},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'abc123', resp.content)

    def test_get_invalid_token_returns_403(self):
        resp = self.client.get(
            '/webhooks/whatsapp/',
            {'hub.mode': 'subscribe', 'hub.verify_token': 'wrong', 'hub.challenge': 'abc'},
        )
        self.assertEqual(resp.status_code, 403)
