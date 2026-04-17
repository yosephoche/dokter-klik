"""Queue management and public live view."""
import datetime
import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDoctorOrAdmin, IsAdminOrOwner
from apps.clinics.models import Clinic
from .models import QueueEntry
from .serializers import QueueEntrySerializer

logger = logging.getLogger(__name__)


class QueueListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrOwner]
    serializer_class = QueueEntrySerializer

    def get_queryset(self):
        clinic = self.request.user.clinic
        date_str = self.request.query_params.get('date')
        try:
            date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
        except ValueError:
            date = datetime.date.today()
        return QueueEntry.objects.filter(clinic=clinic, queue_date=date).order_by('queue_number')

    def perform_create(self, serializer):
        clinic = self.request.user.clinic
        next_num = QueueEntry.get_next_number(clinic)
        serializer.save(clinic=clinic, queue_number=next_num)


class QueueCallView(APIView):
    """PATCH: advance queue entry status and trigger WA notification if needed."""
    permission_classes = [IsAdminOrOwner]

    def patch(self, request, pk):
        try:
            entry = QueueEntry.objects.get(pk=pk, clinic=request.user.clinic)
        except QueueEntry.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        valid_transitions = {
            'waiting': ['called', 'skipped'],
            'called': ['serving', 'skipped'],
            'serving': ['done', 'skipped'],
            'skipped': ['called'],
        }
        allowed = valid_transitions.get(entry.status, [])
        if new_status not in allowed:
            return Response(
                {'detail': f'Cannot transition from {entry.status} to {new_status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()
        if new_status == 'called':
            entry.called_at = now
            self._maybe_send_queue_alert(entry)
        elif new_status == 'serving':
            entry.serving_at = now
        elif new_status == 'done':
            entry.done_at = now

        entry.status = new_status
        entry.save()
        return Response(QueueEntrySerializer(entry).data)

    def _maybe_send_queue_alert(self, called_entry):
        """Send WhatsApp alert to patients who are 3rd in line or fewer."""
        waiting = QueueEntry.objects.filter(
            clinic=called_entry.clinic,
            queue_date=called_entry.queue_date,
            status='waiting',
        ).order_by('queue_number')

        for i, entry in enumerate(waiting[:3]):
            if entry.patient and entry.patient.phone and not entry.notified_at:
                try:
                    from apps.whatsapp.tasks import send_queue_alert
                    send_queue_alert.delay(str(entry.id))
                except Exception:
                    logger.exception('Failed to queue WA alert for queue entry %s', entry.id)


class QueueLiveView(APIView):
    """Public live queue display page (no auth required)."""
    permission_classes = [AllowAny]

    def get(self, request, clinic_slug):
        clinic = get_object_or_404(Clinic, slug=clinic_slug, is_active=True)
        today = datetime.date.today()
        serving = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today, status='serving'
        ).first()
        called = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today, status='called'
        ).first()
        waiting_count = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today, status='waiting'
        ).count()

        context = {
            'clinic': clinic,
            'serving': serving,
            'called': called,
            'waiting_count': waiting_count,
        }
        from django.shortcuts import render
        return render(request, 'queue/display.html', context)


class QueueLivePartialView(APIView):
    """Public HTMX partial for live queue polling (no auth required)."""
    permission_classes = [AllowAny]

    def get(self, request, clinic_slug):
        clinic = get_object_or_404(Clinic, slug=clinic_slug, is_active=True)
        today = datetime.date.today()
        serving = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today, status='serving'
        ).first()
        called = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today, status='called'
        ).first()
        waiting_count = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today, status='waiting'
        ).count()

        context = {
            'clinic': clinic,
            'serving': serving,
            'called': called,
            'waiting_count': waiting_count,
        }
        from django.shortcuts import render
        return render(request, 'queue/partials/queue_board.html', context)
