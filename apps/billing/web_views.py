"""Billing web/HTMX views: invoice list page + detail page + HTMX partial."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from .models import Invoice


class InvoiceListPageView(LoginRequiredMixin, TemplateView):
    """Full invoice list page shell. Data loaded via HTMX partial."""
    template_name = 'billing/invoice_list.html'


class InvoiceListPartialView(LoginRequiredMixin, View):
    """HTMX partial: returns HTML rows of invoices for the clinic."""

    def get(self, request):
        invoices = Invoice.objects.filter(
            clinic=request.user.clinic
        ).select_related('visit__patient').order_by('-created_at')[:50]
        return render(request, 'billing/partials/invoice_rows.html',
                      {'invoices': invoices})


class InvoiceDetailPageView(LoginRequiredMixin, View):
    """Full invoice detail page with payment actions."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, clinic=request.user.clinic)
        return render(request, 'billing/invoice.html', {'invoice': invoice})
