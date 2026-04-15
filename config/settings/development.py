"""Development settings."""
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['*']

# Console email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable HTTPS requirements in dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# DRF: allow browsable API in dev
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# CORS allow all in dev
CORS_ALLOW_ALL_ORIGINS = True

# Local file storage override for dev (skip MinIO if not available)
import os
if not os.environ.get('USE_MINIO'):
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
