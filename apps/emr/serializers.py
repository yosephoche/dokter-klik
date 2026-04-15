from rest_framework import serializers
from .models import Visit, Diagnosis, Prescription, ICD10Code, EMRTemplate


class ICD10Serializer(serializers.ModelSerializer):
    class Meta:
        model = ICD10Code
        fields = ['code', 'description_en', 'description_id', 'is_billable']


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = [
            'id', 'icd10_code', 'icd10_description_en', 'icd10_description_id',
            'is_primary', 'clinical_notes',
        ]
        read_only_fields = ['id']


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = [
            'id', 'drug', 'drug_name', 'quantity', 'unit',
            'dosage_instruction', 'duration_days', 'status',
        ]
        read_only_fields = ['id', 'status']


class VisitSerializer(serializers.ModelSerializer):
    diagnoses = DiagnosisSerializer(many=True, read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = Visit
        fields = [
            'id', 'patient', 'doctor', 'visit_date', 'status',
            'chief_complaint', 'soap_subjective', 'soap_objective',
            'soap_assessment_notes', 'soap_plan_notes',
            'last_autosave', 'finalized_at',
            'diagnoses', 'prescriptions',
        ]
        read_only_fields = ['id', 'visit_date', 'status', 'finalized_at', 'doctor']


class VisitAutosaveSerializer(serializers.ModelSerializer):
    """Minimal serializer for autosave PATCH — only SOAP fields."""
    class Meta:
        model = Visit
        fields = [
            'chief_complaint', 'soap_subjective', 'soap_objective',
            'soap_assessment_notes', 'soap_plan_notes',
        ]
