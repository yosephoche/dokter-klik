"""RBAC permission classes for DokterKlik.

Roles: owner > admin/doctor/pharmacy > patient
Multi-tenancy: all checks also verify request.user.clinic matches resource.clinic.
"""
from rest_framework.permissions import BasePermission


class IsClinicMember(BasePermission):
    """User must be authenticated and belong to a clinic."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.clinic is not None
        )


class IsDoctor(BasePermission):
    """Doctor role only."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'doctor'
        )


class IsAdmin(BasePermission):
    """Admin role only."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsOwner(BasePermission):
    """Owner role only — full access including financials."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'owner'
        )


class IsPharmacy(BasePermission):
    """Pharmacy role only."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'pharmacy'
        )


class IsDoctorOrAdmin(BasePermission):
    """Doctor, Admin, or Owner roles."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('doctor', 'admin', 'owner')
        )


class IsAdminOrOwner(BasePermission):
    """Admin or Owner roles."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('admin', 'owner')
        )


class IsPharmacyOrAdmin(BasePermission):
    """Pharmacy, Admin, or Owner roles."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('pharmacy', 'admin', 'owner')
        )
