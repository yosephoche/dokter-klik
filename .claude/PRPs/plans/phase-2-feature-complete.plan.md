# Plan: Phase 2 — Feature Complete

## Summary
Phase 2 extends DokterKlik MVP (Phase 1) with the five key features: WhatsApp chatbot booking flow, E-Prescription digital delivery, full Inventory management (expiry, purchase orders, reports), automated Follow-up Reminders, and a comprehensive Dashboard Analytics with export. All features build directly on existing Phase 1 patterns (Celery tasks, WhatsApp client, ClinicScopedManager, EncryptedFields, DRF ViewSets) — no new architectural patterns are introduced.

## User Story
As a clinic admin/doctor/patient, I want automated WhatsApp booking, digital prescriptions sent to pharmacy and patient, complete drug inventory with expiry alerts, automatic follow-up reminders, and a rich analytics dashboard, so that the clinic operates efficiently and patients stay engaged without manual follow-up.

## Problem → Solution
Clinic staff manually handles bookings via phone → Chatbot state machine handles booking end-to-end via WhatsApp. Prescriptions printed on paper → Prescription dispatched digitally to pharmacy dashboard and patient WhatsApp. Drug inventory tracked in spreadsheets → Full CRUD with stock movement audit, expiry alerts, purchase orders. Follow-ups forgotten → Doctor schedules reminders in SOAP; Celery beat sends H-3 and H-day messages. Dashboard is basic stats only → Rich analytics with monthly trends, top diagnoses, top drugs, and PDF/CSV export.

## Metadata
- **Complexity**: XL
- **Source PRD**: PRD.md
- **PRD Phase**: Phase 2 — Feature Complete (Bulan 5–8)
- **Estimated Files**: 28 files (create/update)

---

## UX Design

### Before (Phase 1 state)
```
┌─────────────────────────────────────────┐
│  Patient: calls clinic by phone         │
│  Admin: writes in register book         │
│  Doctor: prints paper prescription      │
│  Admin: checks drug stock in Excel      │
│  Doctor: must remember follow-ups       │
│  Owner: no analytics beyond daily count │
└─────────────────────────────────────────┘
```

### After (Phase 2)
```
┌─────────────────────────────────────────┐
│  Patient WA: "Daftar"                   │
│    → Bot: pilih dokter, jadwal          │
│    → Bot: konfirmasi nomor antrean      │
│    → Bot: pengingat H-1 & H-hari        │
│  Doctor SOAP finalize:                  │
│    → Resep → Farmasi dashboard (RT)     │
│    → Resep → Patient WA                 │
│    → Reminder H-3/H-hari auto-scheduled │
│  Farmasi: kelola stok, PO, expired alert│
│  Owner: dashboard analytics + export    │
└─────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| Booking | Phone call to clinic | WhatsApp chatbot | State machine in `whatsapp/chatbot.py` |
| Prescription | Paper handed to pharmacy | Dashboard real-time + WA to patient | Celery `notifications` queue |
| Stock management | External spreadsheet | Full in-app CRUD + PO | `inventory` app extended |
| Follow-up | Manual reminder by staff | Celery beat H-3/H-day | `reminders` queue |
| Analytics | Basic daily count | Monthly trends, top-10, export | `dashboard` app extended |

---

## Mandatory Reading

Files that MUST be read before implementing:

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `apps/whatsapp/client.py` | all | WhatsApp API client pattern |
| P0 | `apps/whatsapp/views.py` | all | Webhook handler to extend with chatbot |
| P0 | `apps/whatsapp/tasks.py` | all | Notification task pattern |
| P0 | `apps/inventory/models.py` | all | Drug & StockMovement models |
| P0 | `apps/inventory/views.py` | all | Inventory view pattern (select_for_update) |
| P0 | `apps/emr/models.py` | all | Visit, Prescription, Diagnosis models |
| P0 | `apps/emr/views.py` | 89-197 | VisitFinalizeView — where to hook E-Rx & Reminder |
| P0 | `apps/core/permissions.py` | all | RBAC permission classes |
| P0 | `apps/core/managers.py` | all | ClinicScopedManager usage |
| P1 | `apps/satusehat/tasks.py` | all | Celery task retry/backoff pattern to mirror |
| P1 | `apps/dashboard/views.py` | all | Existing analytics pattern |
| P1 | `apps/billing/models.py` | all | Invoice model for revenue analytics |
| P1 | `apps/queue/models.py` | all | QueueEntry for booking via WA |
| P1 | `apps/clinics/models.py` | all | DoctorSchedule for booking availability |
| P1 | `config/settings/base.py` | 173-179 | Celery queue names |
| P2 | `apps/core/tests/test_encryption.py` | all | Test pattern: TestCase, override_settings |
| P2 | `apps/inventory/signals.py` | all | Signal pattern for post-save hooks |
| P2 | `apps/inventory/tasks.py` | all | check_expiry beat task pattern |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| Meta WhatsApp Cloud API interactive messages | Meta for Developers | Use `type: "interactive"` with `button` reply for menu choices in chatbot |
| Celery periodic tasks (beat) | Celery docs | Use `django_celery_beat` DB schedules already installed |
| WeasyPrint HTML→PDF | WeasyPrint docs | Pass HTML string to `weasyprint.HTML(string=html).write_pdf()` |
| Django `select_for_update()` | Django docs | Already used in inventory; use same pattern for stock deduction |

---

## Patterns to Mirror

### NAMING_CONVENTION
```python
# SOURCE: apps/whatsapp/tasks.py:9-11
@shared_task(queue='notifications')
def send_queue_alert(queue_entry_id: str):
    """Send WhatsApp notification when patient is 3rd in queue or fewer."""
```
Task names: `send_<action>` for notifications, `check_<condition>` for monitors, `sync_<resource>` for integrations.

### ERROR_HANDLING
```python
# SOURCE: apps/whatsapp/client.py:71-76
except requests.HTTPError as exc:
    raise WhatsAppAPIError(
        f'WhatsApp API error: {exc.response.text}'
    ) from exc
except requests.RequestException as exc:
    raise WhatsAppAPIError(f'WhatsApp request failed: {exc}') from exc
```
Raise domain-specific exceptions, log at `logger.error`, never swallow.

### LOGGING_PATTERN
```python
# SOURCE: apps/whatsapp/tasks.py:6
logger = logging.getLogger(__name__)
# ...
logger.info('WA queue alert sent for entry %s', queue_entry_id)
logger.error('WA queue alert failed for entry %s: %s', queue_entry_id, exc)
logger.warning('No admin phone for low stock alert at clinic %s', ...)
```
Module-level logger, `%s` format (not f-strings), always include ID.

### CELERY_RETRY_PATTERN
```python
# SOURCE: apps/satusehat/tasks.py:9-10, 85-86
@shared_task(bind=True, max_retries=5, default_retry_delay=60, queue='satusehat')
def sync_encounter_to_satusehat(self, visit_id: str):
    # ...
    countdown = 60 * (2 ** self.request.retries)
    raise self.retry(exc=exc, countdown=countdown)
```
Exponential backoff: `countdown = base * 2^retry_count`.

### CLINIC_SCOPED_QUERY
```python
# SOURCE: apps/inventory/views.py:16-17
def get_queryset(self):
    qs = Drug.objects.for_clinic(self.request.user.clinic).filter(is_active=True)
```
Always `.for_clinic(request.user.clinic)` — never raw `.filter()` without clinic scope.

### ATOMIC_STOCK_DEDUCTION
```python
# SOURCE: apps/inventory/views.py:54-66
with transaction.atomic():
    drug_locked = Drug.objects.select_for_update().get(pk=drug.pk)
    if movement_type in ('out', 'expired') and drug_locked.stock < abs(qty):
        return Response({'detail': f'Insufficient stock...'}, status=400)
    drug_locked.stock -= abs(qty)
    drug_locked.save(update_fields=['stock'])
    StockMovement.objects.create(...)
```
Always `select_for_update()` when modifying stock. Follow with StockMovement creation.

### DRF_VIEW_PATTERN
```python
# SOURCE: apps/inventory/views.py:12-25
class DrugListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsPharmacyOrAdmin]
    serializer_class = DrugSerializer

    def get_queryset(self):
        qs = Drug.objects.for_clinic(self.request.user.clinic).filter(is_active=True)
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(generic_name__icontains=q)
        return qs

    def perform_create(self, serializer):
        serializer.save(clinic=self.request.user.clinic)
```

### TEST_STRUCTURE
```python
# SOURCE: apps/core/tests/test_encryption.py:13-18
@override_settings(ENCRYPTION_KEY=TEST_KEY)
class EncryptedFieldTests(TestCase):
    def setUp(self):
        ...
    def test_<behavior>(self):
        """Describe what this test verifies."""
        ...
        self.assertEqual(...)
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `apps/whatsapp/chatbot.py` | CREATE | State machine for WA booking flow |
| `apps/whatsapp/views.py` | UPDATE | Route incoming WA messages to chatbot |
| `apps/whatsapp/tasks.py` | UPDATE | Add booking confirmation, reminder H-1/H-day, e-prescription tasks |
| `apps/whatsapp/urls.py` | UPDATE | No change needed (webhook already registered) |
| `apps/emr/models.py` | UPDATE | Add `FollowUpReminder` model |
| `apps/emr/views.py` | UPDATE | Hook e-prescription delivery and reminder scheduling in `VisitFinalizeView` |
| `apps/emr/serializers.py` | UPDATE | Add `FollowUpReminderSerializer` |
| `apps/emr/urls.py` | UPDATE | Add reminder endpoints |
| `apps/emr/migrations/0003_followupreminder.py` | CREATE | Migration for FollowUpReminder |
| `apps/inventory/models.py` | UPDATE | Add `PurchaseOrder` + `PurchaseOrderItem` models |
| `apps/inventory/views.py` | UPDATE | Add PurchaseOrder views, stock report view |
| `apps/inventory/serializers.py` | UPDATE | Add PurchaseOrderSerializer |
| `apps/inventory/tasks.py` | UPDATE | Extend `check_expiry` to send WA alerts |
| `apps/inventory/urls.py` | UPDATE | Add PO and report endpoints |
| `apps/inventory/migrations/0002_purchaseorder.py` | CREATE | Migration for PurchaseOrder |
| `apps/dashboard/views.py` | UPDATE | Add monthly trends, top diagnoses, top drugs, export endpoints |
| `apps/dashboard/urls.py` | UPDATE | Add new analytics endpoints |
| `apps/dashboard/web_urls.py` | UPDATE | Add export routes |
| `apps/dashboard/serializers.py` | CREATE | Analytics response serializers |
| `apps/dashboard/tasks.py` | CREATE | Report generation (PDF/CSV) Celery tasks |
| `apps/billing/views.py` | UPDATE | Add invoice PDF send-via-WA endpoint |
| `config/celery.py` | UPDATE | Add beat schedule for `send_followup_reminders` and `check_expiry` |
| `apps/whatsapp/tests.py` | CREATE | Chatbot state machine tests |
| `apps/emr/tests.py` | CREATE | Reminder model and scheduling tests |
| `apps/inventory/tests.py` | UPDATE | Add PurchaseOrder and expiry alert tests |
| `apps/dashboard/tests.py` | CREATE | Analytics endpoint tests |

## NOT Building
- Portal Pasien (Phase 3)
- AI Medical Scribbler (Phase 3)
- Telekonsultasi (Phase 3)
- BPJS integration (Phase 4)
- Drug-drug interaction warnings (FR-RX-04 is `Could Have` — deferred)
- Full POS terminal / cash drawer integration
- SMS fallback (messaging abstraction layer is future work)
- WhatsApp template management UI (templates managed in Meta Business Manager)

---

## Step-by-Step Tasks

### Task 1: WhatsApp Chatbot State Machine
- **ACTION**: Create `apps/whatsapp/chatbot.py` with a `BookingChatbot` class
- **IMPLEMENT**:
  ```python
  # apps/whatsapp/chatbot.py
  """WhatsApp booking chatbot state machine."""
  import logging
  from django.utils import timezone
  from apps.clinics.models import Clinic, DoctorSchedule
  from apps.patients.models import Patient
  from apps.queue.models import QueueEntry
  from apps.whatsapp.client import WhatsAppClient, WhatsAppAPIError

  logger = logging.getLogger(__name__)

  STATES = {
      'idle': '_handle_idle',
      'awaiting_doctor': '_handle_doctor_selection',
      'awaiting_date': '_handle_date_selection',
      'awaiting_confirm': '_handle_confirmation',
  }

  class BookingChatbot:
      """
      Stateless per-message handler. State is stored in Django cache keyed by phone.
      
      Flow:
        idle → "daftar" → send doctor list → awaiting_doctor
        awaiting_doctor → doctor_idx → send available dates → awaiting_date
        awaiting_date → date_idx → confirm summary → awaiting_confirm
        awaiting_confirm → "ya" → create QueueEntry → done
      """
      CACHE_TTL = 60 * 30  # 30 minutes session

      def __init__(self, clinic: Clinic):
          self.clinic = clinic
          self.client = WhatsAppClient(clinic)

      def handle(self, from_phone: str, message_text: str):
          from django.core.cache import cache
          session_key = f'wa_booking:{self.clinic.id}:{from_phone}'
          session = cache.get(session_key, {'state': 'idle', 'data': {}})
          
          handler_name = STATES.get(session['state'], '_handle_idle')
          handler = getattr(self, handler_name)
          new_session = handler(from_phone, message_text.strip().lower(), session)
          
          if new_session:
              cache.set(session_key, new_session, self.CACHE_TTL)
          else:
              cache.delete(session_key)

      def _handle_idle(self, phone, text, session):
          if 'daftar' in text or 'booking' in text:
              doctors = list(
                  DoctorSchedule.objects.filter(clinic=self.clinic, is_active=True)
                  .select_related('doctor')
                  .values('doctor__id', 'doctor__first_name', 'doctor__last_name')
                  .distinct()
              )
              if not doctors:
                  self._send_text(phone, 'Maaf, belum ada jadwal dokter tersedia.')
                  return None
              
              lines = [f'{i+1}. dr. {d["doctor__first_name"]} {d["doctor__last_name"]}'
                       for i, d in enumerate(doctors)]
              body = 'Pilih dokter (balas nomor):\n' + '\n'.join(lines)
              self._send_text(phone, body)
              return {'state': 'awaiting_doctor', 'data': {'doctors': [str(d['doctor__id']) for d in doctors]}}
          else:
              self._send_text(phone, 'Ketik *Daftar* untuk membuat janji kunjungan.')
              return None

      def _handle_doctor_selection(self, phone, text, session):
          try:
              idx = int(text) - 1
              doctors = session['data']['doctors']
              if idx < 0 or idx >= len(doctors):
                  raise ValueError
          except (ValueError, KeyError):
              self._send_text(phone, 'Pilihan tidak valid. Balas dengan nomor yang tersedia.')
              return session
          
          doctor_id = doctors[idx]
          import datetime
          today = datetime.date.today()
          # Next 7 days with available schedule for this doctor
          schedules = DoctorSchedule.objects.filter(
              clinic=self.clinic, doctor_id=doctor_id, is_active=True
          )
          available_days = {s.day_of_week for s in schedules}
          dates = []
          for offset in range(1, 8):
              d = today + datetime.timedelta(days=offset)
              if d.weekday() in available_days:
                  dates.append(d)
              if len(dates) == 3:
                  break
          
          if not dates:
              self._send_text(phone, 'Tidak ada jadwal tersedia minggu ini.')
              return None
          
          DAY_NAMES = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
          lines = [f'{i+1}. {DAY_NAMES[d.weekday()]} {d.strftime("%d %b")}' for i, d in enumerate(dates)]
          self._send_text(phone, 'Pilih tanggal:\n' + '\n'.join(lines))
          return {
              'state': 'awaiting_date',
              'data': {
                  'doctor_id': doctor_id,
                  'dates': [str(d) for d in dates],
              }
          }

      def _handle_date_selection(self, phone, text, session):
          try:
              idx = int(text) - 1
              dates = session['data']['dates']
              if idx < 0 or idx >= len(dates):
                  raise ValueError
          except (ValueError, KeyError):
              self._send_text(phone, 'Pilihan tidak valid.')
              return session
          
          chosen_date = dates[idx]
          doctor_id = session['data']['doctor_id']
          from apps.accounts.models import CustomUser
          doctor = CustomUser.objects.get(id=doctor_id)
          self._send_text(
              phone,
              f'Konfirmasi daftar ke dr. {doctor.full_name} pada {chosen_date}?\n'
              f'Balas *Ya* untuk konfirmasi atau *Tidak* untuk batal.'
          )
          return {
              'state': 'awaiting_confirm',
              'data': {'doctor_id': doctor_id, 'date': chosen_date, 'phone': phone}
          }

      def _handle_confirmation(self, phone, text, session):
          if text not in ('ya', 'yes'):
              self._send_text(phone, 'Pendaftaran dibatalkan. Ketik *Daftar* untuk memulai ulang.')
              return None
          
          import datetime
          doctor_id = session['data']['doctor_id']
          date_str = session['data']['date']
          chosen_date = datetime.date.fromisoformat(date_str)
          
          # Find or create patient by phone
          patient = Patient.objects.for_clinic(self.clinic).filter(phone=phone).first()
          
          queue_number = QueueEntry.get_next_number(self.clinic, chosen_date)
          entry = QueueEntry.objects.create(
              clinic=self.clinic,
              patient=patient,
              doctor_id=doctor_id,
              queue_number=queue_number,
              queue_date=chosen_date,
              source='whatsapp',
          )
          
          from apps.accounts.models import CustomUser
          doctor = CustomUser.objects.get(id=doctor_id)
          self._send_text(
              phone,
              f'✅ Booking berhasil!\n'
              f'Dokter: dr. {doctor.full_name}\n'
              f'Tanggal: {chosen_date.strftime("%d %B %Y")}\n'
              f'Nomor antrean: {queue_number}\n\n'
              f'Anda akan mendapat pengingat H-1 sebelum kunjungan.'
          )
          
          # Schedule H-1 reminder
          from apps.whatsapp.tasks import send_booking_reminder
          import datetime as dt
          remind_at = dt.datetime.combine(
              chosen_date - dt.timedelta(days=1),
              dt.time(8, 0),
              tzinfo=timezone.get_current_timezone()
          )
          send_booking_reminder.apply_async(
              args=[str(entry.id)],
              eta=remind_at,
          )
          return None

      def _send_text(self, phone: str, text: str):
          """Send a plain text message (not a template). Only for interactive chatbot flow."""
          if not getattr(self.client, 'phone_number_id', None):
              logger.debug('WA chatbot skipped (no phone_number_id)')
              return
          # Note: plain text messages require session/conversational messaging approval from Meta
          # For compliance, wrap in a text template or use interactive messages in production
          payload = {
              'messaging_product': 'whatsapp',
              'to': phone,
              'type': 'text',
              'text': {'body': text},
          }
          import requests
          from apps.whatsapp.client import GRAPH_API_BASE
          try:
              resp = requests.post(
                  f'{GRAPH_API_BASE}/{self.client.phone_number_id}/messages',
                  json=payload,
                  headers={'Authorization': f'Bearer {self.client.access_token}'},
                  timeout=15,
              )
              resp.raise_for_status()
          except requests.RequestException as exc:
              logger.error('WA chatbot send failed to %s: %s', phone, exc)
  ```
- **MIRROR**: CLINIC_SCOPED_QUERY, LOGGING_PATTERN
- **IMPORTS**: `from django.core.cache import cache`, `from apps.clinics.models import DoctorSchedule`, `from apps.queue.models import QueueEntry`
- **GOTCHA**: WhatsApp `phone` field in `Patient.phone` may have leading zeros; chatbot receives E.164 from Meta. Normalize to `62xxx` when matching. Cache key must include `clinic.id` for multi-tenancy.
- **VALIDATE**: Unit test `_handle_idle` → state transitions. Test `_handle_confirmation` creates `QueueEntry`.

### Task 2: Wire Chatbot into Webhook Handler
- **ACTION**: Update `apps/whatsapp/views.py` POST handler to dispatch to `BookingChatbot`
- **IMPLEMENT**:
  ```python
  # Replace the comment "# Phase 2: route to chatbot state machine" in views.py with:
  if messages:
      msg = messages[0]
      from_phone = msg.get('from', '')
      msg_type = msg.get('type', '')
      text = ''
      if msg_type == 'text':
          text = msg.get('text', {}).get('body', '')
      elif msg_type == 'interactive':
          interactive = msg.get('interactive', {})
          if interactive.get('type') == 'button_reply':
              text = interactive.get('button_reply', {}).get('title', '')
      
      if text and from_phone:
          # Resolve clinic from webhook phone_number_id
          phone_number_id = value.get('metadata', {}).get('phone_number_id', '')
          from apps.clinics.models import Clinic
          clinic = Clinic.objects.filter(
              whatsapp_phone_number_id=phone_number_id, is_active=True
          ).first()
          if clinic:
              from apps.whatsapp.chatbot import BookingChatbot
              chatbot = BookingChatbot(clinic)
              chatbot.handle(from_phone, text)
          else:
              logger.warning('No active clinic for WA phone_number_id %s', phone_number_id)
  ```
- **MIRROR**: ERROR_HANDLING, LOGGING_PATTERN
- **IMPORTS**: `from apps.clinics.models import Clinic`
- **GOTCHA**: `phone_number_id` is inside `value.metadata.phone_number_id` in Meta payload. Always resolve clinic from it — never use a global clinic assumption (multi-tenant).
- **VALIDATE**: Send mock POST payload to webhook; verify `BookingChatbot.handle` is called.

### Task 3: Add Booking Confirmation & Reminder WA Tasks
- **ACTION**: Add `send_booking_reminder` task to `apps/whatsapp/tasks.py`
- **IMPLEMENT**:
  ```python
  @shared_task(queue='notifications')
  def send_booking_reminder(queue_entry_id: str):
      """Send H-1 and H-day reminders for a booked appointment."""
      from apps.queue.models import QueueEntry
      from apps.whatsapp.client import WhatsAppClient, WhatsAppAPIError

      try:
          entry = QueueEntry.objects.select_related('patient', 'doctor', 'clinic').get(
              id=queue_entry_id
          )
      except QueueEntry.DoesNotExist:
          logger.warning('QueueEntry %s not found for booking reminder', queue_entry_id)
          return

      if not entry.patient or not entry.patient.phone:
          return

      client = WhatsAppClient(entry.clinic)
      doctor_name = entry.doctor.full_name if entry.doctor else 'Dokter'
      try:
          client.send_template_message(
              to=entry.patient.phone,
              template_name='booking_reminder',
              components=[{
                  'type': 'body',
                  'parameters': [
                      {'type': 'text', 'text': entry.patient.name_search.title()},
                      {'type': 'text', 'text': f'dr. {doctor_name}'},
                      {'type': 'text', 'text': entry.queue_date.strftime('%d %B %Y')},
                      {'type': 'text', 'text': str(entry.queue_number)},
                  ],
              }],
          )
          logger.info('WA booking reminder sent for entry %s', queue_entry_id)
      except WhatsAppAPIError as exc:
          logger.error('WA booking reminder failed for entry %s: %s', queue_entry_id, exc)
  ```
- **MIRROR**: NAMING_CONVENTION, ERROR_HANDLING, LOGGING_PATTERN
- **GOTCHA**: Task must be idempotent — if called twice (e.g. retry), it sends duplicate WA. Wrap with `entry.notified_at` guard or use eta scheduling.
- **VALIDATE**: Task callable with valid UUID; verify `send_template_message` called with correct params.

### Task 4: E-Prescription — FollowUpReminder Model
- **ACTION**: Add `FollowUpReminder` model to `apps/emr/models.py`
- **IMPLEMENT**:
  ```python
  class FollowUpReminder(BaseModel):
      """Scheduled follow-up reminder set by doctor at end of visit."""
      STATUS_CHOICES = [
          ('pending', 'Pending'),
          ('sent', 'Sent'),
          ('cancelled', 'Cancelled'),
      ]

      visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='reminders')
      patient = models.ForeignKey(
          'patients.Patient', on_delete=models.CASCADE, related_name='reminders'
      )
      clinic = models.ForeignKey(
          'clinics.Clinic', on_delete=models.PROTECT, related_name='reminders'
      )
      remind_date = models.DateField()
      message_template = models.TextField(
          blank=True,
          help_text='Custom message; leave blank to use clinic default template'
      )
      status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
      sent_at = models.DateTimeField(null=True, blank=True)

      objects = ClinicScopedManager()

      class Meta:
          db_table = 'emr_followupreminder'
          ordering = ['remind_date']

      def __str__(self):
          return f'Reminder {self.patient} on {self.remind_date} ({self.status})'
  ```
- **MIRROR**: BaseModel inheritance, ClinicScopedManager
- **IMPORTS**: Already in scope from existing emr/models.py imports
- **GOTCHA**: `remind_date` is a date (not datetime). The Celery beat task will run daily at 07:00 WIB and filter `remind_date = today or today + 3`.
- **VALIDATE**: Run `python manage.py makemigrations emr` and `migrate`.

### Task 5: E-Prescription — Hook into VisitFinalizeView
- **ACTION**: Extend `VisitFinalizeView.post()` in `apps/emr/views.py` to send e-prescription after finalize
- **IMPLEMENT**: After `self._create_invoice(visit)`, add:
  ```python
  # Dispatch e-prescription to pharmacy dashboard (real-time via cache flag)
  # and send copy to patient via WhatsApp
  try:
      from apps.whatsapp.tasks import send_eprescription_to_patient
      send_eprescription_to_patient.delay(str(visit.id))
  except Exception:
      logger.exception('Failed to queue e-prescription WA task for visit %s', visit.id)
  ```
  Also schedule follow-up reminders if any were attached to the visit:
  ```python
  # Schedule follow-up reminders
  try:
      from apps.whatsapp.tasks import send_followup_reminder
      for reminder in visit.reminders.filter(status='pending'):
          from datetime import datetime, time
          import pytz
          tz = pytz.timezone('Asia/Jakarta')
          remind_at = tz.localize(datetime.combine(reminder.remind_date, time(7, 0)))
          send_followup_reminder.apply_async(args=[str(reminder.id)], eta=remind_at)
  except Exception:
      logger.exception('Failed to schedule reminders for visit %s', visit.id)
  ```
- **MIRROR**: LOGGING_PATTERN, existing try/except pattern in `VisitFinalizeView.post()`
- **IMPORTS**: `from apps.whatsapp.tasks import send_eprescription_to_patient, send_followup_reminder`
- **GOTCHA**: Reminders are attached BEFORE finalize by doctor during SOAP fill. Do not create reminders inside `_dispense_prescriptions` — they come from the visit's `reminders` related set.
- **VALIDATE**: Finalize a visit with prescriptions; verify WA task queued in `notifications` queue.

### Task 6: E-Prescription WA Task
- **ACTION**: Add `send_eprescription_to_patient` task to `apps/whatsapp/tasks.py`
- **IMPLEMENT**:
  ```python
  @shared_task(queue='notifications')
  def send_eprescription_to_patient(visit_id: str):
      """Send e-prescription summary to patient via WhatsApp after visit is finalized."""
      from apps.emr.models import Visit
      from apps.whatsapp.client import WhatsAppClient, WhatsAppAPIError

      try:
          visit = Visit.objects.select_related('patient', 'clinic', 'doctor').prefetch_related(
              'prescriptions__drug'
          ).get(id=visit_id)
      except Visit.DoesNotExist:
          logger.warning('Visit %s not found for e-prescription WA', visit_id)
          return

      if not visit.patient or not visit.patient.phone:
          return

      prescriptions = visit.prescriptions.filter(status='dispensed')
      if not prescriptions.exists():
          return

      # Build drug list string (max 10 items to fit template)
      drug_lines = []
      for rx in prescriptions[:10]:
          drug_lines.append(f'• {rx.drug_name} — {rx.dosage_instruction}')
      drug_list = '\n'.join(drug_lines)

      client = WhatsAppClient(visit.clinic)
      try:
          client.send_template_message(
              to=visit.patient.phone,
              template_name='eprescription',
              components=[{
                  'type': 'body',
                  'parameters': [
                      {'type': 'text', 'text': visit.patient.name_search.title()},
                      {'type': 'text', 'text': f'dr. {visit.doctor.full_name}'},
                      {'type': 'text', 'text': drug_list},
                  ],
              }],
          )
          logger.info('E-prescription WA sent for visit %s', visit_id)
      except WhatsAppAPIError as exc:
          logger.error('E-prescription WA failed for visit %s: %s', visit_id, exc)
  ```
- **MIRROR**: NAMING_CONVENTION, ERROR_HANDLING (exact WhatsApp task pattern from `send_queue_alert`)
- **GOTCHA**: `prescriptions[:10]` is a safety guard for WA message body length. WA template body max 1024 chars.
- **VALIDATE**: Create visit with 2+ dispensed prescriptions; verify task sends to patient.phone.

### Task 7: Follow-Up Reminder WA Task + Beat
- **ACTION**: Add `send_followup_reminder` task + `send_due_reminders` beat task
- **IMPLEMENT**:
  ```python
  @shared_task(queue='reminders')
  def send_followup_reminder(reminder_id: str):
      """Send follow-up control reminder to patient via WhatsApp."""
      from apps.emr.models import FollowUpReminder
      from apps.whatsapp.client import WhatsAppClient, WhatsAppAPIError

      try:
          reminder = FollowUpReminder.objects.select_related(
              'patient', 'clinic', 'visit__doctor'
          ).get(id=reminder_id)
      except FollowUpReminder.DoesNotExist:
          logger.warning('FollowUpReminder %s not found', reminder_id)
          return

      if reminder.status != 'pending':
          return

      if not reminder.patient.phone:
          return

      client = WhatsAppClient(reminder.clinic)
      doctor_name = (
          reminder.visit.doctor.full_name if reminder.visit and reminder.visit.doctor else ''
      )
      try:
          client.send_template_message(
              to=reminder.patient.phone,
              template_name='followup_reminder',
              components=[{
                  'type': 'body',
                  'parameters': [
                      {'type': 'text', 'text': reminder.patient.name_search.title()},
                      {'type': 'text', 'text': reminder.remind_date.strftime('%d %B %Y')},
                      {'type': 'text', 'text': doctor_name},
                  ],
              }],
          )
          from django.utils import timezone
          reminder.status = 'sent'
          reminder.sent_at = timezone.now()
          reminder.save(update_fields=['status', 'sent_at', 'updated_at'])
          logger.info('Follow-up reminder sent for reminder %s', reminder_id)
      except WhatsAppAPIError as exc:
          logger.error('Follow-up reminder failed for %s: %s', reminder_id, exc)

  @shared_task(queue='reminders')
  def send_due_reminders():
      """Beat task: send reminders due today (H-day) and H-3 (3 days from now)."""
      import datetime
      from apps.emr.models import FollowUpReminder
      from django.utils import timezone

      today = timezone.localdate()
      h3 = today + datetime.timedelta(days=3)

      due = FollowUpReminder.objects.filter(
          remind_date__in=[today, h3],
          status='pending',
      ).select_related('patient', 'clinic')

      count = 0
      for reminder in due:
          send_followup_reminder.delay(str(reminder.id))
          count += 1
      logger.info('Queued %d follow-up reminders for today/H-3', count)
  ```
- **MIRROR**: CELERY_RETRY_PATTERN (queue names), LOGGING_PATTERN
- **GOTCHA**: `send_due_reminders` is a beat task — register it in `config/celery.py` beat schedule. Run daily at 07:00 WIB.
- **VALIDATE**: Create `FollowUpReminder` with `remind_date=today`; call `send_due_reminders()`; verify `send_followup_reminder` is called.

### Task 8: Register Beat Tasks in Celery
- **ACTION**: Update `config/celery.py` with beat schedule entries
- **IMPLEMENT**: Add to end of `config/celery.py`:
  ```python
  from celery.schedules import crontab

  app.conf.beat_schedule = {
      # Existing tasks (if any from Phase 1)
      'retry-failed-satusehat-syncs': {
          'task': 'apps.satusehat.tasks.retry_failed_syncs',
          'schedule': crontab(minute=0),  # every hour
      },
      'notify-high-satusehat-failure-rate': {
          'task': 'apps.satusehat.tasks.notify_high_failure_rate',
          'schedule': crontab(minute=30),  # every hour at :30
      },
      'check-drug-expiry': {
          'task': 'apps.inventory.tasks.check_expiry',
          'schedule': crontab(hour=6, minute=0),  # daily at 06:00 WIB
      },
      # Phase 2 additions
      'send-due-followup-reminders': {
          'task': 'apps.whatsapp.tasks.send_due_reminders',
          'schedule': crontab(hour=7, minute=0),  # daily at 07:00 WIB
      },
  }
  ```
- **MIRROR**: Celery beat pattern (existing `retry_failed_syncs` structure)
- **GOTCHA**: `TIME_ZONE = 'Asia/Jakarta'` in settings; crontab uses this timezone when `CELERY_TIMEZONE` matches. Verify `CELERY_TIMEZONE = TIME_ZONE` in `base.py` (already set).
- **VALIDATE**: Run `celery -A config beat --loglevel=info` and verify tasks appear in schedule.

### Task 9: Inventory — PurchaseOrder Models
- **ACTION**: Add `PurchaseOrder` and `PurchaseOrderItem` to `apps/inventory/models.py`
- **IMPLEMENT**:
  ```python
  class PurchaseOrder(BaseModel):
      """Incoming stock from supplier."""
      STATUS_CHOICES = [
          ('draft', 'Draft'),
          ('ordered', 'Ordered'),
          ('received', 'Received'),
          ('cancelled', 'Cancelled'),
      ]

      clinic = models.ForeignKey(
          'clinics.Clinic', on_delete=models.CASCADE, related_name='purchase_orders'
      )
      supplier_name = models.CharField(max_length=255)
      order_date = models.DateField()
      received_date = models.DateField(null=True, blank=True)
      status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
      notes = models.TextField(blank=True)
      created_by = models.ForeignKey(
          'accounts.CustomUser', null=True, on_delete=models.SET_NULL
      )

      objects = ClinicScopedManager()

      class Meta:
          db_table = 'inventory_purchaseorder'
          ordering = ['-order_date']

      def __str__(self):
          return f'PO {self.id} — {self.supplier_name} ({self.status})'


  class PurchaseOrderItem(BaseModel):
      """Line item within a PurchaseOrder."""
      purchase_order = models.ForeignKey(
          PurchaseOrder, on_delete=models.CASCADE, related_name='items'
      )
      drug = models.ForeignKey(Drug, on_delete=models.PROTECT)
      quantity_ordered = models.IntegerField()
      quantity_received = models.IntegerField(default=0)
      unit_cost = models.DecimalField(max_digits=12, decimal_places=2)

      class Meta:
          db_table = 'inventory_purchaseorderitem'

      def __str__(self):
          return f'{self.drug.name} x{self.quantity_ordered}'
  ```
- **MIRROR**: BaseModel, ClinicScopedManager (same as Drug model)
- **GOTCHA**: When PO is `received`, trigger a StockMovement `in` for each item (do this in the `receive PO` view/endpoint).
- **VALIDATE**: `makemigrations inventory` succeeds.

### Task 10: Inventory — PurchaseOrder Views
- **ACTION**: Add PO endpoints to `apps/inventory/views.py`
- **IMPLEMENT**:
  ```python
  from .models import Drug, StockMovement, PurchaseOrder, PurchaseOrderItem
  from .serializers import DrugSerializer, StockMovementSerializer, PurchaseOrderSerializer

  class PurchaseOrderListCreateView(generics.ListCreateAPIView):
      permission_classes = [IsPharmacyOrAdmin]
      serializer_class = PurchaseOrderSerializer

      def get_queryset(self):
          return PurchaseOrder.objects.for_clinic(self.request.user.clinic).prefetch_related('items__drug')

      def perform_create(self, serializer):
          serializer.save(clinic=self.request.user.clinic, created_by=self.request.user)

  class PurchaseOrderReceiveView(APIView):
      """POST to mark PO as received and increment drug stock."""
      permission_classes = [IsPharmacyOrAdmin]

      def post(self, request, pk):
          try:
              po = PurchaseOrder.objects.for_clinic(request.user.clinic).get(pk=pk)
          except PurchaseOrder.DoesNotExist:
              return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

          if po.status == 'received':
              return Response({'detail': 'Already received.'}, status=400)

          from django.utils import timezone as tz
          from django.db import transaction

          with transaction.atomic():
              for item in po.items.select_related('drug').all():
                  drug = Drug.objects.select_for_update().get(pk=item.drug_id)
                  drug.stock += item.quantity_ordered
                  drug.save(update_fields=['stock'])
                  StockMovement.objects.create(
                      drug=drug,
                      movement_type='in',
                      quantity=item.quantity_ordered,
                      reference_type='purchase_order',
                      reference_id=po.id,
                      created_by=request.user,
                  )
                  item.quantity_received = item.quantity_ordered
                  item.save(update_fields=['quantity_received'])
              po.status = 'received'
              po.received_date = tz.localdate()
              po.save(update_fields=['status', 'received_date', 'updated_at'])

          return Response(PurchaseOrderSerializer(po).data)
  ```
- **MIRROR**: ATOMIC_STOCK_DEDUCTION (exact pattern), DRF_VIEW_PATTERN, CLINIC_SCOPED_QUERY
- **GOTCHA**: `select_for_update()` inside `transaction.atomic()` — always in this order.
- **VALIDATE**: Create PO, receive it, verify `Drug.stock` incremented and `StockMovement` created.

### Task 11: Inventory — Stock Report View
- **ACTION**: Add stock opname/movement report endpoint
- **IMPLEMENT**:
  ```python
  class StockReportView(APIView):
      """GET stock movement report for a date range."""
      permission_classes = [IsPharmacyOrAdmin]

      def get(self, request):
          from django.db.models import Sum
          import datetime

          date_from = request.query_params.get('from', str(datetime.date.today()))
          date_to = request.query_params.get('to', str(datetime.date.today()))

          movements = StockMovement.objects.filter(
              drug__clinic=request.user.clinic,
              created_at__date__gte=date_from,
              created_at__date__lte=date_to,
          ).select_related('drug', 'created_by').order_by('-created_at')

          return Response(StockMovementSerializer(movements, many=True).data)
  ```
- **MIRROR**: DRF_VIEW_PATTERN, CLINIC_SCOPED_QUERY
- **GOTCHA**: Use `drug__clinic=` filter since `StockMovement` doesn't have a direct `clinic` FK.
- **VALIDATE**: Call endpoint; verify only movements from request user's clinic returned.

### Task 12: Extend check_expiry to Send WA Alert
- **ACTION**: Update `apps/inventory/tasks.py` `check_expiry` to send WA notifications
- **IMPLEMENT**: After the logger.warning line in check_expiry loop:
  ```python
  # Send WA alert to clinic owner/admin
  try:
      from apps.whatsapp.tasks import send_low_stock_alert
      # Reuse low_stock_alert for expiry (or add a dedicated send_expiry_alert task)
      from apps.whatsapp.tasks import send_expiry_alert
      send_expiry_alert.delay(str(drug.id))
  except Exception:
      logger.exception('Failed to queue expiry WA alert for drug %s', drug.id)
  ```
  Add `send_expiry_alert` to `apps/whatsapp/tasks.py`:
  ```python
  @shared_task(queue='notifications')
  def send_expiry_alert(drug_id: str):
      """Notify admin about drug expiring within 3 months."""
      from apps.inventory.models import Drug
      from apps.whatsapp.client import WhatsAppClient, WhatsAppAPIError
      from apps.accounts.models import CustomUser

      try:
          drug = Drug.objects.select_related('clinic').get(id=drug_id)
      except Drug.DoesNotExist:
          return

      admin = CustomUser.objects.filter(
          clinic=drug.clinic, role__in=['owner', 'admin'], phone__isnull=False
      ).exclude(phone='').first()
      if not admin:
          return

      client = WhatsAppClient(drug.clinic)
      try:
          client.send_template_message(
              to=admin.phone,
              template_name='expiry_alert',
              components=[{
                  'type': 'body',
                  'parameters': [
                      {'type': 'text', 'text': drug.name},
                      {'type': 'text', 'text': str(drug.expiry_date)},
                      {'type': 'text', 'text': str(drug.stock)},
                      {'type': 'text', 'text': drug.unit},
                  ],
              }],
          )
          logger.info('WA expiry alert sent for drug %s', drug_id)
      except WhatsAppAPIError as exc:
          logger.error('WA expiry alert failed for drug %s: %s', drug_id, exc)
  ```
- **MIRROR**: `send_low_stock_alert` (exact same pattern)
- **GOTCHA**: Only send once per drug per day — use Django cache `expiry_alerted:{drug_id}` with 24h TTL to prevent spam.
- **VALIDATE**: Set a drug `expiry_date = today + 60 days`; run `check_expiry()`; verify WA task queued.

### Task 13: Dashboard Analytics — Monthly Trends
- **ACTION**: Add monthly analytics endpoints to `apps/dashboard/views.py`
- **IMPLEMENT**:
  ```python
  class MonthlyRevenueView(APIView):
      """Monthly revenue + patient count for last 12 months."""
      permission_classes = [IsAdminOrOwner]

      def get(self, request):
          from apps.billing.models import Invoice
          from apps.queue.models import QueueEntry
          from django.db.models import Sum, Count
          from django.db.models.functions import TruncMonth
          import datetime

          clinic = request.user.clinic
          one_year_ago = datetime.date.today().replace(day=1) - datetime.timedelta(days=365)

          revenue_qs = (
              Invoice.objects.filter(
                  clinic=clinic,
                  payment_status='paid',
                  paid_at__date__gte=one_year_ago,
              )
              .annotate(month=TruncMonth('paid_at'))
              .values('month')
              .annotate(total=Sum('grand_total'), count=Count('id'))
              .order_by('month')
          )

          return Response([
              {
                  'month': entry['month'].strftime('%Y-%m'),
                  'revenue': float(entry['total']),
                  'invoices': entry['count'],
              }
              for entry in revenue_qs
          ])


  class TopDiagnosesView(APIView):
      """Top 10 diagnoses by frequency for a given month."""
      permission_classes = [IsAdminOrOwner]

      def get(self, request):
          from apps.emr.models import Diagnosis, Visit
          from django.db.models import Count
          import datetime

          clinic = request.user.clinic
          month_str = request.query_params.get('month', datetime.date.today().strftime('%Y-%m'))
          try:
              year, month = [int(x) for x in month_str.split('-')]
          except (ValueError, AttributeError):
              return Response({'detail': 'Invalid month format. Use YYYY-MM.'}, status=400)

          qs = (
              Diagnosis.objects.filter(
                  visit__clinic=clinic,
                  visit__status='finalized',
                  visit__finalized_at__year=year,
                  visit__finalized_at__month=month,
              )
              .values('icd10_code', 'icd10_description_id')
              .annotate(count=Count('id'))
              .order_by('-count')[:10]
          )

          return Response(list(qs))


  class TopDrugsView(APIView):
      """Top 20 most dispensed drugs for a given month."""
      permission_classes = [IsAdminOrOwner]

      def get(self, request):
          from apps.emr.models import Prescription
          from django.db.models import Count, Sum
          import datetime

          clinic = request.user.clinic
          month_str = request.query_params.get('month', datetime.date.today().strftime('%Y-%m'))
          try:
              year, month = [int(x) for x in month_str.split('-')]
          except (ValueError, AttributeError):
              return Response({'detail': 'Invalid month format. Use YYYY-MM.'}, status=400)

          qs = (
              Prescription.objects.filter(
                  visit__clinic=clinic,
                  status='dispensed',
                  dispensed_at__year=year,
                  dispensed_at__month=month,
              )
              .values('drug_name')
              .annotate(count=Count('id'), total_qty=Sum('quantity'))
              .order_by('-count')[:20]
          )

          return Response(list(qs))


  class UpcomingRemindersView(APIView):
      """Patients with follow-up reminders due this week."""
      permission_classes = [IsDoctorOrAdmin]

      def get(self, request):
          from apps.emr.models import FollowUpReminder
          import datetime

          clinic = request.user.clinic
          today = datetime.date.today()
          week_end = today + datetime.timedelta(days=7)

          qs = FollowUpReminder.objects.filter(
              clinic=clinic,
              remind_date__gte=today,
              remind_date__lte=week_end,
              status='pending',
          ).select_related('patient', 'visit__doctor').order_by('remind_date')

          data = []
          for r in qs:
              data.append({
                  'id': str(r.id),
                  'patient_name': r.patient.name_search.title(),
                  'patient_phone': r.patient.phone,
                  'remind_date': str(r.remind_date),
                  'doctor': r.visit.doctor.full_name if r.visit and r.visit.doctor else '',
                  'message': r.message_template,
              })
          return Response(data)
  ```
- **MIRROR**: DRF_VIEW_PATTERN, CLINIC_SCOPED_QUERY
- **IMPORTS**: `from apps.core.permissions import IsAdminOrOwner, IsDoctorOrAdmin`
- **GOTCHA**: `TruncMonth` requires `from django.db.models.functions import TruncMonth`. Doctor-role users should only see their own data in UpcomingRemindersView — add filter `visit__doctor=request.user` if `request.user.role == 'doctor'`.
- **VALIDATE**: Call each endpoint; verify clinic scoping.

### Task 14: Dashboard — Export PDF/CSV
- **ACTION**: Create `apps/dashboard/tasks.py` with report generation
- **IMPLEMENT**:
  ```python
  """Dashboard report generation tasks."""
  import logging
  from celery import shared_task

  logger = logging.getLogger(__name__)


  @shared_task(queue='reports')
  def generate_monthly_report_pdf(clinic_id: str, year: int, month: int, requested_by_id: str):
      """Generate monthly PDF report and store in MinIO."""
      from apps.clinics.models import Clinic
      from apps.billing.models import Invoice
      from apps.emr.models import Diagnosis, Visit
      from apps.accounts.models import CustomUser
      from django.db.models import Sum, Count
      from django.template.loader import render_to_string
      import weasyprint
      import io

      try:
          clinic = Clinic.objects.get(id=clinic_id)
      except Clinic.DoesNotExist:
          logger.error('Clinic %s not found for report generation', clinic_id)
          return

      # Gather data
      invoices = Invoice.objects.filter(
          clinic=clinic, payment_status='paid',
          paid_at__year=year, paid_at__month=month
      )
      total_revenue = invoices.aggregate(Sum('grand_total'))['grand_total__sum'] or 0
      total_patients = Visit.objects.filter(
          clinic=clinic, status='finalized',
          finalized_at__year=year, finalized_at__month=month
      ).count()

      top_diagnoses = (
          Diagnosis.objects.filter(
              visit__clinic=clinic, visit__status='finalized',
              visit__finalized_at__year=year, visit__finalized_at__month=month
          )
          .values('icd10_code', 'icd10_description_id')
          .annotate(count=Count('id'))
          .order_by('-count')[:10]
      )

      context = {
          'clinic': clinic,
          'year': year,
          'month': month,
          'total_revenue': total_revenue,
          'total_patients': total_patients,
          'top_diagnoses': list(top_diagnoses),
      }

      html_string = render_to_string('dashboard/monthly_report.html', context)
      pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()

      # Store in MinIO
      try:
          from django.conf import settings
          import boto3
          s3 = boto3.client(
              's3',
              endpoint_url=settings.MINIO_ENDPOINT,
              aws_access_key_id=settings.MINIO_ACCESS_KEY,
              aws_secret_access_key=settings.MINIO_SECRET_KEY,
          )
          key = f'reports/{clinic_id}/{year}-{month:02d}-report.pdf'
          s3.put_object(
              Bucket=settings.MINIO_BUCKET,
              Key=key,
              Body=pdf_bytes,
              ContentType='application/pdf',
          )
          logger.info('Monthly report generated: %s', key)
          return key
      except Exception:
          logger.exception('Failed to store report PDF for clinic %s', clinic_id)
  ```
- **MIRROR**: NAMING_CONVENTION, LOGGING_PATTERN, CELERY_RETRY_PATTERN (queue=`reports`)
- **GOTCHA**: `weasyprint` requires system fonts. In Docker image, install `fonts-liberation` or `fonts-dejavu`. `render_to_string` uses Django template engine — create `templates/dashboard/monthly_report.html`.
- **VALIDATE**: Queue task manually; verify PDF bytes generated and S3/MinIO `put_object` called.

### Task 15: Add URL Routes
- **ACTION**: Update URL configs for all new endpoints
- **IMPLEMENT** `apps/inventory/urls.py` additions:
  ```python
  path('purchase-orders/', PurchaseOrderListCreateView.as_view(), name='po-list'),
  path('purchase-orders/<uuid:pk>/receive/', PurchaseOrderReceiveView.as_view(), name='po-receive'),
  path('stock-report/', StockReportView.as_view(), name='stock-report'),
  ```
  `apps/dashboard/urls.py` additions:
  ```python
  path('monthly-revenue/', MonthlyRevenueView.as_view(), name='monthly-revenue'),
  path('top-diagnoses/', TopDiagnosesView.as_view(), name='top-diagnoses'),
  path('top-drugs/', TopDrugsView.as_view(), name='top-drugs'),
  path('upcoming-reminders/', UpcomingRemindersView.as_view(), name='upcoming-reminders'),
  path('reports/generate/', GenerateReportView.as_view(), name='generate-report'),
  ```
  `apps/emr/urls.py` additions:
  ```python
  path('visits/<uuid:visit_pk>/reminders/', FollowUpReminderListCreateView.as_view(), name='reminder-list'),
  ```
- **MIRROR**: Existing URL pattern in `apps/emr/urls.py` (nested resources under visits)
- **GOTCHA**: UUIDs in URL must use `<uuid:pk>` not `<str:pk>` — all PKs are UUIDs.
- **VALIDATE**: `python manage.py show_urls` shows all new paths.

### Task 16: Write Tests
- **ACTION**: Create test files for chatbot, reminders, inventory PO, and dashboard analytics
- **IMPLEMENT** `apps/whatsapp/tests.py`:
  ```python
  from django.test import TestCase
  from unittest.mock import patch, MagicMock
  from apps.clinics.models import Clinic


  class BookingChatbotTests(TestCase):
      def setUp(self):
          self.clinic = Clinic.objects.create(
              name='Test Clinic',
              slug='test-clinic',
              whatsapp_phone_number_id='123456',
          )

      @patch('apps.whatsapp.chatbot.WhatsAppClient')
      @patch('django.core.cache.cache')
      def test_idle_daftar_transitions_to_awaiting_doctor(self, mock_cache, mock_client):
          """'daftar' keyword in idle state sends doctor list."""
          from apps.whatsapp.chatbot import BookingChatbot
          mock_cache.get.return_value = {'state': 'idle', 'data': {}}
          bot = BookingChatbot(self.clinic)
          bot.handle('628123456789', 'Daftar')
          mock_cache.set.assert_called()

      @patch('apps.whatsapp.chatbot.WhatsAppClient')
      @patch('django.core.cache.cache')
      def test_unknown_keyword_sends_help_text(self, mock_cache, mock_client):
          """Unknown message in idle state sends help text."""
          from apps.whatsapp.chatbot import BookingChatbot
          mock_cache.get.return_value = {'state': 'idle', 'data': {}}
          bot = BookingChatbot(self.clinic)
          bot.handle('628123456789', 'halo apa kabar')
          # Should not transition state
          mock_cache.delete.assert_not_called()
  ```
- **MIRROR**: TEST_STRUCTURE (TestCase, setUp, descriptive docstring, assertEqual)
- **GOTCHA**: Chatbot uses `django.core.cache.cache` — mock it to avoid Redis dependency in tests. Use `@patch` not live Redis.
- **VALIDATE**: `python manage.py test apps.whatsapp` passes.

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected Output | Edge Case? |
|---|---|---|---|
| Chatbot idle → 'daftar' | WA message 'Daftar' | State → awaiting_doctor | No |
| Chatbot doctor selection | '1' in awaiting_doctor | State → awaiting_date | Invalid idx → stay |
| Chatbot confirm 'ya' | 'ya' in awaiting_confirm | QueueEntry created | No |
| Chatbot confirm 'tidak' | 'tidak' | State cleared | No |
| send_eprescription_to_patient | visit_id with dispensed rx | send_template_message called | No rx → skip |
| send_followup_reminder | reminder_id | Status updated to 'sent' | Already sent → skip |
| send_due_reminders | 3 reminders due today | 3 tasks queued | None due → 0 tasks |
| PO receive | PO with 2 items | Stock incremented, StockMovement created | Already received → 400 |
| MonthlyRevenueView | GET with valid month | Revenue data returned | Empty month → [] |
| TopDiagnosesView | GET ?month=2026-04 | Top 10 diagnoses | No data → [] |

### Edge Cases Checklist
- [ ] Patient has no phone number — skip WA send gracefully
- [ ] Chatbot session expired (cache TTL) — restart from idle
- [ ] PO receive with insufficient stock (edge: stock goes negative) — no risk, it's an `in` movement
- [ ] Monthly report for month with zero visits — return zeroes, not 500
- [ ] Follow-up reminder already `sent` — skip in `send_due_reminders`
- [ ] WhatsApp API down — log error, do not crash webhook handler

---

## Validation Commands

### Static Analysis
```bash
docker-compose exec web python manage.py check
```
EXPECT: System check identified no issues.

### Migrations
```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```
EXPECT: All migrations applied cleanly.

### Unit Tests
```bash
docker-compose exec web python manage.py test apps.whatsapp apps.emr apps.inventory apps.dashboard --verbosity=2
```
EXPECT: All tests pass, 0 failures.

### Full Test Suite
```bash
docker-compose exec web python manage.py test --verbosity=1
```
EXPECT: No regressions from Phase 1 tests.

### Show All URLs
```bash
docker-compose exec web python manage.py show_urls | grep -E 'dashboard|inventory|emr|whatsapp'
```
EXPECT: All new endpoints visible.

### Manual Validation
- [ ] Send "Daftar" to WhatsApp webhook POST; verify chatbot response in logs
- [ ] Finalize a Visit with prescriptions; verify `send_eprescription_to_patient` task queued
- [ ] Create FollowUpReminder with `remind_date=today`; run `send_due_reminders`; verify WA task queued
- [ ] Create PurchaseOrder; POST to `/receive/`; verify drug stock increased
- [ ] GET `/api/dashboard/monthly-revenue/`; verify JSON with month/revenue pairs
- [ ] GET `/api/dashboard/top-diagnoses/?month=2026-04`; verify top-10 diagnoses
- [ ] Queue `generate_monthly_report_pdf` task; verify PDF stored in MinIO

---

## Acceptance Criteria
- [ ] WhatsApp chatbot handles full booking flow: idle → doctor → date → confirm → QueueEntry created
- [ ] E-prescription WA sent to patient after visit finalize (if prescriptions dispensed)
- [ ] Follow-up reminders sent H-3 and H-day via Celery beat
- [ ] PurchaseOrder CRUD with receive flow that updates Drug.stock via StockMovement
- [ ] Drug expiry WA alerts sent 3 months before expiry date
- [ ] Dashboard: monthly revenue, top diagnoses, top drugs endpoints working
- [ ] Dashboard: upcoming reminders list for current week
- [ ] All migrations apply cleanly
- [ ] All tests pass (0 failures)
- [ ] No regressions in Phase 1 features

## Completion Checklist
- [ ] Code follows discovered patterns (ClinicScopedManager, select_for_update, logger=%s)
- [ ] Error handling matches codebase style (domain exceptions, log at error level)
- [ ] Logging follows codebase conventions (module-level logger, %s format)
- [ ] Tests follow test patterns (TestCase, override_settings, mock WA client)
- [ ] No hardcoded clinic IDs or phone numbers
- [ ] No unnecessary scope additions (no Phase 3 work)
- [ ] Self-contained — no questions needed during implementation

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| WhatsApp template not approved in Meta | High | Chatbot replies won't send | Use session/conversational messages for chatbot interactive flow; templates for confirmations |
| Cache race condition in chatbot state | Low | Corrupted session | Cache keys are per-clinic + per-phone; atomic cache.set is sufficient |
| WeasyPrint missing system fonts in Docker | Medium | PDF generation fails | Add `RUN apt-get install -y fonts-liberation` to Dockerfile |
| follow-up reminder double-send (beat + eta) | Medium | Duplicate WA | Guard with `status != 'pending'` check at start of `send_followup_reminder` |
| PO receive concurrent request | Low | Double stock increment | `select_for_update()` inside `transaction.atomic()` prevents this |
| Dashboard queries slow on large data | Medium | >2s response time | Add DB indexes on `paid_at`, `finalized_at`, `remind_date`; paginate if needed |

## Notes
- WhatsApp template names used: `booking_reminder`, `eprescription`, `followup_reminder`, `expiry_alert` — these must be pre-approved in Meta Business Manager before going live.
- The chatbot uses Redis cache (already configured) for session state — no new infrastructure needed.
- `FollowUpReminder` uses `ClinicScopedManager` so it integrates with the existing multi-tenant pattern seamlessly.
- PDF report uses WeasyPrint (already in requirements.txt) + MinIO (already configured). Template `templates/dashboard/monthly_report.html` must be created as a Jinja2 template.
- For doctor-scoped analytics (FR-DSH-06), add `visit__doctor=request.user` filter in analytics views when `request.user.role == 'doctor'`.
