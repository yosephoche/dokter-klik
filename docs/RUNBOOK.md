# Runbook — DokterKlik

Operational reference for deploying, monitoring, and recovering the DokterKlik platform.

## Deployment

<!-- AUTO-GENERATED:DEPLOY -->
### Development

```bash
cp .env.example .env
# Edit .env (see docs/ENV.md for all variables)

docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Production

```bash
# Ensure .env is production-ready (DEBUG=False, ALLOWED_HOSTS set, HTTPS creds, etc.)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run migrations (always before starting web workers)
docker-compose exec web python manage.py migrate --noinput

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

Production overrides (`docker-compose.prod.yml`):
- Web: 8 Gunicorn workers, `restart: always`
- Celery workers + beat: `restart: always`
- Nginx: ports 80 + 443, Let's Encrypt certs from `/etc/letsencrypt`

### Services & Ports

| Service | Port | Notes |
|---------|------|-------|
| Nginx (reverse proxy) | 80, 443 | Entry point for all traffic |
| Django (Gunicorn) | 8000 | Behind Nginx; not exposed publicly in prod |
| PostgreSQL 16 | 5432 | Internal only |
| Redis 7 | 6379 | Internal only |
| MinIO S3 | 9000 | File storage API |
| MinIO console | 9001 | Admin UI (dev only) |

### Celery Workers

```bash
# Workers (process async tasks across all queues)
celery -A config worker -Q satusehat,notifications,reminders,reports -l info --concurrency=4

# Beat scheduler (triggers periodic reminder tasks)
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Queues:
| Queue | Purpose |
|-------|---------|
| `satusehat` | FHIR sync to SATUSEHAT API, exponential-backoff retry |
| `notifications` | WhatsApp booking confirmations, invoices |
| `reminders` | Follow-up reminders H-3 and same-day |
| `reports` | PDF generation, CSV export |
<!-- /AUTO-GENERATED:DEPLOY -->

## Health Checks

| Check | Command / URL |
|-------|--------------|
| Django | `GET /admin/` → should return 200 or 302 |
| Database | `docker-compose exec db pg_isready -U dokterklik` |
| Redis | `docker-compose exec redis redis-cli ping` → `PONG` |
| MinIO | `curl -f http://localhost:9000/minio/health/live` |
| Celery | `docker-compose exec celery celery -A config inspect ping` |

## Common Issues & Fixes

### Database not ready on startup
The web container waits for `manage.py check --database default` to succeed before starting. If it loops:
1. Check `docker-compose logs db` for PostgreSQL errors
2. Verify `DATABASE_URL` / `POSTGRES_*` in `.env`

### Migrations out of sync
```bash
docker-compose exec web python manage.py showmigrations   # identify unapplied
docker-compose exec web python manage.py migrate          # apply
```

### SATUSEHAT sync failures
- Check `SyncLog` table for `status=failed` records and their `response_body`
- Retry up to 5× with exponential backoff is automatic (1–16 min intervals)
- If failure rate > 10% in 1 hour, alert is sent to clinic admin
- Verify `SATUSEHAT_BASE_URL`, `SATUSEHAT_CLIENT_ID`, `SATUSEHAT_CLIENT_SECRET` in `.env`

### WhatsApp webhook not receiving events
1. Confirm `WHATSAPP_VERIFY_TOKEN` matches the token registered in Meta developer console
2. Nginx must proxy `POST /webhooks/whatsapp/` to Django
3. Check `WHATSAPP_ENABLED=True` in `.env`

### Static files not loading (production)
```bash
docker-compose exec web python manage.py collectstatic --noinput
# Ensure Nginx `static_files` volume is mounted at /app/staticfiles
```

### Encryption key mismatch
If `ENCRYPTION_KEY` changes after data was written, encrypted fields will raise `InvalidToken`. **Never rotate the key without a migration script** that re-encrypts all `EncryptedField` columns.

## Rollback Procedures

### Application rollback
```bash
# Pull previous image / tag
docker-compose pull web   # or specify image tag

# Re-deploy (migrations are not automatically reversed)
docker-compose up -d web
```

### Database rollback
```bash
# Roll back a specific migration
docker-compose exec web python manage.py migrate <app_label> <migration_name>
```

> Rolling back destructive migrations (dropping columns, tables) requires a database backup. Restore from backup if automated rollback is insufficient.

### Backup & Restore
```bash
# Backup PostgreSQL
docker-compose exec db pg_dump -U dokterklik dokterklik > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T db psql -U dokterklik dokterklik < backup_YYYYMMDD.sql
```

## Alerting & Escalation

| Condition | Trigger | Action |
|-----------|---------|--------|
| SATUSEHAT failure rate > 10%/hr | Automatic (Celery task) | Alert sent to clinic admin |
| Uptime < 99.5% | External monitor | Page on-call engineer |
| RTO breach (> 4 hrs downtime) | — | Escalate to CTO |
| RPO breach (> 1 hr data loss) | — | Escalate to CTO + legal |
| Encryption key exposure | Manual detection | Rotate key immediately + notify DPO |

## Compliance Notes

- Audit logs are retained for **minimum 5 years** (PMK No. 24/2022)
- SATUSEHAT request/response logs: full payload, timestamp, HTTP status — retained 5 years
- Data must be hosted in **Indonesia data centers**
- UU PDP No. 27/2022: any PII breach must be reported within 14 days
