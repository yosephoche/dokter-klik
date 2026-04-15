# DokterKlik

Platform SaaS manajemen klinik untuk klinik pratama dan dokter praktik mandiri di Indonesia.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Django](https://img.shields.io/badge/Django-5.x-green) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

---

## Overview

DokterKlik menggabungkan semua kebutuhan operasional klinik dalam satu platform:

- **Smart EMR** — Rekam medis berbasis SOAP dengan auto-coding ICD-10
- **SATUSEHAT** — Sinkronisasi wajib ke platform Kemenkes (PMK No. 24/2022) via HL7 FHIR R4
- **Antrean Real-time** — Display publik tanpa login, notifikasi WhatsApp saat giliran dekat
- **Billing & Pembayaran** — Invoice otomatis dari data EMR, QRIS + Virtual Account via Midtrans
- **WhatsApp** — Booking, konfirmasi jadwal, resep digital, pengingat kontrol
- **Inventori Apotek** — Stok obat, alert stok menipis

**Model bisnis**: SaaS multi-tenant — Starter (gratis) / Pro (Rp 150.000/bln) / Plus (Rp 300.000/bln)

---

## Tech Stack

| Komponen | Teknologi | Versi |
|----------|-----------|-------|
| Backend | Django | ≥5.0, <5.2 |
| REST API | Django REST Framework | ≥3.15 |
| Database | PostgreSQL | 16 |
| Cache & Message Broker | Redis | 7 |
| Task Queue | Celery + django-celery-beat | ≥5.3 |
| Frontend | HTMX + Jinja2 | Latest |
| File Storage | MinIO (S3-compatible) | Latest |
| Web Server | Nginx + Gunicorn | Latest / ≥21.2 |
| PDF Generation | WeasyPrint | ≥62.0 |
| Enkripsi | Python cryptography (Fernet) | ≥42.0 |
| FHIR Validation | fhir.resources | ≥7.1 |
| Payment Gateway | Midtrans | Latest |
| Container | Docker + Docker Compose | Latest |

---

## Prasyarat

**Dengan Docker** (direkomendasikan):
- Docker ≥24 + Docker Compose v2
- Git

**Tanpa Docker**:
- Python 3.12+
- PostgreSQL 16
- Redis 7
- Git
- (Opsional) MinIO untuk file storage

---

## Quick Start — Dengan Docker

```bash
# 1. Clone repository
git clone <repo-url>
cd dokterklik

# 2. Salin dan konfigurasi environment
cp .env.example .env

# 3. Generate Fernet encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Salin output ke ENCRYPTION_KEY di .env

# 4. Jalankan semua service
docker-compose up -d

# 5. Jalankan migrasi database
docker-compose exec web python manage.py migrate

# 6. Buat superuser admin
docker-compose exec web python manage.py createsuperuser

# 7. Buka aplikasi
open http://localhost
```

### Services & Port

| Service | URL / Port | Keterangan |
|---------|-----------|-----------|
| Web app | http://localhost | Via Nginx reverse proxy |
| Django langsung | http://localhost:8000 | Bypass Nginx (dev only) |
| MinIO console | http://localhost:9001 | Admin file storage |
| Django admin | http://localhost/admin/ | Superuser panel |

> **Catatan**: `entrypoint.sh` otomatis menunggu database siap, menjalankan migrasi, dan mengumpulkan static files setiap kali container `web` start.

---

## Setup Lokal — Tanpa Docker

### 1. Install sistem dependencies

**macOS (Homebrew):**
```bash
brew install postgresql@16 redis python@3.12
brew services start postgresql@16
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y postgresql-16 redis-server python3.12 python3.12-venv \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libpq-dev gcc
sudo systemctl start postgresql redis
```

### 2. Buat database PostgreSQL

```bash
psql -U postgres -c "CREATE USER dokterklik WITH PASSWORD 'dokterklik';"
psql -U postgres -c "CREATE DATABASE dokterklik OWNER dokterklik;"
```

### 3. Setup Python environment

```bash
python3.12 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 4. Konfigurasi environment

```bash
cp .env.example .env
```

Edit `.env` untuk menggunakan koneksi lokal (bukan nama service Docker):

```bash
DATABASE_URL=postgres://dokterklik:dokterklik@localhost:5432/dokterklik
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000          # atau komentari jika tidak pakai MinIO
```

Generate encryption key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste output ke ENCRYPTION_KEY di .env
```

### 5. Setup database & jalankan server

```bash
# Terminal 1 — Django dev server
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

```bash
# Terminal 2 — Celery worker
celery -A config worker -Q satusehat,notifications,reminders,reports -l info
```

```bash
# Terminal 3 — Celery beat scheduler (opsional, untuk reminder otomatis)
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Aplikasi tersedia di: http://localhost:8000

---

## Production Deployment

```bash
# Pastikan .env sudah production-ready:
# DEBUG=False, ALLOWED_HOSTS=<domain>, DJANGO_SETTINGS_MODULE=config.settings.production
# EMAIL_HOST, MIDTRANS_SANDBOX=False, dll.

docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Perbedaan production vs development:**
- Gunicorn: 8 workers (vs 4 dev), access log aktif
- Nginx: port 80 + 443, SSL via Let's Encrypt (`/etc/letsencrypt`)
- Semua service dengan `restart: always`
- `DJANGO_SETTINGS_MODULE=config.settings.production` (HTTPS enforced, HSTS, secure cookies)

Lihat `docs/RUNBOOK.md` untuk prosedur lengkap, health check, dan rollback.

---

## Environment Variables

Variabel paling kritis:

| Variable | Wajib | Keterangan |
|----------|-------|-----------|
| `SECRET_KEY` | Ya | Django secret key, min 50 karakter |
| `ENCRYPTION_KEY` | Ya | Fernet key untuk enkripsi data medis & PII |
| `DATABASE_URL` | Ya | PostgreSQL connection string |
| `REDIS_URL` | Ya | Redis connection string |
| `DJANGO_SETTINGS_MODULE` | Ya | `config.settings.development` atau `production` |
| `SATUSEHAT_BASE_URL` | Ya | URL API SATUSEHAT (staging/production) |
| `WHATSAPP_VERIFY_TOKEN` | Ya | Token verifikasi webhook Meta |
| `MIDTRANS_SERVER_KEY` | Ya | Server key Midtrans |

Lihat **[docs/ENV.md](docs/ENV.md)** untuk referensi lengkap semua 29 variabel dengan kategori dan nilai contoh.

---

## Struktur Project

```
dokterklik/
├── config/
│   ├── settings/
│   │   ├── base.py          # Settings dasar semua environment
│   │   ├── development.py   # DEBUG=True, console email, CORS terbuka
│   │   └── production.py    # HTTPS, HSTS, secure cookies
│   ├── urls.py              # Root URL config
│   └── celery.py            # Celery app & queue routing
│
├── apps/
│   ├── core/                # Enkripsi (Fernet), RBAC, middleware, base model
│   ├── accounts/            # Auth, CustomUser, RBAC roles
│   ├── clinics/             # Multi-tenant root: Clinic, DoctorSchedule
│   ├── patients/            # Data pasien (NIK terenkripsi)
│   ├── emr/                 # EMR SOAP: Visit, Diagnosis, Prescription, ICD-10
│   ├── queue/               # Antrean real-time (ada public view tanpa auth)
│   ├── billing/             # Invoice & Midtrans payment
│   ├── inventory/           # Stok obat & apotek
│   ├── satusehat/           # FHIR R4 sync ke Kemenkes
│   ├── whatsapp/            # Bot booking & notifikasi
│   └── dashboard/           # Analytics & laporan PDF
│
├── templates/               # Jinja2 templates
├── static/                  # CSS, JS, assets
├── docker/
│   ├── Dockerfile           # Python 3.12-slim + WeasyPrint deps
│   ├── entrypoint.sh        # Startup: tunggu DB → migrate → collectstatic
│   └── nginx.conf
├── docker-compose.yml       # Development
├── docker-compose.prod.yml  # Production overrides
├── requirements.txt
└── .env.example
```

### RBAC Roles

| Role | Akses |
|------|-------|
| `owner` | Semua data + laporan keuangan |
| `doctor` | Hanya pasien & visit milik sendiri |
| `admin` | Seluruh data klinik |
| `pharmacy` | Data resep & inventori klinik |
| `patient` | Hanya data diri sendiri (portal pasien) |

---

## API Endpoints

Semua endpoint internal memerlukan autentikasi JWT. Endpoint publik ditandai.

| Prefix | App | Keterangan |
|--------|-----|-----------|
| `POST /api/auth/login/` | accounts | JWT login |
| `GET/POST /api/patients/` | patients | CRUD data pasien |
| `GET/POST /api/visits/` | emr | CRUD rekam medis (SOAP) |
| `GET /api/icd10/` | emr | Autocomplete kode ICD-10 |
| `GET/POST /api/queue/` | queue | Manajemen antrean |
| `GET/POST /api/invoices/` | billing | Invoice |
| `POST /api/payments/` | billing | Pembayaran (cash, QRIS, VA) |
| `GET/POST /api/inventory/` | inventory | Stok obat |
| `GET /api/satusehat/` | satusehat | Status sync & re-sync |
| `GET /api/dashboard/` | dashboard | Analytics & laporan |
| `ANY /webhooks/whatsapp/` | whatsapp | **Publik** — Meta webhook receiver |
| `GET /queue/live/<slug>/` | queue | **Publik** — Display antrean real-time |

---

## Celery Task Queues

| Queue | Tugas |
|-------|-------|
| `satusehat` | Sinkronisasi FHIR ke SATUSEHAT, retry exponential backoff (maks 5×) |
| `notifications` | Kirim WhatsApp: booking, konfirmasi, resep digital, tagihan |
| `reminders` | Pengingat kontrol H-3 & H-hari, alert stok obat menipis |
| `reports` | Generate laporan PDF, export CSV |

```bash
# Start workers (Docker)
docker-compose exec celery celery -A config worker \
    -Q satusehat,notifications,reminders,reports -l info --concurrency=4

# Start beat scheduler (Docker)
docker-compose exec celery-beat celery -A config beat -l info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Periodic tasks dikelola via Django admin: `/admin/django_celery_beat/`

---

## Integrasi Utama

### SATUSEHAT (Wajib — PMK No. 24/2022)
- Protokol: HL7 FHIR R4 + OAuth 2.0 Client Credentials
- Trigger: otomatis setelah dokter finalize kunjungan EMR
- Resources yang dikirim: `Patient`, `Encounter`, `Condition`, `Observation`, `MedicationRequest`
- Retry: exponential backoff maks 5× (interval 1–16 menit)
- Log: request/response disimpan minimal 5 tahun
- URL staging: `https://api-satusehat-stg.dto.kemkes.go.id`
- Credentials per-klinik disimpan terenkripsi di database

### WhatsApp (Meta Cloud API)
- Webhook: `POST /webhooks/whatsapp/` (publik, tanpa auth)
- Verifikasi: `WHATSAPP_VERIFY_TOKEN` di Meta developer console
- Aktifkan dengan `WHATSAPP_ENABLED=True` di `.env`
- Fallback ke SMS gateway jika WhatsApp tidak tersedia

### Midtrans (Payment Gateway)
- Metode: QRIS + Virtual Account (BCA, Mandiri, BNI, CIMB)
- Mode sandbox: `MIDTRANS_SANDBOX=True` (default dev)
- Billing dihitung otomatis dari data EMR (konsultasi + tindakan + obat)

---

## Testing

```bash
# Semua test (Docker)
docker-compose exec web python manage.py test

# Test app tertentu
docker-compose exec web python manage.py test apps.patients

# Dengan coverage
docker-compose exec web coverage run manage.py test
docker-compose exec web coverage report
docker-compose exec web coverage html   # Output: htmlcov/

# Lokal (non-Docker)
python manage.py test
```

---

## Development Roadmap

| Fase | Scope | Timeline |
|------|-------|----------|
| **Phase 1 — MVP** | Smart EMR (SOAP), Integrasi SATUSEHAT, Auto-Coding ICD-10, Billing dasar, Antrean real-time | Bulan 1–4 |
| **Phase 2 — Feature Complete** | Booking WhatsApp, E-Prescription, Inventori Apotek, Pengingat Kontrol, Dashboard Analytics | Bulan 5–8 |
| **Phase 3 — Edge** | Portal Pasien, AI Medical Scribbler (Voice-to-Text), Telekonsultasi (WebRTC) | Bulan 9–12 |
| **Phase 4 — Scale** | Optimasi performa, integrasi BPJS, mobile app native | Bulan 13+ |

---

## Keamanan

- **Enkripsi at-rest**: semua data medis & PII menggunakan Fernet symmetric encryption
- **Enkripsi in-transit**: HTTPS/TLS 1.3 wajib di production (Let's Encrypt auto-renewal)
- **Audit log**: semua akses data pasien dicatat (siapa, kapan, data apa)
- **Session timeout**: auto-logout setelah 30 menit tidak aktif
- **RBAC**: setiap role hanya dapat mengakses data yang relevan
- **Multi-tenancy**: setiap query wajib di-filter per klinik — tidak ada data bocor antar tenant
- **Compliance**: UU PDP No. 27/2022 + PMK No. 24/2022

---

## Dokumentasi

| Dokumen | Isi |
|---------|-----|
| [docs/ENV.md](docs/ENV.md) | Semua environment variables (29 variabel, kategorized) |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Dev setup, kode style, cara menulis test, PR checklist |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Deployment, health check, troubleshooting, rollback, compliance |
