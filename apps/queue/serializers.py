from rest_framework import serializers
from .models import QueueEntry


class QueueEntrySerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.name_search', read_only=True)

    class Meta:
        model = QueueEntry
        fields = [
            'id', 'queue_number', 'queue_date', 'status', 'source',
            'patient', 'patient_name', 'doctor',
            'called_at', 'serving_at', 'done_at', 'notified_at', 'notes',
            'created_at',
        ]
        read_only_fields = [
            'id', 'queue_number', 'queue_date', 'called_at',
            'serving_at', 'done_at', 'notified_at', 'created_at',
        ]
