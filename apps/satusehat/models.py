"""SATUSEHAT sync log model."""
from django.db import models
from apps.core.models import BaseModel


class SyncLog(BaseModel):
    """Records each attempt to sync a resource to SATUSEHAT."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='sync_logs'
    )
    resource_type = models.CharField(max_length=50)  # 'Encounter', 'Patient', etc.
    local_id = models.CharField(max_length=100, db_index=True)
    satusehat_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempt_count = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'satusehat_synclog'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['clinic', 'status']),
            models.Index(fields=['resource_type', 'local_id']),
        ]

    def __str__(self):
        return f'{self.resource_type} {self.local_id} — {self.status}'
