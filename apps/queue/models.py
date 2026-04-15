"""Queue model for real-time patient queue management."""
import datetime
from django.db import models
from django.db.models import Max
from apps.core.models import BaseModel


class QueueEntry(BaseModel):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('called', 'Called'),
        ('serving', 'Serving'),
        ('done', 'Done'),
        ('skipped', 'Skipped'),
    ]
    SOURCE_CHOICES = [
        ('walkin', 'Walk-in'),
        ('whatsapp', 'WhatsApp'),
        ('online', 'Online'),
    ]

    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='queue_entries'
    )
    patient = models.ForeignKey(
        'patients.Patient', null=True, blank=True, on_delete=models.SET_NULL
    )
    doctor = models.ForeignKey(
        'accounts.CustomUser', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='queue_entries'
    )
    queue_number = models.IntegerField()
    queue_date = models.DateField(default=datetime.date.today)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='walkin')
    called_at = models.DateTimeField(null=True, blank=True)
    serving_at = models.DateTimeField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'queue_queueentry'
        unique_together = [('clinic', 'queue_date', 'queue_number')]
        ordering = ['queue_number']

    def __str__(self):
        return f'Queue #{self.queue_number} — {self.clinic} ({self.status})'

    @classmethod
    def get_next_number(cls, clinic, date=None) -> int:
        """Get the next queue number for a clinic on a given date."""
        if date is None:
            date = datetime.date.today()
        result = cls.objects.filter(
            clinic=clinic, queue_date=date
        ).aggregate(Max('queue_number'))
        return (result['queue_number__max'] or 0) + 1
