"""EMR models: ICD10Code, Visit, Diagnosis, Prescription, EMRTemplate."""
from django.db import models
from apps.core.models import BaseModel
from apps.core.managers import ClinicScopedManager
from apps.core.encryption import EncryptedTextField


class ICD10Code(models.Model):
    """ICD-10 code catalogue. SERIAL PK for import performance."""
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=10, unique=True, db_index=True)
    description_en = models.CharField(max_length=500)
    description_id = models.CharField(max_length=500, blank=True)
    chapter = models.CharField(max_length=10, blank=True)
    block = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=10, blank=True)
    is_billable = models.BooleanField(default=True)

    class Meta:
        db_table = 'emr_icd10code'

    def __str__(self):
        return f'{self.code} — {self.description_en}'


class Visit(BaseModel):
    """SOAP-based clinical encounter."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('finalized', 'Finalized'),
    ]

    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.PROTECT, related_name='visits'
    )
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.PROTECT, related_name='visits'
    )
    doctor = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.PROTECT, related_name='visits'
    )
    visit_date = models.DateTimeField(auto_now_add=True)
    chief_complaint = EncryptedTextField(blank=True, null=True)
    soap_subjective = EncryptedTextField(blank=True, null=True)
    soap_objective = EncryptedTextField(blank=True, null=True)
    soap_assessment_notes = EncryptedTextField(blank=True, null=True)
    soap_plan_notes = EncryptedTextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    finalized_at = models.DateTimeField(null=True, blank=True)
    satusehat_encounter_id = models.CharField(max_length=100, blank=True)
    last_autosave = models.DateTimeField(null=True, blank=True)

    objects = ClinicScopedManager()

    class Meta:
        db_table = 'emr_visit'
        ordering = ['-visit_date']

    def __str__(self):
        return f'Visit {self.id} — {self.patient} ({self.status})'


class Diagnosis(BaseModel):
    """ICD-10 diagnosis attached to a visit."""
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='diagnoses')
    icd10_code = models.CharField(max_length=10)
    icd10_description_en = models.CharField(max_length=500, blank=True)
    icd10_description_id = models.CharField(max_length=500, blank=True)
    is_primary = models.BooleanField(default=False)
    clinical_notes = models.TextField(blank=True)
    satusehat_condition_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'emr_diagnosis'

    def __str__(self):
        return f'{self.icd10_code} ({self.visit_id})'


class Prescription(BaseModel):
    """Drug prescription attached to a visit."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('dispensed', 'Dispensed'),
        ('cancelled', 'Cancelled'),
    ]

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='prescriptions')
    drug = models.ForeignKey(
        'inventory.Drug', null=True, blank=True, on_delete=models.SET_NULL
    )
    drug_name = models.CharField(max_length=255)  # snapshot at time of prescription
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    dosage_instruction = models.TextField()
    duration_days = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    dispensed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'emr_prescription'

    def __str__(self):
        return f'{self.drug_name} x{self.quantity}{self.unit}'


class EMRTemplate(BaseModel):
    """Reusable SOAP templates per clinic/doctor."""
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='emr_templates'
    )
    created_by = models.ForeignKey(
        'accounts.CustomUser', null=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=100, blank=True)
    template_subjective = models.TextField(blank=True)
    template_objective = models.TextField(blank=True)
    template_assessment = models.TextField(blank=True)
    template_plan = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'emr_emrtemplate'

    def __str__(self):
        return f'{self.name} ({self.specialty})'
