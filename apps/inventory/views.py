"""Inventory views: Drug CRUD and stock management."""
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsPharmacyOrAdmin
from .models import Drug, StockMovement
from .serializers import DrugSerializer, StockMovementSerializer


class DrugListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsPharmacyOrAdmin]
    serializer_class = DrugSerializer

    def get_queryset(self):
        qs = Drug.objects.for_clinic(self.request.user.clinic).filter(is_active=True)
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(generic_name__icontains=q)
        return qs

    def perform_create(self, serializer):
        serializer.save(clinic=self.request.user.clinic)


class DrugDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsPharmacyOrAdmin]
    serializer_class = DrugSerializer

    def get_queryset(self):
        return Drug.objects.for_clinic(self.request.user.clinic)


class StockAdjustView(APIView):
    """POST to add/remove stock manually (restock, adjustment)."""
    permission_classes = [IsPharmacyOrAdmin]

    def post(self, request, pk):
        try:
            drug = Drug.objects.for_clinic(request.user.clinic).get(pk=pk)
        except Drug.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        qty = request.data.get('quantity', 0)
        movement_type = request.data.get('movement_type', 'in')
        notes = request.data.get('notes', '')

        try:
            qty = int(qty)
        except (ValueError, TypeError):
            return Response({'detail': 'quantity must be an integer.'}, status=400)

        with transaction.atomic():
            drug_locked = Drug.objects.select_for_update().get(pk=drug.pk)
            if movement_type in ('out', 'expired') and drug_locked.stock < abs(qty):
                return Response(
                    {'detail': f'Insufficient stock. Available: {drug_locked.stock}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if movement_type == 'in':
                drug_locked.stock += abs(qty)
            else:
                drug_locked.stock -= abs(qty)
            drug_locked.save(update_fields=['stock'])
            StockMovement.objects.create(
                drug=drug_locked,
                movement_type=movement_type,
                quantity=qty if movement_type == 'in' else -abs(qty),
                notes=notes,
                created_by=request.user,
            )

        return Response(DrugSerializer(drug_locked).data)
