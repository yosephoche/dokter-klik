"""Clinic model — anchor for multi-tenancy."""
import uuid
from django.db import models
from apps.core.encryption import EncryptedCharField


class Clinic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    subscription_plan = models.CharField(
        max_length=20,
        default='starter',
        choices=[('starter', 'Starter'), ('pro', 'Pro'), ('plus', 'Plus')]
    )
    # SATUSEHAT credentials (encrypted)
    satusehat_client_id = EncryptedCharField(max_length=200, blank=True, null=True)
    satusehat_client_secret = EncryptedCharField(max_length=200, blank=True, null=True)
    satusehat_org_id = models.CharField(max_length=100, blank=True)
    # WhatsApp credentials (encrypted)
    whatsapp_phone_number_id = models.CharField(max_length=100, blank=True)
    whatsapp_access_token = EncryptedCharField(max_length=500, blank=True, null=True)
    # Billing
    consultation_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clinics_clinic'
        verbose_name = 'Clinic'
        verbose_name_plural = 'Clinics'

    def __str__(self):
        return self.name


class DoctorSchedule(models.Model):
    """Weekly schedule for a doctor at a clinic."""
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='schedules')
    doctor = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.CASCADE, related_name='schedules'
    )
    day_of_week = models.IntegerField()  # 0=Monday, 6=Sunday
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_patients = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'clinics_doctorschedule'
        unique_together = [('clinic', 'doctor', 'day_of_week')]

    def __str__(self):
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        return f'{self.doctor} @ {self.clinic} — {days[self.day_of_week]}'
