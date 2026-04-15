"""Patient model — NIK and name encrypted at-rest."""
from django.db import models
from apps.core.models import BaseModel
from apps.core.managers import ClinicScopedManager
from apps.core.encryption import EncryptedCharField


class Patient(BaseModel):
    """
    Multi-tenant patient record. NIK and name stored encrypted (Fernet/BYTEA).

    SEARCH NOTE: Use name_search (plaintext lowercase) for ORM filtering.
    Direct filter on name/nik is not possible (ciphertext differs per encrypt).
    """
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='patients'
    )
    medical_record_number = models.CharField(max_length=20, db_index=True)
    nik = EncryptedCharField(max_length=16, blank=True, null=True)
    name = EncryptedCharField(max_length=255)
    # Plaintext lowercase copy for ORM search — NOT for display
    name_search = models.CharField(max_length=255, db_index=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    )
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    blood_type = models.CharField(max_length=5, blank=True)
    allergy_notes = models.TextField(blank=True)
    satusehat_patient_id = models.CharField(max_length=100, blank=True)

    objects = ClinicScopedManager()

    class Meta:
        db_table = 'patients_patient'
        unique_together = [('clinic', 'medical_record_number')]
        ordering = ['name_search']

    def __str__(self):
        return f'{self.medical_record_number} — {self.name_search}'

    def save(self, *args, **kwargs):
        # Populate name_search from plain name before saving
        # name may be a plaintext string (pre-encryption) when coming from a form
        if isinstance(self.name, str) and self.name:
            self.name_search = self.name.lower()
        super().save(*args, **kwargs)

    @classmethod
    def generate_mrn(cls, clinic) -> str:
        """Generate next medical record number for the clinic."""
        import datetime
        prefix = f'MR{datetime.date.today().strftime("%Y%m")}'
        last = cls.objects.for_clinic(clinic).filter(
            medical_record_number__startswith=prefix
        ).order_by('-medical_record_number').first()
        if last:
            try:
                seq = int(last.medical_record_number[len(prefix):]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f'{prefix}{seq:04d}'
