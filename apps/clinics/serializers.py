from rest_framework import serializers
from .models import Clinic, DoctorSchedule


class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = [
            'id', 'name', 'slug', 'address', 'phone', 'email',
            'subscription_plan', 'satusehat_org_id',
            'whatsapp_phone_number_id', 'consultation_fee',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class DoctorScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = [
            'id', 'clinic', 'doctor', 'day_of_week',
            'start_time', 'end_time', 'max_patients', 'is_active'
        ]
        read_only_fields = ['id', 'clinic']
