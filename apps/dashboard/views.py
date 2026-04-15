"""Dashboard analytics views."""
import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.permissions import IsAdminOrOwner


class DashboardStatsView(APIView):
    """Clinic summary stats: today's patients, revenue, queue status."""
    permission_classes = [IsAdminOrOwner]

    def get(self, request):
        clinic = request.user.clinic
        today = datetime.date.today()

        from apps.queue.models import QueueEntry
        from apps.billing.models import Invoice
        from apps.patients.models import Patient
        from django.db.models import Sum

        total_queue_today = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today
        ).count()
        served_today = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today, status='done'
        ).count()
        waiting_today = QueueEntry.objects.filter(
            clinic=clinic, queue_date=today, status='waiting'
        ).count()

        revenue_today = Invoice.objects.filter(
            clinic=clinic,
            paid_at__date=today,
            payment_status='paid',
        ).aggregate(total=Sum('grand_total'))['total'] or 0

        total_patients = Patient.objects.for_clinic(clinic).count()

        return Response({
            'today': str(today),
            'queue': {
                'total': total_queue_today,
                'served': served_today,
                'waiting': waiting_today,
            },
            'revenue_today': float(revenue_today),
            'total_patients': total_patients,
        })
