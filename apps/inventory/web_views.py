"""Inventory web/HTMX views: drug list page + HTMX partial."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

from .models import Drug


class DrugListPageView(LoginRequiredMixin, TemplateView):
    """Full drug/inventory list page shell. Data loaded via HTMX partial."""
    template_name = 'inventory/drug_list.html'


class DrugListPartialView(LoginRequiredMixin, View):
    """HTMX partial: returns HTML rows of drugs for the clinic."""

    def get(self, request):
        q = request.GET.get('q', '').strip()
        qs = Drug.objects.for_clinic(request.user.clinic).filter(is_active=True)
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(generic_name__icontains=q)
        drugs = qs.order_by('name')[:100]
        return render(request, 'inventory/partials/drug_rows.html', {'drugs': drugs})
