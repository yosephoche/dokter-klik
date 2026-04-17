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

    @classmethod
    def create_for_clinic(cls, clinic, patient=None, doctor=None, source='walkin'):
        """Atomically assign the next queue number and create an entry.

        Uses SELECT FOR UPDATE to prevent concurrent numbering races.
        Retries up to 3 times on IntegrityError before raising.
        """
        from django.db import IntegrityError, transaction

        today = datetime.date.today()
        for attempt in range(3):
            try:
                with transaction.atomic():
                    agg = cls.objects.select_for_update().filter(
                        clinic=clinic, queue_date=today
                    ).aggregate(Max('queue_number'))
                    next_number = (agg['queue_number__max'] or 0) + 1
                    return cls.objects.create(
                        clinic=clinic,
                        patient=patient,
                        doctor=doctor,
                        queue_number=next_number,
                        source=source,
                        status='waiting',
                    )
            except IntegrityError:
                if attempt == 2:
                    raise
