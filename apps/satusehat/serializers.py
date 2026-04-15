from rest_framework import serializers
from .models import SyncLog


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = [
            'id', 'resource_type', 'local_id', 'satusehat_id',
            'status', 'attempt_count', 'last_attempt_at', 'error_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
