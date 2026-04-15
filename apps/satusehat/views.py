"""SATUSEHAT dashboard views: monitoring sync status."""
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.permissions import IsAdminOrOwner
from .models import SyncLog
from .serializers import SyncLogSerializer


class SyncLogListView(generics.ListAPIView):
    permission_classes = [IsAdminOrOwner]
    serializer_class = SyncLogSerializer

    def get_queryset(self):
        qs = SyncLog.objects.filter(clinic=self.request.user.clinic)
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs[:100]


class SyncStatsView(APIView):
    permission_classes = [IsAdminOrOwner]

    def get(self, request):
        clinic = request.user.clinic
        total = SyncLog.objects.filter(clinic=clinic).count()
        success = SyncLog.objects.filter(clinic=clinic, status='success').count()
        failed = SyncLog.objects.filter(clinic=clinic, status='failed').count()
        pending = SyncLog.objects.filter(clinic=clinic, status='pending').count()
        return Response({
            'total': total,
            'success': success,
            'failed': failed,
            'pending': pending,
            'success_rate': round(success / total * 100, 1) if total else 0,
        })


class ManualResyncView(APIView):
    """POST to manually trigger re-sync of a failed encounter."""
    permission_classes = [IsAdminOrOwner]

    def post(self, request, pk):
        try:
            log = SyncLog.objects.get(pk=pk, clinic=request.user.clinic)
        except SyncLog.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)

        from .tasks import sync_encounter_to_satusehat
        sync_encounter_to_satusehat.delay(log.local_id)
        log.status = 'pending'
        log.save(update_fields=['status', 'updated_at'])
        return Response({'detail': 'Resync queued.'})
