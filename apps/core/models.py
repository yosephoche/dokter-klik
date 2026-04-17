"""Abstract base model for all DokterKlik models."""
import uuid
from django.db import models
from apps.core.audit_models import AuditLog  # noqa: F401 — expose to Django migrations


class BaseModel(models.Model):
    """Abstract base with UUID primary key and timestamps."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
