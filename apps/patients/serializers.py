from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'id', 'medical_record_number', 'name', 'nik', 'dob', 'gender',
            'phone', 'address', 'blood_type', 'allergy_notes',
            'satusehat_patient_id', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'medical_record_number', 'satusehat_patient_id',
                            'created_at', 'updated_at']


class PatientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/search views."""
    class Meta:
        model = Patient
        fields = [
            'id', 'medical_record_number', 'name', 'dob', 'gender', 'phone',
        ]
