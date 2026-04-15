# DokterKlik — Claude Code Context

## Project Overview

DokterKlik adalah platform SaaS manajemen klinik untuk klinik pratama dan dokter praktik mandiri di Indonesia. Platform ini menggabungkan EMR berbasis SOAP, integrasi wajib SATUSEHAT (PMK No. 24/2022), sistem antrean real-time, billing terintegrasi, dan notifikasi WhatsApp. Model bisnis: SaaS subscription (Starter gratis / Pro Rp 150rb / Plus Rp 300rb per bulan). Multi-tenant: satu deployment melayani banyak klinik dengan isolasi data ketat.

---

## Tech Stack

| Komponen | Teknologi | Versi |
|----------|-----------|-------|
| Backend Framework | Django | LTS 5.x |
| REST API | Django REST Framework | 3.15+ |
| Database | PostgreSQL | 16 |
| Task Queue | Celery | 5.3+ |
| Message Broker / Cache | Redis | 7 |
| Frontend | HTMX + Jinja2 | Latest |
| File Storage | MinIO (S3-compatible) | Latest |
| Reverse Proxy | Nginx | Latest |
| Containerization | Docker + Docker Compose | Latest |
| Enkripsi | Python `cryptography` (Fernet) | 42+ |
| FHIR Validation | `fhir.resources` | 7.1+ |
| PDF Generation | WeasyPrint | 62+ |
| Payment Gateway | Midtrans | Latest |

---

## Project Structure

```
dokterklik/
├── config/
│   ├── settings/
│   │   ├── base.py          # Settings dasar semua environment
│   │   ├── development.py   # DEBUG=True, SMTP console
│   │   └── production.py    # HTTPS, ALLOWED_HOSTS
│   ├── urls.py              # Root URL config
│   ├── celery.py            # Celery app & beat schedule
│   └── wsgi.py / asgi.py
│
├── apps/
│   ├── core/                # Shared utilities
│   │   ├── encryption.py    # Fernet encrypt/decrypt + custom EncryptedField
│   │   ├── permissions.py   # RBAC permission classes
│   │   ├── middleware.py    # Audit log + session timeout (30 min)
│   │   ├── managers.py      # ClinicScopedManager
│   │   └── models.py        # Abstract base model (UUID PK, created_at, updated_at)
│   │
│   ├── accounts/            # Auth, User, RBAC
│   │   └── models.py        # CustomUser (role, clinic FK, MFA)
│   │
│   ├── clinics/             # Multi-tenant klinik
│   │   └── models.py        # Clinic, DoctorSchedule
│   │
│   ├── patients/            # Data pasien (NIK dienkripsi)
│   ├── emr/                 # Electronic Medical Record SOAP
│   │   └── models.py        # Visit, Diagnosis, Prescription, Template, ICD10Code
│   │
│   ├── queue/               # Antrean real-time (ada public view tanpa auth)
│   ├── billing/             # Invoice & pembayaran
│   │   └── midtrans.py      # Midtrans API client
│   │
│   ├── inventory/           # Stok obat & apotek mini
│   ├── satusehat/           # Integrasi SATUSEHAT FHIR R4
│   │   ├── auth.py          # OAuth 2.0 token management
│   │   ├── fhir_mapper.py   # Model → FHIR resource builder
│   │   ├── client.py        # HTTP client ke API SATUSEHAT
│   │   ├── tasks.py         # Celery tasks: sync + exponential backoff
│   │   └── models.py        # SyncLog
│   │
│   ├── whatsapp/            # Bot & notifikasi WhatsApp
│   │   ├── client.py        # Meta Cloud API client
│   │   ├── chatbot.py       # State machine booking flow
│   │   └── tasks.py         # Celery tasks: kirim notifikasi
│   │
│   └── dashboard/           # Analytics & laporan
│
├── templates/               # Jinja2 templates (base.html + per-app)
├── static/                  # CSS, JS, assets
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

## Architecture

### Multi-Tenancy
Semua tabel utama memiliki FK ke `clinics_clinic`. Setiap query **wajib** di-filter berdasarkan klinik pengguna yang login:

```python
# apps/core/managers.py
class ClinicScopedManager(models.Manager):
    def for_clinic(self, clinic):
        return self.get_queryset().filter(clinic=clinic)
```

Jangan pernah query model multi-tenant tanpa `.for_clinic(request.user.clinic)`.

### Celery Queues
| Queue | Tugas |
|-------|-------|
| `satusehat` | Sinkronisasi FHIR ke SATUSEHAT, retry mechanism |
| `notifications` | Kirim WhatsApp booking, konfirmasi, tagihan |
| `reminders` | Pengingat kontrol ulang H-3 dan H-hari |
| `reports` | Generate laporan PDF, export CSV |

---

## Key Conventions

### Models
- Semua model inherit dari abstract base di `apps/core/models.py` (UUID PK, `created_at`, `updated_at`).
- Field sensitif (rekam medis, NIK, token SATUSEHAT, token WhatsApp) **wajib** menggunakan `EncryptedField` dari `apps/core/encryption.py` (Fernet symmetric encryption).
- Kolom sensitif di DB disimpan sebagai `BYTEA`.

### RBAC
Roles yang valid: `owner`, `doctor`, `admin`, `pharmacy`, `patient`. Enforce via `apps/core/permissions.py`. Role-based access:
- `doctor`: hanya data pasiennya sendiri
- `admin`, `pharmacy`: seluruh klinik
- `owner`: semua data + laporan keuangan
- `patient`: hanya data diri sendiri (portal pasien)

### Frontend (HTMX + Jinja2)
- **Tidak ada SPA** — semua server-rendered.
- Gunakan HTMX partial response (`hx-target`, `hx-swap`) untuk update UI tanpa full reload.
- Auto-save EMR setiap 30 detik via JavaScript timer + `hx-post`.
- Responsif mobile-first, dukung resolusi ≥ 360px.
- Dukung browser: Chrome, Firefox, Safari, Edge (versi terbaru).

### API
- Semua endpoint REST menggunakan Django REST Framework ViewSet + serializer.
- Public endpoint (antrean live, webhook WhatsApp) tidak memerlukan auth.
- Seluruh API internal memerlukan autentikasi + pemeriksaan role.

---

## SATUSEHAT Integration

**Alur sinkronisasi** (setelah dokter simpan SOAP):
1. Validasi data + kode ICD menggunakan `fhir.resources`
2. Celery task di-queue ke `satusehat`
3. FHIR resources yang dikirim: `Patient`, `Encounter`, `Condition`, `Observation`, `MedicationRequest`
4. Response dicatat di tabel `SyncLog` (status: `success` / `failed` / `pending`)
5. Jika gagal: retry exponential backoff maksimal **5×** (interval 1–16 menit)
6. Failure rate > 10% dalam 1 jam → alert ke admin klinik

**Autentikasi**: OAuth 2.0 Client Credentials (`client_id` + `client_secret` dari portal SATUSEHAT, disimpan terenkripsi di `clinics_clinic`).

**Logging**: Setiap request/response ke API SATUSEHAT di-log lengkap (timestamp, payload, HTTP status, response body). Retensi log **minimal 5 tahun**.

---

## WhatsApp Integration

- Provider: Meta Cloud API (WhatsApp Business API)
- Webhook handler: `apps/whatsapp/urls.py`
- Booking flow: state machine di `apps/whatsapp/chatbot.py`
- Notifikasi yang dikirim: konfirmasi booking, antrean tinggal 3 nomor, pengingat H-1 dan H-hari, resep digital, alert stok obat menipis
- Fallback: SMS gateway jika WhatsApp API tidak tersedia (arsitektur messaging abstrak)

---

## Payment Gateway

- Provider: **Midtrans** (QRIS + Virtual Account bank-bank utama)
- Client: `apps/billing/midtrans.py`
- Billing dihitung otomatis dari data EMR: konsultasi + tindakan + obat
- Invoice dikirim sebagai PDF atau via WhatsApp

---

## Security Rules

1. **Enkripsi at-rest**: semua data medis dan PII dienkripsi dengan Fernet. Encryption key hanya di environment variable, **tidak pernah** di database atau version control.
2. **Enkripsi in-transit**: wajib HTTPS/TLS 1.3. SSL via Let's Encrypt dengan auto-renewal.
3. **Audit log**: semua akses data medis pasien dicatat (siapa, kapan, data apa).
4. **Session timeout**: otomatis logout setelah 30 menit tidak aktif.
5. **MFA**: opsional untuk akun doctor dan admin (TOTP, secret dienkripsi).
6. **Data hosting**: wajib di data center Indonesia.
7. **Compliance**: UU PDP No. 27/2022 + PMK No. 24/2022 (Rekam Medis Elektronik).
8. **Penetration testing**: berkala — jangan menambah endpoint baru tanpa mempertimbangkan attack surface.

---

## Non-Functional Requirements

| Kategori | Target |
|----------|--------|
| Muat halaman dashboard | < 2 detik |
| Pencarian pasien & autocomplete ICD | < 500ms |
| Sinkronisasi SATUSEHAT per encounter | < 10 detik |
| Uptime | 99.5% |
| RTO | < 4 jam |
| RPO | < 1 jam |
| Kapasitas | 500 klinik, 100.000 rekam medis per klinik |

---

## Development Phases

| Fase | Scope |
|------|-------|
| **Phase 1 — MVP** (Bulan 1–4) | Smart EMR (SOAP), Integrasi SATUSEHAT, Auto-Coding ICD-10, Billing dasar, Antrean real-time |
| **Phase 2 — Feature Complete** (Bulan 5–8) | Booking WhatsApp, E-Prescription, Inventori Apotek, Pengingat Kontrol, Dashboard Analytics |
| **Phase 3 — Edge** (Bulan 9–12) | Portal Pasien, AI Medical Scribbler (Voice-to-Text), Telekonsultasi Hybrid (WebRTC) |
| **Phase 4 — Scale** (Bulan 13+) | Optimasi performa, integrasi BPJS, mobile app native |

---

## Running the Project

```bash
# Setup awal
cp .env.example .env
# Edit .env: isi DATABASE_URL, REDIS_URL, SATUSEHAT_*, WHATSAPP_*, MIDTRANS_*, FERNET_KEY

# Jalankan semua service
docker-compose up -d

# Migrasi database
docker-compose exec web python manage.py migrate

# Buat superuser
docker-compose exec web python manage.py createsuperuser

# Jalankan Celery workers (per queue)
docker-compose exec celery celery -A config worker -Q satusehat,notifications,reminders,reports -l info

# Jalankan Celery beat (scheduler untuk reminder otomatis)
docker-compose exec celery celery -A config beat -l info

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables Kritis
| Variable | Keterangan |
|----------|-----------|
| `FERNET_KEY` | Master encryption key — generate dengan `Fernet.generate_key()`, **jangan commit** |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `SATUSEHAT_BASE_URL` | URL API SATUSEHAT (staging/production) |
| `WHATSAPP_VERIFY_TOKEN` | Token verifikasi webhook Meta |
| `MIDTRANS_SERVER_KEY` | Server key Midtrans |
| `MINIO_ENDPOINT` | Endpoint MinIO untuk file storage |
