# Contributing to DokterKlik

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

## Development Environment Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd dokterklik

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — at minimum set ENCRYPTION_KEY (see ENV.md for all variables)

# 3. Generate the Fernet encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste output into ENCRYPTION_KEY in .env

# 4. Start all services
docker-compose up -d

# 5. Run database migrations
docker-compose exec web python manage.py migrate

# 6. Create a superuser
docker-compose exec web python manage.py createsuperuser
```

Services will be available at:

| Service | URL |
|---------|-----|
| Web app | http://localhost:80 |
| Django direct | http://localhost:8000 |
| MinIO console | http://localhost:9001 |

<!-- AUTO-GENERATED:COMMANDS -->
## Available Commands

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start all services in the background |
| `docker-compose down` | Stop all services |
| `docker-compose exec web python manage.py migrate` | Run database migrations |
| `docker-compose exec web python manage.py makemigrations` | Generate new migrations |
| `docker-compose exec web python manage.py createsuperuser` | Create a Django admin user |
| `docker-compose exec web python manage.py collectstatic` | Collect static files |
| `docker-compose exec web python manage.py shell_plus` | Open Django shell with all models auto-imported |
| `docker-compose exec web python manage.py test` | Run the test suite |
| `docker-compose exec web coverage run manage.py test` | Run tests with coverage |
| `docker-compose exec web coverage report` | Show coverage report |
| `celery -A config worker -Q satusehat,notifications,reminders,reports -l info` | Start Celery workers |
| `celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler` | Start Celery beat scheduler |
<!-- /AUTO-GENERATED:COMMANDS -->

## Testing

### Running tests

```bash
# All tests
docker-compose exec web python manage.py test

# Specific app
docker-compose exec web python manage.py test apps.patients

# With coverage
docker-compose exec web coverage run manage.py test
docker-compose exec web coverage report
docker-compose exec web coverage html   # generates htmlcov/
```

### Writing tests

- Place tests in `apps/<app>/tests/` or `apps/<app>/tests.py`
- Use `factory_boy` for model factories
- Tests that touch the database must use `TestCase` (not `SimpleTestCase`)
- Multi-tenant tests: always scope queries with `.for_clinic()` — test isolation depends on it
- Mock external APIs (SATUSEHAT, WhatsApp, Midtrans) — never call them in tests

## Code Style

- Follow PEP 8
- Model fields: sensitive PII / medical data **must** use `EncryptedField` from `apps/core/encryption.py`
- All models must inherit from the abstract base in `apps/core/models.py` (UUID PK, timestamps)
- Never query multi-tenant models without `.for_clinic(request.user.clinic)`
- API endpoints require authentication + RBAC check; public endpoints are the explicit exception

## PR Checklist

- [ ] Migrations included for schema changes
- [ ] Sensitive fields use `EncryptedField`
- [ ] New endpoints enforce RBAC (`apps/core/permissions.py`)
- [ ] No plaintext secrets in code or committed `.env`
- [ ] Tests cover the new/changed logic
- [ ] SATUSEHAT-affecting changes validated against FHIR R4 spec
- [ ] `docker-compose up` builds and `manage.py migrate` runs cleanly
