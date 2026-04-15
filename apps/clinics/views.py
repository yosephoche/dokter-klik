"""Clinic management views."""
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Clinic, DoctorSchedule
from .serializers import ClinicSerializer, DoctorScheduleSerializer
from apps.core.permissions import IsOwner, IsAdminOrOwner


class ClinicDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ClinicSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        return self.request.user.clinic


class DoctorScheduleListView(generics.ListCreateAPIView):
    serializer_class = DoctorScheduleSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        return DoctorSchedule.objects.filter(clinic=self.request.user.clinic)

    def perform_create(self, serializer):
        serializer.save(clinic=self.request.user.clinic)
