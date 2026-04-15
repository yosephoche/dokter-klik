"""AuditLog model — BigSerial PK (high-volume writes, no UUID overhead)."""
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """Records every access to sensitive medical data.

    Retention: minimum 5 years (per PMK No. 24/2022).
    BigAutoField PK for write performance on high-volume inserts.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    clinic = models.ForeignKey(
        'clinics.Clinic',
        null=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=10)           # GET, POST, PATCH, DELETE
    path = models.CharField(max_length=500)
    resource_type = models.CharField(max_length=100, blank=True)  # Patient, Visit, etc.
    resource_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'core_auditlog'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['clinic', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.action} {self.path} by {self.user_id} at {self.timestamp}'
