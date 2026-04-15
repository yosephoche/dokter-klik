# Environment Variables

Copy `.env.example` to `.env` and fill in all required values before running the project.

> **Never commit `.env` to version control.**

<!-- AUTO-GENERATED:ENV -->
## Django

| Variable | Required | Description | Example / Default |
|----------|----------|-------------|-------------------|
| `DJANGO_SETTINGS_MODULE` | Yes | Settings module to load | `config.settings.development` |
| `SECRET_KEY` | Yes | Django secret key — min 50 chars, unique per environment | `your-very-secret-key-...` |
| `DEBUG` | No | Enable debug mode (never `True` in production) | `True` |
| `ALLOWED_HOSTS` | Yes | Comma-separated allowed hostnames | `localhost,127.0.0.1` |

## Encryption

| Variable | Required | Description | Example / Default |
|----------|----------|-------------|-------------------|
| `ENCRYPTION_KEY` | Yes | Fernet symmetric key for at-rest encryption of PII and medical data. Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | — |

## Database

| Variable | Required | Description | Example / Default |
|----------|----------|-------------|-------------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgres://dokterklik:dokterklik@db:5432/dokterklik` |
| `POSTGRES_DB` | Yes | Database name (used by the `db` Docker service) | `dokterklik` |
| `POSTGRES_USER` | Yes | PostgreSQL username | `dokterklik` |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password | `dokterklik` |

## Redis

| Variable | Required | Description | Example / Default |
|----------|----------|-------------|-------------------|
| `REDIS_URL` | Yes | Redis connection string (used by Celery and Django cache) | `redis://redis:6379/0` |

## MinIO (File Storage)

| Variable | Required | Description | Example / Default |
|----------|----------|-------------|-------------------|
| `MINIO_ENDPOINT` | Yes | MinIO host:port | `minio:9000` |
| `MINIO_ROOT_USER` | Yes | MinIO admin username | `minioadmin` |
| `MINIO_ROOT_PASSWORD` | Yes | MinIO admin password | `minioadmin123` |
| `MINIO_BUCKET_NAME` | Yes | Default storage bucket | `dokterklik` |
| `AWS_ACCESS_KEY_ID` | Yes | S3-compatible access key (same as MinIO root user) | `minioadmin` |
| `AWS_SECRET_ACCESS_KEY` | Yes | S3-compatible secret key (same as MinIO root password) | `minioadmin123` |
| `AWS_STORAGE_BUCKET_NAME` | Yes | Bucket name for `django-storages` | `dokterklik` |
| `AWS_S3_ENDPOINT_URL` | Yes | Full URL for MinIO S3 endpoint | `http://minio:9000` |

## SATUSEHAT

| Variable | Required | Description | Example / Default |
|----------|----------|-------------|-------------------|
| `SATUSEHAT_BASE_URL` | Yes | SATUSEHAT API base URL | `https://api-satusehat-stg.dto.kemkes.go.id` (staging) |
| `SATUSEHAT_CLIENT_ID` | No | Default client ID for testing (per-clinic credentials stored encrypted in DB) | — |
| `SATUSEHAT_CLIENT_SECRET` | No | Default client secret for testing | — |

## WhatsApp (Meta Cloud API)

| Variable | Required | Description | Example / Default |
|----------|----------|-------------|-------------------|
| `WHATSAPP_VERIFY_TOKEN` | Yes | Webhook verification token for Meta | `your-webhook-verify-token` |
| `WHATSAPP_ENABLED` | No | Enable WhatsApp integration | `False` |

## Midtrans (Payment Gateway)

| Variable | Required | Description | Example / Default |
|----------|----------|-------------|-------------------|
| `MIDTRANS_SERVER_KEY` | Yes | Midtrans server key | — |
| `MIDTRANS_CLIENT_KEY` | Yes | Midtrans client key | — |
| `MIDTRANS_SANDBOX` | No | Use Midtrans sandbox environment | `True` |

## Email

| Variable | Required | Description | Example / Default |
|----------|----------|-------------|-------------------|
| `EMAIL_BACKEND` | No | Django email backend | `django.core.mail.backends.console.EmailBackend` (dev) |
| `EMAIL_HOST` | No | SMTP server hostname | — |
| `EMAIL_PORT` | No | SMTP port | `587` |
| `EMAIL_HOST_USER` | No | SMTP username | — |
| `EMAIL_HOST_PASSWORD` | No | SMTP password | — |
| `DEFAULT_FROM_EMAIL` | No | Default sender address | `noreply@dokterklik.id` |
<!-- /AUTO-GENERATED:ENV -->
