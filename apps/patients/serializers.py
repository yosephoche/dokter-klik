from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    # Declare encrypted fields explicitly as CharField so DRF doesn't treat
    # them as BinaryField (which would attempt base64 encode/decode).
    name = serializers.CharField()
    nik = serializers.CharField(allow_blank=True, allow_null=True, required=False)

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
    name = serializers.CharField()

    class Meta:
        model = Patient
        fields = [
            'id', 'medical_record_number', 'name', 'dob', 'gender', 'phone',
        ]
