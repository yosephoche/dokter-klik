"""Dashboard web/HTMX views: stats partial for browser rendering."""
import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View


class DashboardStatsPartialView(LoginRequiredMixin, View):
    """HTMX partial: render stats cards as HTML (not JSON)."""

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

        stats = {
            'today': today,
            'queue_total': total_queue_today,
            'queue_served': served_today,
            'queue_waiting': waiting_today,
            'revenue_today': float(revenue_today),
            'total_patients': total_patients,
        }
        return render(request, 'dashboard/partials/stats_cards.html', {'stats': stats})
