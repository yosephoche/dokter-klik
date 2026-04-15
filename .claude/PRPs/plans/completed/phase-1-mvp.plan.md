# Plan: Phase 1 — MVP (DokterKlik)

## Summary
Implementasi penuh Phase 1 MVP DokterKlik: platform SaaS manajemen klinik berbasis Django + HTMX dengan fitur Smart EMR (SOAP), integrasi wajib SATUSEHAT FHIR R4, Auto-Coding ICD-10, Billing dasar (QRIS + tunai), dan Sistem Antrean Real-Time. Platform ini multi-tenant dengan isolasi data ketat per klinik, enkripsi Fernet pada semua field sensitif, dan RBAC granular untuk 5 role pengguna.

## User Story
As a klinik pratama / dokter praktik mandiri,
I want a platform digital terintegrasi untuk mencatat rekam medis SOAP, sync SATUSEHAT otomatis, kelola antrean, dan proses billing,
So that waktu administratif berkurang 60% dan klinik patuh regulasi PMK No. 24/2022.

## Problem → Solution
Klinik pratama masih pakai buku register + Excel, tidak bisa sync ke SATUSEHAT → Platform Django multi-tenant dengan EMR SOAP, sinkronisasi FHIR R4 via Celery, antrean real-time HTMX, dan billing Midtrans.

## Metadata
- **Complexity**: XL
- **Source PRD**: PRD.md
- **PRD Phase**: Phase 1 — MVP (Bulan 1–4)
- **Estimated Files**: 60+ files

---

## UX Design

### Before
```
┌─────────────────────────────────────────────────────┐
│  Dokter tulis di kertas / Excel                     │
│  → fotokopi / scan manual ke SATUSEHAT (atau tidak) │
│  → pasien antre tanpa tahu estimasi waktu           │
│  → kasir hitung total tagihan manual                │
└─────────────────────────────────────────────────────┘
```

### After
```
┌─────────────────────────────────────────────────────┐
│  Admin daftarkan pasien → nomor antrean otomatis    │
│  Dokter buka form SOAP (4 tab), isi, autosave 30s   │
│  → autocomplete ICD-10 (< 500ms)                   │
│  → klik Simpan & Finalisasi                         │
│  → Celery sync ke SATUSEHAT async (< 10 detik)     │
│  → Invoice otomatis, bayar QRIS/tunai               │
│  → Pasien lihat antrean live via browser / WA       │
└─────────────────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| Pendaftaran pasien | Tulis di buku | Form web → nomor RM otomatis | Admin role |
| Rekam medis | Kertas / Excel | Form SOAP 4-tab + autosave | Doctor role |
| Kode diagnosis | Manual lookup ICD | Autocomplete ketik bahasa ID/EN | HTMX + pg_trgm |
| SATUSEHAT | Upload manual / tidak | Sync otomatis saat finalisasi | Celery async |
| Antrean | Teriakan / papan tulis | Live display web + WA notif | Public, no auth |
| Billing | Kalkulator + bon | Invoice auto dari EMR data | Admin role |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `TECHNICAL_REQUIREMENTS.md` | 1-200 | Project structure + DB schema |
| P0 | `TECHNICAL_REQUIREMENTS.md` | 200-600 | DB schema lanjutan + API endpoints |
| P0 | `TECHNICAL_REQUIREMENTS.md` | 600-900 | SATUSEHAT FHIR + Celery tasks |
| P0 | `TECHNICAL_REQUIREMENTS.md` | 900-1100 | Frontend HTMX patterns + Keamanan |
| P0 | `PRD.md` | 50-200 | Functional requirements + prioritas |
| P0 | `CLAUDE.md` | all | Architecture conventions + RBAC rules |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| SATUSEHAT FHIR R4 | `https://api-satusehat-stg.dto.kemkes.go.id` | Sandbox env untuk dev; OAuth 2.0 client credentials |
| Midtrans | Midtrans docs | QRIS + VA via Snap/Core API; webhook signature verification |
| Meta WhatsApp Cloud API | graph.facebook.com/v19.0 | Template messages harus pre-approved sebelum send |
| fhir.resources Python | PyPI fhir.resources 7.1+ | Validasi FHIR R4 resource sebelum kirim |
| HTMX | htmx.org | `hx-trigger="every 5s"` untuk polling; `hx-swap="none"` untuk autosave |

---

## Patterns to Mirror

### NAMING_CONVENTION
```python
# SOURCE: TECHNICAL_REQUIREMENTS.md (Struktur Project)
# App names: lowercase, plural noun → apps/patients/, apps/emr/, apps/billing/
# Model names: PascalCase, singular → Patient, Visit, Invoice
# Manager methods: snake_case → for_clinic(), get_queryset()
# Task names: verb_noun → sync_encounter_to_satusehat, send_queue_alert
# URL names: kebab-case path, underscore name → /api/icd10/, name='icd10-list'
```

### MULTI_TENANCY_PATTERN
```python
# SOURCE: TECHNICAL_REQUIREMENTS.md:201-209 + CLAUDE.md
class ClinicScopedManager(models.Manager):
    def for_clinic(self, clinic):
        return self.get_queryset().filter(clinic=clinic)

# WAJIB di setiap view:
queryset = Patient.objects.for_clinic(request.user.clinic)
```

### ENCRYPTION_PATTERN
```python
# SOURCE: TECHNICAL_REQUIREMENTS.md:908-930
# apps/core/encryption.py
class EncryptedField:
    """Transparently encrypts/decrypts using Fernet. Key: env ENCRYPTION_KEY"""

class EncryptedCharField(EncryptedField, models.BinaryField): ...
class EncryptedTextField(EncryptedField, models.BinaryField): ...

# Usage di model:
nik = EncryptedCharField(max_length=16, blank=True, null=True)
name = EncryptedCharField(max_length=255, db_column='name')
```

### ABSTRACT_BASE_MODEL
```python
# SOURCE: CLAUDE.md + TECHNICAL_REQUIREMENTS.md
# apps/core/models.py
import uuid
from django.db import models

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### CELERY_TASK_PATTERN
```python
# SOURCE: TECHNICAL_REQUIREMENTS.md:764-776
# apps/satusehat/tasks.py
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def sync_encounter_to_satusehat(self, visit_id: str):
    try:
        # ... sync logic ...
    except SatusehatAPIError as exc:
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries)  # exponential backoff
        )
```

### RBAC_PERMISSION_PATTERN
```python
# SOURCE: TECHNICAL_REQUIREMENTS.md:931-945
# apps/core/permissions.py
from rest_framework.permissions import BasePermission

class IsDoctorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ('doctor', 'admin', 'owner')

class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'owner'
```

### HTMX_AUTOSAVE_PATTERN
```html
<!-- SOURCE: TECHNICAL_REQUIREMENTS.md:846-854 -->
<form id="soap-form"
      hx-patch="/api/visits/{{ visit.id }}/"
      hx-trigger="every 30s, change delay:2s"
      hx-swap="none"
      hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
</form>
```

### HTMX_LIVE_QUEUE_PATTERN
```html
<!-- SOURCE: TECHNICAL_REQUIREMENTS.md:855-863 -->
<div id="queue-board"
     hx-get="/queue/live/{{ clinic.slug }}/partial/"
     hx-trigger="every 5s"
     hx-swap="outerHTML">
</div>
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `docker-compose.yml` | CREATE | Orchestrasi web, db, redis, celery |
| `docker-compose.prod.yml` | CREATE | Production overrides |
| `docker/Dockerfile` | CREATE | Python 3.12 + dependencies |
| `docker/nginx.conf` | CREATE | Reverse proxy + SSL termination |
| `docker/entrypoint.sh` | CREATE | Migrate + collectstatic on startup |
| `.env.example` | CREATE | Template env vars |
| `requirements.txt` | CREATE | Semua Python dependencies |
| `manage.py` | CREATE | Django management entry point |
| `config/__init__.py` | CREATE | Package init |
| `config/settings/base.py` | CREATE | Settings dasar (INSTALLED_APPS, DB, Celery, Jinja2) |
| `config/settings/development.py` | CREATE | DEBUG=True, console email backend |
| `config/settings/production.py` | CREATE | HTTPS, ALLOWED_HOSTS, secure cookies |
| `config/urls.py` | CREATE | Root URL config |
| `config/celery.py` | CREATE | Celery app + beat schedule |
| `config/wsgi.py` | CREATE | WSGI entry point |
| `apps/__init__.py` | CREATE | Package init |
| `apps/core/__init__.py` | CREATE | Package init |
| `apps/core/models.py` | CREATE | BaseModel abstract (UUID PK, timestamps) |
| `apps/core/encryption.py` | CREATE | EncryptedField, EncryptedCharField, EncryptedTextField |
| `apps/core/permissions.py` | CREATE | RBAC permission classes |
| `apps/core/middleware.py` | CREATE | AuditLogMiddleware + SessionTimeoutMiddleware |
| `apps/core/managers.py` | CREATE | ClinicScopedManager |
| `apps/core/jinja2.py` | CREATE | Jinja2 environment factory |
| `apps/accounts/models.py` | CREATE | CustomUser (role, clinic FK, MFA) |
| `apps/accounts/admin.py` | CREATE | Django admin untuk User |
| `apps/accounts/serializers.py` | CREATE | DRF serializers auth |
| `apps/accounts/views.py` | CREATE | Login, logout, MFA views |
| `apps/accounts/urls.py` | CREATE | Auth URL patterns |
| `apps/clinics/models.py` | CREATE | Clinic, DoctorSchedule |
| `apps/clinics/views.py` | CREATE | Clinic management views |
| `apps/clinics/urls.py` | CREATE | URL patterns |
| `apps/patients/models.py` | CREATE | Patient (nik + name encrypted) |
| `apps/patients/serializers.py` | CREATE | DRF serializers |
| `apps/patients/views.py` | CREATE | CRUD + search |
| `apps/patients/urls.py` | CREATE | URL patterns |
| `apps/emr/models.py` | CREATE | Visit, Diagnosis, Prescription, Template, ICD10Code |
| `apps/emr/serializers.py` | CREATE | DRF serializers EMR |
| `apps/emr/views.py` | CREATE | SOAP CRUD + autosave + finalize |
| `apps/emr/urls.py` | CREATE | URL patterns |
| `apps/queue/models.py` | CREATE | QueueEntry |
| `apps/queue/views.py` | CREATE | Queue management + public live view |
| `apps/queue/urls.py` | CREATE | URL patterns (including public) |
| `apps/billing/models.py` | CREATE | Invoice, PaymentTransaction |
| `apps/billing/midtrans.py` | CREATE | Midtrans API client |
| `apps/billing/views.py` | CREATE | Invoice CRUD + payment |
| `apps/billing/urls.py` | CREATE | URL patterns |
| `apps/inventory/models.py` | CREATE | Drug, StockMovement |
| `apps/inventory/views.py` | CREATE | Drug CRUD + stock management |
| `apps/inventory/urls.py` | CREATE | URL patterns |
| `apps/inventory/tasks.py` | CREATE | check_low_stock, check_expiry Celery tasks |
| `apps/satusehat/models.py` | CREATE | SyncLog |
| `apps/satusehat/auth.py` | CREATE | OAuth 2.0 token management dengan Redis cache |
| `apps/satusehat/fhir_mapper.py` | CREATE | Model → FHIR R4 resource builder |
| `apps/satusehat/client.py` | CREATE | HTTP client ke API SATUSEHAT |
| `apps/satusehat/tasks.py` | CREATE | sync_encounter, retry_failed_syncs, notify_high_failure_rate |
| `apps/satusehat/views.py` | CREATE | Dashboard monitoring endpoints |
| `apps/satusehat/urls.py` | CREATE | URL patterns |
| `apps/whatsapp/client.py` | CREATE | Meta Cloud API client |
| `apps/whatsapp/tasks.py` | CREATE | send_queue_alert, send_booking_confirm |
| `apps/whatsapp/urls.py` | CREATE | Webhook handler URL |
| `apps/dashboard/views.py` | CREATE | Analytics endpoints |
| `apps/dashboard/urls.py` | CREATE | URL patterns |
| `apps/core/audit_models.py` | CREATE | AuditLog model |
| `templates/base.html` | CREATE | Base Jinja2 template dengan HTMX CDN |
| `templates/dashboard/index.html` | CREATE | Dashboard utama |
| `templates/patients/list.html` | CREATE | Daftar pasien + search |
| `templates/patients/detail.html` | CREATE | Detail pasien + riwayat |
| `templates/emr/soap_form.html` | CREATE | Form SOAP 4-tab + autosave |
| `templates/queue/management.html` | CREATE | Kelola antrean |
| `templates/queue/display.html` | CREATE | Live queue display (public) |
| `templates/billing/invoice.html` | CREATE | Invoice + pembayaran |

## NOT Building

- Portal Pasien (Phase 3)
- AI Medical Scribbler / Voice-to-Text (Phase 3)
- Telekonsultasi / WebRTC (Phase 3)
- Integrasi BPJS (Phase 4)
- Mobile app native (Phase 4)
- WhatsApp chatbot booking (Phase 2)
- E-Prescription digital (Phase 2)
- Dashboard Analytics lengkap (Phase 2 — hanya ringkasan dasar Phase 1)
- Multi-dokter (> 1) — Phase 2

---

## Step-by-Step Tasks

### Task 1: Docker & Project Scaffolding
- **ACTION**: Buat semua file infrastruktur dan konfigurasi awal
- **IMPLEMENT**:
  - `docker-compose.yml` dengan services: `web` (Django/Gunicorn), `db` (PostgreSQL 16), `redis` (Redis 7), `celery` (worker), `celery-beat`, `minio`, `nginx`
  - `docker/Dockerfile`: FROM python:3.12-slim, install system deps (WeasyPrint, pango), COPY requirements.txt, pip install, COPY project
  - `docker/entrypoint.sh`: wait-for-db, migrate, collectstatic, exec gunicorn
  - `.env.example`: semua env vars dari TECHNICAL_REQUIREMENTS.md section env vars
  - `requirements.txt`: Django>=5.0, djangorestframework>=3.15, celery>=5.3, redis, fhir.resources>=7.1, cryptography>=42, WeasyPrint>=62, Pillow, requests, python-decouple, whitenoise, gunicorn, psycopg2-binary, django-redis, django-storages[s3], boto3
- **GOTCHA**: WeasyPrint butuh system libs (pango, cairo) — install di Dockerfile sebelum pip install
- **VALIDATE**: `docker-compose up -d` → semua container healthy; `docker-compose exec web python manage.py check`

### Task 2: Django Settings & Root Config
- **ACTION**: Setup Django settings dengan environment-based configuration
- **IMPLEMENT**:
  - `config/settings/base.py`:
    - `INSTALLED_APPS`: django defaults + `rest_framework`, `corsheaders`, `whitenoise`, semua apps DokterKlik
    - `DATABASES`: PostgreSQL dari `DATABASE_URL` via python-decouple
    - `REDIS_URL` untuk cache + Celery broker
    - `TEMPLATES`: Jinja2 backend ke `apps.core.jinja2.environment`
    - `AUTH_USER_MODEL = 'accounts.CustomUser'`
    - `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'`
    - DRF settings: pagination, permission_classes, throttle
    - Celery settings: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_BEAT_SCHEDULE`
    - `ENCRYPTION_KEY` dari env (Fernet key)
  - `config/settings/development.py`: DEBUG=True, EMAIL_BACKEND console
  - `config/settings/production.py`: ALLOWED_HOSTS, SECURE_HSTS, SSL cookies
  - `config/urls.py`: include semua app URLs + django admin
  - `config/celery.py`: `app = Celery('dokterklik')`, auto-discover tasks, beat schedule
- **MIRROR**: HTMX_PATTERNS untuk Jinja2 environment
- **GOTCHA**: `DJANGO_SETTINGS_MODULE=config.settings.development` di dev; Jinja2 dan Django templates TIDAK bisa mixed tanpa explicit backend list
- **VALIDATE**: `python manage.py check --deploy` di production settings; `python manage.py shell -c "from django.conf import settings; print(settings.DATABASES)"`

### Task 3: Core App — Base Model, Encryption, Permissions
- **ACTION**: Buat fondasi shared utilities yang dipakai seluruh app
- **IMPLEMENT**:
  - `apps/core/models.py`: `BaseModel` abstract dengan UUID PK, `created_at`, `updated_at`
  - `apps/core/managers.py`: `ClinicScopedManager` dengan `.for_clinic(clinic)` method
  - `apps/core/encryption.py`:
    ```python
    from cryptography.fernet import Fernet
    from django.conf import settings
    import base64

    def get_fernet():
        return Fernet(settings.ENCRYPTION_KEY.encode())

    class EncryptedMixin:
        def encrypt(self, value): ...
        def decrypt(self, value): ...

    class EncryptedCharField(EncryptedMixin, models.BinaryField):
        def from_db_value(self, value, expression, connection):
            if value is None: return value
            return self.decrypt(bytes(value))

        def get_prep_value(self, value):
            if value is None: return value
            return self.encrypt(str(value))

    class EncryptedTextField(EncryptedMixin, models.BinaryField): ...
    ```
  - `apps/core/permissions.py`:
    ```python
    class IsClinicMember(BasePermission): ...
    class IsDoctor(BasePermission): ...
    class IsAdmin(BasePermission): ...
    class IsOwner(BasePermission): ...
    class IsPharmacy(BasePermission): ...
    class IsDoctorOrAdmin(BasePermission): ...
    ```
  - `apps/core/middleware.py`:
    ```python
    class AuditLogMiddleware:
        AUDITED_PATHS = ['/api/patients/', '/api/visits/', '/api/invoices/']
        def __call__(self, request): ...  # log ke AuditLog model

    class SessionTimeoutMiddleware:
        SESSION_TIMEOUT = 30 * 60  # 30 menit
        def __call__(self, request): ...  # check last_activity, redirect if expired
    ```
  - `apps/core/audit_models.py`: `AuditLog` model (BigSerial PK karena high-volume, bukan UUID)
  - `apps/core/jinja2.py`: `environment()` factory dengan global functions (url, static, csrf_input)
- **GOTCHA**: `EncryptedField` inherit dari `BinaryField` — query filter TIDAK bisa langsung karena ciphertext berbeda tiap encrypt. Gunakan `name_search` (plaintext lowercase) untuk search.
- **VALIDATE**: `from apps.core.encryption import EncryptedCharField; f = EncryptedCharField(); assert f.decrypt(f.encrypt("test")) == "test"`

### Task 4: Accounts App — CustomUser & Auth
- **ACTION**: Buat custom user model dengan role-based access
- **IMPLEMENT**:
  - `apps/accounts/models.py`:
    ```python
    class CustomUser(AbstractBaseUser, PermissionsMixin):
        ROLES = [('owner','Owner'),('doctor','Doctor'),('admin','Admin'),
                 ('pharmacy','Pharmacy'),('patient','Patient')]
        id = UUIDField(primary_key=True, default=uuid4)
        clinic = ForeignKey('clinics.Clinic', null=True, on_delete=CASCADE)
        role = CharField(max_length=20, choices=ROLES)
        email = EmailField(unique=True)
        phone = CharField(max_length=20, blank=True)
        mfa_enabled = BooleanField(default=False)
        mfa_secret = EncryptedCharField(max_length=100, blank=True, null=True)
        is_active = BooleanField(default=True)
        last_active = DateTimeField(null=True, blank=True)
        created_at = DateTimeField(auto_now_add=True)

        USERNAME_FIELD = 'email'
        objects = CustomUserManager()
    ```
  - `apps/accounts/views.py`: Login (JWT or session), logout, MFA setup/verify, password change
  - JWT via `djangorestframework-simplejwt` — tambahkan ke requirements.txt
- **GOTCHA**: `AUTH_USER_MODEL` harus dideklarasi SEBELUM `makemigrations` pertama. Ubah di settings dulu, BARU buat model.
- **VALIDATE**: `python manage.py createsuperuser` berhasil; login via `/api/auth/login/` dapat token

### Task 5: Clinics App — Multi-Tenant Foundation
- **ACTION**: Buat model Clinic sebagai anchor multi-tenancy
- **IMPLEMENT**:
  - `apps/clinics/models.py`:
    ```python
    class Clinic(models.Model):  # Tidak inherit BaseModel (tidak butuh updated_at auto)
        id = UUIDField(primary_key=True, default=uuid4)
        name = CharField(max_length=255)
        slug = SlugField(max_length=100, unique=True)
        address = TextField(blank=True)
        phone = CharField(max_length=20, blank=True)
        subscription_plan = CharField(max_length=20, default='starter',
            choices=[('starter','Starter'),('pro','Pro'),('plus','Plus')])
        satusehat_client_id = EncryptedCharField(max_length=200, blank=True, null=True)
        satusehat_client_secret = EncryptedCharField(max_length=200, blank=True, null=True)
        satusehat_org_id = CharField(max_length=100, blank=True)
        whatsapp_phone_number_id = CharField(max_length=100, blank=True)
        whatsapp_access_token = EncryptedCharField(max_length=500, blank=True, null=True)
        created_at = DateTimeField(auto_now_add=True)
        updated_at = DateTimeField(auto_now=True)

    class DoctorSchedule(models.Model):
        clinic = ForeignKey(Clinic, on_delete=CASCADE)
        doctor = ForeignKey('accounts.CustomUser', on_delete=CASCADE)
        day_of_week = IntegerField()  # 0=Senin, 6=Minggu
        start_time = TimeField()
        end_time = TimeField()
        is_active = BooleanField(default=True)
    ```
- **GOTCHA**: `slug` digunakan di public URL `/queue/live/<slug>/` — harus URL-safe, unik
- **VALIDATE**: `Clinic.objects.create(name='Test', slug='test-klinik')` berhasil

### Task 6: Patients App — Encrypted Patient Data
- **ACTION**: Buat model Patient dengan enkripsi NIK + nama
- **IMPLEMENT**:
  - `apps/patients/models.py`:
    ```python
    class Patient(BaseModel):
        clinic = ForeignKey('clinics.Clinic', on_delete=CASCADE)
        medical_record_number = CharField(max_length=20)
        nik = EncryptedCharField(max_length=16, blank=True, null=True)
        name = EncryptedCharField(max_length=255)
        name_search = CharField(max_length=255, db_index=True)  # lowercase, untuk search
        dob = DateField(null=True, blank=True)
        gender = CharField(max_length=10, choices=[('male','Male'),('female','Female')])
        phone = CharField(max_length=20, blank=True)
        address = TextField(blank=True)
        blood_type = CharField(max_length=5, blank=True)
        allergy_notes = TextField(blank=True)
        satusehat_patient_id = CharField(max_length=100, blank=True)

        objects = ClinicScopedManager()

        class Meta:
            unique_together = [('clinic', 'medical_record_number')]

        def save(self, *args, **kwargs):
            # Populate name_search dari plaintext sebelum enkripsi
            if self._state.adding or self._name_changed:
                self.name_search = self._plain_name.lower()
            super().save(*args, **kwargs)
    ```
  - `apps/patients/views.py`:
    - `PatientSearchView`: filter `name_search__icontains=q` ATAU `medical_record_number__istartswith=q`
    - Untuk NIK search: decrypt semua dan filter (acceptable karena NIK search jarang)
  - `apps/patients/serializers.py`: DRF serializer, decrypt name sebelum return
- **GOTCHA**: Karena `name` dienkripsi ke `BYTEA`, ORM filter seperti `name__icontains` TIDAK berfungsi. WAJIB gunakan `name_search` (plaintext lowercase) untuk search. Saat simpan pasien, set `name_search = plain_name.lower()`.
- **VALIDATE**: Buat pasien, search berdasarkan nama → muncul; buka DB langsung → field `name` berupa bytes (ciphertext)

### Task 7: ICD-10 Database & Autocomplete
- **ACTION**: Import data ICD-10 dan buat endpoint autocomplete cepat (< 500ms)
- **IMPLEMENT**:
  - `apps/emr/models.py` — model `ICD10Code`:
    ```python
    class ICD10Code(models.Model):
        id = models.AutoField(primary_key=True)  # SERIAL, bukan UUID
        code = CharField(max_length=10, unique=True)
        description_en = CharField(max_length=500)
        description_id = CharField(max_length=500, blank=True)
        chapter = CharField(max_length=10, blank=True)
        block = CharField(max_length=20, blank=True)
        category = CharField(max_length=10, blank=True)
        is_billable = BooleanField(default=True)
    ```
  - Management command `apps/emr/management/commands/import_icd10.py`:
    - Load dari CSV/JSON file ICD-10 WHO (tersedia publik)
    - Bulk insert via `ICD10Code.objects.bulk_create()`
  - Migration tambahkan GIN trigram index:
    ```python
    from django.db import migrations
    class Migration(migrations.Migration):
        operations = [
            migrations.RunSQL(
                "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
                reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;"
            ),
            migrations.RunSQL(
                "CREATE INDEX idx_icd10_search ON emr_icd10code "
                "USING gin((description_en || ' ' || COALESCE(description_id,'')) gin_trgm_ops);",
            ),
            migrations.RunSQL(
                "CREATE INDEX idx_icd10_code_prefix ON emr_icd10code(code varchar_pattern_ops);"
            ),
        ]
    ```
  - `apps/emr/views.py` — `ICD10SearchView`:
    ```python
    class ICD10SearchView(APIView):
        throttle_classes = [UserRateThrottle]  # 20 req/min
        def get(self, request):
            q = request.GET.get('q', '').strip()
            lang = request.GET.get('lang', 'id')
            if len(q) < 2: return Response([])
            qs = ICD10Code.objects.filter(is_billable=True)
            if q[0].isalpha() and len(q) <= 5:
                qs = qs.filter(code__istartswith=q)
            else:
                search_field = 'description_id' if lang == 'id' else 'description_en'
                qs = qs.filter(**{f'{search_field}__icontains': q})
            return Response(ICD10Serializer(qs[:20], many=True).data)
    ```
- **GOTCHA**: `pg_trgm` extension harus diaktifkan sebelum CREATE INDEX. Lakukan di migration terpisah atau di `entrypoint.sh`. GIN index pada concatenated columns bekerja baik untuk full-text trigram search.
- **VALIDATE**: `GET /api/icd10/?q=demam&lang=id` mengembalikan hasil dalam < 500ms; `GET /api/icd10/?q=A00` mengembalikan kode cholera

### Task 8: EMR App — SOAP Form & Visit Management
- **ACTION**: Buat model Visit + form SOAP dengan autosave dan finalisasi
- **IMPLEMENT**:
  - `apps/emr/models.py` — models `Visit`, `Diagnosis`, `Prescription`, `EMRTemplate`:
    ```python
    class Visit(BaseModel):
        clinic = ForeignKey('clinics.Clinic', on_delete=PROTECT)
        patient = ForeignKey('patients.Patient', on_delete=PROTECT)
        doctor = ForeignKey('accounts.CustomUser', on_delete=PROTECT)
        visit_date = DateTimeField(auto_now_add=True)
        chief_complaint = EncryptedTextField(blank=True)
        soap_subjective = EncryptedTextField(blank=True)
        soap_objective = EncryptedTextField(blank=True)
        soap_assessment_notes = EncryptedTextField(blank=True)
        soap_plan_notes = EncryptedTextField(blank=True)
        status = CharField(max_length=20, default='draft',
            choices=[('draft','Draft'),('finalized','Finalized')])
        finalized_at = DateTimeField(null=True, blank=True)
        satusehat_encounter_id = CharField(max_length=100, blank=True)
        last_autosave = DateTimeField(null=True, blank=True)
        objects = ClinicScopedManager()

    class Diagnosis(BaseModel):
        visit = ForeignKey(Visit, on_delete=CASCADE, related_name='diagnoses')
        icd10_code = CharField(max_length=10)
        icd10_description_en = CharField(max_length=500, blank=True)
        icd10_description_id = CharField(max_length=500, blank=True)
        is_primary = BooleanField(default=False)
        clinical_notes = TextField(blank=True)
        satusehat_condition_id = CharField(max_length=100, blank=True)

    class Prescription(BaseModel):
        visit = ForeignKey(Visit, on_delete=CASCADE, related_name='prescriptions')
        drug = ForeignKey('inventory.Drug', null=True, on_delete=SET_NULL)
        drug_name = CharField(max_length=255)  # snapshot
        quantity = DecimalField(max_digits=10, decimal_places=2)
        unit = CharField(max_length=50)
        dosage_instruction = TextField()
        duration_days = IntegerField(null=True, blank=True)
        status = CharField(max_length=20, default='pending',
            choices=[('pending','Pending'),('dispensed','Dispensed'),('cancelled','Cancelled')])
        dispensed_at = DateTimeField(null=True, blank=True)
    ```
  - `apps/emr/views.py`:
    - `VisitCreateView`: buat visit + queue entry sekaligus
    - `VisitDetailView`: GET visit dengan decrypt SOAP fields
    - `VisitAutosaveView (PATCH /api/visits/<id>/)`: update SOAP fields, update `last_autosave`
    - `VisitFinalizeView (POST /api/visits/<id>/finalize/)`:
      1. Validasi minimal 1 diagnosis dengan kode ICD-10 valid
      2. Set `status='finalized'`, `finalized_at=now()`
      3. Buat Invoice otomatis dari data visit
      4. Kurangi stok obat untuk setiap Prescription
      5. Queue Celery task: `sync_encounter_to_satusehat.delay(str(visit.id))`
      6. Return 200 dengan visit data
  - Template `templates/emr/soap_form.html`:
    - 4 tab (Subjective, Objective, Assessment, Plan) dengan HTMX autosave
    - ICD-10 search input dengan `hx-get="/api/icd10/"` dan debounce 300ms
    - Drug search dengan autocomplete dari inventory
    - Tombol "Simpan & Finalisasi" yang trigger finalize endpoint
- **GOTCHA**: Saat `PATCH` autosave, jangan ubah `status` dari `finalized` kembali ke `draft`. Check `if visit.status == 'finalized': raise PermissionDenied`.
- **VALIDATE**: Buat visit, isi SOAP, klik simpan → `last_autosave` ter-update; finalisasi → `status='finalized'`, Celery task ter-queue

### Task 9: Queue App — Real-Time Queue
- **ACTION**: Buat sistem antrean dengan live display tanpa auth
- **IMPLEMENT**:
  - `apps/queue/models.py`:
    ```python
    class QueueEntry(BaseModel):
        clinic = ForeignKey('clinics.Clinic', on_delete=CASCADE)
        patient = ForeignKey('patients.Patient', null=True, on_delete=SET_NULL)
        doctor = ForeignKey('accounts.CustomUser', null=True, on_delete=SET_NULL)
        queue_number = IntegerField()
        queue_date = DateField(default=date.today)
        status = CharField(max_length=20, default='waiting',
            choices=[('waiting','Waiting'),('called','Called'),
                     ('serving','Serving'),('done','Done'),('skipped','Skipped')])
        source = CharField(max_length=20, default='walkin',
            choices=[('walkin','Walk-in'),('whatsapp','WhatsApp'),('online','Online')])
        called_at = DateTimeField(null=True, blank=True)
        serving_at = DateTimeField(null=True, blank=True)
        done_at = DateTimeField(null=True, blank=True)
        notified_at = DateTimeField(null=True, blank=True)

        class Meta:
            unique_together = [('clinic', 'queue_date', 'queue_number')]

        @classmethod
        def get_next_number(cls, clinic, date):
            last = cls.objects.filter(clinic=clinic, queue_date=date).aggregate(Max('queue_number'))
            return (last['queue_number__max'] or 0) + 1
    ```
  - `apps/queue/views.py`:
    - `QueueManagementView`: list antrean hari ini per klinik (auth required)
    - `QueueCallView (PATCH /api/queue/<id>/call/)`: ubah status + trigger WA notif jika tinggal 3
    - `QueueLiveView (GET /queue/live/<clinic_slug>/)`: PUBLIC, no auth, render Jinja2 template
    - `QueueLivePartialView (GET /queue/live/<clinic_slug>/partial/)`: PUBLIC, return HTML partial untuk HTMX polling
  - `apps/queue/urls.py`:
    ```python
    urlpatterns = [
        path('api/queue/', QueueListCreateView.as_view()),
        path('api/queue/<uuid:pk>/call/', QueueCallView.as_view()),
        # ... other status transitions
        path('queue/live/<slug:clinic_slug>/', QueueLiveView.as_view()),  # PUBLIC
        path('queue/live/<slug:clinic_slug>/partial/', QueueLivePartialView.as_view()),  # PUBLIC HTMX
    ]
    ```
  - Template `templates/queue/display.html`:
    ```html
    <div id="queue-board"
         hx-get="/queue/live/{{ clinic.slug }}/partial/"
         hx-trigger="every 5s"
         hx-swap="outerHTML">
      <h1>Nomor Antrean: {{ current_number }}</h1>
      <p>Menunggu: {{ waiting_count }}</p>
    </div>
    ```
- **GOTCHA**: Public endpoint `/queue/live/<slug>/` TIDAK memerlukan auth — pastikan `permission_classes = []` dan exclude dari session middleware. Jangan expose data medis di endpoint public ini.
- **VALIDATE**: Akses `/queue/live/test-klinik/` tanpa login → berhasil render; update queue status → halaman refresh otomatis setiap 5 detik

### Task 10: Billing App — Invoice & Midtrans
- **ACTION**: Buat sistem billing otomatis dari data EMR + integrasi Midtrans
- **IMPLEMENT**:
  - `apps/billing/models.py`:
    ```python
    class Invoice(BaseModel):
        visit = OneToOneField('emr.Visit', on_delete=PROTECT)
        clinic = ForeignKey('clinics.Clinic', on_delete=PROTECT)
        invoice_number = CharField(max_length=50, unique=True)
            # Format: INV-{YYYYMM}-{sequence padded 4 digit}
        total_consultation = DecimalField(max_digits=12, decimal_places=2, default=0)
        total_procedures = DecimalField(max_digits=12, decimal_places=2, default=0)
        total_drugs = DecimalField(max_digits=12, decimal_places=2, default=0)
        discount = DecimalField(max_digits=12, decimal_places=2, default=0)
        grand_total = DecimalField(max_digits=12, decimal_places=2, default=0)
        payment_method = CharField(max_length=20, blank=True,
            choices=[('cash','Cash'),('qris','QRIS'),('virtual_account','VA'),('free','Free')])
        payment_status = CharField(max_length=20, default='pending',
            choices=[('pending','Pending'),('paid','Paid'),('cancelled','Cancelled')])
        midtrans_order_id = CharField(max_length=100, blank=True)
        midtrans_transaction_id = CharField(max_length=100, blank=True)
        paid_at = DateTimeField(null=True, blank=True)
        pdf_file = CharField(max_length=500, blank=True)  # path di MinIO
    ```
  - `apps/billing/midtrans.py`:
    ```python
    import requests, hashlib, json
    from django.conf import settings

    class MidtransClient:
        BASE_URL = 'https://api.midtrans.com/v2'  # production
        # 'https://api.sandbox.midtrans.com/v2' untuk sandbox

        def __init__(self):
            self.server_key = settings.MIDTRANS_SERVER_KEY

        def create_qris_transaction(self, order_id: str, amount: int) -> dict:
            payload = {
                "payment_type": "qris",
                "transaction_details": {"order_id": order_id, "gross_amount": amount},
                "qris": {"acquirer": "gopay"}
            }
            return self._post('/charge', payload)

        def verify_webhook_signature(self, order_id, status_code, gross_amount, signature_key) -> bool:
            key = f"{order_id}{status_code}{gross_amount}{self.server_key}"
            return hashlib.sha512(key.encode()).hexdigest() == signature_key

        def _post(self, path, payload) -> dict: ...
    ```
  - `apps/billing/views.py`:
    - `InvoiceDetailView`: GET invoice dengan breakdown biaya
    - `PayCashView (POST /api/invoices/<id>/pay/cash/)`: update status paid, catat kembalian
    - `PayQRISView (POST /api/invoices/<id>/pay/qris/)`: buat Midtrans transaction, return QR code URL
    - `MidtransWebhookView (POST /api/payments/midtrans/webhook/)`: verify signature, update payment status
    - `InvoicePDFView`: generate PDF via WeasyPrint, upload ke MinIO, return URL
- **GOTCHA**: Midtrans webhook harus verify signature sebelum proses. Endpoint webhook EXEMPT dari CSRF karena bukan browser request — gunakan `@csrf_exempt` atau tambahkan ke `CSRF_TRUSTED_ORIGINS`.
- **VALIDATE**: Create invoice → amount benar dari EMR data; pay cash → status='paid'; QRIS → QR code URL dikembalikan

### Task 11: Inventory App — Drug Management
- **ACTION**: Buat manajemen stok obat dengan notifikasi low-stock
- **IMPLEMENT**:
  - `apps/inventory/models.py`:
    ```python
    class Drug(BaseModel):
        clinic = ForeignKey('clinics.Clinic', on_delete=CASCADE)
        name = CharField(max_length=255)
        generic_name = CharField(max_length=255, blank=True)
        category = CharField(max_length=100, blank=True)
        unit = CharField(max_length=50)
        buy_price = DecimalField(max_digits=12, decimal_places=2, default=0)
        sell_price = DecimalField(max_digits=12, decimal_places=2, default=0)
        stock = IntegerField(default=0)
        min_stock = IntegerField(default=10)
        expiry_date = DateField(null=True, blank=True)
        barcode = CharField(max_length=100, blank=True)
        is_active = BooleanField(default=True)
        objects = ClinicScopedManager()

    class StockMovement(BaseModel):
        drug = ForeignKey(Drug, on_delete=CASCADE, related_name='movements')
        movement_type = CharField(max_length=20,
            choices=[('in','Restock'),('out','Dispense'),
                     ('adjustment','Adjustment'),('expired','Expired')])
        quantity = IntegerField()  # positif=masuk, negatif=keluar
        reference_type = CharField(max_length=50, blank=True)
        reference_id = UUIDField(null=True, blank=True)
        notes = TextField(blank=True)
        created_by = ForeignKey('accounts.CustomUser', null=True, on_delete=SET_NULL)
    ```
  - `apps/inventory/tasks.py`:
    ```python
    @shared_task
    def check_low_stock(drug_id: str):
        """Triggered setelah stock update. Kirim WA notif jika stock < min_stock."""
        drug = Drug.objects.get(id=drug_id)
        if drug.stock < drug.min_stock:
            send_whatsapp_low_stock_alert.delay(drug_id)

    @shared_task
    def check_expiry():
        """Beat: harian 06:00. Alert untuk obat expiry dalam 3 bulan."""
        ...
    ```
  - Signal `post_save` pada `StockMovement` → trigger `check_low_stock.delay()`
- **GOTCHA**: Stock decrement saat prescribe harus atomic dengan `select_for_update()` untuk hindari race condition. Jika stok < qty yang diresepkan, raise `ValidationError` (jangan silent fail).
- **VALIDATE**: Resepkan obat → stok berkurang; stok < min_stock → Celery task ter-queue; stok = 0 → error saat prescribe

### Task 12: SATUSEHAT Integration
- **ACTION**: Buat integrasi lengkap FHIR R4 ke API SATUSEHAT dengan OAuth + retry
- **IMPLEMENT**:
  - `apps/satusehat/auth.py`:
    ```python
    import redis
    from django.conf import settings

    def get_satusehat_token(clinic) -> str:
        """Ambil token dari Redis cache. Refresh jika expired."""
        r = redis.from_url(settings.REDIS_URL)
        cache_key = f"satusehat_token_{clinic.id}"
        token = r.get(cache_key)
        if token:
            return token.decode()
        # Fetch baru
        resp = requests.post(
            f"{settings.SATUSEHAT_BASE_URL}/oauth/client_credentials/accesstoken",
            data={
                'grant_type': 'client_credentials',
                'client_id': clinic.satusehat_client_id,  # auto-decrypt
                'client_secret': clinic.satusehat_client_secret,
            }
        )
        data = resp.json()
        ttl = data['expires_in'] - 60  # buffer 60 detik
        r.setex(cache_key, ttl, data['access_token'])
        return data['access_token']
    ```
  - `apps/satusehat/fhir_mapper.py`:
    ```python
    from fhir.resources.patient import Patient as FHIRPatient
    from fhir.resources.encounter import Encounter as FHIREncounter
    from fhir.resources.condition import Condition as FHIRCondition

    def build_patient_resource(patient) -> dict:
        """Map Patient model → FHIR R4 Patient resource dict"""
        resource = FHIRPatient.parse_obj({
            "resourceType": "Patient",
            "meta": {"profile": ["https://fhir.kemkes.go.id/r4/StructureDefinition/Patient"]},
            "identifier": [{"use": "official",
                "system": "https://fhir.kemkes.go.id/id/nik",
                "value": patient.nik}],  # auto-decrypt
            "name": [{"use": "official", "text": patient.name}],
            "gender": patient.gender,
            "birthDate": str(patient.dob),
        })
        resource.dict()  # validate via fhir.resources
        return resource.dict()

    def build_encounter_resource(visit) -> dict: ...
    def build_condition_resource(diagnosis, visit) -> dict: ...
    def build_medication_request_resource(prescription, visit) -> dict: ...
    ```
  - `apps/satusehat/client.py`:
    ```python
    class SatusehatClient:
        def __init__(self, clinic):
            self.clinic = clinic
            self.base_url = settings.SATUSEHAT_BASE_URL

        def _get_headers(self):
            return {"Authorization": f"Bearer {get_satusehat_token(self.clinic)}",
                    "Content-Type": "application/json"}

        def post_resource(self, resource_type: str, payload: dict) -> dict:
            resp = requests.post(
                f"{self.base_url}/fhir-r4/v1/{resource_type}",
                json=payload, headers=self._get_headers(), timeout=30
            )
            resp.raise_for_status()
            return resp.json()
    ```
  - `apps/satusehat/tasks.py`:
    ```python
    @shared_task(bind=True, max_retries=5, default_retry_delay=60)
    def sync_encounter_to_satusehat(self, visit_id: str):
        from apps.emr.models import Visit
        visit = Visit.objects.select_related('patient', 'clinic', 'doctor').get(id=visit_id)
        log, _ = SyncLog.objects.get_or_create(
            clinic=visit.clinic, resource_type='Encounter', local_id=visit_id
        )
        client = SatusehatClient(visit.clinic)
        try:
            # 1. Sync Patient
            patient_payload = build_patient_resource(visit.patient)
            patient_resp = client.post_resource('Patient', patient_payload)
            visit.patient.satusehat_patient_id = patient_resp['id']
            visit.patient.save(update_fields=['satusehat_patient_id'])

            # 2. Sync Encounter
            enc_payload = build_encounter_resource(visit)
            enc_resp = client.post_resource('Encounter', enc_payload)
            visit.satusehat_encounter_id = enc_resp['id']
            visit.save(update_fields=['satusehat_encounter_id'])

            # 3. Sync Conditions (per diagnosis)
            for diagnosis in visit.diagnoses.all():
                cond_payload = build_condition_resource(diagnosis, visit)
                cond_resp = client.post_resource('Condition', cond_payload)
                diagnosis.satusehat_condition_id = cond_resp['id']
                diagnosis.save(update_fields=['satusehat_condition_id'])

            # 4. Sync MedicationRequests
            for prescription in visit.prescriptions.filter(status='pending'):
                rx_payload = build_medication_request_resource(prescription, visit)
                client.post_resource('MedicationRequest', rx_payload)

            log.status = 'success'
            log.save(update_fields=['status', 'updated_at'])

        except Exception as exc:
            log.attempt_count += 1
            log.error_message = str(exc)
            log.status = 'failed'
            log.save()
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    ```
  - `apps/satusehat/models.py`: `SyncLog` model sesuai schema
  - `apps/satusehat/views.py`: Dashboard endpoint (status, logs, resync, stats)
- **GOTCHA**: SATUSEHAT sandbox URL berbeda dari production. Gunakan `SATUSEHAT_BASE_URL` env var. Token cache key harus per-klinik (multi-tenant). `fhir.resources` validasi strict — profile URL harus exact match dengan spec Kemenkes, bukan HL7 generic.
- **VALIDATE**: Di sandbox, POST Patient resource → response 201; check SyncLog.status='success'; test retry dengan invalid token → retry exponential

### Task 13: WhatsApp Basic Notifications
- **ACTION**: Buat WhatsApp client untuk notifikasi queue (Phase 1 — hanya queue alert)
- **IMPLEMENT**:
  - `apps/whatsapp/client.py`:
    ```python
    import requests
    from django.conf import settings

    class WhatsAppClient:
        BASE_URL = 'https://graph.facebook.com/v19.0'

        def __init__(self, clinic):
            self.phone_number_id = clinic.whatsapp_phone_number_id
            self.access_token = clinic.whatsapp_access_token  # auto-decrypt

        def send_template_message(self, to: str, template_name: str,
                                   language_code: str = 'id',
                                   components: list = None) -> dict:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language_code},
                    "components": components or []
                }
            }
            resp = requests.post(
                f"{self.BASE_URL}/{self.phone_number_id}/messages",
                json=payload,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            resp.raise_for_status()
            return resp.json()
    ```
  - `apps/whatsapp/tasks.py`:
    ```python
    @shared_task
    def send_queue_alert(queue_entry_id: str):
        """Kirim WA notifikasi saat giliran pasien tinggal 3 nomor."""
        entry = QueueEntry.objects.select_related('patient', 'clinic').get(id=queue_entry_id)
        if not entry.patient.phone:
            return
        client = WhatsAppClient(entry.clinic)
        client.send_template_message(
            to=entry.patient.phone,
            template_name='queue_alert',
            components=[{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": entry.patient.name},
                    {"type": "text", "text": str(entry.queue_number)},
                ]
            }]
        )
        entry.notified_at = timezone.now()
        entry.save(update_fields=['notified_at'])
    ```
  - Trigger di `QueueCallView`: cek berapa banyak antrian tersisa, jika ≤ 3 trigger task
- **GOTCHA**: WhatsApp template messages harus sudah di-approve Meta sebelum bisa digunakan. Di development, gunakan WhatsApp sandbox atau skip notifikasi jika `WHATSAPP_ENABLED=False`. Template parameters HARUS exact match dengan template yang disubmit ke Meta.
- **VALIDATE**: Queue call dengan posisi ke-3 → task ter-queue di Celery; jika `WHATSAPP_ENABLED=False` → skip gracefully

### Task 14: Frontend Templates — Core UI
- **ACTION**: Buat base template + halaman utama dengan HTMX
- **IMPLEMENT**:
  - `templates/base.html`:
    ```html
    <!DOCTYPE html>
    <html lang="id">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
      <title>{% block title %}DokterKlik{% endblock %}</title>
      <script src="https://unpkg.com/htmx.org@1.9.12"></script>
      <link rel="stylesheet" href="{{ static('css/main.css') }}">
    </head>
    <body hx-boost="true">
      <nav><!-- role-based navigation --></nav>
      {% block content %}{% endblock %}
      <script>
        // CSRF token untuk HTMX
        document.body.addEventListener('htmx:configRequest', (evt) => {
          evt.detail.headers['X-CSRFToken'] = '{{ csrf_token() }}';
        });
      </script>
    </body>
    </html>
    ```
  - `templates/emr/soap_form.html`: 4 tab (Subjective, Objective, Assessment, Plan), ICD-10 autocomplete, drug autocomplete, autosave form
  - `templates/queue/display.html`: public live display dengan HTMX polling 5 detik
  - `templates/queue/management.html`: dashboard admin untuk manage antrean
  - `templates/patients/list.html`: search bar dengan HTMX, daftar pasien
  - `templates/billing/invoice.html`: breakdown invoice + payment form
  - `apps/core/jinja2.py`:
    ```python
    from jinja2 import Environment
    from django.templatetags.static import static
    from django.urls import reverse

    def environment(**options):
        env = Environment(**options)
        env.globals.update({
            'static': static,
            'url': reverse,
        })
        return env
    ```
- **GOTCHA**: Jinja2 dan Django templates berbeda — `{{ variable }}` sama, tapi Django tags `{% load static %}` TIDAK ada di Jinja2. Gunakan `static()` function yang di-register di `environment()`. CSRF di Jinja2: `{{ csrf_input() }}` atau via HTMX header.
- **VALIDATE**: Buka `/patients/` di browser → render dengan navigation; autosave form → PATCH request dikirim setiap 30 detik; live queue → auto-refresh setiap 5 detik

### Task 15: Database Migrations & Initial Data
- **ACTION**: Buat semua migrations dan data awal yang diperlukan
- **IMPLEMENT**:
  - Jalankan `python manage.py makemigrations` untuk semua apps dalam urutan dependency:
    1. `core` → `clinics` → `accounts` → `patients` → `emr` → `inventory` → `billing` → `queue` → `satusehat` → `whatsapp` → `dashboard`
  - `apps/core/migrations/0001_initial.py`: AuditLog table + partitioning hint
  - `apps/emr/migrations/0002_icd10_indexes.py`: pg_trgm extension + GIN indexes
  - `apps/patients/migrations/0002_patient_search_index.py`: GIN trigram index pada `name_search`
  - Management command `import_icd10`: download/load ICD-10 dataset
  - Fixtures untuk system EMR templates (5 spesialisasi dasar)
- **GOTCHA**: Migration order matters — `accounts` depends on `clinics`, `emr` depends on `patients` dan `inventory`. Jika ada circular dependency, gunakan lazy reference string `'app.Model'` di ForeignKey.
- **VALIDATE**: `python manage.py migrate` berhasil tanpa error; `python manage.py import_icd10` load minimal 10.000 kode; `ICD10Code.objects.count() > 10000`

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected Output | Edge Case? |
|---|---|---|---|
| EncryptedField encrypt/decrypt | plaintext string | roundtrip identical | Empty string, unicode chars |
| ClinicScopedManager.for_clinic | clinic instance | queryset filtered by clinic | Cross-clinic isolation |
| ICD10 search endpoint | q='demam', lang='id' | list of matching codes | Query < 2 chars → empty |
| Visit autosave | PATCH with SOAP data | status 200, last_autosave updated | Finalized visit → 403 |
| Visit finalize | finalized visit | SyncLog created, Celery task queued | Missing ICD-10 → 400 |
| Queue number generation | multiple concurrent entries | sequential unique numbers | Same date constraint |
| Invoice auto-calculation | visit with prescriptions | grand_total = consultation + drugs | Zero drugs → only consult |
| Midtrans webhook | valid signature | payment_status='paid' | Invalid signature → 400 |
| SATUSEHAT token cache | clinic with credentials | token cached in Redis | Expired token → refresh |
| FHIR mapper | Patient model | valid FHIR R4 dict | Missing DOB → null |

### Edge Cases Checklist
- [ ] Cross-clinic data access (Patient dari klinik lain tidak bisa diakses)
- [ ] Encrypted field dengan null value
- [ ] Visit finalisasi dua kali → idempotent
- [ ] Queue number conflict (race condition)
- [ ] SATUSEHAT API timeout (> 30 detik)
- [ ] Midtrans webhook duplikat (payment sudah paid)
- [ ] Stock decrement saat concurrent prescriptions
- [ ] ICD-10 search dengan special characters (/, &)
- [ ] Session timeout saat autosave sedang berjalan

---

## Validation Commands

### Static Analysis
```bash
docker-compose exec web python manage.py check
docker-compose exec web python manage.py check --deploy  # production settings
```
EXPECT: System check identified no issues.

### Database Migrations
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py showmigrations
```
EXPECT: All migrations applied; no pending migrations.

### Unit Tests
```bash
docker-compose exec web python manage.py test apps --verbosity=2
```
EXPECT: All tests pass.

### SATUSEHAT Connection Test
```bash
docker-compose exec web python manage.py shell -c "
from apps.satusehat.auth import get_satusehat_token
from apps.clinics.models import Clinic
clinic = Clinic.objects.first()
print(get_satusehat_token(clinic))
"
```
EXPECT: Bearer token string (non-empty).

### ICD-10 Performance Test
```bash
docker-compose exec web python manage.py shell -c "
import time
from apps.emr.models import ICD10Code
start = time.time()
results = list(ICD10Code.objects.filter(description_id__icontains='demam')[:20])
elapsed = (time.time() - start) * 1000
print(f'{len(results)} results in {elapsed:.0f}ms')
assert elapsed < 500, f'Too slow: {elapsed}ms'
"
```
EXPECT: Results in < 500ms.

### Celery Worker Test
```bash
docker-compose exec celery celery -A config inspect active
docker-compose exec web python manage.py shell -c "
from apps.satusehat.tasks import sync_encounter_to_satusehat
result = sync_encounter_to_satusehat.delay('test-id')
print(result.id)
"
```
EXPECT: Task ID returned; task visible in Celery worker logs.

### Browser Validation
```bash
docker-compose up -d
# Buka http://localhost:8000
```
EXPECT: Dashboard render; form SOAP autosave setiap 30 detik; live queue refresh setiap 5 detik.

### Manual Validation
- [ ] Login sebagai admin → dashboard muncul dengan data klinik
- [ ] Daftar pasien baru → nomor RM otomatis ter-generate
- [ ] Buka form SOAP → isi subjective → tunggu 30 detik → cek network tab: PATCH request dikirim
- [ ] Search ICD-10 "demam" → hasil muncul < 500ms
- [ ] Finalisasi kunjungan → SyncLog entry ter-buat dengan status 'pending' → berubah ke 'success'
- [ ] Tambah ke antrean → buka `/queue/live/<slug>/` tanpa login → nomor muncul
- [ ] Bayar invoice dengan cash → status berubah ke 'paid'
- [ ] Kurangi stok obat < min_stock → check Celery task terjadwal

---

## Acceptance Criteria
- [ ] Semua 15 tasks completed
- [ ] `python manage.py check` tanpa errors
- [ ] `python manage.py test apps` semua pass
- [ ] SATUSEHAT sandbox sync berhasil (SyncLog.status='success')
- [ ] ICD-10 autocomplete < 500ms dengan dataset lengkap
- [ ] Live queue accessible tanpa login
- [ ] Invoice auto-calculate dari EMR data
- [ ] Enkripsi: field sensitif tersimpan sebagai BYTEA di DB
- [ ] Multi-tenancy: data klinik A tidak bisa diakses dari klinik B
- [ ] Autosave form SOAP setiap 30 detik (network tab verify)

## Completion Checklist
- [ ] Semua model inherit dari BaseModel atau define UUID PK eksplisit
- [ ] Semua view multi-tenant filter via `.for_clinic(request.user.clinic)`
- [ ] Field sensitif gunakan EncryptedCharField/EncryptedTextField
- [ ] Celery tasks gunakan `@shared_task(bind=True, max_retries=5)`
- [ ] Public endpoints (live queue, WA webhook, Midtrans webhook) exempt dari auth
- [ ] Audit log di semua akses data medis
- [ ] Rate limiting di ICD-10 search endpoint
- [ ] `ENCRYPTION_KEY` hanya di `.env`, tidak di code atau version control
- [ ] HTMX autosave menggunakan `hx-swap="none"` (tidak re-render form saat autosave)
- [ ] Jinja2 environment dengan `static()` dan `url()` globals

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SATUSEHAT API spec berubah | Medium | High | Abstraction layer di `fhir_mapper.py`; versioning adapter |
| EncryptedField tidak bisa di-filter ORM | Certain | Medium | Gunakan `name_search` plaintext untuk search; dokumentasikan ini |
| Celery task gagal tanpa notifikasi | Low | High | `notify_high_failure_rate` beat task + admin alert |
| Race condition queue numbering | Medium | Medium | `unique_together` + DB constraint + `get_or_create` pattern |
| WeasyPrint dependencies di Docker | Low | Medium | Test Dockerfile build dulu sebelum deploy; gunakan slim image dengan explicit deps |
| SATUSEHAT token refresh concurrent | Medium | Medium | Redis `setnx` atau lock untuk atomic token refresh |

## Notes
- Project ini greenfield — tidak ada kode yang perlu dimigrasikan
- Phase 1 fokus pada fitur `Must Have` dari PRD. Semua `Should Have` dan `Could Have` defer ke Phase 2
- ICD-10 dataset: download dari WHO atau gunakan dataset publik Indonesia; bulk_create saat seeding
- Untuk WhatsApp notifikasi di development: set `WHATSAPP_ENABLED=False` di dev settings untuk skip actual API calls
- SATUSEHAT staging/sandbox tersedia di `https://api-satusehat-stg.dto.kemkes.go.id`
- Multi-tenancy isolation adalah hard requirement — selalu test cross-clinic access dalam unit tests
