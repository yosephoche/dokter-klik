"""Shared model managers."""
from django.db import models


class ClinicScopedManager(models.Manager):
    """Manager that filters queryset by clinic. ALWAYS use for multi-tenant models."""

    def for_clinic(self, clinic):
        """Return queryset scoped to the given clinic."""
        return self.get_queryset().filter(clinic=clinic)
