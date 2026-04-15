"""Patient CRUD and search views."""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.permissions import IsDoctorOrAdmin, IsAdminOrOwner
from .models import Patient
from .serializers import PatientSerializer, PatientListSerializer


class PatientListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsDoctorOrAdmin]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return PatientListSerializer
        return PatientSerializer

    def get_queryset(self):
        clinic = self.request.user.clinic
        qs = Patient.objects.for_clinic(clinic)
        q = self.request.query_params.get('q', '').strip()
        if q:
            # Search by name (plaintext index) or medical record number
            qs = qs.filter(name_search__icontains=q) | qs.filter(
                medical_record_number__istartswith=q
            )
        return qs.order_by('name_search')

    def perform_create(self, serializer):
        clinic = self.request.user.clinic
        mrn = Patient.generate_mrn(clinic)
        plain_name = serializer.validated_data.get('name', '')
        serializer.save(
            clinic=clinic,
            medical_record_number=mrn,
            name_search=plain_name.lower() if plain_name else '',
        )


class PatientDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsDoctorOrAdmin]
    serializer_class = PatientSerializer

    def get_queryset(self):
        return Patient.objects.for_clinic(self.request.user.clinic)

    def perform_update(self, serializer):
        plain_name = serializer.validated_data.get('name', '')
        if plain_name:
            serializer.save(name_search=plain_name.lower())
        else:
            serializer.save()
