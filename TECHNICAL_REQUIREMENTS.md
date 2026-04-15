# Technical Requirements Document
# DokterKlik — Platform SaaS Manajemen Klinik

| **Versi** | 1.0 |
|-----------|-----|
| **Tanggal** | 15 April 2026 |
| **Status** | Draft |
| **Referensi** | PRD DokterKlik v1.0 |
| **Klasifikasi** | Internal |

---

## Daftar Isi

1. [Technology Stack](#1-technology-stack)
2. [Struktur Project](#2-struktur-project)
3. [Arsitektur Sistem](#3-arsitektur-sistem)
4. [Database Schema](#4-database-schema)
5. [API Endpoints](#5-api-endpoints)
6. [Integrasi SATUSEHAT (FHIR R4)](#6-integrasi-satusehat-fhir-r4)
7. [Celery Task Registry](#7-celery-task-registry)
8. [Frontend (HTMX + Jinja2)](#8-frontend-htmx--jinja2)
9. [Keamanan](#9-keamanan)
10. [Integrasi WhatsApp](#10-integrasi-whatsapp)
11. [Payment Gateway](#11-payment-gateway)
12. [File Storage](#12-file-storage)
13. [Infrastruktur & Docker](#13-infrastruktur--docker)
14. [Non-Functional Requirements](#14-non-functional-requirements)
15. [ICD-10 Database](#15-icd-10-database)
16. [Dependencies](#16-dependencies)
17. [Development Milestones](#17-development-milestones)

---

## 1. Technology Stack

| Komponen | Teknologi | Versi | Justifikasi |
|----------|-----------|-------|-------------|
| **Backend Framework** | Django | LTS 5.x | Ekosistem matang, ORM kuat, komunitas besar Indonesia |
| **REST API** | Django REST Framework | 3.15+ | Serializer, ViewSet, permissions terintegrasi |
| **Database** | PostgreSQL | 16 | Reliabilitas tinggi, JSONB, enkripsi TDE, pg_trgm |
| **Task Queue** | Celery | 5.3+ | Background jobs: SATUSEHAT sync, notifikasi WA |
| **Message Broker** | Redis | 7 | Celery broker + cache layer + session storage |
| **Frontend** | HTMX + Jinja2 | Latest | Server-rendered, reload parsial, tanpa SPA overhead |
| **File Storage** | MinIO (S3-compatible) | Latest | Data medis, enkripsi at-rest, deployment lokal |
| **Reverse Proxy** | Nginx | Latest | SSL termination, static files, load balancing |
| **Containerization** | Docker + Docker Compose | Latest | Konsistensi dev/staging/production |
| **Enkripsi** | Python `cryptography` (Fernet) | 42+ | Enkripsi data medis sensitif at-rest |
| **FHIR Validation** | `fhir.resources` | 7.1+ | Validasi resource FHIR R4 sebelum kirim ke SATUSEHAT |
| **PDF Generation** | WeasyPrint | 62+ | Invoice dan laporan dalam format PDF |
| **Payment** | Midtrans | Latest | QRIS + Virtual Account, pasar Indonesia |

---

## 2. Struktur Project

```
dokterklik/
├── config/                         # Konfigurasi Django
│   ├── settings/
│   │   ├── base.py                 # Settings dasar (semua environment)
│   │   ├── development.py          # Override untuk dev (DEBUG, SMTP console)
│   │   └── production.py           # Override untuk prod (HTTPS, ALLOWED_HOSTS)
│   ├── urls.py                     # Root URL configuration
│   ├── celery.py                   # Celery app & beat schedule
│   └── wsgi.py / asgi.py
│
├── apps/
│   ├── core/                       # Shared utilities
│   │   ├── encryption.py           # Fernet encrypt/decrypt + custom model fields
│   │   ├── permissions.py          # RBAC permission classes
│   │   ├── middleware.py           # Audit log + session timeout middleware
│   │   └── models.py               # Abstract base model (UUID PK, timestamps)
│   │
│   ├── accounts/                   # Auth, User, RBAC
│   │   ├── models.py               # CustomUser dengan role & clinic FK
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── clinics/                    # Multi-tenant klinik
│   │   ├── models.py               # Clinic, DoctorSchedule
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── patients/                   # Data pasien
│   │   ├── models.py               # Patient (data terenkripsi)
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── emr/                        # Electronic Medical Record
│   │   ├── models.py               # Visit, Diagnosis, Prescription, Template, ICD10Code
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── queue/                      # Sistem antrean
│   │   ├── models.py               # QueueEntry
│   │   ├── views.py                # Termasuk public live view (no auth)
│   │   └── urls.py
│   │
│   ├── billing/                    # Invoice & pembayaran
│   │   ├── models.py               # Invoice, PaymentTransaction
│   │   ├── midtrans.py             # Midtrans API client
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── inventory/                  # Stok obat & apotek
│   │   ├── models.py               # Drug, StockMovement
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── satusehat/                  # Integrasi SATUSEHAT
│   │   ├── auth.py                 # OAuth 2.0 token management
│   │   ├── fhir_mapper.py          # Model → FHIR resource builder
│   │   ├── client.py               # HTTP client ke API SATUSEHAT
│   │   ├── tasks.py                # Celery tasks: sync, retry
│   │   ├── models.py               # SyncLog
│   │   └── urls.py                 # Dashboard monitoring endpoints
│   │
│   ├── whatsapp/                   # Bot & notifikasi WhatsApp
│   │   ├── client.py               # Meta Cloud API client
│   │   ├── chatbot.py              # State machine untuk booking flow
│   │   ├── tasks.py                # Celery tasks: kirim notifikasi
│   │   └── urls.py                 # Webhook handler
│   │
│   └── dashboard/                  # Analytics & laporan
│       ├── views.py
│       ├── serializers.py
│       └── urls.py
│
├── templates/                      # Jinja2 templates
│   ├── base.html
│   ├── dashboard/
│   ├── patients/
│   ├── emr/
│   ├── queue/
│   ├── billing/
│   └── inventory/
│
├── static/                         # CSS, JS, assets
├── docker/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── entrypoint.sh
├── docker-compose.yml
├── docker-compose.prod.yml
├── manage.py
├── requirements.txt
└── .env.example
```

---

## 3. Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────┐
│                         INTERNET                            │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS / TLS 1.3
                    ┌───────▼────────┐
                    │     Nginx      │  SSL Termination
                    │  Reverse Proxy │  Static Files
                    └───────┬────────┘
                            │
              ┌─────────────▼──────────────┐
              │      Django (Gunicorn)      │
              │                            │
              │  ┌─────────┐ ┌──────────┐  │
              │  │  Views  │ │DRF APIs  │  │
              │  └────┬────┘ └─────┬────┘  │
              │       └─────┬──────┘        │
              │        ┌────▼────┐          │
              │        │  ORM    │          │
              └────────┼─────────┼──────────┘
                       │         │
            ┌──────────▼──┐  ┌───▼──────────┐
            │ PostgreSQL  │  │    Redis      │
            │  (Data)     │  │ Cache/Session │
            └─────────────┘  └───┬───────────┘
                                 │ Broker
                    ┌────────────▼───────────────┐
                    │       Celery Workers        │
                    │                            │
                    │  queue: satusehat          │
                    │  queue: notifications      │
                    │  queue: reminders          │
                    │  queue: reports            │
                    └──┬─────────────────────────┘
                       │
          ┌────────────┼──────────────────┐
          │            │                  │
  ┌───────▼──┐  ┌──────▼──────┐  ┌───────▼───────┐
  │SATUSEHAT │  │  WhatsApp   │  │    MinIO       │
  │  API     │  │ Cloud API   │  │ File Storage   │
  └──────────┘  └─────────────┘  └───────────────┘
```

### Multi-Tenancy
Semua tabel utama memiliki FK ke `clinics_clinic`. Setiap query di-filter otomatis berdasarkan klinik pengguna yang login melalui custom QuerySet manager.

```python
# apps/core/managers.py
class ClinicScopedManager(models.Manager):
    def for_clinic(self, clinic):
        return self.get_queryset().filter(clinic=clinic)
```

---

## 4. Database Schema

### 4.1 `clinics_clinic`

```sql
CREATE TABLE clinics_clinic (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    address         TEXT,
    phone           VARCHAR(20),
    subscription_plan VARCHAR(20) NOT NULL DEFAULT 'starter',
        -- ENUM: starter, pro, plus
    satusehat_client_id     BYTEA,  -- encrypted
    satusehat_client_secret BYTEA,  -- encrypted
    satusehat_org_id        VARCHAR(100),
    whatsapp_phone_number_id VARCHAR(100),
    whatsapp_access_token   BYTEA,  -- encrypted
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.2 `accounts_user`

```sql
CREATE TABLE accounts_user (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id       UUID REFERENCES clinics_clinic(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,
        -- ENUM: owner, doctor, admin, pharmacy, patient
    email           VARCHAR(254) UNIQUE NOT NULL,
    phone           VARCHAR(20),                -- WA number untuk notifikasi
    password        VARCHAR(128) NOT NULL,
    mfa_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret      BYTEA,                      -- encrypted TOTP secret
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_active     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.3 `patients_patient`

```sql
CREATE TABLE patients_patient (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id               UUID REFERENCES clinics_clinic(id) ON DELETE CASCADE,
    medical_record_number   VARCHAR(20) NOT NULL,
        -- UNIQUE per klinik: UNIQUE(clinic_id, medical_record_number)
    nik                     BYTEA,              -- encrypted Fernet
    name                    BYTEA NOT NULL,     -- encrypted Fernet
    name_search             VARCHAR(255),       -- plaintext untuk search index (hashed/truncated)
    dob                     DATE,
    gender                  VARCHAR(10),        -- male, female
    phone                   VARCHAR(20),        -- WA number
    address                 TEXT,
    blood_type              VARCHAR(5),
    allergy_notes           TEXT,
    satusehat_patient_id    VARCHAR(100),       -- IHS Number dari SATUSEHAT
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(clinic_id, medical_record_number)
);

-- Index untuk pencarian cepat (FR-EMR-06)
CREATE INDEX idx_patient_name_search ON patients_patient
    USING gin(name_search gin_trgm_ops);
CREATE INDEX idx_patient_clinic ON patients_patient(clinic_id);
```

> **Catatan enkripsi:** Field `nik` dan `name` disimpan sebagai ciphertext (Fernet). Field `name_search` menyimpan versi yang aman untuk pencarian (lowercase, trigram index) tanpa menyimpan data sensitif secara plaintext.

### 4.4 `emr_visit`

```sql
CREATE TABLE emr_visit (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id               UUID REFERENCES clinics_clinic(id),
    patient_id              UUID REFERENCES patients_patient(id),
    doctor_id               UUID REFERENCES accounts_user(id),
    visit_date              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    chief_complaint         BYTEA,              -- encrypted (Subjective)
    soap_subjective         BYTEA,              -- encrypted TEXT
    soap_objective          BYTEA,              -- encrypted TEXT (vital signs, fisik)
    soap_assessment_notes   BYTEA,              -- encrypted TEXT (catatan assessment)
    soap_plan_notes         BYTEA,              -- encrypted TEXT (rencana tindakan)
    status                  VARCHAR(20) NOT NULL DEFAULT 'draft',
        -- ENUM: draft, finalized
    finalized_at            TIMESTAMPTZ,
    satusehat_encounter_id  VARCHAR(100),
    last_autosave           TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_visit_patient ON emr_visit(patient_id);
CREATE INDEX idx_visit_doctor_date ON emr_visit(doctor_id, visit_date DESC);
CREATE INDEX idx_visit_clinic_date ON emr_visit(clinic_id, visit_date DESC);
```

### 4.5 `emr_diagnosis`

```sql
CREATE TABLE emr_diagnosis (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id                UUID REFERENCES emr_visit(id) ON DELETE CASCADE,
    icd10_code              VARCHAR(10) NOT NULL,
    icd10_description_en    VARCHAR(500),
    icd10_description_id    VARCHAR(500),
    is_primary              BOOLEAN NOT NULL DEFAULT FALSE,
    clinical_notes          TEXT,
    satusehat_condition_id  VARCHAR(100),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.6 `emr_icd10code`

```sql
CREATE TABLE emr_icd10code (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(10) UNIQUE NOT NULL,    -- e.g. "A00.0"
    description_en  VARCHAR(500) NOT NULL,
    description_id  VARCHAR(500),
    chapter         VARCHAR(10),                    -- e.g. "I"
    block           VARCHAR(20),                    -- e.g. "A00-A09"
    category        VARCHAR(10),                    -- e.g. "A00"
    is_billable     BOOLEAN NOT NULL DEFAULT TRUE
);

-- Index untuk autocomplete (< 500ms target)
CREATE INDEX idx_icd10_search ON emr_icd10code
    USING gin(
        (description_en || ' ' || COALESCE(description_id, ''))
        gin_trgm_ops
    );
CREATE INDEX idx_icd10_code_prefix ON emr_icd10code(code varchar_pattern_ops);
```

### 4.7 `emr_template`

```sql
CREATE TABLE emr_template (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id       UUID REFERENCES clinics_clinic(id),
    doctor_id       UUID REFERENCES accounts_user(id) NULL,
        -- NULL = template bawaan klinik, NOT NULL = template personal dokter
    name            VARCHAR(255) NOT NULL,
    specialty       VARCHAR(50),
        -- ENUM: general, pediatric, dermatology, ent, ophthalmology
    template_data   JSONB NOT NULL,
        -- { subjective: "...", objective: "...", assessment: "...", plan: "..." }
    is_system       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.8 `emr_prescription`

```sql
CREATE TABLE emr_prescription (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id        UUID REFERENCES emr_visit(id) ON DELETE CASCADE,
    drug_id         UUID REFERENCES inventory_drug(id),
    drug_name       VARCHAR(255) NOT NULL,   -- snapshot nama saat prescribe
    quantity        DECIMAL(10,2) NOT NULL,
    unit            VARCHAR(50) NOT NULL,
    dosage_instruction TEXT NOT NULL,       -- "3x sehari sesudah makan"
    duration_days   INTEGER,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- ENUM: pending, dispensed, cancelled
    dispensed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.9 `inventory_drug`

```sql
CREATE TABLE inventory_drug (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id       UUID REFERENCES clinics_clinic(id),
    name            VARCHAR(255) NOT NULL,
    generic_name    VARCHAR(255),
    category        VARCHAR(100),
    unit            VARCHAR(50) NOT NULL,    -- tablet, kapsul, ml, sachet
    buy_price       DECIMAL(12,2) NOT NULL DEFAULT 0,
    sell_price      DECIMAL(12,2) NOT NULL DEFAULT 0,
    stock           INTEGER NOT NULL DEFAULT 0,
    min_stock       INTEGER NOT NULL DEFAULT 10,  -- threshold notifikasi
    expiry_date     DATE,
    barcode         VARCHAR(100),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_drug_clinic ON inventory_drug(clinic_id);
CREATE INDEX idx_drug_name ON inventory_drug USING gin(name gin_trgm_ops);
```

### 4.10 `inventory_stockmovement`

```sql
CREATE TABLE inventory_stockmovement (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drug_id         UUID REFERENCES inventory_drug(id),
    movement_type   VARCHAR(20) NOT NULL,
        -- ENUM: in (restock), out (dispense), adjustment, expired
    quantity        INTEGER NOT NULL,       -- positif = masuk, negatif = keluar
    reference_type  VARCHAR(50),           -- 'prescription', 'purchase_order', 'manual'
    reference_id    UUID,
    notes           TEXT,
    created_by_id   UUID REFERENCES accounts_user(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.11 `billing_invoice`

```sql
CREATE TABLE billing_invoice (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id            UUID UNIQUE REFERENCES emr_visit(id),
    clinic_id           UUID REFERENCES clinics_clinic(id),
    invoice_number      VARCHAR(50) UNIQUE NOT NULL,
        -- Format: INV-{YYYYMM}-{SEQUENCE}
    total_consultation  DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_procedures    DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_drugs         DECIMAL(12,2) NOT NULL DEFAULT 0,
    discount            DECIMAL(12,2) NOT NULL DEFAULT 0,
    grand_total         DECIMAL(12,2) NOT NULL DEFAULT 0,
    payment_method      VARCHAR(20),
        -- ENUM: cash, qris, virtual_account, free
    payment_status      VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- ENUM: pending, paid, cancelled
    midtrans_order_id   VARCHAR(100),
    midtrans_transaction_id VARCHAR(100),
    paid_at             TIMESTAMPTZ,
    pdf_file            VARCHAR(500),       -- path di MinIO
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.12 `queue_entry`

```sql
CREATE TABLE queue_entry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id       UUID REFERENCES clinics_clinic(id),
    patient_id      UUID REFERENCES patients_patient(id),
    doctor_id       UUID REFERENCES accounts_user(id) NULL,
    queue_number    INTEGER NOT NULL,
    queue_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'waiting',
        -- ENUM: waiting, called, serving, done, skipped
    source          VARCHAR(20) NOT NULL DEFAULT 'walkin',
        -- ENUM: walkin, whatsapp, online
    called_at       TIMESTAMPTZ,
    serving_at      TIMESTAMPTZ,
    done_at         TIMESTAMPTZ,
    notified_at     TIMESTAMPTZ,    -- kapan WA notif "tinggal 3 nomor" dikirim
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(clinic_id, queue_date, queue_number)
);

CREATE INDEX idx_queue_clinic_date ON queue_entry(clinic_id, queue_date, status);
```

### 4.13 `satusehat_synclog`

```sql
CREATE TABLE satusehat_synclog (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id       UUID REFERENCES clinics_clinic(id),
    resource_type   VARCHAR(30) NOT NULL,
        -- ENUM: Patient, Encounter, Condition, Observation, MedicationRequest
    local_id        VARCHAR(100) NOT NULL,   -- ID di sistem DokterKlik
    satusehat_id    VARCHAR(100),            -- ID yang dikembalikan SATUSEHAT
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- ENUM: pending, success, failed
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    last_attempt    TIMESTAMPTZ,
    request_payload JSONB,      -- full FHIR resource yang dikirim
    response_body   JSONB,      -- response dari SATUSEHAT
    http_status     INTEGER,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_synclog_status ON satusehat_synclog(status, attempt_count);
CREATE INDEX idx_synclog_clinic ON satusehat_synclog(clinic_id, created_at DESC);
```

### 4.14 `audit_log`

```sql
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES accounts_user(id),
    clinic_id       UUID REFERENCES clinics_clinic(id),
    action          VARCHAR(50) NOT NULL,
        -- ENUM: view, create, update, delete, export, login, logout
    resource_type   VARCHAR(50) NOT NULL,   -- 'patient', 'visit', 'invoice', dst
    resource_id     VARCHAR(100),
    ip_address      INET,
    user_agent      TEXT,
    extra_data      JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_auditlog_user ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_auditlog_resource ON audit_log(resource_type, resource_id);
-- Partitioning by month untuk performa (retensi 5 tahun)
```

---

## 5. API Endpoints

### 5.1 Autentikasi

| Method | Endpoint | Deskripsi | Auth |
|--------|----------|-----------|------|
| POST | `/api/auth/login/` | Login dengan email + password | No |
| POST | `/api/auth/logout/` | Invalidate session/token | Yes |
| POST | `/api/auth/token/refresh/` | Refresh JWT token | Yes |
| POST | `/api/auth/mfa/setup/` | Setup TOTP MFA | Yes |
| POST | `/api/auth/mfa/verify/` | Verifikasi TOTP code | Yes |
| POST | `/api/auth/password/change/` | Ganti password | Yes |

### 5.2 Pasien

| Method | Endpoint | Deskripsi | Role |
|--------|----------|-----------|------|
| GET | `/api/patients/?q=<nama\|nik\|mrn>` | Pencarian cepat | admin, doctor |
| POST | `/api/patients/` | Daftar pasien baru | admin |
| GET | `/api/patients/<id>/` | Detail pasien | admin, doctor |
| PUT | `/api/patients/<id>/` | Update data pasien | admin |
| GET | `/api/patients/<id>/visits/` | Riwayat kunjungan | admin, doctor |
| GET | `/api/patients/<id>/prescriptions/` | Riwayat resep | pharmacy, doctor |

### 5.3 EMR / SOAP

| Method | Endpoint | Deskripsi | Role |
|--------|----------|-----------|------|
| POST | `/api/visits/` | Buat kunjungan baru | admin, doctor |
| GET | `/api/visits/<id>/` | Detail kunjungan | admin, doctor |
| PATCH | `/api/visits/<id>/` | Autosave SOAP (throttle 30s) | doctor |
| POST | `/api/visits/<id>/finalize/` | Finalisasi + trigger SATUSEHAT sync | doctor |
| GET | `/api/emr/templates/` | List template per spesialisasi | doctor |
| POST | `/api/emr/templates/` | Buat template kustom | doctor |
| PUT | `/api/emr/templates/<id>/` | Update template | doctor |
| DELETE | `/api/emr/templates/<id>/` | Hapus template kustom | doctor |
| POST | `/api/visits/<id>/attachments/` | Upload file penunjang | doctor |

### 5.4 ICD-10

| Method | Endpoint | Deskripsi | Role |
|--------|----------|-----------|------|
| GET | `/api/icd10/?q=<query>&lang=id\|en` | Autocomplete kode ICD-10 | doctor |
| GET | `/api/icd10/<code>/` | Detail kode ICD-10 | doctor |
| GET | `/api/icd10/frequent/` | Kode yang sering dipakai per dokter | doctor |

### 5.5 Antrean

| Method | Endpoint | Deskripsi | Role |
|--------|----------|-----------|------|
| GET | `/api/queue/?date=<YYYY-MM-DD>` | List antrean per hari | admin, doctor |
| POST | `/api/queue/` | Tambah pasien ke antrean | admin |
| PATCH | `/api/queue/<id>/call/` | Panggil nomor antrean | admin |
| PATCH | `/api/queue/<id>/serve/` | Tandai sedang dilayani | admin |
| PATCH | `/api/queue/<id>/done/` | Tandai selesai | admin |
| PATCH | `/api/queue/<id>/skip/` | Lewati nomor | admin |
| GET | `/queue/live/<clinic_slug>/` | Live display (public, no auth, HTMX) | Public |

### 5.6 Billing

| Method | Endpoint | Deskripsi | Role |
|--------|----------|-----------|------|
| GET | `/api/invoices/<visit_id>/` | Detail invoice | admin |
| POST | `/api/invoices/<visit_id>/pay/cash/` | Bayar tunai | admin |
| POST | `/api/invoices/<visit_id>/pay/qris/` | Buat transaksi QRIS | admin |
| POST | `/api/invoices/<visit_id>/pay/va/` | Buat Virtual Account | admin |
| GET | `/api/invoices/<visit_id>/pdf/` | Download PDF invoice | admin |
| POST | `/api/payments/midtrans/webhook/` | Midtrans payment callback | Public (verified) |
| GET | `/api/billing/history/?from=&to=&method=&status=` | Riwayat transaksi | admin, owner |

### 5.7 Inventori

| Method | Endpoint | Deskripsi | Role |
|--------|----------|-----------|------|
| GET | `/api/drugs/?q=<nama>` | Pencarian obat | pharmacy, doctor |
| POST | `/api/drugs/` | Tambah obat baru | pharmacy, admin |
| GET | `/api/drugs/<id>/` | Detail obat | pharmacy |
| PATCH | `/api/drugs/<id>/` | Update data obat | pharmacy |
| POST | `/api/drugs/<id>/restock/` | Catat penerimaan barang | pharmacy |
| GET | `/api/drugs/low-stock/` | Daftar obat stok menipis | pharmacy, admin |
| GET | `/api/drugs/<id>/movements/` | Riwayat pergerakan stok | pharmacy |

### 5.8 SATUSEHAT

| Method | Endpoint | Deskripsi | Role |
|--------|----------|-----------|------|
| GET | `/api/satusehat/status/` | Dashboard monitoring sync | admin, owner |
| GET | `/api/satusehat/logs/?status=&resource_type=` | Log sinkronisasi | admin |
| POST | `/api/satusehat/resync/<log_id>/` | Re-sync manual | admin |
| GET | `/api/satusehat/stats/` | Statistik success/fail rate | admin, owner |

### 5.9 Dashboard & Laporan

| Method | Endpoint | Deskripsi | Role |
|--------|----------|-----------|------|
| GET | `/api/dashboard/daily/?date=` | Ringkasan harian | owner, admin, doctor |
| GET | `/api/dashboard/monthly/?month=YYYY-MM` | Laporan bulanan | owner, admin |
| GET | `/api/dashboard/diagnoses/top/?period=` | 10 diagnosis terbanyak | owner, doctor |
| GET | `/api/dashboard/drugs/top/` | Top 20 obat terlaku | owner, pharmacy |
| GET | `/api/reports/export/?format=pdf\|csv&period=` | Export laporan | owner |

---

## 6. Integrasi SATUSEHAT (FHIR R4)

### 6.1 Environment

| Environment | Base URL |
|------------|----------|
| Sandbox | `https://api-satusehat-stg.dto.kemkes.go.id` |
| Production | `https://api-satusehat.kemkes.go.id` |

### 6.2 Autentikasi OAuth 2.0

```
POST {base_url}/oauth/client_credentials/accesstoken
?grant_type=client_credentials

Headers:
  Content-Type: application/x-www-form-urlencoded

Body:
  client_id={clinic.satusehat_client_id}
  client_secret={clinic.satusehat_client_secret}

Response:
  { "access_token": "...", "expires_in": 3600, "token_type": "Bearer" }
```

**Cache Strategy:** Token disimpan di Redis dengan key `satusehat_token_{clinic_id}`, TTL = `expires_in - 60` detik (buffer 60 detik sebelum expire).

### 6.3 FHIR Resource yang Dikirim

| Resource | Trigger | Endpoint SATUSEHAT |
|----------|---------|-------------------|
| **Patient** | Pasien baru / update | `POST /fhir-r4/v1/Patient` |
| **Encounter** | Visit difinalisasi | `POST /fhir-r4/v1/Encounter` |
| **Condition** | Setiap diagnosis | `POST /fhir-r4/v1/Condition` |
| **Observation** | Vital signs diisi | `POST /fhir-r4/v1/Observation` |
| **MedicationRequest** | Setiap resep obat | `POST /fhir-r4/v1/MedicationRequest` |

### 6.4 Contoh FHIR Resource

**Patient:**
```json
{
  "resourceType": "Patient",
  "meta": { "profile": ["https://fhir.kemkes.go.id/r4/StructureDefinition/Patient"] },
  "identifier": [
    {
      "use": "official",
      "system": "https://fhir.kemkes.go.id/id/nik",
      "value": "3171234567890001"
    }
  ],
  "name": [{ "use": "official", "text": "Budi Santoso" }],
  "telecom": [{ "system": "phone", "value": "08123456789", "use": "mobile" }],
  "gender": "male",
  "birthDate": "1990-05-15",
  "address": [{ "use": "home", "country": "ID" }]
}
```

**Encounter:**
```json
{
  "resourceType": "Encounter",
  "status": "finished",
  "class": {
    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
    "code": "AMB",
    "display": "ambulatory"
  },
  "subject": { "reference": "Patient/{satusehat_patient_id}" },
  "participant": [{
    "individual": { "reference": "Practitioner/{doctor_ihs_number}" }
  }],
  "period": {
    "start": "2026-04-15T08:00:00+07:00",
    "end": "2026-04-15T08:30:00+07:00"
  },
  "location": [{
    "location": { "reference": "Location/{clinic_location_id}" }
  }]
}
```

### 6.5 Alur Sinkronisasi

```
Dokter klik "Simpan & Finalisasi"
    │
    ▼
Django validates SOAP completeness + ICD-10 codes
    │
    ▼
Visit.status = 'finalized', finalized_at = NOW()
    │
    ▼
Celery task: sync_encounter_to_satusehat(visit_id) → async
    │
    ▼
[Task Execution]
1. Get/refresh OAuth token (Redis cache)
2. POST Patient → get/update satusehat_patient_id
3. POST Encounter → save satusehat_encounter_id
4. For each Diagnosis: POST Condition
5. For each Prescription: POST MedicationRequest
6. Update SyncLog status = 'success'
    │
    ├── [On HTTP Error / Timeout]
    │       SyncLog.attempt_count++
    │       Retry dengan exponential backoff:
    │         attempt 1: delay 60s
    │         attempt 2: delay 120s
    │         attempt 3: delay 240s
    │         attempt 4: delay 480s
    │         attempt 5: delay 960s
    │       Setelah 5 gagal: status = 'failed', notifikasi admin
    │
    └── [On Success]
            SyncLog.status = 'success'
            Visit.satusehat_encounter_id = returned_id
```

### 6.6 Retry & Error Handling

```python
# apps/satusehat/tasks.py
@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def sync_encounter_to_satusehat(self, visit_id: str):
    try:
        # ... sync logic ...
    except SatusehatAPIError as exc:
        log.attempt_count += 1
        log.error_message = str(exc)
        log.save()
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries)  # exponential backoff
        )
```

---

## 7. Celery Task Registry

| Task Name | Trigger | Queue | Prioritas |
|-----------|---------|-------|-----------|
| `satusehat.tasks.sync_encounter` | Visit finalized | `satusehat` | High |
| `satusehat.tasks.retry_failed_syncs` | Beat: setiap 30 menit | `satusehat` | Normal |
| `satusehat.tasks.notify_high_failure_rate` | Beat: setiap 1 jam | `satusehat` | Normal |
| `whatsapp.tasks.send_queue_alert` | Queue position ≤ 3 | `notifications` | High |
| `whatsapp.tasks.send_booking_confirm` | Booking created | `notifications` | High |
| `whatsapp.tasks.send_visit_reminder` | Beat: harian 07:00 | `reminders` | Normal |
| `whatsapp.tasks.send_followup_reminder` | Beat: harian 08:00 | `reminders` | Normal |
| `inventory.tasks.check_low_stock` | Drug stock updated | `notifications` | Normal |
| `inventory.tasks.check_expiry` | Beat: harian 06:00 | `notifications` | Low |
| `dashboard.tasks.generate_monthly_report` | Beat: 1st tiap bulan | `reports` | Low |

### Celery Beat Schedule

```python
# config/celery.py
CELERY_BEAT_SCHEDULE = {
    'retry-failed-syncs': {
        'task': 'apps.satusehat.tasks.retry_failed_syncs',
        'schedule': crontab(minute='*/30'),
    },
    'check-satusehat-failure-rate': {
        'task': 'apps.satusehat.tasks.notify_high_failure_rate',
        'schedule': crontab(minute=0),  # setiap jam
    },
    'send-visit-reminders': {
        'task': 'apps.whatsapp.tasks.send_visit_reminder',
        'schedule': crontab(hour=7, minute=0),
    },
    'check-drug-expiry': {
        'task': 'apps.inventory.tasks.check_expiry',
        'schedule': crontab(hour=6, minute=0),
    },
    'generate-monthly-report': {
        'task': 'apps.dashboard.tasks.generate_monthly_report',
        'schedule': crontab(day_of_month=1, hour=1, minute=0),
    },
}
```

---

## 8. Frontend (HTMX + Jinja2)

### 8.1 Halaman Utama

| URL | Template | Akses | Fitur Utama |
|-----|----------|-------|-------------|
| `/` | `dashboard/index.html` | owner, admin, doctor | Ringkasan harian |
| `/patients/` | `patients/list.html` | admin, doctor | Search, daftar pasien |
| `/patients/<id>/` | `patients/detail.html` | admin, doctor | Detail + riwayat |
| `/patients/<id>/visit/new/` | `emr/soap_form.html` | doctor | Form SOAP + autosave |
| `/patients/<id>/visit/<id>/` | `emr/visit_detail.html` | admin, doctor | Detail kunjungan |
| `/queue/` | `queue/management.html` | admin | Kelola antrean |
| `/queue/live/<slug>/` | `queue/display.html` | Public | Live display TV |
| `/billing/<visit_id>/` | `billing/invoice.html` | admin | Invoice + bayar |
| `/inventory/` | `inventory/drug_list.html` | pharmacy, admin | Manajemen stok |
| `/satusehat/` | `satusehat/dashboard.html` | admin, owner | Status sync |
| `/reports/` | `dashboard/reports.html` | owner | Analytics + export |

### 8.2 HTMX Patterns

```html
<!-- 1. Autosave SOAP setiap 30 detik (FR-EMR-04) -->
<form id="soap-form"
      hx-patch="/api/visits/{{ visit.id }}/"
      hx-trigger="every 30s, change delay:2s"
      hx-swap="none"
      hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
  <!-- Tab Subjective, Objective, Assessment, Plan -->
</form>

<!-- 2. Live queue polling setiap 5 detik (FR-QUE-01) -->
<div id="queue-board"
     hx-get="/queue/live/{{ clinic.slug }}/partial/"
     hx-trigger="every 5s"
     hx-swap="outerHTML">
  <!-- Nomor antrean aktif -->
</div>

<!-- 3. ICD-10 autocomplete (FR-ICD-01) -->
<input type="text"
       name="icd10_search"
       hx-get="/api/icd10/"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#icd10-results"
       hx-swap="innerHTML"
       placeholder="Cari diagnosis...">
<ul id="icd10-results"></ul>

<!-- 4. Patient search (FR-EMR-06) -->
<input type="search"
       hx-get="/api/patients/"
       hx-trigger="keyup changed delay:400ms"
       hx-target="#patient-results"
       name="q"
       placeholder="Nama, NIK, atau No. RM">

<!-- 5. Drug autocomplete dari inventory -->
<input type="text"
       hx-get="/api/drugs/"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#drug-results"
       name="q">
```

### 8.3 Jinja2 Environment

```python
# config/settings/base.py
TEMPLATES = [{
    'BACKEND': 'django.template.backends.jinja2.Jinja2',
    'DIRS': [BASE_DIR / 'templates'],
    'OPTIONS': {
        'environment': 'apps.core.jinja2.environment',
        'extensions': ['jinja2.ext.do'],
    },
}]
```

---

## 9. Keamanan

### 9.1 Enkripsi Data Medis (Fernet)

```python
# apps/core/encryption.py

class EncryptedField:
    """
    Custom Django model field yang secara transparan enkripsi/dekripsi
    menggunakan Fernet symmetric encryption.
    Key: dari env ENCRYPTION_KEY (256-bit base64-encoded)
    """

class EncryptedCharField(EncryptedField, models.BinaryField): ...
class EncryptedTextField(EncryptedField, models.BinaryField): ...
```

**Fields yang dienkripsi:**
- `patients_patient.nik`
- `patients_patient.name`
- `emr_visit.soap_subjective/objective/assessment/plan`
- `clinics_clinic.satusehat_client_id/secret`
- `clinics_clinic.whatsapp_access_token`
- `accounts_user.mfa_secret`

### 9.2 RBAC Permission Matrix

| Aksi | owner | doctor | admin | pharmacy | patient |
|------|-------|--------|-------|----------|---------|
| Lihat semua pasien | ✓ | ✗ | ✓ | ✗ | ✗ |
| Lihat pasien sendiri | ✓ | ✓ | ✓ | ✗ | ✗ |
| Buat/edit SOAP | ✓ | ✓ | ✗ | ✗ | ✗ |
| Kelola antrean | ✓ | ✓ | ✓ | ✗ | ✗ |
| Proses billing | ✓ | ✗ | ✓ | ✗ | ✗ |
| Kelola inventori | ✓ | ✗ | ✓ | ✓ | ✗ |
| Dispensing resep | ✓ | ✗ | ✗ | ✓ | ✗ |
| Lihat dashboard penuh | ✓ | ✗ | ✗ | ✗ | ✗ |
| Export laporan | ✓ | ✗ | ✗ | ✗ | ✗ |
| Konfigurasi klinik | ✓ | ✗ | ✗ | ✗ | ✗ |
| Lihat rekam medis sendiri | ✗ | ✗ | ✗ | ✗ | ✓ |

### 9.3 Audit Log Middleware

```python
# apps/core/middleware.py
class AuditLogMiddleware:
    """
    Log setiap request yang mengakses data medis pasien.
    Catat: user, action, resource_type, resource_id, IP, timestamp.
    """

class SessionTimeoutMiddleware:
    """
    Invalidate session setelah 30 menit tidak aktif.
    Redirect ke login page.
    """
```

### 9.4 Keamanan API

- **CSRF:** Django CSRF middleware aktif untuk semua form
- **Rate Limiting:** DRF throttling — 100 req/menit per user, 20 req/menit endpoint ICD-10
- **HTTPS:** Wajib TLS 1.3, HSTS header
- **CORS:** Dibatasi hanya origin klinik terdaftar
- **SQL Injection:** ORM Django, tidak ada raw query kecuali pg_trgm search (parameterized)
- **XSS:** Jinja2 auto-escape aktif

---

## 10. Integrasi WhatsApp

### 10.1 Provider: Meta Cloud API (WhatsApp Business)

```
Base URL: https://graph.facebook.com/v19.0
Auth: Bearer {whatsapp_access_token}
```

### 10.2 WhatsApp Client

```python
# apps/whatsapp/client.py
class WhatsAppClient:
    def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str,
        components: list
    ) -> dict: ...

    def send_text_message(self, to: str, body: str) -> dict: ...
```

### 10.3 Template Messages (harus di-approve Meta)

| Template Name | Trigger | Parameter |
|--------------|---------|-----------|
| `queue_alert` | Tinggal 3 antrian | nama_pasien, nomor_antrean, dokter |
| `booking_confirm` | Booking dibuat | nama_pasien, tanggal, jam, nomor_antrean |
| `visit_reminder_h1` | H-1 kunjungan | nama_pasien, tanggal, jam, dokter |
| `visit_reminder_hday` | Hari kunjungan | nama_pasien, jam, nama_klinik |
| `followup_reminder` | Jadwal kontrol ulang | nama_pasien, tanggal_kontrol |
| `low_stock_alert` | Stok obat menipis | nama_obat, stok_sisa, min_stok |

### 10.4 Chatbot Booking Flow (State Machine)

```
State: IDLE
  Trigger: "Daftar" / "daftar" / "booking"
  → State: ASK_NAME
  → Bot: "Selamat datang! Siapa nama Anda?"

State: ASK_NAME
  Trigger: pesan teks
  → State: ASK_DOCTOR (jika multi-dokter) atau ASK_DATE
  → Bot: "Pilih dokter:\n1. dr. Andi (Umum)\n2. dr. Budi (Anak)"

State: ASK_DOCTOR
  Trigger: angka pilihan
  → State: ASK_DATE
  → Bot: "Pilih hari:\n1. Senin (08:00-12:00)\n2. Rabu ..."

State: ASK_DATE
  Trigger: angka pilihan
  → State: CONFIRM
  → Bot: "Konfirmasi:\nNama: ...\nDokter: ...\nHari: ...\nKetik 'Ya' untuk konfirmasi"

State: CONFIRM
  Trigger: "Ya" / "ya"
  → State: DONE
  → Buat QueueEntry di database
  → Bot: "Pendaftaran berhasil! No. Antrean: 5 🎉\n..."
  → Kirim booking_confirm template

State: CONFIRM
  Trigger: "Tidak" / "tidak"
  → State: IDLE
  → Bot: "Pendaftaran dibatalkan. Ketik 'Daftar' untuk mulai lagi."
```

State disimpan di Redis: key `wa_chat_state_{phone_number}`, TTL 30 menit.

### 10.5 Webhook Handler

```
POST /api/whatsapp/webhook/  → Terima pesan masuk, proses chatbot
GET  /api/whatsapp/webhook/  → Verifikasi webhook Meta (challenge response)
```

---

## 11. Payment Gateway

### 11.1 Midtrans Integration

**Produk yang digunakan:**
- **QRIS** via Midtrans Snap / Core API
- **Virtual Account** — BCA, BNI, BRI, Mandiri, Permata
- **Cash** — diproses manual di sistem

```python
# apps/billing/midtrans.py
class MidtransClient:
    SANDBOX_URL = "https://api.sandbox.midtrans.com"
    PRODUCTION_URL = "https://api.midtrans.com"

    def create_qris_charge(self, invoice: Invoice) -> QRISResponse:
        """
        POST /v2/charge
        payment_type: "gopay" (QRIS compatible)
        Returns: qr_code_url, transaction_id
        """

    def create_va_charge(self, invoice: Invoice, bank: str) -> VAResponse:
        """
        POST /v2/charge
        payment_type: "bank_transfer"
        bank: bca | bni | bri | mandiri | permata
        Returns: va_number, bank, expiry_time
        """

    def verify_webhook_signature(
        self,
        order_id: str,
        status_code: str,
        gross_amount: str,
        server_key: str,
        received_signature: str
    ) -> bool:
        """
        SHA512(order_id + status_code + gross_amount + server_key)
        """
```

### 11.2 Payment Webhook Flow

```
Midtrans POST /api/payments/midtrans/webhook/
    │
    ▼
Verify signature (SHA512)
    │
    ▼
Update Invoice.payment_status berdasarkan transaction_status:
  - settlement / capture → paid
  - cancel / expire      → cancelled
  - pending              → pending
    │
    ▼
Jika paid:
  - Generate PDF invoice
  - Kirim WA ke pasien (opsional)
  - Update billing_invoice.paid_at
```

---

## 12. File Storage

### 12.1 MinIO Buckets

| Bucket | Konten | Access | URL Expiry |
|--------|--------|--------|------------|
| `dokterklik-medical` | Foto luka, hasil lab, USG | Private | Signed URL 1 jam |
| `dokterklik-invoices` | Invoice PDF | Private | Signed URL 15 menit |
| `dokterklik-reports` | Laporan bulanan PDF/CSV | Private | Signed URL 15 menit |
| `dokterklik-static` | CSS, JS, images | Public | Permanent |

### 12.2 Django Storage Config

```python
# config/settings/base.py
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "endpoint_url": env("MINIO_ENDPOINT"),
            "access_key": env("MINIO_ACCESS_KEY"),
            "secret_key": env("MINIO_SECRET_KEY"),
            "bucket_name": "dokterklik-medical",
            "file_overwrite": False,
            "default_acl": "private",
        },
    },
}
```

---

## 13. Infrastruktur & Docker

### 13.1 Docker Compose Services

```yaml
# docker-compose.yml
services:
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
    depends_on: [db, redis]
    env_file: .env

  celery:
    build: .
    command: celery -A config worker -l info -Q default,satusehat,notifications,reminders,reports
    depends_on: [db, redis]

  celery-beat:
    build: .
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    depends_on: [db, redis]

  db:
    image: postgres:16-alpine
    volumes: [postgres_data:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: dokterklik
      POSTGRES_USER: dokterklik
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes: [redis_data:/data]

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    volumes: [minio_data:/data]
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./docker/nginx.conf:/etc/nginx/conf.d/default.conf
      - ./static:/app/static
      - certbot_certs:/etc/letsencrypt
```

### 13.2 Environment Variables (.env.example)

```bash
# Django
DJANGO_SECRET_KEY=
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=dokterklik.com,www.dokterklik.com
DJANGO_SETTINGS_MODULE=config.settings.production

# Database
DATABASE_URL=postgres://dokterklik:password@db:5432/dokterklik

# Redis
REDIS_URL=redis://redis:6379/0

# Encryption
ENCRYPTION_KEY=   # Fernet key: Fernet.generate_key()

# SATUSEHAT (dikonfigurasi per klinik via Admin)
SATUSEHAT_BASE_URL=https://api-satusehat.kemkes.go.id

# MinIO
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=

# Midtrans
MIDTRANS_SERVER_KEY=
MIDTRANS_CLIENT_KEY=
MIDTRANS_IS_PRODUCTION=False

# WhatsApp Meta Cloud API
# (dikonfigurasi per klinik via Admin, bukan global)

# Email (untuk notifikasi internal)
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

---

## 14. Non-Functional Requirements

| Requirement | Target | Implementasi Teknis |
|-------------|--------|---------------------|
| Dashboard load | < 2 detik | Redis cache hasil agregasi, query dioptimasi dengan `select_related` + `prefetch_related`, index pada kolom sort |
| Patient search | < 500ms | `pg_trgm` GIN index pada `name_search`, limit 20 hasil |
| ICD-10 autocomplete | < 500ms | GIN index trigram pada tabel ICD-10, query dijalankan dengan connection pool |
| SATUSEHAT sync | < 10 detik | Async Celery task, tidak memblokir HTTP response |
| SATUSEHAT success rate | > 99% | Retry 5x exponential backoff, monitor failure rate per jam |
| Session timeout | 30 menit | `SessionTimeoutMiddleware` + Redis TTL |
| Data enkripsi | 100% at-rest + in-transit | Fernet untuk data medis, TLS 1.3 untuk semua traffic |
| Audit log | 100% akses data pasien | Middleware + retensi 5 tahun (partitioned table) |
| Uptime | 99.5% | Docker health checks, Nginx retry upstream |
| Multi-tenant isolation | 100% | `clinic` FK di semua tabel + custom QuerySet manager |
| Mobile responsif | ≥ 360px | Mobile-first CSS (Tailwind / Bootstrap 5) |
| Browser support | Chrome, Firefox, Safari, Edge | HTMX + vanilla JS, no transpilation dependency |

---

## 15. ICD-10 Database

### Data Source
- WHO ICD-10 release (CM/tabular) — ~14.000 kode billable
- Terjemahan bahasa Indonesia dari Kemenkes RI

### Import Strategy
```bash
python manage.py import_icd10 data/icd10_id.csv
```

Format CSV:
```
code,description_en,description_id,chapter,block,category,is_billable
A00.0,"Cholera due to Vibrio cholerae 01, biovar cholerae","Kolera akibat Vibrio cholerae 01, biovar cholerae",I,A00-A09,A00,true
```

### Frequent Code Cache
- Kode yang sering dipakai per dokter disimpan di Redis: `icd10_frequent_{doctor_id}`
- Update setiap kali dokter menyimpan diagnosis
- Ditampilkan sebagai shortlist di atas hasil autocomplete

---

## 16. Dependencies

```
# requirements.txt

# Core
Django>=5.0,<6.0
djangorestframework>=3.15
django-environ>=0.11

# Database
psycopg[binary]>=3.1

# Async Tasks
celery[redis]>=5.3
django-celery-beat>=2.6
redis>=5.0

# FHIR / Healthcare
fhir.resources>=7.1

# Security / Encryption
cryptography>=42.0

# File Storage
django-storages[s3]>=1.14
boto3>=1.34

# Frontend
django-htmx>=1.17
Jinja2>=3.1

# Payment
midtransclient>=1.4

# PDF Generation
weasyprint>=62.0

# Utilities
Pillow>=10.0
python-dateutil>=2.9
phonenumbers>=8.13

# Dev
django-debug-toolbar>=4.3
```

---

## 17. Development Milestones

### Phase 1 — MVP (Bulan 1–4)

| # | Task | Referensi PRD |
|---|------|---------------|
| 1 | Django project setup, Docker Compose, PostgreSQL, Redis | - |
| 2 | `accounts` app: CustomUser, login/logout, RBAC, session timeout | FR-DSH-06 |
| 3 | `clinics` app: Clinic model, multi-tenant QuerySet | - |
| 4 | `patients` app: Patient model (enkripsi), pencarian cepat | FR-EMR-06 |
| 5 | `emr` app: Visit SOAP form, autosave 30s, riwayat kunjungan | FR-EMR-01 to 05 |
| 6 | `emr` app: ICD-10 import + autocomplete (pg_trgm) | FR-ICD-01, 05 |
| 7 | `satusehat` app: OAuth auth, FHIR mapper, Celery sync tasks | FR-SS-01 to 05 |
| 8 | `queue` app: QueueEntry model, live HTMX display | FR-QUE-01, 04 |
| 9 | `billing` app: Invoice generation, pembayaran tunai | FR-BIL-01, 05 |
| 10 | Audit log middleware, enkripsi Fernet | Seksi 5.2 PRD |

### Phase 2 — Feature Complete (Bulan 5–8)

| # | Task | Referensi PRD |
|---|------|---------------|
| 11 | `whatsapp` app: Meta Cloud API client, chatbot booking | FR-WA-01 to 05 |
| 12 | `emr` app: E-Prescription terintegrasi form SOAP | FR-RX-01 to 05 |
| 13 | `inventory` app: Manajemen stok, low-stock alert | FR-INV-01 to 05 |
| 14 | Pengingat kontrol otomatis via Celery beat | FR-REM-01 to 04 |
| 15 | QRIS + Virtual Account via Midtrans | FR-BIL-03, 04 |
| 16 | `dashboard` app: Analytics harian/bulanan, export PDF/CSV | FR-DSH-01 to 05 |
| 17 | Notifikasi WA: queue alert, reminder, low stock | FR-QUE-02, INV-03 |
| 18 | SATUSEHAT dashboard monitoring + re-sync manual | FR-SS-04, 07 |

### Phase 3 — Edge Features (Bulan 9–12)

| # | Task | Referensi PRD |
|---|------|---------------|
| 19 | Portal pasien: OTP WA login, riwayat kunjungan | FR-PTL-01 to 05 |
| 20 | AI Medical Scribbler: speech-to-text → SOAP | FR-AI-01 to 05 |
| 21 | Telekonsultasi: WebRTC video call terintegrasi | FR-TEL-01 to 05 |

---

*--- Akhir Dokumen ---*

*Technical Requirements Document ini merupakan turunan langsung dari PRD DokterKlik v1.0 dan menjadi referensi utama proses development. Setiap perubahan pada dokumen ini harus direview dan disetujui oleh tech lead sebelum diimplementasikan.*
