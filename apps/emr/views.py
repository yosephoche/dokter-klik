"""EMR views: ICD-10 search, SOAP CRUD, autosave, finalize."""
import logging
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.core.permissions import IsDoctorOrAdmin, IsDoctor
from .models import Visit, Diagnosis, Prescription, ICD10Code
from .serializers import (
    VisitSerializer, VisitAutosaveSerializer,
    DiagnosisSerializer, PrescriptionSerializer, ICD10Serializer,
)

logger = logging.getLogger(__name__)


class ICD10SearchView(APIView):
    """Fast ICD-10 autocomplete using pg_trgm GIN index. < 500ms SLA."""
    throttle_classes = [UserRateThrottle]
    throttle_scope = 'icd10'

    def get(self, request):
        q = request.GET.get('q', '').strip()
        lang = request.GET.get('lang', 'id')
        if len(q) < 2:
            return Response([])

        qs = ICD10Code.objects.filter(is_billable=True)
        # If query looks like a code prefix (letter + up to 4 chars), search by code
        if q[0].isalpha() and len(q) <= 5:
            qs = qs.filter(code__istartswith=q.upper())
        else:
            search_field = 'description_id' if lang == 'id' else 'description_en'
            qs = qs.filter(**{f'{search_field}__icontains': q})

        return Response(ICD10Serializer(qs[:20], many=True).data)


class VisitListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsDoctorOrAdmin]
    serializer_class = VisitSerializer

    def get_queryset(self):
        qs = Visit.objects.for_clinic(self.request.user.clinic).select_related(
            'patient', 'doctor'
        )
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            clinic=self.request.user.clinic,
            doctor=self.request.user,
        )


class VisitDetailView(generics.RetrieveAPIView):
    permission_classes = [IsDoctorOrAdmin]
    serializer_class = VisitSerializer

    def get_queryset(self):
        return Visit.objects.for_clinic(self.request.user.clinic)


class VisitAutosaveView(APIView):
    """PATCH endpoint for autosave — only updates SOAP fields."""
    permission_classes = [IsDoctorOrAdmin]

    def patch(self, request, pk):
        try:
            visit = Visit.objects.for_clinic(request.user.clinic).get(pk=pk)
        except Visit.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if visit.status == 'finalized':
            raise PermissionDenied('Cannot edit a finalized visit.')

        serializer = VisitAutosaveSerializer(visit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(last_autosave=timezone.now())
        return Response({'last_autosave': visit.last_autosave})


class VisitFinalizeView(APIView):
    """POST to finalize a visit: validate ICD-10, create invoice, queue SATUSEHAT sync."""
    permission_classes = [IsDoctorOrAdmin]

    def post(self, request, pk):
        try:
            visit = Visit.objects.for_clinic(request.user.clinic).prefetch_related(
                'diagnoses', 'prescriptions__drug'
            ).get(pk=pk)
        except Visit.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if visit.status == 'finalized':
            return Response(VisitSerializer(visit).data)  # idempotent

        if not visit.diagnoses.exists():
            raise ValidationError({'diagnoses': 'At least one diagnosis is required to finalize.'})

        if not visit.diagnoses.filter(is_primary=True).exists():
            raise ValidationError({'diagnoses': 'A primary diagnosis must be set.'})

        # Finalize
        visit.status = 'finalized'
        visit.finalized_at = timezone.now()
        visit.save(update_fields=['status', 'finalized_at', 'updated_at'])

        # Decrement stock for prescriptions (atomic)
        self._dispense_prescriptions(visit)

        # Create invoice
        self._create_invoice(visit)

        # Queue SATUSEHAT sync (async)
        try:
            from apps.satusehat.tasks import sync_encounter_to_satusehat
            sync_encounter_to_satusehat.delay(str(visit.id))
        except Exception:
            logger.exception('Failed to queue SATUSEHAT sync for visit %s', visit.id)

        return Response(VisitSerializer(visit).data)

    def _dispense_prescriptions(self, visit):
        from django.db import transaction
        from apps.inventory.models import Drug, StockMovement

        for rx in visit.prescriptions.filter(status='pending'):
            if not rx.drug_id:
                continue
            with transaction.atomic():
                drug = Drug.objects.select_for_update().get(pk=rx.drug_id)
                qty = int(rx.quantity)
                if drug.stock < qty:
                    raise ValidationError(
                        f'Insufficient stock for {drug.name}: {drug.stock} available, '
                        f'{qty} requested.'
                    )
                drug.stock -= qty
                drug.save(update_fields=['stock'])
                StockMovement.objects.create(
                    drug=drug,
                    movement_type='out',
                    quantity=-qty,
                    reference_type='prescription',
                    reference_id=rx.id,
                    created_by=self.request.user,
                )
            rx.status = 'dispensed'
            rx.dispensed_at = timezone.now()
            rx.save(update_fields=['status', 'dispensed_at', 'updated_at'])

    def _create_invoice(self, visit):
        from apps.billing.models import Invoice
        from django.db.models import Sum
        import datetime

        if hasattr(visit, 'invoice'):
            return  # already exists

        # Calculate totals
        consultation_fee = visit.clinic.consultation_fee
        drug_total = sum(
            (rx.drug.sell_price * rx.quantity)
            for rx in visit.prescriptions.filter(status='dispensed')
            if rx.drug
        )

        # Generate invoice number: INV-{YYYYMM}-{seq:04d}
        prefix = f'INV-{datetime.date.today().strftime("%Y%m")}-'
        last = Invoice.objects.filter(
            clinic=visit.clinic,
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').first()
        seq = 1
        if last:
            try:
                seq = int(last.invoice_number[len(prefix):]) + 1
            except ValueError:
                seq = 1

        grand_total = consultation_fee + drug_total
        Invoice.objects.create(
            visit=visit,
            clinic=visit.clinic,
            invoice_number=f'{prefix}{seq:04d}',
            total_consultation=consultation_fee,
            total_drugs=drug_total,
            grand_total=grand_total,
        )


class DiagnosisListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsDoctorOrAdmin]
    serializer_class = DiagnosisSerializer

    def get_queryset(self):
        visit = self._get_visit()
        return Diagnosis.objects.filter(visit=visit)

    def _get_visit(self):
        visit_pk = self.kwargs['visit_pk']
        try:
            return Visit.objects.for_clinic(self.request.user.clinic).get(pk=visit_pk)
        except Visit.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound()

    def perform_create(self, serializer):
        visit = self._get_visit()
        if visit.status == 'finalized':
            raise PermissionDenied('Cannot add diagnosis to a finalized visit.')
        serializer.save(visit=visit)


class PrescriptionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsDoctorOrAdmin]
    serializer_class = PrescriptionSerializer

    def get_queryset(self):
        visit_pk = self.kwargs['visit_pk']
        return Prescription.objects.filter(
            visit__clinic=self.request.user.clinic,
            visit_id=visit_pk,
        )

    def perform_create(self, serializer):
        visit_pk = self.kwargs['visit_pk']
        try:
            visit = Visit.objects.for_clinic(self.request.user.clinic).get(pk=visit_pk)
        except Visit.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound()
        if visit.status == 'finalized':
            raise PermissionDenied('Cannot add prescription to a finalized visit.')
        serializer.save(visit=visit)
