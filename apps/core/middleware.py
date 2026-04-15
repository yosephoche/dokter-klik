"""Core middleware: audit logging and session timeout."""
import time
import logging
from django.conf import settings
from django.utils import timezone
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


class AuditLogMiddleware:
    """Log all accesses to sensitive API paths to AuditLog model."""

    AUDITED_PATHS = getattr(
        settings, 'AUDIT_LOG_PATHS',
        ['/api/patients/', '/api/visits/', '/api/invoices/']
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._maybe_log(request, response)
        return response

    def _maybe_log(self, request, response):
        if not any(request.path.startswith(p) for p in self.AUDITED_PATHS):
            return
        if not request.user or not request.user.is_authenticated:
            return
        try:
            from apps.core.audit_models import AuditLog
            clinic = getattr(request.user, 'clinic', None)
            AuditLog.objects.create(
                user=request.user,
                clinic=clinic,
                action=request.method,
                path=request.path,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception:
            logger.exception('Failed to write audit log')

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[-1].strip()
        return request.META.get('REMOTE_ADDR')


class SessionTimeoutMiddleware:
    """Automatically expire sessions after SESSION_TIMEOUT seconds of inactivity."""

    SESSION_TIMEOUT = getattr(settings, 'SESSION_TIMEOUT', 30 * 60)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            now = time.time()
            if last_activity and (now - last_activity) > self.SESSION_TIMEOUT:
                from django.contrib.auth import logout
                logout(request)
                if request.path.startswith('/api/'):
                    from django.http import JsonResponse
                    return JsonResponse(
                        {'detail': 'Session expired. Please login again.'},
                        status=401
                    )
                return redirect('/api/auth/login/')
            request.session['last_activity'] = now
        return self.get_response(request)
